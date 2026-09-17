"""Sync debouncer (1h) + rating aggregation for Yandex Disk export."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.config import get_settings
from src.core.database import get_session_factory
from src.models.entities import Report
from src.models.enums import ReportStatus
from src.services.caps import apply_combined_cap
from src.services.global_rules import load_combined_caps
from src.services.periods import month_key, semester_range
from src.services.rating_caps import apply_monthly_caps, load_monthly_caps
from src.services.yandex_sheets import SheetsWriter, build_client

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClubTotal:
    club_id: str
    club_name: str
    total_points: int
    breakdown: dict[str, int] = field(default_factory=dict)


class SyncDebouncer:
    """Coalesce rating sync requests into one run after quiet period."""

    def __init__(self, *, debounce_seconds: int | None = None) -> None:
        settings = get_settings()
        self._debounce_seconds = (
            debounce_seconds if debounce_seconds is not None else settings.sync_debounce_seconds
        )
        self._task: asyncio.Task[None] | None = None
        self._pending = False
        self.last_run_at: datetime | None = None
        self.last_error: str | None = None
        self.run_count = 0

    @property
    def pending(self) -> bool:
        return self._pending

    def notify(self) -> None:
        self._pending = True
        if self._task is not None and not self._task.done():
            self._task.cancel()
        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self._run_after_debounce())

    def notify_immediate(self) -> None:
        self._pending = True
        if self._task is not None and not self._task.done():
            self._task.cancel()
        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self._run_after_debounce(0))

    async def _run_after_debounce(self, delay: float | None = None) -> None:
        try:
            await asyncio.sleep(self._debounce_seconds if delay is None else delay)
        except asyncio.CancelledError:
            return
        try:
            await self.flush()
        except Exception:
            # last_error already set in flush; keep debouncer alive
            logger.exception("debounced sync failed")

    async def flush(self, writer: SheetsWriter | None = None) -> list[ClubTotal]:
        self._pending = False
        settings = get_settings()
        factory = get_session_factory()
        writer = writer or build_client()
        try:
            async with factory() as session:
                totals = await compute_rating(session, semester=settings.current_semester)
                rows = _totals_to_rows(totals, semester=settings.current_semester)
                await writer.write_rows(rows)
            self.last_run_at = datetime.now(UTC)
            self.last_error = None
            self.run_count += 1
            logger.info("Yandex sync completed clubs=%s", len(totals))
            return totals
        except Exception as exc:
            self.last_error = str(exc)
            logger.exception("Yandex sync failed")
            raise

    def cancel(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()
        self._task = None
        self._pending = False


def _totals_to_rows(totals: list[ClubTotal], *, semester: str) -> list[list[object]]:
    rows: list[list[object]] = [["Rank", "Club", "Total", "Semester", "Breakdown"]]
    for rank, item in enumerate(totals, start=1):
        breakdown = ", ".join(
            f"{code}={pts}" for code, pts in sorted(item.breakdown.items()) if pts
        )
        rows.append([rank, item.club_name, item.total_points, semester, breakdown])
    return rows


async def compute_rating(session: AsyncSession, *, semester: str) -> list[ClubTotal]:
    """COMPLETED reports for semester; monthly caps per month; then G1 from DB."""
    rng = semester_range(semester)
    query = (
        select(Report)
        .options(selectinload(Report.club), selectinload(Report.criteria))
        .where(
            Report.status == ReportStatus.COMPLETED,
            Report.is_deleted.is_(False),
        )
    )
    if rng is not None:
        start, end = rng
        query = query.where(Report.activity_date >= start, Report.activity_date < end)

    result = await session.execute(query)
    reports = list(result.scalars().all())

    monthly_caps = await load_monthly_caps(session, semester=semester)
    g1_list = await load_combined_caps(session, semester=semester)

    # club → month → criteria → points
    nested: dict[str, dict[str, dict[str, int]]] = {}
    names: dict[str, str] = {}
    for report in reports:
        if not report.club or not report.criteria:
            continue
        points = (
            report.final_points
            if report.final_points is not None
            else (report.calculated_points or 0)
        )
        mkey = month_key(report.activity_date)
        code = report.criteria.code
        nested.setdefault(report.club_id, {}).setdefault(mkey, {})
        month_map = nested[report.club_id][mkey]
        month_map[code] = month_map.get(code, 0) + int(points)
        names[report.club_id] = report.club.name

    totals: list[ClubTotal] = []
    for club_id, by_month in nested.items():
        semester_breakdown: dict[str, int] = {}
        for _mkey, month_points in by_month.items():
            # Monthly caps AND G1 combined_cap are per-month (catalog: monthly aggregate)
            capped_month = apply_monthly_caps(month_points, monthly_caps)
            for g1 in g1_list:
                capped_month = apply_combined_cap(capped_month, g1)
            for code, pts in capped_month.items():
                semester_breakdown[code] = semester_breakdown.get(code, 0) + pts
        totals.append(
            ClubTotal(
                club_id=club_id,
                club_name=names.get(club_id, club_id),
                total_points=sum(semester_breakdown.values()),
                breakdown=semester_breakdown,
            )
        )
    totals.sort(key=lambda item: (-item.total_points, item.club_name))
    return totals


debouncer = SyncDebouncer()
