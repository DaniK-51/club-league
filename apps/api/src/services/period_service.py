"""Period CRUD, public listing, resolve by activity_date, rating window lookup."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors import api_error
from src.models.entities import Period, Report, User
from src.policies.common import ensure_moderator
from src.schemas.common import ErrorCode
from src.schemas.period import CreatePeriodDTO, PeriodOut, UpdatePeriodDTO
from src.services.audit_service import AuditService
from src.services.periods import semester_range

BUSINESS_TZ = ZoneInfo("Europe/Moscow")


class PeriodNotFoundError(Exception):
    pass


def _parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=BUSINESS_TZ)
    return parsed.astimezone(UTC)


def _snapshot(period: Period) -> dict[str, str]:
    return {
        "name": period.name,
        "start_date": period.start_date.isoformat(),
        "end_date": period.end_date.isoformat(),
    }


def _audit_display(action_title: str, period: Period, **extra: Any) -> dict[str, Any]:
    return {
        "title": action_title,
        "summary": period.name,
        "name": period.name,
        **extra,
    }


async def _report_counts_by_period(session: AsyncSession) -> dict[str, int]:
    rows = await session.execute(
        select(Report.period_id, func.count())
        .where(Report.period_id.is_not(None), Report.is_deleted.is_(False))
        .group_by(Report.period_id)
    )
    return {str(pid): int(count) for pid, count in rows.all() if pid is not None}


def _to_period_out(period: Period, *, report_count: int) -> PeriodOut:
    return PeriodOut(
        id=period.id,
        name=period.name,
        startDate=period.start_date.isoformat(),
        endDate=period.end_date.isoformat(),
        isArchived=period.is_archived,
        reportCount=report_count,
    )


async def _period_out(session: AsyncSession, period: Period) -> PeriodOut:
    count = await session.scalar(
        select(func.count())
        .select_from(Report)
        .where(Report.period_id == period.id, Report.is_deleted.is_(False))
    )
    return _to_period_out(period, report_count=int(count or 0))


async def _list_all_periods(session: AsyncSession) -> list[PeriodOut]:
    """All periods (active + archived), startDate desc, with report counts."""
    result = await session.execute(select(Period).order_by(Period.start_date.desc()))
    periods = list(result.scalars().all())
    counts = await _report_counts_by_period(session)
    return [_to_period_out(p, report_count=counts.get(p.id, 0)) for p in periods]


async def list_periods(session: AsyncSession, *, user: User) -> list[PeriodOut]:
    ensure_moderator(user)
    return await _list_all_periods(session)


async def list_periods_public(session: AsyncSession) -> list[PeriodOut]:
    """Public rating filter list — no auth, includes archived periods."""
    return await _list_all_periods(session)


async def create_period(
    session: AsyncSession, *, user: User, payload: CreatePeriodDTO
) -> PeriodOut:
    ensure_moderator(user)
    existing = await session.scalar(select(Period).where(Period.name == payload.name))
    if existing is not None:
        raise api_error(400, ErrorCode.VALIDATION_ERROR, f"Period {payload.name} already exists")
    now = datetime.now(UTC)
    period = Period(
        name=payload.name,
        start_date=_parse_dt(payload.startDate),
        end_date=_parse_dt(payload.endDate),
        is_archived=False,
        created_at=now,
        updated_at=now,
    )
    session.add(period)
    await session.flush()
    await AuditService(session).log(
        entity_type="period",
        entity_id=period.id,
        action="created",
        performed_by_id=user.id,
        performed_by_role=user.role.value,
        old_value=None,
        new_value=_snapshot(period),
        display_data=_audit_display(
            "Period created",
            period,
            startDate=period.start_date.isoformat(),
            endDate=period.end_date.isoformat(),
        ),
    )
    await session.commit()
    return await _period_out(session, period)


async def update_period(
    session: AsyncSession, *, user: User, period_id: str, payload: UpdatePeriodDTO
) -> PeriodOut:
    ensure_moderator(user)
    period = await session.get(Period, period_id)
    if period is None:
        raise PeriodNotFoundError(period_id)
    old_snapshot = _snapshot(period)
    if payload.name is not None:
        period.name = payload.name
    if payload.startDate is not None:
        period.start_date = _parse_dt(payload.startDate)
    if payload.endDate is not None:
        period.end_date = _parse_dt(payload.endDate)
    period.updated_at = datetime.now(UTC)
    await session.flush()
    await AuditService(session).log(
        entity_type="period",
        entity_id=period.id,
        action="updated",
        performed_by_id=user.id,
        performed_by_role=user.role.value,
        old_value=old_snapshot,
        new_value=_snapshot(period),
        display_data=_audit_display("Period updated", period),
    )
    await session.commit()
    return await _period_out(session, period)


async def delete_period(session: AsyncSession, *, user: User, period_id: str) -> None:
    ensure_moderator(user)
    period = await session.get(Period, period_id)
    if period is None:
        raise PeriodNotFoundError(period_id)
    count = await session.scalar(
        select(func.count()).select_from(Report).where(Report.period_id == period_id)
    )
    if count and int(count) > 0:
        raise api_error(
            400,
            ErrorCode.VALIDATION_ERROR,
            f"Cannot delete period with {count} reports",
        )
    old_name = period.name
    await session.delete(period)
    await AuditService(session).log(
        entity_type="period",
        entity_id=period_id,
        action="deleted",
        performed_by_id=user.id,
        performed_by_role=user.role.value,
        old_value={"name": old_name},
        new_value=None,
        display_data={"title": "Period deleted", "summary": old_name},
    )
    await session.commit()


async def resolve_period_for_date(
    session: AsyncSession, activity_date: datetime
) -> Period | None:
    """Find period containing activity_date (start <= date < end)."""
    return await session.scalar(
        select(Period)
        .where(
            Period.start_date <= activity_date,
            Period.end_date > activity_date,
        )
        .limit(1)
    )


async def assign_report_period(
    session: AsyncSession, *, report: Report, activity_date: datetime
) -> Period | None:
    """Set report.period / period_id from activity_date. Returns resolved Period."""
    period = await resolve_period_for_date(session, activity_date)
    report.period = period
    report.period_id = period.id if period is not None else None
    return period


async def get_period_by_name(session: AsyncSession, name: str) -> Period | None:
    return await session.scalar(select(Period).where(Period.name == name))


async def get_current_period(session: AsyncSession) -> Period | None:
    """Last non-archived period by start_date."""
    return await session.scalar(
        select(Period)
        .where(Period.is_archived.is_(False))
        .order_by(Period.start_date.desc())
        .limit(1)
    )


def require_period(period: Period | None, *, name: str) -> Period:
    """Archive/rating gate: Period table is source of truth."""
    if period is None:
        raise api_error(404, ErrorCode.PERIOD_NOT_FOUND, f"Period {name} not found")
    return period


def require_active_period(period: Period | None, *, name: str) -> Period:
    period = require_period(period, name=name)
    if period.is_archived:
        raise api_error(
            400,
            ErrorCode.ALREADY_ARCHIVED,
            f"Period {name} already archived",
        )
    return period


async def resolve_rating_window(
    session: AsyncSession,
    *,
    period_name: str | None = None,
    semester: str | None = None,
) -> tuple[datetime | None, datetime | None, str]:
    """Return (start, end, period_label) for rating aggregation.

    Priority: period_name → semester → current Period → semester_range fallback.
    """
    period_row: Period | None
    label = period_name or semester or ""

    if period_name:
        period_row = await get_period_by_name(session, period_name)
    elif semester:
        period_row = await get_period_by_name(session, semester)
    else:
        period_row = await get_current_period(session)

    if period_row is not None:
        return period_row.start_date, period_row.end_date, period_row.name
    if label:
        rng = semester_range(label)
        if rng is not None:
            return rng[0], rng[1], label
    return None, None, label
