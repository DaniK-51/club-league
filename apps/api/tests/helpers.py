"""Shared integration-test helpers (DB wipe + auth headers + period seed).

Import as:
    from tests.helpers import add_default_periods, auth as _auth, wipe_db as _wipe
"""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_session_factory
from src.models.entities import (
    Club,
    ClubLeader,
    Criteria,
    CriteriaRule,
    Period,
    Report,
    ReportLink,
    RulesVersion,
    User,
)

TZ = ZoneInfo("Europe/Moscow")


def auth(token: str) -> dict[str, str]:
    """Bearer Authorization header for httpx client calls."""
    return {"Authorization": f"Bearer {token}"}


async def wipe_db() -> None:
    """Reset integration DB state between fixtures.

    Truncates FK-RESTRICT tables (sudo_actions, audit_logs) before deleting
    users; then deletes entities in FK-safe order.
    """
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(
            text("TRUNCATE sudo_actions, audit_logs, archive_batches RESTART IDENTITY CASCADE")
        )
        await session.execute(delete(ReportLink))
        await session.execute(delete(Report))
        await session.execute(delete(Period))
        await session.execute(delete(CriteriaRule))
        await session.execute(delete(Criteria))
        await session.execute(delete(RulesVersion))
        await session.execute(delete(ClubLeader))
        await session.execute(delete(User))
        await session.execute(delete(Club))
        await session.commit()


async def add_default_periods(
    session: AsyncSession,
    *,
    now: datetime | None = None,
    names: tuple[str, ...] = ("2026-fall", "2026-spring"),
) -> list[Period]:
    """Seed standard 2026 periods (Europe/Moscow) used by most fixtures."""
    stamp = now or datetime.now(UTC)
    catalog: dict[str, tuple[datetime, datetime]] = {
        "2026-fall": (
            datetime(2026, 9, 1, tzinfo=TZ),
            datetime(2027, 1, 1, tzinfo=TZ),
        ),
        "2026-spring": (
            datetime(2026, 1, 1, tzinfo=TZ),
            datetime(2026, 6, 1, tzinfo=TZ),
        ),
        "2026-summer": (
            datetime(2026, 6, 1, tzinfo=TZ),
            datetime(2026, 9, 1, tzinfo=TZ),
        ),
    }
    created: list[Period] = []
    for name in names:
        start, end = catalog[name]
        period = Period(
            name=name,
            start_date=start,
            end_date=end,
            is_archived=False,
            created_at=stamp,
            updated_at=stamp,
        )
        session.add(period)
        created.append(period)
    return created
