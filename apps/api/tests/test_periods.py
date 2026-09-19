"""Period management + manual-points approve + rating/archive by period."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from src.core.database import get_session_factory
from src.core.security import create_access_token
from src.models.entities import (
    Club,
    ClubLeader,
    Criteria,
    CriteriaRule,
    Period,
    Report,
    RulesVersion,
    User,
)
from src.models.enums import ClubCategory, ReportStatus, UserRole

from tests.helpers import TZ, add_default_periods
from tests.helpers import auth as _auth
from tests.helpers import wipe_db as _wipe


@pytest.fixture
async def env(client: AsyncClient) -> AsyncIterator[dict[str, str]]:
    await _wipe()
    factory = get_session_factory()
    async with factory() as session:
        now = datetime.now(UTC)
        leader = User(
            sso_id="sso-p-leader",
            email="p.leader@x.test",
            name="L",
            role=UserRole.CLUB_LEADER,
            can_sudo=False,
            created_at=now,
        )
        mod = User(
            sso_id="sso-p-mod",
            email="p.mod@x.test",
            name="M",
            role=UserRole.MODERATOR,
            can_sudo=True,
            created_at=now,
        )
        guest = User(
            sso_id="sso-p-guest",
            email="p.guest@x.test",
            name="G",
            role=UserRole.GUEST,
            can_sudo=False,
            created_at=now,
        )
        session.add_all([leader, mod, guest])
        await session.flush()
        club = Club(name="Period Club", category=ClubCategory.SPORT)
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
        periods = await add_default_periods(session, now=now, names=("2026-fall",))
        period = periods[0]
        await session.commit()
        yield {
            "leader": create_access_token(
                user_id=leader.id, role=UserRole.CLUB_LEADER, can_sudo=False
            ),
            "mod": create_access_token(user_id=mod.id, role=UserRole.MODERATOR, can_sudo=True),
            "guest": create_access_token(user_id=guest.id, role=UserRole.GUEST, can_sudo=False),
            "criteria_id": criteria.id,
            "period_id": period.id,
            "club_id": club.id,
        }
    await _wipe()


async def _create_report(
    client: AsyncClient,
    env: dict[str, str],
    *,
    activity_date: str = "2026-09-15T12:00:00+03:00",
    count: int = 3,
) -> str:
    resp = await client.post(
        "/api/reports",
        headers=_auth(env["leader"]),
        json={
            "criteriaId": env["criteria_id"],
            "activityDate": activity_date,
            "reportData": {"count": count},
            "links": ["https://t.me/p/1"],
        },
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["data"]["id"])


# ─── Period CRUD ────────────────────────────────────────────────────────────


async def test_admin_period_crud(client: AsyncClient, env: dict[str, str]) -> None:
    resp = await client.get("/api/admin/periods", headers=_auth(env["mod"]))
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert any(p["name"] == "2026-fall" for p in items)
    fall = next(p for p in items if p["name"] == "2026-fall")
    assert fall["isArchived"] is False
    assert fall["reportCount"] == 0

    resp = await client.post(
        "/api/admin/periods",
        headers=_auth(env["mod"]),
        json={
            "name": "2027-spring",
            "startDate": "2027-01-01T00:00:00+03:00",
            "endDate": "2027-06-01T00:00:00+03:00",
        },
    )
    assert resp.status_code == 201, resp.text
    created = resp.json()["data"]
    assert created["name"] == "2027-spring"
    pid = created["id"]

    resp = await client.patch(
        f"/api/admin/periods/{pid}",
        headers=_auth(env["mod"]),
        json={"name": "2027-spring-x"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "2027-spring-x"

    resp = await client.delete(f"/api/admin/periods/{pid}", headers=_auth(env["mod"]))
    assert resp.status_code == 200
    assert resp.json()["data"]["success"] is True

    resp = await client.delete(f"/api/admin/periods/{pid}", headers=_auth(env["mod"]))
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "PERIOD_NOT_FOUND"


async def test_create_period_invalid_dates(client: AsyncClient, env: dict[str, str]) -> None:
    resp = await client.post(
        "/api/admin/periods",
        headers=_auth(env["mod"]),
        json={
            "name": "bad",
            "startDate": "2026-05-01T00:00:00+03:00",
            "endDate": "2026-01-01T00:00:00+03:00",
        },
    )
    assert resp.status_code == 422


async def test_periods_forbidden_for_guest(client: AsyncClient, env: dict[str, str]) -> None:
    resp = await client.get("/api/admin/periods", headers=_auth(env["guest"]))
    assert resp.status_code == 403


# ─── Report → Period assignment ─────────────────────────────────────────────


async def test_report_gets_period_name(client: AsyncClient, env: dict[str, str]) -> None:
    rid = await _create_report(client, env, activity_date="2026-09-15T12:00:00+03:00")
    resp = await client.get(f"/api/reports/{rid}", headers=_auth(env["mod"]))
    data = resp.json()["data"]
    assert data["periodName"] == "2026-fall"


async def test_report_outside_period_has_null_period_name(
    client: AsyncClient, env: dict[str, str]
) -> None:
    rid = await _create_report(client, env, activity_date="2025-03-10T12:00:00+03:00")
    resp = await client.get(f"/api/reports/{rid}", headers=_auth(env["mod"]))
    assert resp.json()["data"]["periodName"] is None


async def test_update_activity_date_reassigns_period(
    client: AsyncClient, env: dict[str, str]
) -> None:
    factory = get_session_factory()
    async with factory() as session:
        now = datetime.now(UTC)
        session.add(
            Period(
                name="2026-spring",
                start_date=datetime(2026, 1, 1, tzinfo=TZ),
                end_date=datetime(2026, 6, 1, tzinfo=TZ),
                is_archived=False,
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()

    rid = await _create_report(client, env, activity_date="2026-09-15T12:00:00+03:00")
    resp = await client.patch(
        f"/api/reports/{rid}",
        headers=_auth(env["leader"]),
        json={"activityDate": "2026-03-01T12:00:00+03:00"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["periodName"] == "2026-spring"


async def test_delete_period_blocked_when_reports_exist(
    client: AsyncClient, env: dict[str, str]
) -> None:
    await _create_report(client, env)
    resp = await client.delete(
        f"/api/admin/periods/{env['period_id']}", headers=_auth(env["mod"])
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


# ─── Approve with manual points — comment NOT required ─────────────────────


async def test_approve_manual_points_without_comment(
    client: AsyncClient, env: dict[str, str]
) -> None:
    rid = await _create_report(client, env)
    await client.post(f"/api/reports/{rid}/submit", headers=_auth(env["leader"]))

    resp = await client.patch(
        f"/api/reports/{rid}/calculation",
        headers=_auth(env["mod"]),
        json={"method": "manual", "manualPoints": 350, "reason": "jury decision"},
    )
    assert resp.status_code == 200

    resp = await client.patch(
        f"/api/reports/{rid}/moderate",
        headers=_auth(env["mod"]),
        json={"status": "APPROVED", "comment": ""},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["status"] == "APPROVED"
    assert data["calculationMethod"] == "manual"
    assert data["finalPoints"] == 350
    assert data["manualPoints"] == 350
    assert data["periodName"] == "2026-fall"


async def test_approve_auto_override_still_requires_comment(
    client: AsyncClient, env: dict[str, str]
) -> None:
    rid = await _create_report(client, env)
    await client.post(f"/api/reports/{rid}/submit", headers=_auth(env["leader"]))
    resp = await client.patch(
        f"/api/reports/{rid}/moderate",
        headers=_auth(env["mod"]),
        json={"status": "APPROVED", "finalPoints": 100, "comment": ""},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "COMMENT_REQUIRED"


async def test_changes_required_still_requires_comment(
    client: AsyncClient, env: dict[str, str]
) -> None:
    rid = await _create_report(client, env)
    await client.post(f"/api/reports/{rid}/submit", headers=_auth(env["leader"]))
    await client.patch(
        f"/api/reports/{rid}/calculation",
        headers=_auth(env["mod"]),
        json={"method": "manual", "manualPoints": 10},
    )
    resp = await client.patch(
        f"/api/reports/{rid}/moderate",
        headers=_auth(env["mod"]),
        json={"status": "CHANGES_REQUIRED", "comment": ""},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "COMMENT_REQUIRED"


# ─── Rating by period ───────────────────────────────────────────────────────


async def _insert_completed_report(
    env: dict[str, str],
    *,
    activity_date: datetime,
    final_points: int,
) -> None:
    factory = get_session_factory()
    async with factory() as session:
        now = datetime.now(UTC)
        period = await session.scalar(select(Period).where(Period.name == "2026-fall"))
        report = Report(
            club_id=env["club_id"],
            criteria_id=env["criteria_id"],
            rules_version_id=(
                await session.scalar(
                    select(RulesVersion.id).where(RulesVersion.semester == "2026-fall")
                )
            ),
            activity_date=activity_date,
            report_data={"count": 1},
            status=ReportStatus.COMPLETED,
            calculated_points=250,
            final_points=final_points,
            calculation_method="auto",
            is_deleted=False,
            period_id=period.id if period else None,
            created_at=now,
            updated_at=now,
        )
        session.add(report)
        await session.commit()


async def test_rating_filters_by_period(client: AsyncClient, env: dict[str, str]) -> None:
    factory = get_session_factory()
    async with factory() as session:
        now = datetime.now(UTC)
        session.add(
            Period(
                name="2026-spring",
                start_date=datetime(2026, 1, 1, tzinfo=TZ),
                end_date=datetime(2026, 6, 1, tzinfo=TZ),
                is_archived=False,
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()

    await _insert_completed_report(
        env,
        activity_date=datetime(2026, 9, 10, 12, 0, tzinfo=TZ),
        final_points=400,
    )
    await _insert_completed_report(
        env,
        activity_date=datetime(2026, 3, 10, 12, 0, tzinfo=TZ),
        final_points=999,
    )

    resp = await client.get("/api/rating", params={"period": "2026-fall"})
    assert resp.status_code == 200
    clubs = resp.json()["data"]["clubs"]
    assert len(clubs) == 1
    assert clubs[0]["name"] == "Period Club"
    assert clubs[0]["totalPoints"] == 400

    resp = await client.get("/api/rating", params={"period": "2026-spring"})
    clubs = resp.json()["data"]["clubs"]
    assert len(clubs) == 1
    assert clubs[0]["totalPoints"] == 999


# ─── Archive by period ──────────────────────────────────────────────────────


async def test_archive_period_sets_is_archived(
    client: AsyncClient, env: dict[str, str]
) -> None:
    await _insert_completed_report(
        env,
        activity_date=datetime(2026, 9, 10, 12, 0, tzinfo=TZ),
        final_points=250,
    )

    resp = await client.post(
        "/api/reports/archive",
        headers=_auth(env["mod"]),
        params={"period": "2026-fall"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["period"] == "2026-fall"
    assert data["reportCount"] == 1

    factory = get_session_factory()
    async with factory() as session:
        period = await session.scalar(select(Period).where(Period.name == "2026-fall"))
        assert period is not None
        assert period.is_archived is True

    resp = await client.post(
        "/api/reports/archive",
        headers=_auth(env["mod"]),
        params={"period": "2026-fall"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "ALREADY_ARCHIVED"


async def test_archive_unknown_period(client: AsyncClient, env: dict[str, str]) -> None:
    resp = await client.post(
        "/api/reports/archive",
        headers=_auth(env["mod"]),
        params={"period": "1999-fall"},
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "PERIOD_NOT_FOUND"


# ─── Public periods + rating after archive ──────────────────────────────────


async def test_public_periods_no_auth(client: AsyncClient, env: dict[str, str]) -> None:
    factory = get_session_factory()
    async with factory() as session:
        now = datetime.now(UTC)
        session.add(
            Period(
                name="2025-fall",
                start_date=datetime(2025, 9, 1, tzinfo=TZ),
                end_date=datetime(2026, 1, 1, tzinfo=TZ),
                is_archived=True,
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()

    # No Authorization header
    resp = await client.get("/api/periods")
    assert resp.status_code == 200, resp.text
    items = resp.json()["data"]
    names = {p["name"] for p in items}
    assert "2026-fall" in names
    assert "2025-fall" in names
    archived = next(p for p in items if p["name"] == "2025-fall")
    assert archived["isArchived"] is True
    active = next(p for p in items if p["name"] == "2026-fall")
    assert active["isArchived"] is False

    # Admin endpoint still requires moderator
    resp = await client.get("/api/admin/periods")
    assert resp.status_code == 401


async def test_rating_stable_after_archive(client: AsyncClient, env: dict[str, str]) -> None:
    await _insert_completed_report(
        env,
        activity_date=datetime(2026, 9, 10, 12, 0, tzinfo=TZ),
        final_points=400,
    )

    before = await client.get("/api/rating", params={"period": "2026-fall"})
    assert before.status_code == 200
    before_clubs = before.json()["data"]["clubs"]
    assert len(before_clubs) == 1
    assert before_clubs[0]["totalPoints"] == 400

    archive = await client.post(
        "/api/reports/archive",
        headers=_auth(env["mod"]),
        params={"period": "2026-fall"},
    )
    assert archive.status_code == 200, archive.text

    after = await client.get("/api/rating", params={"period": "2026-fall"})
    assert after.status_code == 200
    after_clubs = after.json()["data"]["clubs"]
    assert len(after_clubs) == 1
    assert after_clubs[0]["totalPoints"] == 400
    assert after_clubs[0]["name"] == before_clubs[0]["name"]

    # Public periods list shows archived flag
    periods = await client.get("/api/periods")
    fall = next(p for p in periods.json()["data"] if p["name"] == "2026-fall")
    assert fall["isArchived"] is True
