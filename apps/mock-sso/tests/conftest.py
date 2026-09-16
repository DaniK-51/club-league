from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from src.main import app
from src.store import reset_state


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    reset_state()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://sso.test") as ac:
        yield ac
    reset_state()
