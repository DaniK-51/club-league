"""Period CRUD + resolve_report_period."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors import api_error
from src.models.entities import Period, Report, User
from src.policies.common import ensure_moderator
from src.schemas.common import ErrorCode
from src.schemas.period import CreatePeriodDTO, PeriodOut, UpdatePeriodDTO
from src.services.audit_service import AuditService
from src.services.periods import BUSINESS_TZ


class PeriodNotFoundError(Exception):
    pass


def _parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=BUSINESS_TZ)
    return parsed.astimezone(UTC)


async def _period_out(session: AsyncSession, period: Period) -> PeriodOut:
    count = await session.scalar(
        select(func.count())
        .select_from(Report)
        .where(Report.period_id == period.id, Report.is_deleted.is_(False))
    )
    return PeriodOut(
        id=period.id,
        name=period.name,
        startDate=period.start_date.isoformat(),
        endDate=period.end_date.isoformat(),
        isArchived=period.is_archived,
        reportCount=int(count or 0),
    )


async def list_periods(session: AsyncSession, *, user: User) -> list[PeriodOut]:
    ensure_moderator(user)
    result = await session.execute(select(Period).order_by(Period.start_date.desc()))
    return [await _period_out(session, p) for p in result.scalars().all()]


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
        new_value={
            "name": period.name,
            "start_date": period.start_date.isoformat(),
            "end_date": period.end_date.isoformat(),
        },
        display_data={
            "title": "Period created",
            "summary": period.name,
            "name": period.name,
            "startDate": period.start_date.isoformat(),
            "endDate": period.end_date.isoformat(),
        },
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
    old_snapshot = {
        "name": period.name,
        "start_date": period.start_date.isoformat(),
        "end_date": period.end_date.isoformat(),
    }
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
        new_value={
            "name": period.name,
            "start_date": period.start_date.isoformat(),
            "end_date": period.end_date.isoformat(),
        },
        display_data={
            "title": "Period updated",
            "summary": period.name,
            "name": period.name,
        },
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


def period_display_context(period: Period | None) -> dict[str, object]:
    if period is None:
        return {"period": None}
    return {
        "period": period.name,
        "periodStart": period.start_date.isoformat(),
        "periodEnd": period.end_date.isoformat(),
    }