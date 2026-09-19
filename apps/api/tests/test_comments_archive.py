"""Comments-from-audit + archive period tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from src.core.database import get_session_factory
from src.core.security import create_access_token
from src.models.entities import (
    Club,
    ClubLeader,
    Criteria,
    CriteriaRule,
    RulesVersion,
    User,
)
from src.models.enums import ClubCategory, UserRole
from src.services.periods import semester_range

from tests.helpers import add_default_periods
from tests.helpers import auth as _auth
from tests.helpers import wipe_db as _wipe


def test_semester_range() -> None:
    rng = semester_range("2026-fall")
    assert rng is not None
    start, end = rng
    assert start.year == 2026 and start.month == 9
    assert end.year == 2027 and end.month == 1
    assert semester_range("bad") is None


@pytest.fixture
async def env(client: AsyncClient) -> AsyncIterator[dict[str, str]]:
    await _wipe()
    factory = get_session_factory()
    async with factory() as session:
        now = datetime.now(UTC)
        leader = User(
            sso_id="sso-c-leader",
            email="c.leader@x.test",
            name="L",
            role=UserRole.CLUB_LEADER,
            can_sudo=False,
            created_at=now,
        )
        mod = User(
            sso_id="sso-c-mod",
            email="c.mod@x.test",
            name="M",
            role=UserRole.MODERATOR,
            can_sudo=True,
            created_at=now,
        )
        session.add_all([leader, mod])
        await session.flush()
        club = Club(name="C Club", category=ClubCategory.SPORT)
        session.add(club)
        await session.flush()
        session.add(ClubLeader(club_id=club.id, user_id=leader.id, is_primary=True))
        version = RulesVersion(semester="2026-fall", valid_from=now)
        session.add(version)
        await session.flush()
        criteria = Criteria(code="C8", name_ru="C8", name_en="C8", category=None)
        session.add(criteria)
        await session.flush()
        session.add(
            CriteriaRule(
                criteria_id=criteria.id,
                rule_type="tiered",
                config={"tiers": [{"count": 1, "pts": 250}]},
                priority=0,
                version_id=version.id,
            )
        )
        await add_default_periods(session, now=now)
        await session.commit()
        yield {
            "leader": create_access_token(
                user_id=leader.id, role=UserRole.CLUB_LEADER, can_sudo=False
            ),
            "mod": create_access_token(
                user_id=mod.id, role=UserRole.MODERATOR, can_sudo=True
            ),
            "criteria_id": criteria.id,
        }
    await _wipe()


async def _submit(client: AsyncClient, env: dict[str, str]) -> str:
    resp = await client.post(
        "/api/reports",
        headers=_auth(env["leader"]),
        json={
            "criteriaId": env["criteria_id"],
            "activityDate": "2026-09-15T12:00:00+00:00",
            "reportData": {"count": 1},
            "links": ["https://t.me/c/1"],
        },
    )
    rid = resp.json()["data"]["id"]
    await client.post(f"/api/reports/{rid}/submit", headers=_auth(env["leader"]))
    return rid


async def test_comments_thread_from_audit(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _submit(client, env)
    await client.patch(
        f"/api/reports/{rid}/moderate",
        headers=_auth(env["mod"]),
        json={"status": "APPROVED", "comment": "looks good"},
    )
    resp = await client.get(f"/api/reports/{rid}/comments", headers=_auth(env["mod"]))
    assert resp.status_code == 200
    entries = resp.json()["data"]
    assert len(entries) >= 2
    bodies = [e["body"] for e in entries]
    assert any("looks good" in b for b in bodies)
    assert any("status" in b.lower() or "APPROVED" in b for b in bodies)


async def test_archive_filters_by_semester(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _submit(client, env)
    await client.patch(
        f"/api/reports/{rid}/moderate",
        headers=_auth(env["mod"]),
        json={"status": "APPROVED"},
    )
    await client.post(f"/api/reports/{rid}/complete", headers=_auth(env["leader"]))

    # activity_date 2026-09-15 is in 2026-fall
    ok = await client.post(
        "/api/reports/archive",
        headers=_auth(env["mod"]),
        params={"period": "2026-fall"},
    )
    assert ok.status_code == 200
    assert ok.json()["data"]["reportCount"] == 1

    # other period has nothing
    empty = await client.post(
        "/api/reports/archive",
        headers=_auth(env["mod"]),
        params={"period": "2026-spring"},
    )
    assert empty.status_code == 400


async def test_moderator_cannot_delete_non_draft(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _submit(client, env)
    resp = await client.delete(f"/api/reports/{rid}", headers=_auth(env["mod"]))
    assert resp.status_code == 400
