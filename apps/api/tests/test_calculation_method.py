"""Tests for calculation method storage (manual points, PATCH /calculation)."""

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

from tests.helpers import auth as _auth
from tests.helpers import wipe_db as _wipe


@pytest.fixture
async def env(client: AsyncClient) -> AsyncIterator[dict[str, str]]:
    await _wipe()
    factory = get_session_factory()
    async with factory() as session:
        now = datetime.now(UTC)
        leader = User(
            sso_id="sso-calc-leader",
            email="calc.leader@x.test",
            name="Leader",
            role=UserRole.CLUB_LEADER,
            can_sudo=False,
            created_at=now,
        )
        mod = User(
            sso_id="sso-calc-mod",
            email="calc.mod@x.test",
            name="Mod",
            role=UserRole.MODERATOR,
            can_sudo=True,
            created_at=now,
        )
        session.add_all([leader, mod])
        await session.flush()
        club = Club(name="Calc Club", category=ClubCategory.SPORT)
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
                config={"tiers": [{"count": 1, "pts": 250}, {"min": 2, "max": 5, "pts": 500}]},
                priority=0,
                version_id=version.id,
            )
        )
        await session.commit()
        yield {
            "leader": create_access_token(user_id=leader.id, role=UserRole.CLUB_LEADER, can_sudo=False),
            "mod": create_access_token(user_id=mod.id, role=UserRole.MODERATOR, can_sudo=True),
            "criteria_id": criteria.id,
        }
    await _wipe()


async def _create_and_submit(client: AsyncClient, env: dict[str, str]) -> str:
    resp = await client.post(
        "/api/reports",
        headers=_auth(env["leader"]),
        json={
            "criteriaId": env["criteria_id"],
            "activityDate": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
            "reportData": {"count": 3},
            "links": ["https://t.me/calc/1"],
        },
    )
    rid = resp.json()["data"]["id"]
    await client.post(f"/api/reports/{rid}/submit", headers=_auth(env["leader"]))
    return rid


# ─── ReportResponse includes calculation fields ─────────────────────────────


async def test_response_defaults_auto(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create_and_submit(client, env)
    resp = await client.get(f"/api/reports/{rid}", headers=_auth(env["mod"]))
    data = resp.json()["data"]
    assert data["calculationMethod"] == "auto"
    assert data["manualPoints"] is None
    assert data["calculatedPoints"] == 500


# ─── PATCH /calculation ─────────────────────────────────────────────────────


async def test_set_manual_points(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create_and_submit(client, env)
    resp = await client.patch(
        f"/api/reports/{rid}/calculation",
        headers=_auth(env["mod"]),
        json={"method": "manual", "manualPoints": 350},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["calculationMethod"] == "manual"
    assert data["manualPoints"] == 350
    assert data["status"] == "ON_MODERATION"  # status unchanged
    assert data["calculatedPoints"] == 500  # unchanged


async def test_set_auto_clears_manual_points(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create_and_submit(client, env)
    await client.patch(
        f"/api/reports/{rid}/calculation",
        headers=_auth(env["mod"]),
        json={"method": "manual", "manualPoints": 100},
    )
    resp = await client.patch(
        f"/api/reports/{rid}/calculation",
        headers=_auth(env["mod"]),
        json={"method": "auto"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["calculationMethod"] == "auto"
    assert data["manualPoints"] is None


async def test_manual_requires_points(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create_and_submit(client, env)
    resp = await client.patch(
        f"/api/reports/{rid}/calculation",
        headers=_auth(env["mod"]),
        json={"method": "manual"},
    )
    assert resp.status_code == 422


async def test_moderator_only(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create_and_submit(client, env)
    resp = await client.patch(
        f"/api/reports/{rid}/calculation",
        headers=_auth(env["leader"]),
        json={"method": "manual", "manualPoints": 100},
    )
    assert resp.status_code == 403


async def test_draft_rejected(client: AsyncClient, env: dict[str, str]) -> None:
    resp = await client.post(
        "/api/reports",
        headers=_auth(env["leader"]),
        json={
            "criteriaId": env["criteria_id"],
            "activityDate": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
            "reportData": {"count": 1},
            "links": ["https://t.me/calc/2"],
        },
    )
    rid = resp.json()["data"]["id"]
    patch = await client.patch(
        f"/api/reports/{rid}/calculation",
        headers=_auth(env["mod"]),
        json={"method": "manual", "manualPoints": 100},
    )
    assert patch.status_code == 400


# ─── Approve uses manual points ─────────────────────────────────────────────


async def test_approve_uses_manual_points(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create_and_submit(client, env)
    await client.patch(
        f"/api/reports/{rid}/calculation",
        headers=_auth(env["mod"]),
        json={"method": "manual", "manualPoints": 350},
    )
    resp = await client.patch(
        f"/api/reports/{rid}/moderate",
        headers=_auth(env["mod"]),
        json={"status": "APPROVED", "comment": "manual applied"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["finalPoints"] == 350
    assert data["calculationMethod"] == "manual"


async def test_approve_auto_uses_calculated(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create_and_submit(client, env)
    resp = await client.patch(
        f"/api/reports/{rid}/moderate",
        headers=_auth(env["mod"]),
        json={"status": "APPROVED"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["finalPoints"] == 500


async def test_moderate_override_beats_manual(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create_and_submit(client, env)
    await client.patch(
        f"/api/reports/{rid}/calculation",
        headers=_auth(env["mod"]),
        json={"method": "manual", "manualPoints": 350},
    )
    resp = await client.patch(
        f"/api/reports/{rid}/moderate",
        headers=_auth(env["mod"]),
        json={"status": "APPROVED", "finalPoints": 200, "comment": "override"},
    )
    assert resp.json()["data"]["finalPoints"] == 200


# ─── Comments include calculation_updated ───────────────────────────────────


async def test_calculation_in_comments_thread(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create_and_submit(client, env)
    await client.patch(
        f"/api/reports/{rid}/calculation",
        headers=_auth(env["mod"]),
        json={"method": "manual", "manualPoints": 350},
    )
    resp = await client.get(f"/api/reports/{rid}/comments", headers=_auth(env["mod"]))
    entries = resp.json()["data"]
    actions = [e["action"] for e in entries]
    assert "calculation_updated" in actions
    calc_entry = next(e for e in entries if e["action"] == "calculation_updated")
    assert "manual" in calc_entry["body"]
    assert "350" in calc_entry["body"]
