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
async def reports_env(client: AsyncClient) -> AsyncIterator[dict[str, str]]:
    await _wipe()
    factory = get_session_factory()
    async with factory() as session:
        now = datetime.now(UTC)
        leader = User(
            sso_id="sso-rep-leader",
            email="rep.leader@innopolis.university",
            name="Rep Leader",
            role=UserRole.CLUB_LEADER,
            can_sudo=False,
            created_at=now,
        )
        other = User(
            sso_id="sso-rep-other",
            email="rep.other@innopolis.university",
            name="Other Leader",
            role=UserRole.CLUB_LEADER,
            can_sudo=False,
            created_at=now,
        )
        mod = User(
            sso_id="sso-rep-mod",
            email="rep.mod@innopolis.university",
            name="Rep Mod",
            role=UserRole.MODERATOR,
            can_sudo=True,
            created_at=now,
        )
        session.add_all([leader, other, mod])
        await session.flush()

        club = Club(name="Report Club", category=ClubCategory.SPORT)
        other_club = Club(name="Other Club", category=ClubCategory.TECH)
        session.add_all([club, other_club])
        await session.flush()

        session.add(ClubLeader(club_id=club.id, user_id=leader.id, is_primary=True))
        session.add(ClubLeader(club_id=other_club.id, user_id=other.id, is_primary=True))

        version = RulesVersion(semester="2026-fall", valid_from=now)
        session.add(version)
        await session.flush()

        criteria = Criteria(
            code="C8",
            name_ru="Образовательный контент",
            name_en="Educational content",
            category=None,
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
                        {"min": 6, "max": 10, "pts": 800},
                        {"min": 11, "max": None, "pts": 1000},
                    ]
                },
                priority=0,
                version_id=version.id,
            )
        )
        await session.commit()

        yield {
            "leader_token": create_access_token(
                user_id=leader.id, role=UserRole.CLUB_LEADER, can_sudo=False
            ),
            "other_token": create_access_token(
                user_id=other.id, role=UserRole.CLUB_LEADER, can_sudo=False
            ),
            "mod_token": create_access_token(
                user_id=mod.id, role=UserRole.MODERATOR, can_sudo=True
            ),
            "criteria_id": criteria.id,
            "club_id": club.id,
        }

    await _wipe()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_create_report_calculates_points_and_flags_overdue(
    client: AsyncClient, reports_env: dict[str, str]
) -> None:
    old_date = (datetime.now(UTC) - timedelta(days=10)).date().isoformat()
    resp = await client.post(
        "/api/reports",
        headers=_auth(reports_env["leader_token"]),
        json={
            "criteriaId": reports_env["criteria_id"],
            "activityDate": f"{old_date}T12:00:00+00:00",
            "reportData": {"count": 3},
            "links": ["https://docs.google.com/document/d/xyz"],
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert data["status"] == "DRAFT"
    assert data["calculatedPoints"] == 500
    assert data["isOverdue"] is True
    assert data["links"][0]["domain"] == "docs.google.com"


async def test_create_rejects_bad_domain(
    client: AsyncClient, reports_env: dict[str, str]
) -> None:
    resp = await client.post(
        "/api/reports",
        headers=_auth(reports_env["leader_token"]),
        json={
            "criteriaId": reports_env["criteria_id"],
            "activityDate": "2026-09-01T12:00:00+00:00",
            "reportData": {"count": 1},
            "links": ["https://malware.example/"],
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"]["code"] == "DOMAIN_NOT_ALLOWED"


async def test_update_draft_and_submit(
    client: AsyncClient, reports_env: dict[str, str]
) -> None:
    create = await client.post(
        "/api/reports",
        headers=_auth(reports_env["leader_token"]),
        json={
            "criteriaId": reports_env["criteria_id"],
            "activityDate": "2026-09-01T12:00:00+00:00",
            "reportData": {"count": 1},
            "links": ["https://t.me/club/1"],
        },
    )
    report_id = create.json()["data"]["id"]

    patched = await client.patch(
        f"/api/reports/{report_id}",
        headers=_auth(reports_env["leader_token"]),
        json={"reportData": {"count": 8}},
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["calculatedPoints"] == 800

    submitted = await client.post(
        f"/api/reports/{report_id}/submit",
        headers=_auth(reports_env["leader_token"]),
    )
    assert submitted.status_code == 200
    assert submitted.json()["data"]["status"] == "ON_MODERATION"

    # cannot edit after submit
    again = await client.patch(
        f"/api/reports/{report_id}",
        headers=_auth(reports_env["leader_token"]),
        json={"reportData": {"count": 1}},
    )
    assert again.status_code == 400


async def test_other_leader_cannot_access(
    client: AsyncClient, reports_env: dict[str, str]
) -> None:
    create = await client.post(
        "/api/reports",
        headers=_auth(reports_env["leader_token"]),
        json={
            "criteriaId": reports_env["criteria_id"],
            "activityDate": "2026-09-01T12:00:00+00:00",
            "reportData": {"count": 1},
            "links": ["https://t.me/club/2"],
        },
    )
    report_id = create.json()["data"]["id"]
    resp = await client.get(
        f"/api/reports/{report_id}",
        headers=_auth(reports_env["other_token"]),
    )
    assert resp.status_code == 403


async def test_soft_delete_only_draft(
    client: AsyncClient, reports_env: dict[str, str]
) -> None:
    create = await client.post(
        "/api/reports",
        headers=_auth(reports_env["leader_token"]),
        json={
            "criteriaId": reports_env["criteria_id"],
            "activityDate": "2026-09-01T12:00:00+00:00",
            "reportData": {"count": 1},
            "links": ["https://github.com/x/y"],
        },
    )
    report_id = create.json()["data"]["id"]

    submitted = await client.post(
        f"/api/reports/{report_id}/submit",
        headers=_auth(reports_env["leader_token"]),
    )
    assert submitted.status_code == 200

    delete_resp = await client.delete(
        f"/api/reports/{report_id}",
        headers=_auth(reports_env["leader_token"]),
    )
    assert delete_resp.status_code == 400


async def test_list_for_leader_only_own_club(
    client: AsyncClient, reports_env: dict[str, str]
) -> None:
    await client.post(
        "/api/reports",
        headers=_auth(reports_env["leader_token"]),
        json={
            "criteriaId": reports_env["criteria_id"],
            "activityDate": "2026-09-01T12:00:00+00:00",
            "reportData": {"count": 1},
            "links": ["https://t.me/club/3"],
        },
    )
    own = await client.get("/api/reports", headers=_auth(reports_env["leader_token"]))
    assert own.status_code == 200
    assert len(own.json()["data"]) == 1

    other = await client.get("/api/reports", headers=_auth(reports_env["other_token"]))
    assert other.json()["data"] == []

    mod = await client.get("/api/reports", headers=_auth(reports_env["mod_token"]))
    assert len(mod.json()["data"]) == 1


async def test_report_not_found(client: AsyncClient, reports_env: dict[str, str]) -> None:
    missing = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(
        f"/api/reports/{missing}",
        headers=_auth(reports_env["leader_token"]),
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["error"]["code"] == "REPORT_NOT_FOUND"


async def test_moderator_cannot_create_report(
    client: AsyncClient, reports_env: dict[str, str]
) -> None:
    resp = await client.post(
        "/api/reports",
        headers=_auth(reports_env["mod_token"]),
        json={
            "criteriaId": reports_env["criteria_id"],
            "activityDate": "2026-09-01T12:00:00+00:00",
            "reportData": {"count": 1},
            "links": ["https://t.me/club/mod"],
        },
    )
    assert resp.status_code == 403


async def test_moderator_cannot_update_or_submit(
    client: AsyncClient, reports_env: dict[str, str]
) -> None:
    create = await client.post(
        "/api/reports",
        headers=_auth(reports_env["leader_token"]),
        json={
            "criteriaId": reports_env["criteria_id"],
            "activityDate": "2026-09-01T12:00:00+00:00",
            "reportData": {"count": 1},
            "links": ["https://t.me/club/x"],
        },
    )
    report_id = create.json()["data"]["id"]

    patch = await client.patch(
        f"/api/reports/{report_id}",
        headers=_auth(reports_env["mod_token"]),
        json={"reportData": {"count": 2}},
    )
    assert patch.status_code == 403

    submit = await client.post(
        f"/api/reports/{report_id}/submit",
        headers=_auth(reports_env["mod_token"]),
    )
    assert submit.status_code == 403


async def test_guest_has_no_club_reports_list(
    client: AsyncClient, reports_env: dict[str, str]
) -> None:
    from sqlalchemy import delete as sa_delete

    factory = get_session_factory()
    async with factory() as session:
        guest = User(
            sso_id="sso-guest-list",
            email="guest.list@x.test",
            name="Guest",
            role=UserRole.GUEST,
            can_sudo=False,
            created_at=datetime.now(UTC),
        )
        session.add(guest)
        await session.commit()
        guest_id = guest.id

    token = create_access_token(user_id=guest_id, role=UserRole.GUEST, can_sudo=False)
    resp = await client.get("/api/reports", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["data"] == []

    async with factory() as session:
        await session.execute(sa_delete(User).where(User.id == guest_id))
        await session.commit()
