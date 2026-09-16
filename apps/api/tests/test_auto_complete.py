"""Integration tests for auto-complete APPROVED→COMPLETED timer."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select, text

from src.core.database import get_session_factory
from src.core.security import create_access_token
from src.models.entities import (
    AuditLog,
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
from src.services.archive_service import complete_approved_if_stale
from src.services.auto_complete import start_auto_complete_timer, stop_auto_complete_timer


async def _wipe() -> None:
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(text("TRUNCATE sudo_actions, audit_logs RESTART IDENTITY CASCADE"))
        await session.execute(text("TRUNCATE archive_batches RESTART IDENTITY CASCADE"))
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
async def env(client: AsyncClient) -> AsyncIterator[dict[str, object]]:
    await _wipe()
    factory = get_session_factory()
    async with factory() as session:
        now = datetime.now(UTC)
        mod = User(
            sso_id="sso-ac-mod",
            email="ac.mod@x.test",
            name="M",
            role=UserRole.MODERATOR,
            can_sudo=True,
            created_at=now,
        )
        session.add(mod)
        await session.flush()
        club = Club(name="AC Club", category=ClubCategory.SPORT)
        session.add(club)
        await session.flush()
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
            "mod_id": mod.id,
            "mod_token": create_access_token(
                user_id=mod.id, role=UserRole.MODERATOR, can_sudo=True
            ),
            "club_id": club.id,
            "criteria_id": criteria.id,
            "version_id": version.id,
        }
    await _wipe()


def _auth(t: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {t}"}


async def _make_approved(
    session,
    *,
    club_id: str,
    criteria_id: str,
    version_id: str,
    moderated_at: datetime,
    moderated_by_id: str,
) -> str:
    rid = f"00000000-0000-0000-0000-{datetime.now(UTC).strftime('%H%M%S%f')[:12]}"
    session.add(
        Report(
            id=rid,
            club_id=club_id,
            criteria_id=criteria_id,
            rules_version_id=version_id,
            activity_date=datetime.now(UTC),
            report_data={},
            status=ReportStatus.APPROVED,
            calculated_points=250,
            final_points=250,
            is_deleted=False,
            moderated_at=moderated_at,
            moderated_by_id=moderated_by_id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
    )
    await session.commit()
    return rid


async def test_no_stale_reports_returns_zero(env: dict[str, object]) -> None:
    factory = get_session_factory()
    async with factory() as session:
        count = await complete_approved_if_stale(session, older_than_days=7)
        assert count == 0


async def test_stale_report_completes(env: dict[str, object]) -> None:
    factory = get_session_factory()
    async with factory() as session:
        rid = await _make_approved(
            session,
            club_id=str(env["club_id"]),
            criteria_id=str(env["criteria_id"]),
            version_id=str(env["version_id"]),
            moderated_at=datetime.now(UTC) - timedelta(days=10),
            moderated_by_id=str(env["mod_id"]),
        )
        count = await complete_approved_if_stale(session, older_than_days=7)
        assert count == 1
        report = await session.get(Report, rid)
        assert report is not None
        assert report.status == ReportStatus.COMPLETED


async def test_fresh_report_not_completed(env: dict[str, object]) -> None:
    factory = get_session_factory()
    async with factory() as session:
        rid = await _make_approved(
            session,
            club_id=str(env["club_id"]),
            criteria_id=str(env["criteria_id"]),
            version_id=str(env["version_id"]),
            moderated_at=datetime.now(UTC) - timedelta(days=2),
            moderated_by_id=str(env["mod_id"]),
        )
        count = await complete_approved_if_stale(session, older_than_days=7)
        assert count == 0
        report = await session.get(Report, rid)
        assert report is not None
        assert report.status == ReportStatus.APPROVED


async def test_skips_report_without_performer(env: dict[str, object]) -> None:
    factory = get_session_factory()
    async with factory() as session:
        rid = await _make_approved(
            session,
            club_id=str(env["club_id"]),
            criteria_id=str(env["criteria_id"]),
            version_id=str(env["version_id"]),
            moderated_at=datetime.now(UTC) - timedelta(days=30),
            moderated_by_id=str(env["mod_id"]),
        )
        report = await session.get(Report, rid)
        assert report is not None
        report.moderated_by_id = None
        await session.commit()

        count = await complete_approved_if_stale(session, older_than_days=7)
        assert count == 0
        report = await session.get(Report, rid)
        assert report is not None
        assert report.status == ReportStatus.APPROVED


async def test_writes_audit_log(env: dict[str, object]) -> None:
    factory = get_session_factory()
    async with factory() as session:
        rid = await _make_approved(
            session,
            club_id=str(env["club_id"]),
            criteria_id=str(env["criteria_id"]),
            version_id=str(env["version_id"]),
            moderated_at=datetime.now(UTC) - timedelta(days=10),
            moderated_by_id=str(env["mod_id"]),
        )
        await complete_approved_if_stale(session, older_than_days=7)
        rows = (
            await session.execute(select(AuditLog).where(AuditLog.entity_id == rid))
        ).scalars().all()
        assert len(rows) >= 1
        assert rows[0].action == "status_changed"
        assert rows[0].new_value is not None
        assert rows[0].new_value["status"] == "COMPLETED"


def test_start_stop_timer() -> None:
    import asyncio

    async def _run() -> None:
        start_auto_complete_timer()
        await asyncio.sleep(0.05)
        stop_auto_complete_timer()

    asyncio.run(_run())
