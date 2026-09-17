from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.errors import api_error
from src.models.entities import (
    ClubLeader,
    Criteria,
    CriteriaRule,
    Report,
    ReportLink,
    RulesVersion,
    User,
)
from src.models.enums import ReportStatus, UserRole
from src.policies.common import ensure_club_leader
from src.schemas.common import ErrorCode
from src.schemas.report import (
    CreateReportDTO,
    ReportResponse,
    SetCalculationDTO,
    UpdateReportDTO,
    is_overdue,
    parse_activity_date,
)
from src.schemas.rules import ReportDataError, RuleValidationError, UnknownRuleTypeError
from src.services.audit_service import AuditService
from src.services.link_validation import LinkValidationError, validate_links
from src.services.report_state import (
    ensure_leader_transition,
)
from src.services.rules_engine import RulesEngine


class ReportNotFoundError(Exception):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


async def _load_rules_for_criteria(
    session: AsyncSession, criteria_id: str
) -> tuple[RulesVersion, CriteriaRule | None]:
    version = await session.scalar(
        select(RulesVersion).order_by(RulesVersion.valid_from.desc()).limit(1)
    )
    if version is None:
        raise api_error(
            404,
            ErrorCode.RULES_VERSION_NOT_FOUND,
            "No rules version",
            message_key="rules.version_not_found",
        )
    rule = await session.scalar(
        select(CriteriaRule).where(
            CriteriaRule.criteria_id == criteria_id,
            CriteriaRule.version_id == version.id,
        )
    )
    return version, rule


def _calculate_points(rule: CriteriaRule | None, report_data: dict[str, Any]) -> int | None:
    if rule is None:
        return None
    engine = RulesEngine()
    try:
        result = engine.calculate(
            rule_type=rule.rule_type,
            config=dict(rule.config),
            report_data=report_data,
        )
    except (RuleValidationError, ReportDataError, UnknownRuleTypeError):
        # Leave calculated_points empty; moderator can set final points later.
        return None
    return result.points


def report_to_response(report: Report) -> ReportResponse:
    return ReportResponse(
        id=report.id,
        clubName=report.club.name if report.club else "",
        criteriaCode=report.criteria.code if report.criteria else "",
        activityDate=report.activity_date.isoformat(),
        isOverdue=is_overdue(report.activity_date),
        status=report.status,
        calculatedPoints=report.calculated_points,
        finalPoints=report.final_points,
        calculationMethod=report.calculation_method or "auto",
        manualPoints=report.manual_points,
        links=[{"url": link.url, "domain": link.domain} for link in report.links],
        reportData=dict(report.report_data or {}),
    )


async def _get_report(session: AsyncSession, report_id: str) -> Report | None:
    return await session.scalar(
        select(Report)
        .options(
            selectinload(Report.links),
            selectinload(Report.club),
            selectinload(Report.criteria),
        )
        .where(Report.id == report_id, Report.is_deleted.is_(False))
    )


async def _resolve_club_id(session: AsyncSession, user: User, club_id: str | None) -> str:
    result = await session.execute(select(ClubLeader).where(ClubLeader.user_id == user.id))
    leaderships = list(result.scalars().all())
    if not leaderships:
        raise api_error(
            403,
            ErrorCode.NOT_CLUB_LEADER,
            "Club leader role required",
            message_key="forbidden.club_leader_required",
        )
    if club_id is not None:
        ensure_club_leader(user, frozenset(link.club_id for link in leaderships), club_id)
        return club_id
    if len(leaderships) == 1:
        return leaderships[0].club_id
    primary = next((link for link in leaderships if link.is_primary), None)
    return (primary or leaderships[0]).club_id


