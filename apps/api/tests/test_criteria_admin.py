"""Criteria catalog + admin rules CRUD + audit list."""

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
    Criteria,
    CriteriaRule,
    RulesVersion,
    User,
)
from src.models.enums import ClubCategory, UserRole


async def _wipe() -> None:
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(text("TRUNCATE sudo_actions, audit_logs RESTART IDENTITY CASCADE"))
        await session.execute(delete(CriteriaRule))
        await session.execute(delete(Criteria))
        await session.execute(delete(RulesVersion))
        await session.execute(delete(User))
        await session.execute(delete(Club))
        await session.commit()


@pytest.fixture
async def env(client: AsyncClient) -> AsyncIterator[dict[str, str]]:
    await _wipe()
    factory = get_session_factory()
    async with factory() as session:
        now = datetime.now(UTC)
        mod = User(
            sso_id="sso-cr-mod",
            email="cr.mod@x.test",
            name="M",
            role=UserRole.MODERATOR,
            can_sudo=True,
            created_at=now,
        )
        guest = User(
            sso_id="sso-cr-guest",
            email="cr.guest@x.test",
            name="G",
            role=UserRole.GUEST,
            can_sudo=False,
            created_at=now,
        )
        session.add_all([mod, guest])
        await session.flush()
        version = RulesVersion(semester="2026-fall", valid_from=now)
        session.add(version)
        await session.flush()
        c8 = Criteria(code="C8", name_ru="Образовательный контент", name_en="Educational", category=None)
        s1 = Criteria(code="S1", name_ru="Спорт", name_en="Sport", category=ClubCategory.SPORT)
        session.add_all([c8, s1])
        await session.flush()
        rule = CriteriaRule(
            criteria_id=c8.id,
            rule_type="tiered",
            config={"tiers": [{"count": 1, "pts": 250}]},
            priority=0,
            version_id=version.id,
        )
        session.add(rule)
        await session.commit()
        yield {
            "mod": create_access_token(user_id=mod.id, role=UserRole.MODERATOR, can_sudo=True),
            "guest": create_access_token(user_id=guest.id, role=UserRole.GUEST, can_sudo=False),
            "rule_id": rule.id,
            "c8_id": c8.id,
        }
    await _wipe()


def _auth(t: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {t}"}


async def test_public_criteria_list(client: AsyncClient, env: dict[str, str]) -> None:
    resp = await client.get("/api/criteria")
    assert resp.status_code == 200
    codes = [c["code"] for c in resp.json()["data"]]
    assert "C8" in codes
    assert "S1" in codes
    c8 = next(c for c in resp.json()["data"] if c["code"] == "C8")
    assert c8["rules"][0]["ruleType"] == "tiered"
    assert c8["rules"][0]["config"]["tiers"][0]["pts"] == 250


async def test_criteria_filter_by_category(client: AsyncClient, env: dict[str, str]) -> None:
    resp = await client.get("/api/criteria", params={"category": "SPORT"})
    codes = [c["code"] for c in resp.json()["data"]]
    assert codes == ["S1"]


async def test_guest_cannot_update_rule(client: AsyncClient, env: dict[str, str]) -> None:
    resp = await client.patch(
        f"/api/admin/rules/{env['rule_id']}",
        headers=_auth(env["guest"]),
        json={"priority": 1},
    )
    assert resp.status_code == 403


async def test_update_rule_config_and_audit(client: AsyncClient, env: dict[str, str]) -> None:
    resp = await client.patch(
        f"/api/admin/rules/{env['rule_id']}",
        headers=_auth(env["mod"]),
        json={"config": {"tiers": [{"count": 1, "pts": 300}]}},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["config"]["tiers"][0]["pts"] == 300

    audit = await client.get(
        "/api/admin/audit",
        headers=_auth(env["mod"]),
        params={"entityType": "rule", "entityId": env["rule_id"]},
    )
    assert audit.status_code == 200
    items = audit.json()["data"]["items"]
    assert any(i["action"] == "updated" for i in items)


async def test_update_rule_invalid_config(client: AsyncClient, env: dict[str, str]) -> None:
    resp = await client.patch(
        f"/api/admin/rules/{env['rule_id']}",
        headers=_auth(env["mod"]),
        json={"config": {"tiers": []}},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_audit_requires_moderator(client: AsyncClient, env: dict[str, str]) -> None:
    resp = await client.get("/api/admin/audit", headers=_auth(env["guest"]))
    assert resp.status_code == 403
