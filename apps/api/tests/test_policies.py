from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from src.models.enums import UserRole
from src.policies.common import (
    ensure_club_leader,
    ensure_moderator,
    ensure_not_moderator_as_leader,
    ensure_sudo,
)
from src.schemas.common import ErrorCode


def _user(role: UserRole, *, can_sudo: bool = False) -> SimpleNamespace:
    return SimpleNamespace(id="u1", role=role, can_sudo=can_sudo)


def test_ensure_moderator_ok() -> None:
    ensure_moderator(_user(UserRole.MODERATOR))  # type: ignore[arg-type]


def test_ensure_moderator_fail() -> None:
    with pytest.raises(HTTPException) as exc:
        ensure_moderator(_user(UserRole.CLUB_LEADER))  # type: ignore[arg-type]
    assert exc.value.status_code == 403
    assert exc.value.detail["error"]["code"] == ErrorCode.FORBIDDEN


def test_ensure_sudo_ok() -> None:
    ensure_sudo(_user(UserRole.MODERATOR, can_sudo=True))  # type: ignore[arg-type]


def test_ensure_sudo_fail_without_flag() -> None:
    with pytest.raises(HTTPException) as exc:
        ensure_sudo(_user(UserRole.MODERATOR, can_sudo=False))  # type: ignore[arg-type]
    assert exc.value.detail["error"]["code"] == ErrorCode.SUDO_REQUIRED


def test_ensure_club_leader_ok() -> None:
    ensure_club_leader(_user(UserRole.CLUB_LEADER), frozenset({"c1"}), "c1")  # type: ignore[arg-type]


def test_ensure_club_leader_wrong_club() -> None:
    with pytest.raises(HTTPException) as exc:
        ensure_club_leader(_user(UserRole.CLUB_LEADER), frozenset({"c1"}), "c2")  # type: ignore[arg-type]
    assert exc.value.detail["error"]["code"] == ErrorCode.NOT_CLUB_LEADER


def test_moderator_passes_club_leader_check() -> None:
    ensure_club_leader(_user(UserRole.MODERATOR), frozenset(), None)  # type: ignore[arg-type]


def test_ensure_not_moderator_as_leader() -> None:
    with pytest.raises(HTTPException):
        ensure_not_moderator_as_leader(_user(UserRole.MODERATOR), frozenset({"c1"}))  # type: ignore[arg-type]
    ensure_not_moderator_as_leader(_user(UserRole.MODERATOR), frozenset())  # type: ignore[arg-type]
