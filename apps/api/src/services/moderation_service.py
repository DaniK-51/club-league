"""Moderation: approve / request changes / close / dispute / complete."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.errors import api_error
from src.models.entities import Report, User
from src.models.enums import ReportStatus, UserRole
from src.policies.common import ensure_club_leader, ensure_moderator
from src.schemas.common import ErrorCode
from src.schemas.moderation import DisputeReportDTO, ModerateReportDTO
from src.services.audit_service import AuditService
from src.services.report_service import (
    ReportNotFoundError,
    _criteria_context,
    _get_report,
    _user_club_ids,
)
from src.services.report_state import (
    ensure_leader_transition,
    ensure_moderator_transition,
)
from src.services.sync_service import debouncer


def _now() -> datetime:
    return datetime.now(UTC)


def resolve_final_points(
    *,
    calculated: int | None,
    override: int | None,
    target_status: ReportStatus,
    calculation_method: str = "auto",
    manual_points: int | None = None,
) -> int | None:
    """finalPoints based on calculation method. CLOSED → 0."""
    if target_status == ReportStatus.CLOSED:
        return 0
    if override is not None:
        return override
    if calculation_method == "manual" and manual_points is not None:
        return manual_points
    return calculated


def requires_comment(
    *,
    target_status: ReportStatus,
    calculated: int | None,
    final_points: int | None,
    calculation_method: str = "auto",
) -> bool:
    """Comment required for CHANGES_REQUIRED or explicit override.

    When calculation_method="manual", points were already justified via
    PATCH /calculation (which has its own reason + audit trail).
    Caller still checks that a non-empty comment is present.
    """
    if target_status == ReportStatus.CHANGES_REQUIRED:
        return True
    if calculation_method == "manual":
        return False
    return final_points is not None and calculated is not None and final_points != calculated


async def moderate_report(
    session: AsyncSession,
    *,
    user: User,
    report_id: str,
    payload: ModerateReportDTO,
) -> Report:
    ensure_moderator(user)
    report = await _get_report(session, report_id)
    if report is None:
        raise ReportNotFoundError(report_id)

    old_status = report.status
    ensure_moderator_transition(old_status, payload.status)

    final_points = resolve_final_points(
        calculated=report.calculated_points,
        override=payload.finalPoints,
        target_status=payload.status,
        calculation_method=report.calculation_method or "auto",
        manual_points=report.manual_points,
    )
    comment = payload.comment.strip()
    if requires_comment(
        target_status=payload.status,
        calculated=report.calculated_points,
        final_points=final_points,
        calculation_method=report.calculation_method or "auto",
    ) and not comment:
        raise api_error(
            400,
            ErrorCode.COMMENT_REQUIRED,
            "Comment required",
            message_key="moderation.comment_required",
        )

    old_snapshot = {
        "status": old_status.value,
        "final_points": report.final_points,
        "moderation_comment": report.moderation_comment,
    }

    report.status = payload.status
    report.final_points = final_points
    report.moderation_comment = comment or None
    report.moderated_by_id = user.id
    report.moderated_at = _now()
    report.updated_at = _now()
    await session.flush()

    summary = f"{old_status.value} → {report.status.value}"
    if comment:
        summary += f" — {comment}"

    await AuditService(session).log(
        entity_type="report",
        entity_id=report.id,
        action="status_changed",
        performed_by_id=user.id,
        performed_by_role=user.role.value,
        old_value=old_snapshot,
        new_value={
            "status": report.status.value,
            "final_points": report.final_points,
            "moderation_comment": report.moderation_comment,
        },
        display_data={
            "title": "Status changed",
            "summary": summary,
            **_criteria_context(report),
            "oldStatus": old_status.value,
            "newStatus": report.status.value,
            "calculatedPoints": report.calculated_points,
            "finalPoints": report.final_points,
            "calculationMethod": report.calculation_method or "auto",
            "manualPoints": report.manual_points,
            "moderationComment": comment or None,
        },
    )
    if payload.finalPoints is not None and payload.finalPoints != report.calculated_points:
        await AuditService(session).log(
            entity_type="report",
            entity_id=report.id,
            action="points_updated",
            performed_by_id=user.id,
            performed_by_role=user.role.value,
            old_value={"calculated_points": report.calculated_points},
            new_value={"final_points": report.final_points},
            display_data={
                "title": "Points updated",
                "summary": f"finalPoints: {report.calculated_points} → {report.final_points}",
                **_criteria_context(report),
                "oldPoints": report.calculated_points,
                "newPoints": report.final_points,
                "calculationMethod": report.calculation_method or "auto",
                "manualPoints": report.manual_points,
                "moderationComment": comment or None,
            },
            reason=comment or None,
        )

    await session.commit()

    if report.status == ReportStatus.COMPLETED:
        debouncer.notify()

    loaded = await _get_report(session, report.id)
    assert loaded is not None
    return loaded


async def dispute_report(
    session: AsyncSession,
    *,
    user: User,
    report_id: str,
    payload: DisputeReportDTO,
) -> Report:
    report = await _get_report(session, report_id)
    if report is None:
        raise ReportNotFoundError(report_id)

    if user.role != UserRole.MODERATOR:
        ensure_club_leader(user, await _user_club_ids(session, user.id), report.club_id)

    old_status = report.status
    ensure_leader_transition(old_status, ReportStatus.DISPUTED)

    comment = payload.comment.strip()
    report.status = ReportStatus.DISPUTED
    report.moderation_comment = comment
    report.updated_at = _now()
    await session.flush()

    summary = f"{old_status.value} → {report.status.value}"
    if comment:
        summary += f" — {comment}"

    await AuditService(session).log(
        entity_type="report",
        entity_id=report.id,
        action="status_changed",
        performed_by_id=user.id,
        performed_by_role=user.role.value,
        old_value={"status": old_status.value},
        new_value={"status": report.status.value},
        display_data={
            "title": "Status changed",
            "summary": summary,
            **_criteria_context(report),
            "oldStatus": old_status.value,
            "newStatus": report.status.value,
            "calculatedPoints": report.calculated_points,
            "finalPoints": report.final_points,
        },
        reason=comment,
    )
    await session.commit()
    loaded = await _get_report(session, report.id)
    assert loaded is not None
    return loaded


async def complete_report(
    session: AsyncSession,
    *,
    user: User,
    report_id: str,
) -> Report:
    """Leader confirms APPROVED → COMPLETED (counts toward rating)."""
    report = await _get_report(session, report_id)
    if report is None:
        raise ReportNotFoundError(report_id)

    if user.role != UserRole.MODERATOR:
        ensure_club_leader(user, await _user_club_ids(session, user.id), report.club_id)

    old_status = report.status
    ensure_leader_transition(old_status, ReportStatus.COMPLETED)

    report.status = ReportStatus.COMPLETED
    report.updated_at = _now()
    await session.flush()

    await AuditService(session).log(
        entity_type="report",
        entity_id=report.id,
        action="status_changed",
        performed_by_id=user.id,
        performed_by_role=user.role.value,
        old_value={"status": old_status.value},
        new_value={"status": report.status.value},
        display_data={
            "title": "Status changed",
            "summary": f"{old_status.value} → {report.status.value}",
            **_criteria_context(report),
            "oldStatus": old_status.value,
            "newStatus": report.status.value,
            "calculatedPoints": report.calculated_points,
            "finalPoints": report.final_points,
        },
    )
    await session.commit()

    debouncer.notify()

    loaded = await _get_report(session, report.id)
    assert loaded is not None
    return loaded


async def list_completed_points_by_criteria(
    session: AsyncSession,
    *,
    club_id: str,
    period_start: datetime,
    period_end: datetime,
) -> dict[str, int]:
    """Sum final_points (fallback calculated) of COMPLETED reports by criteria code."""
    result = await session.execute(
        select(Report)
        .options(selectinload(Report.criteria))
        .where(
            Report.club_id == club_id,
            Report.status == ReportStatus.COMPLETED,
            Report.is_deleted.is_(False),
            Report.activity_date >= period_start,
            Report.activity_date < period_end,
        )
    )
    totals: dict[str, int] = {}
    for report in result.scalars().all():
        code = report.criteria.code if report.criteria else "UNKNOWN"
        points = report.final_points if report.final_points is not None else (
            report.calculated_points or 0
        )
        totals[code] = totals.get(code, 0) + int(points)
    return totals
