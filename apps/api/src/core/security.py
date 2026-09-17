from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from jose import JWTError, jwt

from src.core.config import get_settings
from src.models.enums import UserRole

TokenType = Literal["access", "refresh"]


class TokenError(Exception):
    pass


def create_access_token(
    *,
    user_id: str,
    role: UserRole,
    can_sudo: bool,
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": user_id,
        "type": "access",
        "role": role.value,
        "can_sudo": can_sudo,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(*, user_id: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": user_id,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.refresh_token_expire_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_token_pair(
    *,
    user_id: str,
    role: UserRole,
    can_sudo: bool,
) -> tuple[str, str]:
    return (
        create_access_token(user_id=user_id, role=role, can_sudo=can_sudo),
        create_refresh_token(user_id=user_id),
    )


def decode_token(token: str, *, expected_type: TokenType) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise TokenError("invalid_token") from exc
    if payload.get("type") != expected_type:
        raise TokenError("wrong_token_type")
    if not payload.get("sub"):
        raise TokenError("missing_sub")
    return payload
