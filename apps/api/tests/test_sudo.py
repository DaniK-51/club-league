"""Sudo mode integration tests (force_status, restore_deleted, override_points)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select, text
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
    SudoAction,
    User,
)
from src.models.enums import ClubCategory, UserRole


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
async def sudo_env(client: AsyncClient) -> AsyncIterator[dict[str, str]]:
    await _wipe()
    factory = get_session_factory()
    async with factory() as session:
        now = datetime.now(UTC)
        leader = User(
            sso_id="sso-sudo-leader",
            email="sudo.leader@x.test",
            name="L",
            role=UserRole.CLUB_LEADER,
            can_sudo=False,
            created_at=now,
        )
        mod = User(
            sso_id="sso-sudo-mod",
            email="sudo.mod@x.test",
            name="M",
            role=UserRole.MODERATOR,
            can_sudo=True,
            created_at=now,
        )
        mod_no_sudo = User(
            sso_id="sso-sudo-mod2",
            email="sudo.mod2@x.test",
            name="M2",
            role=UserRole.MODERATOR,
            can_sudo=False,
            created_at=now,
        )
        session.add_all([leader, mod, mod_no_sudo])
        await session.flush()
        club = Club(name="Sudo Club", category=ClubCategory.TECH)
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
        await session.commit()
        yield {
            "leader": create_access_token(
                user_id=leader.id, role=UserRole.CLUB_LEADER, can_sudo=False
            ),
            "sudo": create_access_token(
                user_id=mod.id, role=UserRole.MODERATOR, can_sudo=True
            ),
            "mod_no_sudo": create_access_token(
                user_id=mod_no_sudo.id, role=UserRole.MODERATOR, can_sudo=False
            ),
            "criteria_id": criteria.id,
        }
    await _wipe()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_draft(client: AsyncClient, env: dict[str, str], *, submit: bool = False) -> str:
    resp = await client.post(
        "/api/reports",
        headers=_auth(env["leader"]),
        json={
            "criteriaId": env["criteria_id"],
            "activityDate": "2026-09-01T12:00:00+00:00",
            "reportData": {"count": 1},
            "links": ["https://t.me/sudo/1"],
        },
    )
    report_id = resp.json()["data"]["id"]
    if submit:
        await client.post(f"/api/reports/{report_id}/submit", headers=_auth(env["leader"]))
    return report_id


async def test_force_status_skips_state_machine(
    client: AsyncClient, sudo_env: dict[str, str]
) -> None:
    report_id = await _create_draft(client, sudo_env)
    # DRAFT → COMPLETED is illegal without sudo
    resp = await client.post(
        "/api/admin/sudo",
        headers=_auth(sudo_env["sudo"]),
        json={
            "action": "force_status",
            "targetReportId": report_id,
            "newValue": "COMPLETED",
            "reason": "fix stuck report",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["status"] == "COMPLETED"
    assert data["action"] == "force_status"


async def test_restore_deleted(client: AsyncClient, sudo_env: dict[str, str]) -> None:
    report_id = await _create_draft(client, sudo_env)
    await client.delete(f"/api/reports/{report_id}", headers=_auth(sudo_env["leader"]))

    gone = await client.get(f"/api/reports/{report_id}", headers=_auth(sudo_env["leader"]))
    assert gone.status_code == 404

    restored = await client.post(
        "/api/admin/sudo",
        headers=_auth(sudo_env["sudo"]),
        json={
            "action": "restore_deleted",
            "targetReportId": report_id,
            "newValue": True,
            "reason": "accidental delete",
        },
    )
    assert restored.status_code == 200
    assert restored.json()["data"]["isDeleted"] is False

    again = await client.get(f"/api/reports/{report_id}", headers=_auth(sudo_env["leader"]))
    assert again.status_code == 200


async def test_override_points(client: AsyncClient, sudo_env: dict[str, str]) -> None:
    report_id = await _create_draft(client, sudo_env, submit=True)
    resp = await client.post(
        "/api/admin/sudo",
        headers=_auth(sudo_env["sudo"]),
        json={
            "action": "override_points",
            "targetReportId": report_id,
            "newValue": 999,
            "reason": "manual adjustment",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["finalPoints"] == 999

    factory = get_session_factory()
    async with factory() as session:
        rows = (
            await session.execute(
                select(SudoAction).where(SudoAction.entity_id == report_id)
            )
        ).scalars().all()
        assert len(rows) == 1
        assert rows[0].reason == "manual adjustment"
        assert rows[0].action == "override_points"


async def test_sudo_requires_can_sudo(client: AsyncClient, sudo_env: dict[str, str]) -> None:
    report_id = await _create_draft(client, sudo_env)
    resp = await client.post(
        "/api/admin/sudo",
        headers=_auth(sudo_env["mod_no_sudo"]),
        json={
            "action": "force_status",
            "targetReportId": report_id,
            "newValue": "COMPLETED",
            "reason": "nope",
        },
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["error"]["code"] == "SUDO_REQUIRED"


async def test_sudo_requires_reason(client: AsyncClient, sudo_env: dict[str, str]) -> None:
    report_id = await _create_draft(client, sudo_env)
    resp = await client.post(
        "/api/admin/sudo",
        headers=_auth(sudo_env["sudo"]),
        json={
            "action": "force_status",
            "targetReportId": report_id,
            "newValue": "COMPLETED",
            "reason": "   ",
        },
    )
    assert resp.status_code == 400


async def test_leader_cannot_sudo(client: AsyncClient, sudo_env: dict[str, str]) -> None:
    report_id = await _create_draft(client, sudo_env)
    resp = await client.post(
        "/api/admin/sudo",
        headers=_auth(sudo_env["leader"]),
        json={
            "action": "force_status",
            "targetReportId": report_id,
            "newValue": "COMPLETED",
            "reason": "hack",
        },
    )
    assert resp.status_code == 403


async def test_restore_not_deleted_fails(client: AsyncClient, sudo_env: dict[str, str]) -> None:
    report_id = await _create_draft(client, sudo_env)
    resp = await client.post(
        "/api/admin/sudo",
        headers=_auth(sudo_env["sudo"]),
        json={
            "action": "restore_deleted",
            "targetReportId": report_id,
            "newValue": True,
            "reason": "noop",
        },
    )
    assert resp.status_code == 400
