"""E2E tests: full user journeys through HTTP API.

Covers flows not in test_e2e.py: changes_required, overdue,
ACL boundaries, sudo restore/override, combined caps, sync, i18n.
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
async def env(client: AsyncClient) -> AsyncIterator[dict[str, str]]:
    await _wipe()
    factory = get_session_factory()
    async with factory() as session:
        now = datetime.now(UTC)
        leader = User(
            sso_id="sso-e2e2-leader",
            email="e2e2.leader@x.test",
            name="Leader",
            role=UserRole.CLUB_LEADER,
            can_sudo=False,
            created_at=now,
        )
        other_leader = User(
            sso_id="sso-e2e2-other",
            email="e2e2.other@x.test",
            name="Other",
            role=UserRole.CLUB_LEADER,
            can_sudo=False,
            created_at=now,
        )
        mod = User(
            sso_id="sso-e2e2-mod",
            email="e2e2.mod@x.test",
            name="Mod",
            role=UserRole.MODERATOR,
            can_sudo=True,
            created_at=now,
        )
        guest = User(
            sso_id="sso-e2e2-guest",
            email="e2e2.guest@x.test",
            name="Guest",
            role=UserRole.GUEST,
            can_sudo=False,
            created_at=now,
        )
        session.add_all([leader, other_leader, mod, guest])
        await session.flush()
        club = Club(name="Club A", category=ClubCategory.SPORT)
        other_club = Club(name="Club B", category=ClubCategory.TECH)
        session.add_all([club, other_club])
        await session.flush()
        session.add(ClubLeader(club_id=club.id, user_id=leader.id, is_primary=True))
        session.add(ClubLeader(club_id=other_club.id, user_id=other_leader.id, is_primary=True))
        version = RulesVersion(semester="2026-fall", valid_from=now)
        session.add(version)
        await session.flush()
        c8 = Criteria(code="C8", name_ru="Educational", name_en="Educational", category=None)
        c4 = Criteria(code="C4", name_ru="Social post", name_en="Social post", category=None)
        c5 = Criteria(code="C5", name_ru="Social aesthetics", name_en="Social aesthetics", category=None)
        g1 = Criteria(code="G1", name_ru="Social cap", name_en="Social cap", category=None)
        session.add_all([c8, c4, c5, g1])
        await session.flush()
        session.add_all(
            [
                CriteriaRule(
                    criteria_id=c8.id,
                    rule_type="tiered",
                    config={"tiers": [{"count": 1, "pts": 250}, {"min": 2, "max": 5, "pts": 500}]},
                    priority=0,
                    version_id=version.id,
                ),
                CriteriaRule(
                    criteria_id=c4.id,
                    rule_type="binary_with_monthly_cap",
                    config={"options": {"informative": 500}, "monthly_cap": 500},
                    priority=0,
                    version_id=version.id,
                ),
                CriteriaRule(
                    criteria_id=c5.id,
                    rule_type="binary",
                    config={"standard": 200},
                    priority=0,
                    version_id=version.id,
                ),
                CriteriaRule(
                    criteria_id=g1.id,
                    rule_type="combined_cap",
                    config={
                        "criteria_codes": ["C4", "C5"],
                        "max_percent_of_total_monthly": 15,
                    },
                    priority=0,
                    version_id=version.id,
                ),
            ]
        )
        await add_default_periods(session, now=now)
        await session.commit()
        yield {
            "leader": create_access_token(user_id=leader.id, role=UserRole.CLUB_LEADER, can_sudo=False),
            "other": create_access_token(user_id=other_leader.id, role=UserRole.CLUB_LEADER, can_sudo=False),
            "mod": create_access_token(user_id=mod.id, role=UserRole.MODERATOR, can_sudo=True),
            "guest": create_access_token(user_id=guest.id, role=UserRole.GUEST, can_sudo=False),
            "c8": c8.id,
            "c4": c4.id,
            "c5": c5.id,
            "club": club.id,
            "other_club": other_club.id,
        }
    await _wipe()


async def _create(
    client: AsyncClient,
    token: str,
    criteria_id: str,
    *,
    data: dict | None = None,
    links: list[str] | None = None,
    days_ago: int = 1,
) -> str:
    resp = await client.post(
        "/api/reports",
        headers=_auth(token),
        json={
            "criteriaId": criteria_id,
            "activityDate": (datetime.now(UTC) - timedelta(days=days_ago)).isoformat(),
            "reportData": data or {"count": 1},
            "links": links or ["https://t.me/e2e2/1"],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


async def _submit(client: AsyncClient, token: str, rid: str) -> None:
    r = await client.post(f"/api/reports/{rid}/submit", headers=_auth(token))
    assert r.status_code == 200, r.text


async def _approve(client: AsyncClient, token: str, rid: str, *, points: int | None = None) -> None:
    body: dict = {"status": "APPROVED", "comment": "ok"}
    if points is not None:
        body["finalPoints"] = points
    r = await client.patch(f"/api/reports/{rid}/moderate", headers=_auth(token), json=body)
    assert r.status_code == 200, r.text


# ─── CHANGES_REQUIRED loop ──────────────────────────────────────────────────


async def test_changes_required_resubmit_cycle(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create(client, env["leader"], env["c8"])
    await _submit(client, env["leader"], rid)

    # Moderator requests changes
    changes = await client.patch(
        f"/api/reports/{rid}/moderate",
        headers=_auth(env["mod"]),
        json={"status": "CHANGES_REQUIRED", "comment": "Need more links"},
    )
    assert changes.status_code == 200
    assert changes.json()["data"]["status"] == "CHANGES_REQUIRED"

    # Leader can edit
    edit = await client.patch(
        f"/api/reports/{rid}",
        headers=_auth(env["leader"]),
        json={"reportData": {"count": 3}, "links": ["https://t.me/e2e2/1", "https://t.me/e2e2/2"]},
    )
    assert edit.status_code == 200
    assert edit.json()["data"]["calculatedPoints"] == 500

    # Resubmit
    await _submit(client, env["leader"], rid)
    get_r = await client.get(f"/api/reports/{rid}", headers=_auth(env["leader"]))
    assert get_r.json()["data"]["status"] == "ON_MODERATION"

    # Approve
    await _approve(client, env["mod"], rid)
    get_r = await client.get(f"/api/reports/{rid}", headers=_auth(env["leader"]))
    assert get_r.json()["data"]["status"] == "APPROVED"
    assert get_r.json()["data"]["finalPoints"] == 500


# ─── Soft deadline (overdue) ────────────────────────────────────────────────


async def test_overdue_report_flagged_but_allowed(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create(client, env["leader"], env["c8"], days_ago=10)
    get_r = await client.get(f"/api/reports/{rid}", headers=_auth(env["leader"]))
    assert get_r.status_code == 200
    assert get_r.json()["data"]["isOverdue"] is True
    # Still allowed to submit
    await _submit(client, env["leader"], rid)


# ─── ACL boundaries ─────────────────────────────────────────────────────────


async def test_moderator_cannot_create_report(client: AsyncClient, env: dict[str, str]) -> None:
    resp = await client.post(
        "/api/reports",
        headers=_auth(env["mod"]),
        json={
            "criteriaId": env["c8"],
            "activityDate": datetime.now(UTC).isoformat(),
            "reportData": {"count": 1},
            "links": ["https://t.me/x"],
        },
    )
    assert resp.status_code == 403


async def test_guest_cannot_create_report(client: AsyncClient, env: dict[str, str]) -> None:
    resp = await client.post(
        "/api/reports",
        headers=_auth(env["guest"]),
        json={
            "criteriaId": env["c8"],
            "activityDate": datetime.now(UTC).isoformat(),
            "reportData": {"count": 1},
            "links": ["https://t.me/x"],
        },
    )
    assert resp.status_code == 403


async def test_other_leader_cannot_view_report(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create(client, env["leader"], env["c8"])
    resp = await client.get(f"/api/reports/{rid}", headers=_auth(env["other"]))
    assert resp.status_code == 403


async def test_leader_cannot_moderate(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create(client, env["leader"], env["c8"])
    await _submit(client, env["leader"], rid)
    resp = await client.patch(
        f"/api/reports/{rid}/moderate",
        headers=_auth(env["leader"]),
        json={"status": "APPROVED"},
    )
    assert resp.status_code == 403


async def test_leader_list_only_own_club(client: AsyncClient, env: dict[str, str]) -> None:
    await _create(client, env["leader"], env["c8"])
    own = await client.get("/api/reports", headers=_auth(env["leader"]))
    assert len(own.json()["data"]) == 1
    other = await client.get("/api/reports", headers=_auth(env["other"]))
    assert other.json()["data"] == []


async def test_guest_list_empty(client: AsyncClient, env: dict[str, str]) -> None:
    await _create(client, env["leader"], env["c8"])
    resp = await client.get("/api/reports", headers=_auth(env["guest"]))
    assert resp.json()["data"] == []


# ─── Validation & links ─────────────────────────────────────────────────────


async def test_bad_domain_rejected(client: AsyncClient, env: dict[str, str]) -> None:
    resp = await client.post(
        "/api/reports",
        headers=_auth(env["leader"]),
        json={
            "criteriaId": env["c8"],
            "activityDate": datetime.now(UTC).isoformat(),
            "reportData": {"count": 1},
            "links": ["https://evil.example.com/"],
        },
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "DOMAIN_NOT_ALLOWED"


async def test_duplicate_links_rejected(client: AsyncClient, env: dict[str, str]) -> None:
    resp = await client.post(
        "/api/reports",
        headers=_auth(env["leader"]),
        json={
            "criteriaId": env["c8"],
            "activityDate": datetime.now(UTC).isoformat(),
            "reportData": {"count": 1},
            "links": ["https://t.me/same", "https://t.me/same"],
        },
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "DUPLICATE_LINK"


async def test_empty_body_validation_error(client: AsyncClient, env: dict[str, str]) -> None:
    resp = await client.post("/api/reports", headers=_auth(env["leader"]), json={})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_edit_after_submit_fails(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create(client, env["leader"], env["c8"])
    await _submit(client, env["leader"], rid)
    resp = await client.patch(
        f"/api/reports/{rid}",
        headers=_auth(env["leader"]),
        json={"reportData": {"count": 2}},
    )
    assert resp.status_code == 400


async def test_delete_only_draft(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create(client, env["leader"], env["c8"])
    await _submit(client, env["leader"], rid)
    resp = await client.delete(f"/api/reports/{rid}", headers=_auth(env["leader"]))
    assert resp.status_code == 400


# ─── Sudo restore & override ────────────────────────────────────────────────


async def test_sudo_restore_deleted(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create(client, env["leader"], env["c8"])
    await client.delete(f"/api/reports/{rid}", headers=_auth(env["leader"]))
    gone = await client.get(f"/api/reports/{rid}", headers=_auth(env["leader"]))
    assert gone.status_code == 404

    restore = await client.post(
        "/api/admin/sudo",
        headers=_auth(env["mod"]),
        json={
            "action": "restore_deleted",
            "targetReportId": rid,
            "newValue": True,
            "reason": "accidental delete",
        },
    )
    assert restore.status_code == 200
    again = await client.get(f"/api/reports/{rid}", headers=_auth(env["leader"]))
    assert again.status_code == 200
    assert again.json()["data"]["status"] == "DRAFT"


async def test_sudo_override_points(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create(client, env["leader"], env["c8"])
    await _submit(client, env["leader"], rid)
    resp = await client.post(
        "/api/admin/sudo",
        headers=_auth(env["mod"]),
        json={
            "action": "override_points",
            "targetReportId": rid,
            "newValue": 999,
            "reason": "manual adjustment",
        },
    )
    assert resp.status_code == 200
    get_r = await client.get(f"/api/reports/{rid}", headers=_auth(env["mod"]))
    assert get_r.json()["data"]["finalPoints"] == 999


async def test_sudo_requires_reason(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create(client, env["leader"], env["c8"])
    resp = await client.post(
        "/api/admin/sudo",
        headers=_auth(env["mod"]),
        json={
            "action": "force_status",
            "targetReportId": rid,
            "newValue": "COMPLETED",
            "reason": "   ",
        },
    )
    assert resp.status_code == 400


# ─── Combined cap C4+C5 in rating ───────────────────────────────────────────


async def test_combined_cap_applies_in_rating(client: AsyncClient, env: dict[str, str]) -> None:
    """C4=500, C5=200, C8=250. Uncapped total=950. Budget=15%→142. Social capped to 142."""
    rid_c4 = await _create(client, env["leader"], env["c4"], data={"variant": "informative"})
    rid_c5 = await _create(client, env["leader"], env["c5"], data={"variant": "standard"})
    rid_c8 = await _create(client, env["leader"], env["c8"], data={"count": 1})
    for rid in (rid_c4, rid_c5, rid_c8):
        await _submit(client, env["leader"], rid)
        await _approve(client, env["mod"], rid)
        await client.post(f"/api/reports/{rid}/complete", headers=_auth(env["leader"]))

    rating = await client.get("/api/rating", headers=_auth(env["mod"]))
    clubs = rating.json()["data"]["clubs"]
    assert len(clubs) == 1
    breakdown = clubs[0]["breakdown"]
    assert breakdown["C8"] == 250
    # Social capped: uncapped total = 500+200+250 = 950; budget = 15% of 950 = 142
    social = breakdown.get("C4", 0) + breakdown.get("C5", 0)
    assert social == 142
    assert clubs[0]["totalPoints"] == 250 + 142


# ─── Sync force & status ────────────────────────────────────────────────────


async def test_sync_force_and_status(client: AsyncClient, env: dict[str, str]) -> None:
    force = await client.post(
        "/api/admin/sync/force",
        headers=_auth(env["mod"]),
        json={"semester": "2026-fall"},
    )
    assert force.status_code == 200
    assert force.json()["data"]["status"] == "queued"

    status = await client.get("/api/admin/sync/status", headers=_auth(env["mod"]))
    assert status.status_code == 200
    assert "debounceSeconds" in status.json()["data"]


async def test_sync_requires_moderator(client: AsyncClient, env: dict[str, str]) -> None:
    resp = await client.post("/api/admin/sync/force", headers=_auth(env["leader"]), json={})
    assert resp.status_code == 403


# ─── i18n ───────────────────────────────────────────────────────────────────


async def test_i18n_ru_error_message(client: AsyncClient, env: dict[str, str]) -> None:
    resp = await client.get("/api/users/me", headers={"Accept-Language": "ru-RU"})
    assert resp.status_code == 401
    assert resp.json()["error"]["message"] == "Отсутствует bearer token"


async def test_i18n_en_error_message(client: AsyncClient, env: dict[str, str]) -> None:
    resp = await client.get("/api/users/me", headers={"Accept-Language": "en-US"})
    assert resp.status_code == 401
    assert resp.json()["error"]["message"] == "Missing bearer token"


# ─── Admin rules CRUD ───────────────────────────────────────────────────────


async def test_admin_update_rule_config(client: AsyncClient, env: dict[str, str]) -> None:
    # Get rule id from criteria
    criteria = await client.get("/api/criteria")
    c8 = next(c for c in criteria.json()["data"] if c["code"] == "C8")
    rule_id = c8["rules"][0]["id"]

    resp = await client.patch(
        f"/api/admin/rules/{rule_id}",
        headers=_auth(env["mod"]),
        json={"config": {"tiers": [{"count": 1, "pts": 300}]}},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["config"]["tiers"][0]["pts"] == 300

    # New report uses updated rule
    rid = await _create(client, env["leader"], env["c8"])
    get_r = await client.get(f"/api/reports/{rid}", headers=_auth(env["leader"]))
    assert get_r.json()["data"]["calculatedPoints"] == 300


async def test_admin_audit_list(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create(client, env["leader"], env["c8"])
    await _submit(client, env["leader"], rid)
    await _approve(client, env["mod"], rid)

    resp = await client.get(
        "/api/admin/audit",
        headers=_auth(env["mod"]),
        params={"entityType": "report", "entityId": rid},
    )
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 2
    actions = [i["action"] for i in items]
    assert "created" in actions
    assert "status_changed" in actions


# ─── Auth refresh ───────────────────────────────────────────────────────────


async def test_refresh_token_flow(client: AsyncClient, env: dict[str, str]) -> None:
    # Use SSO callback to get tokens — monkeypatch not needed if we craft refresh
    # directly via security helpers
    from sqlalchemy import select
    from src.core.security import create_refresh_token

    factory = get_session_factory()
    async with factory() as session:
        leader = (
            await session.execute(select(User).where(User.email == "e2e2.leader@x.test"))
        ).scalar_one()
        refresh = create_refresh_token(user_id=leader.id)

    resp = await client.post("/api/auth/refresh", json={"refreshToken": refresh})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["accessToken"]
    assert data["refreshToken"]
    assert data["user"]["email"] == "e2e2.leader@x.test"
