"""Sudo mode: force transitions, restore soft-deleted reports, override points.

Requires role=MODERATOR and can_sudo=True. Always logs to sudo_actions + audit_logs.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.errors import api_error
from src.models.entities import Report, User
from src.models.enums import ReportStatus
from src.policies.common import ensure_sudo
from src.schemas.common import ErrorCode
from src.schemas.sudo import SudoActionDTO
from src.services.audit_service import AuditService


class SudoReportNotFoundError(Exception):
    def __init__(self, report_id: str) -> None:
        super().__init__(report_id)


class SudoValidationError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


def _now() -> datetime:
    return datetime.now(UTC)


async def _load_report(
    session: AsyncSession,
    report_id: str,
    *,
    include_deleted: bool = False,
) -> Report:
    query = (
        select(Report)
        .options(
            selectinload(Report.links),
            selectinload(Report.club),
            selectinload(Report.criteria),
        )
        .where(Report.id == report_id)
    )
    if not include_deleted:
        query = query.where(Report.is_deleted.is_(False))
    report = await session.scalar(query)
    if report is None:
        raise SudoReportNotFoundError(report_id)
    return report


def _parse_status(value: Any) -> ReportStatus:
    if isinstance(value, ReportStatus):
        return value
    if not isinstance(value, str):
        raise SudoValidationError("newValue must be a ReportStatus string")
    try:
        return ReportStatus(value)
    except ValueError as exc:
        raise SudoValidationError(f"invalid status {value!r}") from exc


def _parse_points(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SudoValidationError("newValue must be a non-negative integer")
    return value


async def run_sudo_action(
    session: AsyncSession,
    *,
    user: User,
    payload: SudoActionDTO,
) -> Report:
    ensure_sudo(user)

    reason = payload.reason.strip()
    if not reason:
        raise api_error(
            400, ErrorCode.SUDO_REQUIRED, "reason is required", message_key="sudo.reason_required"
        )

    audit = AuditService(session)

    if payload.action == "force_status":
        report = await _load_report(session, payload.targetReportId)
        old_status = report.status
        new_status = _parse_status(payload.newValue)
        old_snapshot = {"status": old_status.value}
        report.status = new_status
        report.updated_at = _now()
        new_snapshot = {"status": new_status.value}
        sudo_action = "force_status"

    elif payload.action == "restore_deleted":
        report = await _load_report(
            session, payload.targetReportId, include_deleted=True
        )
        if not report.is_deleted:
            raise SudoValidationError("report is not deleted")
        old_snapshot = {
            "is_deleted": True,
            "deleted_at": report.deleted_at.isoformat() if report.deleted_at else None,
        }
        report.is_deleted = False
        report.deleted_at = None
        report.updated_at = _now()
        new_snapshot = {"is_deleted": False}
        sudo_action = "restore_deleted"

    elif payload.action == "override_points":
        report = await _load_report(session, payload.targetReportId)
        points = _parse_points(payload.newValue)
        old_snapshot = {
            "calculated_points": report.calculated_points,
            "final_points": report.final_points,
        }
        report.final_points = points
        report.updated_at = _now()
        new_snapshot = {"final_points": points}
        sudo_action = "override_points"

    else:  # pragma: no cover - Literal prevents this
        raise SudoValidationError(f"unknown action {payload.action}")

    await session.flush()
    await audit.log_sudo_action(
        performed_by=user,
        action=sudo_action,
        entity_type="report",
        entity_id=report.id,
        old_value=old_snapshot,
        new_value=new_snapshot,
        reason=reason,
    )
    await session.commit()

    loaded = await _load_report(session, report.id, include_deleted=True)
    return loaded
