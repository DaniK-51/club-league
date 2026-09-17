from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.config import settings


@dataclass(frozen=True)
class UserProfile:
    sub: str
    email: str
    name: str


@dataclass
class AuthCode:
    profile: UserProfile
    redirect_uri: str
    client_id: str
    expires_at: datetime


@dataclass
class AccessToken:
    profile: UserProfile
    expires_at: datetime


SEED_USERS: tuple[UserProfile, ...] = (
    UserProfile(
        sub="sso-mod-1",
        email="moderator@innopolis.university",
        name="Тимофей Модератор",
    ),
    UserProfile(
        sub="sso-leader-1",
        email="leader@innopolis.university",
        name="Лидер Клуба",
    ),
    UserProfile(
        sub="sso-guest-1",
        email="guest@innopolis.university",
        name="Гость",
    ),
)

USERS_BY_EMAIL: dict[str, UserProfile] = {u.email: u for u in SEED_USERS}
USERS_BY_SUB: dict[str, UserProfile] = {u.sub: u for u in SEED_USERS}

_codes: dict[str, AuthCode] = {}
_tokens: dict[str, AccessToken] = {}


def _now() -> datetime:
    return datetime.now(UTC)


def _purge_expired() -> None:
    now = _now()
    for store in (_codes, _tokens):
        expired = [k for k, v in store.items() if v.expires_at < now]
        for k in expired:
            del store[k]


def create_code(*, email: str, redirect_uri: str, client_id: str) -> str | None:
    _purge_expired()
    profile = USERS_BY_EMAIL.get(email)
    if profile is None:
        return None
    code = secrets.token_urlsafe(32)
    _codes[code] = AuthCode(
        profile=profile,
        redirect_uri=redirect_uri,
        client_id=client_id,
        expires_at=_now() + timedelta(seconds=settings.code_ttl_seconds),
    )
    return code


def consume_code(
    code: str,
    *,
    redirect_uri: str,
    client_id: str,
    client_secret: str,
) -> UserProfile | None:
    _purge_expired()
    entry = _codes.pop(code, None)
    if entry is None:
        return None
    if entry.expires_at < _now():
        return None
    if entry.redirect_uri != redirect_uri or entry.client_id != client_id:
        return None
    if client_secret != settings.client_secret:
        return None
    return entry.profile


def create_token(profile: UserProfile) -> str:
    _purge_expired()
    token = secrets.token_urlsafe(32)
    _tokens[token] = AccessToken(
        profile=profile,
        expires_at=_now() + timedelta(seconds=settings.token_ttl_seconds),
    )
    return token


def resolve_token(token: str) -> UserProfile | None:
    _purge_expired()
    entry = _tokens.get(token)
    if entry is None or entry.expires_at < _now():
        return None
    return entry.profile


def reset_state() -> None:
    _codes.clear()
    _tokens.clear()