async def create_report(
    session: AsyncSession,
    *,
    user: User,
    payload: CreateReportDTO,
) -> Report:
    if user.role == UserRole.MODERATOR:
        raise api_error(
            403,
            ErrorCode.FORBIDDEN,
            "Moderators cannot create club reports",
            message_key="forbidden.cannot_create_report",
        )

    club_id = await _resolve_club_id(session, user, None)
    criteria = await session.scalar(select(Criteria).where(Criteria.id == payload.criteriaId))
    if criteria is None:
        raise api_error(
            404,
            ErrorCode.RULES_VERSION_NOT_FOUND,
            "Criteria not found",
            message_key="report.criteria_not_found",
        )

    try:
        validated_links = validate_links(payload.links)
    except LinkValidationError as exc:
        raise api_error(400, exc.code, str(exc)) from None

    version, rule = await _load_rules_for_criteria(session, criteria.id)
    activity_date = parse_activity_date(payload.activityDate)
    points = _calculate_points(rule, dict(payload.reportData))
    now = _now()

    report = Report(
        club_id=club_id,
        criteria_id=criteria.id,
        rules_version_id=version.id,
        activity_date=activity_date,
        report_data=dict(payload.reportData),
        status=ReportStatus.DRAFT,
        calculated_points=points,
        is_deleted=False,
        created_at=now,
        updated_at=now,
    )
    session.add(report)
    await session.flush()

    for url, domain in validated_links:
        session.add(ReportLink(report_id=report.id, url=url, domain=domain, created_at=now))

    await AuditService(session).log(
        entity_type="report",
        entity_id=report.id,
        action="created",
        performed_by_id=user.id,
        performed_by_role=user.role.value,
        old_value=None,
        new_value={
            "status": report.status.value,
            "club_id": club_id,
            "criteria_id": criteria.id,
            "calculated_points": points,
            "is_overdue": is_overdue(activity_date),
        },
    )
    await session.commit()
    loaded = await _get_report(session, report.id)
    assert loaded is not None
    return loaded


async def _user_club_ids(session: AsyncSession, user_id: str) -> frozenset[str]:
    result = await session.execute(select(ClubLeader.club_id).where(ClubLeader.user_id == user_id))
    return frozenset(row[0] for row in result.all())


# Statuses where moderator may edit reportData via PATCH /reports/:id
_MODERATOR_EDIT_STATUSES = frozenset({
    ReportStatus.ON_MODERATION,
    ReportStatus.DISPUTED,
    ReportStatus.CHANGES_REQUIRED,
    ReportStatus.APPROVED,
})

# Statuses where moderator may set calculation method
_MODERATOR_CALC_STATUSES = frozenset({
    ReportStatus.ON_MODERATION,
    ReportStatus.DISPUTED,
    ReportStatus.CHANGES_REQUIRED,
    ReportStatus.APPROVED,
})

# Statuses where leader may edit (via ensure_editable)
_LEADER_EDIT_STATUSES = frozenset({ReportStatus.DRAFT, ReportStatus.CHANGES_REQUIRED})


async def update_report(
    session: AsyncSession,
    *,
    user: User,
    report_id: str,
    payload: UpdateReportDTO,
) -> Report:
    report = await _get_report(session, report_id)
    if report is None:
        raise ReportNotFoundError(report_id)

    if user.role == UserRole.MODERATOR:
        # Moderator may only edit reportData, and only in specific statuses
        if payload.activityDate is not None or payload.links is not None:
            raise api_error(
                403,
                ErrorCode.FORBIDDEN,
                "Moderator can only edit reportData",
            )
        if report.status not in _MODERATOR_EDIT_STATUSES:
            raise api_error(
                400,
                ErrorCode.INVALID_STATUS_TRANSITION,
                f"Moderator cannot edit reportData in status {report.status.value}",
            )
    else:
        ensure_club_leader(user, await _user_club_ids(session, user.id), report.club_id)
        if report.status not in _LEADER_EDIT_STATUSES:
            raise api_error(
                400,
                ErrorCode.INVALID_STATUS_TRANSITION,
                f"Report not editable in status {report.status.value}",
            )

    old_snapshot = {
        "activity_date": report.activity_date.isoformat(),
        "report_data": dict(report.report_data or {}),
        "calculated_points": report.calculated_points,
        "links": [link.url for link in report.links],
    }

    if payload.activityDate is not None:
        report.activity_date = parse_activity_date(payload.activityDate)
    if payload.reportData is not None:
        report.report_data = dict(payload.reportData)
    if payload.links is not None:
        try:
            validated_links = validate_links(payload.links)
        except LinkValidationError as exc:
            raise api_error(400, exc.code, str(exc)) from None
        report.links.clear()
        now = _now()
        for url, domain in validated_links:
            session.add(
                ReportLink(report_id=report.id, url=url, domain=domain, created_at=now)
            )

    if payload.reportData is not None:
        _, rule = await _load_rules_for_criteria(session, report.criteria_id)
        report.calculated_points = _calculate_points(rule, dict(report.report_data))

    report.updated_at = _now()
    await session.flush()

    await AuditService(session).log(
        entity_type="report",
        entity_id=report.id,
        action="updated",
        performed_by_id=user.id,
        performed_by_role=user.role.value,
        old_value=old_snapshot,
        new_value={
            "activity_date": report.activity_date.isoformat(),
            "report_data": dict(report.report_data or {}),
            "calculated_points": report.calculated_points,
        },
    )
    await session.commit()
    loaded = await _get_report(session, report.id)
    assert loaded is not None
    return loaded


