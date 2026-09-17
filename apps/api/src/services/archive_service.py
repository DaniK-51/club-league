"""Batch archive COMPLETED/CLOSED reports (state machine → ARCHIVED)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.config import get_settings
from src.core.errors import api_error
from src.models.entities import ArchiveBatch, Report, User
from src.models.enums import ReportStatus, UserRole
from src.policies.common import ensure_moderator
from src.schemas.common import ErrorCode
from src.services.audit_service import AuditService
from src.services.periods import semester_range


def _now() -> datetime:
    return datetime.now(UTC)


async def archive_period(
    session: AsyncSession, *, user: User, period: str | None = None
) -> ArchiveBatch:
    """Move COMPLETED/CLOSED reports of the period to ARCHIVED.

    Filter: `activity_date` inside semester range (docs: batch archive by period).
    """
    ensure_moderator(user)
    target_period = period or get_settings().current_semester
    rng = semester_range(target_period)
    if rng is None:
        raise api_error(400, ErrorCode.INVALID_STATUS_TRANSITION, f"Invalid period: {target_period}")
    start, end = rng

    result = await session.execute(
        select(Report)
        .options(
            selectinload(Report.links),
            selectinload(Report.club),
            selectinload(Report.criteria),
        )
        .where(
            Report.status.in_([ReportStatus.COMPLETED, ReportStatus.CLOSED]),
            Report.is_deleted.is_(False),
            Report.activity_date >= start,
            Report.activity_date < end,
        )
    )
    reports = list(result.scalars().all())
    if not reports:
        raise api_error(
            400,
            ErrorCode.INVALID_STATUS_TRANSITION,
            "No reports to archive",
            message_key="archive.no_candidates",
        )

    batch = ArchiveBatch(
        period=target_period,
        archived_at=_now(),
        archived_by_id=user.id,
        report_count=len(reports),
    )
    session.add(batch)
    await session.flush()

    audit = AuditService(session)
    for report in reports:
        old_status = report.status
        report.status = ReportStatus.ARCHIVED
        report.archive_batch_id = batch.id
        report.updated_at = _now()
        await audit.log(
            entity_type="report",
            entity_id=report.id,
            action="status_changed",
            performed_by_id=user.id,
            performed_by_role=UserRole.MODERATOR.value,
            old_value={"status": old_status.value},
            new_value={"status": report.status.value, "archive_batch_id": batch.id},
            reason=f"archive period {target_period}",
        )

    await session.commit()
    return batch


async def complete_approved_if_stale(
    session: AsyncSession,
    *,
    older_than_days: int,
    actor_id: str | None = None,
) -> int:
    """Auto-timer: APPROVED reports older than N days → COMPLETED."""
    from datetime import timedelta

    cutoff = datetime.now(UTC) - timedelta(days=older_than_days)
    result = await session.execute(
        select(Report).where(
            Report.status == ReportStatus.APPROVED,
            Report.is_deleted.is_(False),
            Report.moderated_at.is_not(None),
            Report.moderated_at < cutoff,
        )
    )
    reports = list(result.scalars().all())
    if not reports:
        return 0

    audit = AuditService(session)
    completed = 0
    for report in reports:
        performer = report.moderated_by_id or actor_id
        if not performer:
            # Never mutate without an audit actor (FK-safe)
            continue
        old_status = report.status
        report.status = ReportStatus.COMPLETED
        report.updated_at = _now()
        await audit.log(
            entity_type="report",
            entity_id=report.id,
            action="status_changed",
            performed_by_id=performer,
            performed_by_role="MODERATOR",
            old_value={"status": old_status.value},
            new_value={"status": report.status.value},
            reason=f"auto-complete after {older_than_days}d",
        )
        completed += 1
    await session.commit()
    return completed
