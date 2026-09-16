"""i18n: Accept-Language switches API error messages."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from src.main import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_unauthorized_en_default(client: AsyncClient) -> None:
    resp = await client.get("/api/users/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["message"] == "Missing bearer token"


async def test_unauthorized_ru(client: AsyncClient) -> None:
    resp = await client.get("/api/users/me", headers={"Accept-Language": "ru-RU,ru;q=0.9"})
    assert resp.status_code == 401
    assert resp.json()["error"]["message"] == "Отсутствует bearer token"


async def test_t_fallback_to_en() -> None:
    from src.core.i18n import t

    assert t("report.not_found", "ru") == "Отчёт не найден"
    assert t("report.not_found", "en") == "Report not found"
    assert t("missing.key") == "missing.key"
