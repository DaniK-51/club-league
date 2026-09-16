"""Integration tests for AuditService against PostgreSQL."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import delete, text
from sqlalchemy.exc import DBAPIError

from src.core.database import get_session_factory
from src.models.entities import Club, ClubLeader, User
from src.models.enums import UserRole
from src.services.audit_service import (
    GENESIS_HASH,
    AuditService,
    ChainBrokenError,
    user_public_snapshot,
)


async def _reset() -> None:
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(text("TRUNCATE sudo_actions, audit_logs RESTART IDENTITY CASCADE"))
        await session.execute(delete(ClubLeader))
        await session.execute(delete(User))
        await session.execute(delete(Club))
        await session.commit()


@pytest.fixture
async def audit_session() -> AsyncIterator[object]:
    await _reset()
    factory = get_session_factory()
    async with factory() as session:
        yield session
        await session.rollback()
    await _reset()


async def _make_user(session, *, email: str, role: UserRole = UserRole.GUEST) -> User:
    unique = f"{uuid4().hex[:8]}.{email}"
    user = User(
        sso_id=f"sso-{unique}",
        email=unique,
        name=email.split("@")[0],
        role=role,
        can_sudo=role == UserRole.MODERATOR,
        created_at=datetime.now(UTC),
    )
    session.add(user)
    await session.flush()
    return user


async def test_chain_builds_and_verifies(audit_session) -> None:
    session = audit_session  # type: ignore[assignment]
    user = await _make_user(session, email="audit1@innopolis.university")
    service = AuditService(session)
    e1 = await service.log_user_created(user)
    assert e1.prev_hash == GENESIS_HASH
    assert e1.seq >= 1

    user.name = "Renamed"
    await session.flush()
    e2 = await service.log_user_profile_updated(
        user, old_snapshot={**user_public_snapshot(user), "name": "audit1"}
    )
    assert e2.prev_hash == e1.hash
    assert e2.seq > e1.seq

    await service.verify_chain()
    assert await service.is_chain_valid() is True
    await session.commit()


async def test_append_only_trigger_blocks_update(audit_session) -> None:
    session = audit_session  # type: ignore[assignment]
    user = await _make_user(session, email="audit2@innopolis.university")
    service = AuditService(session)
    await service.log_user_created(user)
    await session.commit()

    with pytest.raises(DBAPIError):
        await session.execute(
            text("UPDATE audit_logs SET action = 'tampered' WHERE entity_id = :id"),
            {"id": user.id},
        )
    await session.rollback()


async def test_append_only_trigger_blocks_delete(audit_session) -> None:
    session = audit_session  # type: ignore[assignment]
    user = await _make_user(session, email="audit3@innopolis.university")
    service = AuditService(session)
    await service.log_user_created(user)
    await session.commit()

    with pytest.raises(DBAPIError):
        await session.execute(text("DELETE FROM audit_logs"))
    await session.rollback()


async def test_sudo_action_writes_both_tables(audit_session) -> None:
    session = audit_session  # type: ignore[assignment]
    mod = await _make_user(session, email="mod@innopolis.university", role=UserRole.MODERATOR)
    service = AuditService(session)
    sudo_row, audit_row = await service.log_sudo_action(
        performed_by=mod,
        action="force_status",
        entity_type="report",
        entity_id="report-1",
        old_value={"status": "DRAFT"},
        new_value={"status": "ARCHIVED"},
        reason="cleanup after test",
    )
    assert sudo_row.reason == "cleanup after test"
    assert audit_row.action == "sudo_action"
    assert audit_row.reason == "cleanup after test"
    await service.verify_chain()
    await session.commit()

    count = await session.scalar(
        text("SELECT count(*) FROM sudo_actions WHERE entity_id = 'report-1'")
    )
    assert count == 1


async def test_sudo_requires_reason(audit_session) -> None:
    session = audit_session  # type: ignore[assignment]
    mod = await _make_user(session, email="mod2@innopolis.university", role=UserRole.MODERATOR)
    service = AuditService(session)
    with pytest.raises(ValueError):
        await service.log_sudo_action(
            performed_by=mod,
            action="force_status",
            entity_type="report",
            entity_id="r",
            old_value=None,
            new_value=None,
            reason="   ",
        )


async def test_chain_detects_manual_tamper(audit_session) -> None:
    session = audit_session  # type: ignore[assignment]
    user = await _make_user(session, email="audit4@innopolis.university")
    service = AuditService(session)
    await service.log_user_created(user)
    await session.commit()

    # Bypass ORM trigger? UPDATE will fail; instead corrupt via new insert with wrong prev.
    # Simulate broken link by inserting a row that claims wrong prev_hash using raw SQL
    # would also fail if trigger blocks UPDATE only. INSERT is allowed.
    await session.execute(
        text(
            """
            INSERT INTO audit_logs (
                id, prev_hash, hash, entity_type, entity_id, action,
                old_value, new_value, performed_by_id, performed_by_role,
                performed_at, reason
            ) VALUES (
                gen_random_uuid(), :prev, :hash, 'user', :uid, 'updated',
                NULL, NULL, CAST(:by_id AS uuid), 'GUEST', now(), NULL
            )
            """
        ),
        {
            "prev": "f" * 64,
            "hash": "a" * 64,
            "uid": user.id,
            "by_id": user.id,
        },
    )
    await session.commit()
    assert await service.is_chain_valid() is False
    with pytest.raises(ChainBrokenError):
        await service.verify_chain()
