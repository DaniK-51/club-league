from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from src.core.config import get_settings
from src.core.database import dispose_engine
from src.main import app


@pytest.fixture(scope="session", autouse=True)
async def _db_engine_lifecycle() -> AsyncIterator[None]:
    yield
    await dispose_engine()


@pytest.fixture(autouse=True)
def _disable_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    monkeypatch.setenv("SSO_TOKEN_URL", "http://mock-sso:9001/token")
    monkeypatch.setenv("SSO_USERINFO_URL", "http://mock-sso:9001/userinfo")
    monkeypatch.setenv("SSO_AUTHORIZE_URL", "http://mock-sso:9001/authorize")
    monkeypatch.setenv("SSO_CLIENT_ID", "club-league-dev")
    monkeypatch.setenv("SSO_CLIENT_SECRET", "club-league-dev-secret")
    monkeypatch.setenv("SSO_REDIRECT_URI", "http://mock-sso:9001/callback")
    get_settings.cache_clear()
    yield
    monkeypatch.delenv("RATE_LIMIT_ENABLED", raising=False)
    get_settings.cache_clear()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
