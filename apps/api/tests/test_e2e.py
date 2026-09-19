"""E2E test: full report lifecycle through HTTP API.

Login (mock SSO) → create → submit → moderate → complete → archive → rating.
Uses the real DB and FastAPI app; SSO client is monkeypatched.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

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

from tests.helpers import add_default_periods
from tests.helpers import auth as _auth
from tests.helpers import wipe_db as _wipe


@pytest.fixture
async def e2e_env(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[dict[str, str]]:
    await _wipe()
    factory = get_session_factory()
    async with factory() as session:
        now = datetime.now(UTC)
        leader = User(
            sso_id="sso-e2e-leader",
            email="e2e.leader@x.test",
            name="E2E Leader",
            role=UserRole.CLUB_LEADER,
            can_sudo=False,
            created_at=now,
        )
        mod = User(
            sso_id="sso-e2e-mod",
            email="e2e.mod@x.test",
            name="E2E Mod",
            role=UserRole.MODERATOR,
            can_sudo=True,
            created_at=now,
        )
        session.add_all([leader, mod])
        await session.flush()
        club = Club(name="E2E Club", category=ClubCategory.SPORT)
        session.add(club)
        await session.flush()
        session.add(ClubLeader(club_id=club.id, user_id=leader.id, is_primary=True))
        version = RulesVersion(semester="2026-fall", valid_from=now)
        session.add(version)
        await session.flush()
        criteria = Criteria(
            code="C8", name_ru="Образовательный контент", name_en="Educational", category=None
        )
        session.add(criteria)
        await session.flush()
        session.add(
            CriteriaRule(
                criteria_id=criteria.id,
                rule_type="tiered",
                config={
                    "tiers": [
                        {"count": 1, "pts": 250},
                        {"min": 2, "max": 5, "pts": 500},
                    ]
                },
                priority=0,
                version_id=version.id,
            )
        )
        await add_default_periods(session, now=now)
        await session.commit()
        yield {
            "leader_token": create_access_token(
                user_id=leader.id, role=UserRole.CLUB_LEADER, can_sudo=False
            ),
            "mod_token": create_access_token(
                user_id=mod.id, role=UserRole.MODERATOR, can_sudo=True
            ),
            "criteria_id": criteria.id,
            "club_id": club.id,
        }
    await _wipe()


async def test_full_report_lifecycle(client: AsyncClient, e2e_env: dict[str, str]) -> None:
    """E2E: DRAFT → ON_MODERATION → APPROVED → COMPLETED → ARCHIVED → rating."""
    # 1. Leader creates DRAFT
    create = await client.post(
        "/api/reports",
        headers=_auth(e2e_env["leader_token"]),
        json={
            "criteriaId": e2e_env["criteria_id"],
            "activityDate": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
            "reportData": {"count": 3},
            "links": ["https://docs.google.com/document/d/e2e-test"],
        },
    )
    assert create.status_code == 201
    rid = create.json()["data"]["id"]
    assert create.json()["data"]["status"] == "DRAFT"
    assert create.json()["data"]["calculatedPoints"] == 500

    # 2. Leader submits
    submit = await client.post(f"/api/reports/{rid}/submit", headers=_auth(e2e_env["leader_token"]))
    assert submit.status_code == 200
    assert submit.json()["data"]["status"] == "ON_MODERATION"

    # 3. Moderator approves
    moderate = await client.patch(
        f"/api/reports/{rid}/moderate",
        headers=_auth(e2e_env["mod_token"]),
        json={"status": "APPROVED", "comment": "Looks good"},
    )
    assert moderate.status_code == 200
    assert moderate.json()["data"]["status"] == "APPROVED"
    assert moderate.json()["data"]["finalPoints"] == 500

    # 4. Comments thread exists
    comments = await client.get(f"/api/reports/{rid}/comments", headers=_auth(e2e_env["mod_token"]))
    assert comments.status_code == 200
    bodies = [c["body"] for c in comments.json()["data"]]
    assert any("Looks good" in b for b in bodies)

    # 5. Leader completes
    complete = await client.post(
        f"/api/reports/{rid}/complete", headers=_auth(e2e_env["leader_token"])
    )
    assert complete.status_code == 200
    assert complete.json()["data"]["status"] == "COMPLETED"

    # 6. Rating reflects COMPLETED report
    rating = await client.get("/api/rating", headers=_auth(e2e_env["mod_token"]))
    assert rating.status_code == 200
    clubs = rating.json()["data"]["clubs"]
    assert len(clubs) == 1
    assert clubs[0]["name"] == "E2E Club"
    assert clubs[0]["totalPoints"] == 500

    # 7. Archive the period
    archive = await client.post(
        "/api/reports/archive",
        headers=_auth(e2e_env["mod_token"]),
        params={"period": "2026-fall"},
    )
    assert archive.status_code == 200
    assert archive.json()["data"]["reportCount"] == 1

    # 8. Report is now ARCHIVED
    get_r = await client.get(f"/api/reports/{rid}", headers=_auth(e2e_env["mod_token"]))
    assert get_r.status_code == 200
    assert get_r.json()["data"]["status"] == "ARCHIVED"

    # 9. Rating is empty after archive (COMPLETED no longer present)
    rating2 = await client.get("/api/rating", headers=_auth(e2e_env["mod_token"]))
    assert rating2.json()["data"]["clubs"] == []


async def test_full_lifecycle_with_dispute(client: AsyncClient, e2e_env: dict[str, str]) -> None:
    """E2E: DRAFT → submit → APPROVED → DISPUTED → re-APPROVED → COMPLETED."""
    create = await client.post(
        "/api/reports",
        headers=_auth(e2e_env["leader_token"]),
        json={
            "criteriaId": e2e_env["criteria_id"],
            "activityDate": (datetime.now(UTC) - timedelta(days=2)).isoformat(),
            "reportData": {"count": 3},
            "links": ["https://t.me/e2e/1"],
        },
    )
    rid = create.json()["data"]["id"]
    await client.post(f"/api/reports/{rid}/submit", headers=_auth(e2e_env["leader_token"]))
    await client.patch(
        f"/api/reports/{rid}/moderate",
        headers=_auth(e2e_env["mod_token"]),
        json={"status": "APPROVED", "finalPoints": 200, "comment": "reduced"},
    )

    # Dispute
    dispute = await client.post(
        f"/api/reports/{rid}/dispute",
        headers=_auth(e2e_env["leader_token"]),
        json={"comment": "Points too low"},
    )
    assert dispute.status_code == 200
    assert dispute.json()["data"]["status"] == "DISPUTED"

    # Moderator re-approves with higher points
    reapprove = await client.patch(
        f"/api/reports/{rid}/moderate",
        headers=_auth(e2e_env["mod_token"]),
        json={"status": "APPROVED", "finalPoints": 500, "comment": "restored"},
    )
    assert reapprove.status_code == 200
    assert reapprove.json()["data"]["status"] == "APPROVED"
    assert reapprove.json()["data"]["finalPoints"] == 500

    # Complete
    complete = await client.post(
        f"/api/reports/{rid}/complete", headers=_auth(e2e_env["leader_token"])
    )
    assert complete.status_code == 200
    assert complete.json()["data"]["status"] == "COMPLETED"
