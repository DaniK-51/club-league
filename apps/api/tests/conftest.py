from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from src.core.database import dispose_engine
from src.main import app


@pytest.fixture(scope="session", autouse=True)
async def _db_engine_lifecycle() -> AsyncIterator[None]:
    yield
    await dispose_engine()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
