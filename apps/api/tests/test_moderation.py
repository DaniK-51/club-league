"""Moderation flow integration tests."""

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
    Report,
    ReportLink,
    RulesVersion,
    User,
)
from src.models.enums import ClubCategory, ReportStatus, UserRole
from src.services.moderation_service import requires_comment, resolve_final_points


async def _wipe() -> None:
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(text("TRUNCATE sudo_actions, audit_logs RESTART IDENTITY CASCADE"))
        await session.execute(delete(ReportLink))
        await session.execute(delete(Report))
        await session.execute(delete(CriteriaRule))
        await session.execute(delete(Criteria))
        await session.execute(delete(RulesVersion))
        await session.execute(delete(ClubLeader))
        await session.execute(delete(User))
        await session.execute(delete(Club))
        await session.commit()


@pytest.fixture
async def mod_env(client: AsyncClient) -> AsyncIterator[dict[str, str]]:
    await _wipe()
    factory = get_session_factory()
    async with factory() as session:
        now = datetime.now(UTC)
        leader = User(
            sso_id="sso-mod-leader",
            email="modflow.leader@x.test",
            name="L",
            role=UserRole.CLUB_LEADER,
            can_sudo=False,
            created_at=now,
        )
        mod = User(
            sso_id="sso-mod-mod",
            email="modflow.mod@x.test",
            name="M",
            role=UserRole.MODERATOR,
            can_sudo=True,
            created_at=now,
        )
        session.add_all([leader, mod])
        await session.flush()
        club = Club(name="Mod Club", category=ClubCategory.SPORT)
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
            "leader": create_access_token(
                user_id=leader.id, role=UserRole.CLUB_LEADER, can_sudo=False
            ),
            "mod": create_access_token(
                user_id=mod.id, role=UserRole.MODERATOR, can_sudo=True
            ),
            "criteria_id": criteria.id,
        }
    await _wipe()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_submitted(client: AsyncClient, env: dict[str, str]) -> str:
    resp = await client.post(
        "/api/reports",
        headers=_auth(env["leader"]),
        json={
            "criteriaId": env["criteria_id"],
            "activityDate": "2026-09-01T12:00:00+00:00",
            "reportData": {"count": 1},
            "links": ["https://t.me/modflow/1"],
        },
    )
    report_id = resp.json()["data"]["id"]
    await client.post(f"/api/reports/{report_id}/submit", headers=_auth(env["leader"]))
    return report_id


