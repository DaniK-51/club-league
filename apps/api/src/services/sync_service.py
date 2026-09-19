"""Sync debouncer (1h) + rating aggregation for Yandex Disk export."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.config import get_settings
from src.core.database import get_session_factory
from src.models.entities import Report
from src.models.enums import ReportStatus
from src.schemas.rules import CombinedCapConfig
from src.services.caps import apply_combined_cap
from src.services.global_rules import load_combined_caps
from src.services.period_service import resolve_rating_window
from src.services.periods import month_key
from src.services.rating_caps import apply_monthly_caps, load_monthly_caps
from src.services.yandex_sheets import SheetsWriter, build_client

logger = logging.getLogger(__name__)

# Archived included so historical ratings stay stable after period archive.
_RATING_STATUSES = (ReportStatus.COMPLETED, ReportStatus.ARCHIVED)


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
            logger.exception("debounced sync failed")

    async def flush(self, writer: SheetsWriter | None = None) -> list[ClubTotal]:
        self._pending = False
        settings = get_settings()
        factory = get_session_factory()
        writer = writer or build_client()
        try:
            async with factory() as session:
                totals = await compute_rating(session)
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


def _report_points(report: Report) -> int:
    if report.final_points is not None:
        return int(report.final_points)
    return int(report.calculated_points or 0)


def _aggregate_totals(
    reports: Iterable[Report],
    *,
    monthly_caps: dict[str, int],
    g1_list: list[CombinedCapConfig],
) -> list[ClubTotal]:
    nested: dict[str, dict[str, dict[str, int]]] = {}
    names: dict[str, str] = {}
    for report in reports:
        if not report.club or not report.criteria:
            continue
        points = _report_points(report)
        mkey = month_key(report.activity_date)
        code = report.criteria.code
        month_map = nested.setdefault(report.club_id, {}).setdefault(mkey, {})
        month_map[code] = month_map.get(code, 0) + points
        names[report.club_id] = report.club.name

    totals: list[ClubTotal] = []
    for club_id, by_month in nested.items():
        period_breakdown: dict[str, int] = {}
        for month_points in by_month.values():
            # Monthly caps AND G1 combined_cap are per-month (catalog).
            capped_month = apply_monthly_caps(month_points, monthly_caps)
            for g1 in g1_list:
                capped_month = apply_combined_cap(capped_month, g1)
            for code, pts in capped_month.items():
                period_breakdown[code] = period_breakdown.get(code, 0) + pts
        totals.append(
            ClubTotal(
                club_id=club_id,
                club_name=names.get(club_id, club_id),
                total_points=sum(period_breakdown.values()),
                breakdown=period_breakdown,
            )
        )
    totals.sort(key=lambda item: (-item.total_points, item.club_name))
    return totals


async def compute_rating(
    session: AsyncSession,
    *,
    semester: str | None = None,
    period_name: str | None = None,
) -> list[ClubTotal]:
    """COMPLETED + ARCHIVED for period/semester window; monthly caps; then G1."""
    start, end, period_label = await resolve_rating_window(
        session, period_name=period_name, semester=semester
    )

    query = (
        select(Report)
        .options(selectinload(Report.club), selectinload(Report.criteria))
        .where(
            Report.status.in_(_RATING_STATUSES),
            Report.is_deleted.is_(False),
        )
    )
    if start is not None and end is not None:
        query = query.where(Report.activity_date >= start, Report.activity_date < end)

    result = await session.execute(query)
    reports = list(result.scalars().all())

    monthly_caps = await load_monthly_caps(session, semester=period_label)
    g1_list = await load_combined_caps(session, semester=period_label)
    return _aggregate_totals(reports, monthly_caps=monthly_caps, g1_list=g1_list)


debouncer = SyncDebouncer()