async def set_calculation(
    session: AsyncSession,
    *,
    user: User,
    report_id: str,
    payload: SetCalculationDTO,
) -> Report:
    """Set calculation method + manual points WITHOUT changing status."""
    if user.role != UserRole.MODERATOR:
        raise api_error(403, ErrorCode.FORBIDDEN, "Moderator only")

    report = await _get_report(session, report_id)
    if report is None:
        raise ReportNotFoundError(report_id)

    if report.status not in _MODERATOR_CALC_STATUSES:
        raise api_error(
            400,
            ErrorCode.INVALID_STATUS_TRANSITION,
            f"Cannot set calculation in status {report.status.value}",
        )

    old_snapshot = {
        "calculation_method": report.calculation_method,
        "manual_points": report.manual_points,
    }

    report.calculation_method = payload.method
    report.manual_points = payload.manualPoints if payload.method == "manual" else None
    report.updated_at = _now()
    await session.flush()

    await AuditService(session).log(
        entity_type="report",
        entity_id=report.id,
        action="calculation_updated",
        performed_by_id=user.id,
        performed_by_role=user.role.value,
        old_value=old_snapshot,
        new_value={
            "calculation_method": report.calculation_method,
            "manual_points": report.manual_points,
        },
    )
    await session.commit()
    loaded = await _get_report(session, report.id)
    assert loaded is not None
    return loaded


async def submit_report(session: AsyncSession, *, user: User, report_id: str) -> Report:
    report = await _get_report(session, report_id)
    if report is None:
        raise ReportNotFoundError(report_id)

    if user.role == UserRole.MODERATOR:
        raise api_error(
            403,
            ErrorCode.FORBIDDEN,
            "Moderators cannot submit reports",
            message_key="forbidden.cannot_submit",
        )

    ensure_club_leader(user, await _user_club_ids(session, user.id), report.club_id)
    old_status = report.status
    ensure_leader_transition(old_status, ReportStatus.ON_MODERATION)

    report.status = ReportStatus.ON_MODERATION
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
    )
    await session.commit()
    loaded = await _get_report(session, report.id)
    assert loaded is not None
    return loaded


async def soft_delete_report(session: AsyncSession, *, user: User, report_id: str) -> None:
    """Soft-delete: only DRAFT for everyone (AGENTS: leaders see hard delete)."""
    report = await _get_report(session, report_id)
    if report is None:
        raise ReportNotFoundError(report_id)

    if user.role != UserRole.MODERATOR:
        ensure_club_leader(user, await _user_club_ids(session, user.id), report.club_id)
    if report.status != ReportStatus.DRAFT:
        raise api_error(
            400,
            ErrorCode.INVALID_STATUS_TRANSITION,
            "Only DRAFT can be deleted",
            message_key="report.delete_only_draft",
        )

    old_status = report.status
    report.is_deleted = True
    report.deleted_at = _now()
    report.updated_at = _now()
    await session.flush()

    await AuditService(session).log(
        entity_type="report",
        entity_id=report.id,
        action="deleted",
        performed_by_id=user.id,
        performed_by_role=user.role.value,
        old_value={"status": old_status.value},
        new_value={"is_deleted": True},
    )
    await session.commit()


async def get_report(session: AsyncSession, *, user: User, report_id: str) -> Report:
    report = await _get_report(session, report_id)
    if report is None:
        raise ReportNotFoundError(report_id)
    if user.role != UserRole.MODERATOR:
        ensure_club_leader(user, await _user_club_ids(session, user.id), report.club_id)
    return report


async def list_reports(
    session: AsyncSession,
    *,
    user: User,
    club_id: str | None = None,
) -> list[Report]:
    query = (
        select(Report)
        .options(
            selectinload(Report.links),
            selectinload(Report.club),
            selectinload(Report.criteria),
        )
        .where(Report.is_deleted.is_(False))
        .order_by(Report.created_at.desc())
    )
    if user.role != UserRole.MODERATOR:
        result = await session.execute(select(ClubLeader.club_id).where(ClubLeader.user_id == user.id))
        club_ids = frozenset(row[0] for row in result.all())
        if not club_ids:
            return []
        if club_id is not None:
            ensure_club_leader(user, club_ids, club_id)
            query = query.where(Report.club_id == club_id)
        else:
            query = query.where(Report.club_id.in_(club_ids))
    elif club_id is not None:
        query = query.where(Report.club_id == club_id)

    result = await session.execute(query)
    return list(result.scalars().all())
