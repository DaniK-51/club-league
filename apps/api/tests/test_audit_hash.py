"""Unit tests for audit hash chain."""

from datetime import UTC, datetime

from src.services.audit_service import GENESIS_HASH, compute_hash


def test_genesis_prev_hash_is_64_zeros() -> None:
    assert len(GENESIS_HASH) == 64
    assert set(GENESIS_HASH) == {"0"}


def test_compute_hash_is_deterministic() -> None:
    kwargs = {
        "prev_hash": GENESIS_HASH,
        "entity_type": "report",
        "entity_id": "abc",
        "action": "created",
        "old_value": None,
        "new_value": {"status": "DRAFT"},
        "performed_by_id": "user-1",
        "performed_by_role": "CLUB_LEADER",
        "performed_at": datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        "reason": None,
    }
    h1 = compute_hash(**kwargs)
    h2 = compute_hash(**kwargs)
    assert h1 == h2
    assert len(h1) == 64


def test_compute_hash_changes_with_payload() -> None:
    base = {
        "prev_hash": GENESIS_HASH,
        "entity_type": "report",
        "entity_id": "abc",
        "action": "created",
        "old_value": None,
        "new_value": {"status": "DRAFT"},
        "performed_by_id": "user-1",
        "performed_by_role": "CLUB_LEADER",
        "performed_at": datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        "reason": None,
    }
    h1 = compute_hash(**base)
    h2 = compute_hash(**{**base, "new_value": {"status": "ON_MODERATION"}})
    assert h1 != h2