async def test_approve_uses_calculated_points(client: AsyncClient, mod_env: dict[str, str]) -> None:
    report_id = await _create_submitted(client, mod_env)
    resp = await client.patch(
        f"/api/reports/{report_id}/moderate",
        headers=_auth(mod_env["mod"]),
        json={"status": "APPROVED", "comment": "ok"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "APPROVED"
    assert data["finalPoints"] == 250
    assert data["calculatedPoints"] == 250


async def test_approve_override_points_requires_comment(
    client: AsyncClient, mod_env: dict[str, str]
) -> None:
    report_id = await _create_submitted(client, mod_env)
    missing = await client.patch(
        f"/api/reports/{report_id}/moderate",
        headers=_auth(mod_env["mod"]),
        json={"status": "APPROVED", "finalPoints": 100},
    )
    assert missing.status_code == 400
    assert missing.json()["detail"]["error"]["code"] == "COMMENT_REQUIRED"

    ok = await client.patch(
        f"/api/reports/{report_id}/moderate",
        headers=_auth(mod_env["mod"]),
        json={"status": "APPROVED", "finalPoints": 100, "comment": "reduced"},
    )
    assert ok.status_code == 200
    assert ok.json()["data"]["finalPoints"] == 100


async def test_changes_required_requires_comment(
    client: AsyncClient, mod_env: dict[str, str]
) -> None:
    report_id = await _create_submitted(client, mod_env)
    resp = await client.patch(
        f"/api/reports/{report_id}/moderate",
        headers=_auth(mod_env["mod"]),
        json={"status": "CHANGES_REQUIRED"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"]["code"] == "COMMENT_REQUIRED"


async def test_close_sets_zero_points(client: AsyncClient, mod_env: dict[str, str]) -> None:
    report_id = await _create_submitted(client, mod_env)
    resp = await client.patch(
        f"/api/reports/{report_id}/moderate",
        headers=_auth(mod_env["mod"]),
        json={"status": "CLOSED", "comment": "nope"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["finalPoints"] == 0
    assert resp.json()["data"]["status"] == "CLOSED"


async def test_leader_cannot_moderate(client: AsyncClient, mod_env: dict[str, str]) -> None:
    report_id = await _create_submitted(client, mod_env)
    resp = await client.patch(
        f"/api/reports/{report_id}/moderate",
        headers=_auth(mod_env["leader"]),
        json={"status": "APPROVED"},
    )
    assert resp.status_code == 403


async def test_approve_from_draft_invalid(client: AsyncClient, mod_env: dict[str, str]) -> None:
    resp = await client.post(
        "/api/reports",
        headers=_auth(mod_env["leader"]),
        json={
            "criteriaId": mod_env["criteria_id"],
            "activityDate": "2026-09-01T12:00:00+00:00",
            "reportData": {"count": 1},
            "links": ["https://t.me/modflow/2"],
        },
    )
    report_id = resp.json()["data"]["id"]
    mod = await client.patch(
        f"/api/reports/{report_id}/moderate",
        headers=_auth(mod_env["mod"]),
        json={"status": "APPROVED"},
    )
    assert mod.status_code == 400
    assert mod.json()["detail"]["error"]["code"] == "INVALID_STATUS_TRANSITION"


async def test_dispute_and_moderator_review(client: AsyncClient, mod_env: dict[str, str]) -> None:
    report_id = await _create_submitted(client, mod_env)
    await client.patch(
        f"/api/reports/{report_id}/moderate",
        headers=_auth(mod_env["mod"]),
        json={"status": "APPROVED"},
    )
    dispute = await client.post(
        f"/api/reports/{report_id}/dispute",
        headers=_auth(mod_env["leader"]),
        json={"comment": "points too low"},
    )
    assert dispute.status_code == 200
    assert dispute.json()["data"]["status"] == "DISPUTED"

    review = await client.patch(
        f"/api/reports/{report_id}/moderate",
        headers=_auth(mod_env["mod"]),
        json={"status": "APPROVED", "finalPoints": 400, "comment": "bump"},
    )
    assert review.status_code == 200
    assert review.json()["data"]["finalPoints"] == 400


async def test_complete_approved(client: AsyncClient, mod_env: dict[str, str]) -> None:
    report_id = await _create_submitted(client, mod_env)
    await client.patch(
        f"/api/reports/{report_id}/moderate",
        headers=_auth(mod_env["mod"]),
        json={"status": "APPROVED"},
    )
    done = await client.post(
        f"/api/reports/{report_id}/complete",
        headers=_auth(mod_env["leader"]),
    )
    assert done.status_code == 200
    assert done.json()["data"]["status"] == "COMPLETED"


def test_resolve_final_points_helpers() -> None:
    assert resolve_final_points(calculated=10, override=None, target_status=ReportStatus.APPROVED) == 10
    assert resolve_final_points(calculated=10, override=5, target_status=ReportStatus.APPROVED) == 5
    assert resolve_final_points(calculated=10, override=None, target_status=ReportStatus.CLOSED) == 0
    assert requires_comment(
        target_status=ReportStatus.CHANGES_REQUIRED,
        calculated=1,
        final_points=1,
        comment="",
    )
    assert requires_comment(
        target_status=ReportStatus.APPROVED,
        calculated=10,
        final_points=5,
        comment="",
    )
    assert not requires_comment(
        target_status=ReportStatus.APPROVED,
        calculated=10,
        final_points=10,
        comment="",
    )
