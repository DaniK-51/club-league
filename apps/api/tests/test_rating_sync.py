"""Public rating endpoint integration tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, text
from src.core.database import get_session_factory
from src.core.security import create_access_token
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
from src.models.enums import ClubCategory, ReportStatus, UserRole


async def _wipe() -> None:
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(text("TRUNCATE sudo_actions, audit_logs, archive_batches RESTART IDENTITY CASCADE"))
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


@pytest.fixture
async def rating_env(client: AsyncClient) -> AsyncIterator[dict[str, str]]:
    await _wipe()
    factory = get_session_factory()
    async with factory() as session:
        now = datetime.now(UTC)
        mod = User(
            sso_id="sso-rating-mod",
            email="rating.mod@x.test",
            name="M",
            role=UserRole.MODERATOR,
            can_sudo=True,
            created_at=now,
        )
        session.add(mod)
        await session.flush()

        club = Club(name="Rating Club", category=ClubCategory.SPORT)
        session.add(club)
        await session.flush()

        version = RulesVersion(semester="2026-fall", valid_from=now)
        session.add(version)
        await session.flush()

        c8 = Criteria(code="C8", name_ru="C8", name_en="C8", category=None)
        c4 = Criteria(code="C4", name_ru="C4", name_en="C4", category=None)
        c5 = Criteria(code="C5", name_ru="C5", name_en="C5", category=None)
        session.add_all([c8, c4, c5])
        await session.flush()

        for crit, rule_type, config in [
            (c8, "tiered", {"tiers": [{"min": 0, "max": None, "pts": 1000}]}),
            (c4, "binary", {"informative": 500}),
            (c5, "binary", {"standard": 500}),
        ]:
            session.add(
                CriteriaRule(
                    criteria_id=crit.id,
                    rule_type=rule_type,
                    config=config,
                    priority=0,
                    version_id=version.id,
                )
            )

        # COMPLETED reports: C8=1000, C4=500, C5=500 → social over 15%
        for crit, points in [(c8, 1000), (c4, 500), (c5, 500)]:
            session.add(
                Report(
                    club_id=club.id,
                    criteria_id=crit.id,
                    rules_version_id=version.id,
                    activity_date=now,
                    report_data={},
                    status=ReportStatus.COMPLETED,
                    calculated_points=points,
                    final_points=points,
                    is_deleted=False,
                    created_at=now,
                    updated_at=now,
                )
            )
        await session.commit()
        yield {
            "mod": create_access_token(
                user_id=mod.id, role=UserRole.MODERATOR, can_sudo=True
            ),
        }
    await _wipe()


async def test_public_rating_applies_combined_cap(
    client: AsyncClient, rating_env: dict[str, str]
) -> None:
    resp = await client.get("/api/rating")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "semester" not in data
    assert len(data["clubs"]) == 1
    club = data["clubs"][0]
    assert club["name"] == "Rating Club"
    # total before cap 2000; C4+C5=1000 → budget 15% of 2000 = 300
    assert club["breakdown"]["C8"] == 1000
    assert club["breakdown"]["C4"] + club["breakdown"]["C5"] == 300
    assert club["totalPoints"] == 1300


async def test_sync_force_requires_moderator(
    client: AsyncClient, rating_env: dict[str, str]
) -> None:
    # no auth
    resp = await client.post("/api/admin/sync/force")
    assert resp.status_code == 401

    ok = await client.post(
        "/api/admin/sync/force",
        headers={"Authorization": f"Bearer {rating_env['mod']}"},
    )
    assert ok.status_code == 200
    assert ok.json()["data"]["status"] == "queued"


async def test_sync_status(client: AsyncClient, rating_env: dict[str, str]) -> None:
    resp = await client.get(
        "/api/admin/sync/status",
        headers={"Authorization": f"Bearer {rating_env['mod']}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["debounceSeconds"] == 3600
