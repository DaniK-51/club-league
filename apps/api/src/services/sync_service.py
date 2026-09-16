"""Sync debouncer (1h) + rating aggregation for Yandex Sheets export."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.config import get_settings
from src.core.database import get_session_factory
from src.models.entities import Report
from src.models.enums import ReportStatus
from src.services.caps import CombinedCapConfig, apply_combined_cap
from src.services.yandex_sheets import SheetsWriter, build_client

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClubTotal:
    club_id: str
    club_name: str
    total_points: int
    breakdown: dict[str, int]


class SyncDebouncer:
    """Coalesce rating sync requests into one run after quiet period."""

    def __init__(self, *, debounce_seconds: int | None = None) -> None:
        settings = get_settings()
        self._debounce_seconds = (
            debounce_seconds
            if debounce_seconds is not None
            else settings.sync_debounce_seconds
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
        """Schedule a sync after debounce window (resets timer on each call)."""
        self._pending = True
        if self._task is not None and not self._task.done():
            self._task.cancel()
        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self._run_after_debounce())

    async def _run_after_debounce(self) -> None:
        try:
            await asyncio.sleep(self._debounce_seconds)
        except asyncio.CancelledError:
            return
        await self.flush()

    async def flush(self, writer: SheetsWriter | None = None) -> list[ClubTotal]:
        """Run sync immediately (ignores debounce). Returns club totals."""
        self._pending = False
        settings = get_settings()
        factory = get_session_factory()
        writer = writer or build_client()
        try:
            async with factory() as session:
                totals = await compute_rating(session, semester=settings.current_semester)
                rows = _totals_to_rows(totals)
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


def _totals_to_rows(totals: list[ClubTotal]) -> list[list[object]]:
    """Sheet layout: rank, club, total, then top criteria breakdown."""
    rows: list[list[object]] = [["Rank", "Club", "Total", "Semester", "Breakdown"]]
    semester = get_settings().current_semester
    for rank, item in enumerate(totals, start=1):
        breakdown = ", ".join(
            f"{code}={pts}" for code, pts in sorted(item.breakdown.items()) if pts
        )
        rows.append([rank, item.club_name, item.total_points, semester, breakdown])
    return rows


async def compute_rating(session: AsyncSession, *, semester: str) -> list[ClubTotal]:
    """Sum final_points of COMPLETED reports per club; apply G1 combined cap.

    `semester` is reserved for RulesVersion filtering; currently all COMPLETED count.
    """
    result = await session.execute(
        select(Report)
        .options(selectinload(Report.club), selectinload(Report.criteria))
        .where(
            Report.status == ReportStatus.COMPLETED,
            Report.is_deleted.is_(False),
        )
    )
    reports = list(result.scalars().all())

    by_club: dict[str, dict[str, int]] = {}
    names: dict[str, str] = {}
    for report in reports:
        if not report.club or not report.criteria:
            continue
        points = (
            report.final_points
            if report.final_points is not None
            else (report.calculated_points or 0)
        )
        by_club.setdefault(report.club_id, {})
        code = report.criteria.code
        by_club[report.club_id][code] = by_club[report.club_id].get(code, 0) + int(points)
        names[report.club_id] = report.club.name

    cap = CombinedCapConfig(
        criteria_codes=["C4", "C5"],
        max_percent_of_total_monthly=15,
    )

    totals: list[ClubTotal] = []
    for club_id, breakdown in by_club.items():
        capped = apply_combined_cap(breakdown, cap)
        totals.append(
            ClubTotal(
                club_id=club_id,
                club_name=names.get(club_id, club_id),
                total_points=sum(capped.values()),
                breakdown=capped,
            )
        )
    totals.sort(key=lambda item: (-item.total_points, item.club_name))
    return totals


# Process-wide debouncer (single worker per API process).
debouncer = SyncDebouncer()
