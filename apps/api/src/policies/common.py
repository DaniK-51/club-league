from __future__ import annotations

from dataclasses import dataclass

from src.core.errors import api_error
from src.models.entities import User
from src.models.enums import UserRole
from src.schemas.common import ErrorCode


@dataclass(frozen=True)
class AuthzContext:
    user_id: str
    role: UserRole
    can_sudo: bool
    club_ids: frozenset[str]


def build_context(user: User, club_ids: frozenset[str]) -> AuthzContext:
    return AuthzContext(
        user_id=user.id,
        role=user.role,
        can_sudo=user.can_sudo,
        club_ids=club_ids,
    )


def ensure_moderator(user: User) -> None:
    if user.role != UserRole.MODERATOR:
        raise api_error(
            403, ErrorCode.FORBIDDEN, "Moderator role required", message_key="forbidden.moderator_required"
        )


def ensure_sudo(user: User) -> None:
    if user.role != UserRole.MODERATOR or not user.can_sudo:
        raise api_error(
            403, ErrorCode.SUDO_REQUIRED, "Sudo privileges required", message_key="forbidden.sudo_required"
        )


def ensure_club_leader(user: User, club_ids: frozenset[str], club_id: str | None) -> None:
    if user.role == UserRole.MODERATOR:
        return
    if not club_ids:
        raise api_error(
            403, ErrorCode.NOT_CLUB_LEADER, "Club leader role required", message_key="forbidden.club_leader_required"
        )
    if club_id is not None and club_id not in club_ids:
        raise api_error(
            403, ErrorCode.NOT_CLUB_LEADER, "Not a leader of this club", message_key="forbidden.not_leader_of_club"
        )


def ensure_not_moderator_as_leader(user: User, club_ids: frozenset[str]) -> None:
    """Moderator and club leader are mutually exclusive by design."""
    if user.role == UserRole.MODERATOR and club_ids:
        raise api_error(
            403,
            ErrorCode.FORBIDDEN,
            "Moderator cannot be a club leader",
            message_key="forbidden.moderator_not_leader",
        )
