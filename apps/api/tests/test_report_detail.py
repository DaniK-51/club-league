"""Tests for frontend report-detail requests: reportData, moderator edit, comments."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

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
from src.models.enums import ClubCategory, UserRole


async def _wipe() -> None:
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(text("TRUNCATE sudo_actions, audit_logs RESTART IDENTITY CASCADE"))
        await session.execute(text("TRUNCATE archive_batches RESTART IDENTITY CASCADE"))
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
async def env(client: AsyncClient) -> AsyncIterator[dict[str, str]]:
    await _wipe()
    factory = get_session_factory()
    async with factory() as session:
        now = datetime.now(UTC)
        leader = User(
            sso_id="sso-rd-leader",
            email="rd.leader@x.test",
            name="Leader",
            role=UserRole.CLUB_LEADER,
            can_sudo=False,
            created_at=now,
        )
        mod = User(
            sso_id="sso-rd-mod",
            email="rd.mod@x.test",
            name="Mod",
            role=UserRole.MODERATOR,
            can_sudo=True,
            created_at=now,
        )
        guest = User(
            sso_id="sso-rd-guest",
            email="rd.guest@x.test",
            name="Guest",
            role=UserRole.GUEST,
            can_sudo=False,
            created_at=now,
        )
        session.add_all([leader, mod, guest])
        await session.flush()
        club = Club(name="RD Club", category=ClubCategory.SPORT)
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
        from zoneinfo import ZoneInfo

        tz = ZoneInfo("Europe/Moscow")
        now_p = datetime.now(UTC)
        for pname, ps, pe in [
            ("2026-fall", datetime(2026, 9, 1, tzinfo=tz), datetime(2027, 1, 1, tzinfo=tz)),
            ("2026-spring", datetime(2026, 1, 1, tzinfo=tz), datetime(2026, 6, 1, tzinfo=tz)),
        ]:
            session.add(
                Period(
                    name=pname,
                    start_date=ps,
                    end_date=pe,
                    is_archived=False,
                    created_at=now_p,
                    updated_at=now_p,
                )
            )
        await session.commit()
        yield {
            "leader": create_access_token(user_id=leader.id, role=UserRole.CLUB_LEADER, can_sudo=False),
            "mod": create_access_token(user_id=mod.id, role=UserRole.MODERATOR, can_sudo=True),
            "guest": create_access_token(user_id=guest.id, role=UserRole.GUEST, can_sudo=False),
            "criteria_id": criteria.id,
        }
    await _wipe()


def _auth(t: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {t}"}


async def _create_draft(client: AsyncClient, env: dict[str, str], *, count: int = 1) -> str:
    resp = await client.post(
        "/api/reports",
        headers=_auth(env["leader"]),
        json={
            "criteriaId": env["criteria_id"],
            "activityDate": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
            "reportData": {"count": count},
            "links": ["https://t.me/rd/1"],
        },
    )
    assert resp.status_code == 201
    return resp.json()["data"]["id"]


async def _submit(client: AsyncClient, env: dict[str, str], rid: str) -> None:
    r = await client.post(f"/api/reports/{rid}/submit", headers=_auth(env["leader"]))
    assert r.status_code == 200


# ─── reportData in ReportResponse ───────────────────────────────────────────


async def test_report_response_includes_report_data(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create_draft(client, env, count=3)
    resp = await client.get(f"/api/reports/{rid}", headers=_auth(env["leader"]))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["reportData"] == {"count": 3}
    assert data["calculatedPoints"] == 500


async def test_list_includes_report_data(client: AsyncClient, env: dict[str, str]) -> None:
    await _create_draft(client, env, count=2)
    resp = await client.get("/api/reports", headers=_auth(env["leader"]))
    assert resp.status_code == 200
    assert resp.json()["data"][0]["reportData"] == {"count": 2}


# ─── Moderator edit reportData ──────────────────────────────────────────────


async def test_moderator_edits_report_data_on_moderation(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create_draft(client, env, count=1)
    await _submit(client, env, rid)  # ON_MODERATION

    patch = await client.patch(
        f"/api/reports/{rid}",
        headers=_auth(env["mod"]),
        json={"reportData": {"count": 3}},
    )
    assert patch.status_code == 200
    data = patch.json()["data"]
    assert data["reportData"] == {"count": 3}
    assert data["calculatedPoints"] == 500
    assert data["status"] == "ON_MODERATION"


async def test_moderator_edits_report_data_on_disputed(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create_draft(client, env)
    await _submit(client, env, rid)
    # Approve → dispute
    await client.patch(
        f"/api/reports/{rid}/moderate",
        headers=_auth(env["mod"]),
        json={"status": "APPROVED", "comment": "ok"},
    )
    await client.post(
        f"/api/reports/{rid}/dispute",
        headers=_auth(env["leader"]),
        json={"comment": "too low"},
    )

    patch = await client.patch(
        f"/api/reports/{rid}",
        headers=_auth(env["mod"]),
        json={"reportData": {"count": 4}},
    )
    assert patch.status_code == 200
    assert patch.json()["data"]["reportData"] == {"count": 4}


async def test_moderator_cannot_edit_draft(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create_draft(client, env)
    patch = await client.patch(
        f"/api/reports/{rid}",
        headers=_auth(env["mod"]),
        json={"reportData": {"count": 2}},
    )
    assert patch.status_code == 400
    assert patch.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


async def test_moderator_cannot_edit_links(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create_draft(client, env)
    await _submit(client, env, rid)
    patch = await client.patch(
        f"/api/reports/{rid}",
        headers=_auth(env["mod"]),
        json={"links": ["https://t.me/new"]},
    )
    assert patch.status_code == 403


async def test_leader_still_edits_draft(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create_draft(client, env, count=1)
    patch = await client.patch(
        f"/api/reports/{rid}",
        headers=_auth(env["leader"]),
        json={"reportData": {"count": 2}},
    )
    assert patch.status_code == 200
    assert patch.json()["data"]["calculatedPoints"] == 500


# ─── POST /comments ─────────────────────────────────────────────────────────


async def test_post_comment_leader(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create_draft(client, env)
    resp = await client.post(
        f"/api/reports/{rid}/comments",
        headers=_auth(env["leader"]),
        json={"body": "Hello from leader"},
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["action"] == "comment"
    assert data["body"] == "Hello from leader"
    assert data["authorRole"] == "CLUB_LEADER"


async def test_post_comment_moderator(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create_draft(client, env)
    await _submit(client, env, rid)
    resp = await client.post(
        f"/api/reports/{rid}/comments",
        headers=_auth(env["mod"]),
        json={"body": "Moderator note"},
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["authorRole"] == "MODERATOR"


async def test_post_comment_guest_forbidden(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create_draft(client, env)
    resp = await client.post(
        f"/api/reports/{rid}/comments",
        headers=_auth(env["guest"]),
        json={"body": "Guest comment"},
    )
    assert resp.status_code == 403


async def test_post_comment_empty_body(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create_draft(client, env)
    resp = await client.post(
        f"/api/reports/{rid}/comments",
        headers=_auth(env["leader"]),
        json={"body": ""},
    )
    assert resp.status_code == 422


async def test_post_comment_on_archived(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create_draft(client, env)
    await _submit(client, env, rid)
    await client.patch(
        f"/api/reports/{rid}/moderate",
        headers=_auth(env["mod"]),
        json={"status": "APPROVED", "comment": "ok"},
    )
    await client.post(f"/api/reports/{rid}/complete", headers=_auth(env["leader"]))
    await client.post(
        "/api/reports/archive",
        headers=_auth(env["mod"]),
        params={"period": "2026-fall"},
    )
    resp = await client.post(
        f"/api/reports/{rid}/comments",
        headers=_auth(env["leader"]),
        json={"body": "Too late"},
    )
    assert resp.status_code == 400


# ─── GET /comments includes action=comment ──────────────────────────────────


async def test_comments_thread_includes_regular_comments(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create_draft(client, env)
    await _submit(client, env, rid)
    await client.patch(
        f"/api/reports/{rid}/moderate",
        headers=_auth(env["mod"]),
        json={"status": "APPROVED", "comment": "Looks good"},
    )
    await client.post(
        f"/api/reports/{rid}/comments",
        headers=_auth(env["leader"]),
        json={"body": "Thanks!"},
    )

    resp = await client.get(f"/api/reports/{rid}/comments", headers=_auth(env["mod"]))
    assert resp.status_code == 200
    entries = resp.json()["data"]
    actions = [e["action"] for e in entries]
    assert "comment" in actions
    # Regular comment body comes from new_value.body
    comment = next(e for e in entries if e["action"] == "comment")
    assert comment["body"] == "Thanks!"
    # Moderation comment still works
    mod_entry = next(e for e in entries if e["action"] == "status_changed" and "Looks good" in e["body"])
    assert mod_entry is not None
