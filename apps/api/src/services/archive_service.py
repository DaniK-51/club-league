"""Batch archive COMPLETED/CLOSED reports (state machine → ARCHIVED)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

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
from src.services.period_service import get_period_by_name, require_active_period
from src.services.report_service import _criteria_context


def _now() -> datetime:
    return datetime.now(UTC)


async def archive_period(
    session: AsyncSession, *, user: User, period: str | None = None
) -> ArchiveBatch:
    """Move COMPLETED/CLOSED reports of the period to ARCHIVED.

    Filter: `activity_date` inside period range from the Period table.
    """
    ensure_moderator(user)
    target = period or get_settings().current_semester
    period_row = require_active_period(await get_period_by_name(session, target), name=target)
    start, end, period_name = period_row.start_date, period_row.end_date, period_row.name

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
        period=period_name,
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
            display_data={
                "title": "Report archived",
                "summary": f"Archived in period {period_name}",
                **_criteria_context(report),
                "oldStatus": old_status.value,
                "newStatus": report.status.value,
                "period": period_name,
                "batchId": batch.id,
            },
            reason=f"archive period {period_name}",
        )

    period_row.is_archived = True
    period_row.updated_at = _now()

    await session.commit()
    return batch


async def complete_approved_if_stale(
    session: AsyncSession,
    *,
    older_than_days: int,
    actor_id: str | None = None,
) -> int:
    """Auto-timer: APPROVED reports older than N days → COMPLETED."""
    cutoff = datetime.now(UTC) - timedelta(days=older_than_days)
    result = await session.execute(
        select(Report)
        .options(selectinload(Report.criteria))
        .where(
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
            display_data={
                "title": "Auto-completed",
                "summary": f"{old_status.value} → {report.status.value} (auto after {older_than_days}d)",
                **_criteria_context(report),
                "oldStatus": old_status.value,
                "newStatus": report.status.value,
                "auto": True,
            },
            reason=f"auto-complete after {older_than_days}d",
        )
        completed += 1
    await session.commit()
    return completed
