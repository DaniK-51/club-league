from datetime import UTC, datetime, timedelta

import pytest
from src.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from src.models.enums import UserRole


def test_access_token_roundtrip() -> None:
    token = create_access_token(user_id="user-1", role=UserRole.GUEST, can_sudo=False)
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == "user-1"
    assert payload["role"] == "GUEST"
    assert payload["can_sudo"] is False


def test_refresh_token_roundtrip() -> None:
    token = create_refresh_token(user_id="user-1")
    payload = decode_token(token, expected_type="refresh")
    assert payload["sub"] == "user-1"


def test_access_token_rejected_as_refresh() -> None:
    token = create_access_token(user_id="user-1", role=UserRole.GUEST, can_sudo=False)
    with pytest.raises(TokenError):
        decode_token(token, expected_type="refresh")


def test_garbage_token_rejected() -> None:
    with pytest.raises(TokenError):
        decode_token("not.a.jwt", expected_type="access")


def test_expired_token_rejected() -> None:
    from jose import jwt
    from src.core.config import get_settings

    settings = get_settings()
    past = datetime.now(UTC) - timedelta(hours=1)
    token = jwt.encode(
        {
            "sub": "user-1",
            "type": "access",
            "iat": past,
            "exp": past + timedelta(minutes=1),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(TokenError):
        decode_token(token, expected_type="access")
