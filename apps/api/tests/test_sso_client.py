"""SSOClient unit tests using httpx.MockTransport (no real network)."""

from __future__ import annotations

import json

import httpx
import pytest
from src.services.sso_client import SSOClient, SSOError


def _transport(
    *,
    token_status: int = 200,
    token_json: dict | None = None,
    userinfo_status: int = 200,
    userinfo_json: dict | None = None,
    token_raises: bool = False,
    userinfo_raises: bool = False,
) -> httpx.MockTransport:
    token_body = token_json if token_json is not None else {"access_token": "tok", "token_type": "Bearer"}
    userinfo_body = userinfo_json if userinfo_json is not None else {
        "sub": "sso-1",
        "email": "a@innopolis.university",
        "name": "A",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            if token_raises:
                raise httpx.ConnectError("boom", request=request)
            return httpx.Response(token_status, json=token_body)
        if request.url.path.endswith("/userinfo"):
            if userinfo_raises:
                raise httpx.ConnectError("boom", request=request)
            return httpx.Response(userinfo_status, json=userinfo_body)
        return httpx.Response(404, json={})

    return httpx.MockTransport(handler)


async def test_exchange_code_success() -> None:
    client = httpx.AsyncClient(transport=_transport())
    sso = SSOClient(client)
    profile = await sso.exchange_code("good-code")
    assert profile.sso_id == "sso-1"
    assert profile.email == "a@innopolis.university"
    assert profile.name == "A"
    await client.aclose()


async def test_token_http_error() -> None:
    client = httpx.AsyncClient(transport=_transport(token_status=400))
    sso = SSOClient(client)
    with pytest.raises(SSOError, match="sso_token_exchange_failed"):
        await sso.exchange_code("bad")
    await client.aclose()


async def test_token_missing_access_token() -> None:
    client = httpx.AsyncClient(transport=_transport(token_json={"token_type": "Bearer"}))
    sso = SSOClient(client)
    with pytest.raises(SSOError, match="sso_token_missing"):
        await sso.exchange_code("x")
    await client.aclose()


async def test_userinfo_http_error() -> None:
    client = httpx.AsyncClient(transport=_transport(userinfo_status=401))
    sso = SSOClient(client)
    with pytest.raises(SSOError, match="sso_userinfo_failed"):
        await sso.exchange_code("x")
    await client.aclose()


async def test_incomplete_profile() -> None:
    client = httpx.AsyncClient(
        transport=_transport(userinfo_json={"sub": "sso-1", "email": "", "name": "A"})
    )
    sso = SSOClient(client)
    with pytest.raises(SSOError, match="sso_profile_incomplete"):
        await sso.exchange_code("x")
    await client.aclose()


async def test_token_unreachable() -> None:
    client = httpx.AsyncClient(transport=_transport(token_raises=True))
    sso = SSOClient(client)
    with pytest.raises(SSOError, match="sso_token_unreachable"):
        await sso.exchange_code("x")
    await client.aclose()


async def test_userinfo_unreachable() -> None:
    client = httpx.AsyncClient(transport=_transport(userinfo_raises=True))
    sso = SSOClient(client)
    with pytest.raises(SSOError, match="sso_userinfo_unreachable"):
        await sso.exchange_code("x")
    await client.aclose()


async def test_context_manager_closes_owned_client() -> None:
    async with SSOClient() as sso:
        # force real client path but with mock transport injected after
        assert sso._client is not None
    # after exit owned client is closed/reset
    assert sso._client is None


def test_transport_payload_shape() -> None:
    # sanity: mock handler returns JSON
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=json.dumps({"ok": True}))

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        assert client.get("http://test/x").json() == {"ok": True}
