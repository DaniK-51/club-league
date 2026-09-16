from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import delete
from src.core.database import get_session_factory
from src.models.entities import Club, ClubLeader, User
from src.models.enums import UserRole
from src.services.sso_client import SSOProfile


@pytest.fixture
async def clean_users() -> AsyncIterator[None]:
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(delete(ClubLeader))
        await session.execute(delete(User))
        await session.execute(delete(Club))
        await session.commit()
    yield
    async with factory() as session:
        await session.execute(delete(ClubLeader))
        await session.execute(delete(User))
        await session.execute(delete(Club))
        await session.commit()


@pytest.fixture
def fake_sso(monkeypatch: pytest.MonkeyPatch) -> SSOProfile:
    profile = SSOProfile(
        sso_id="sso-test-1",
        email="test.user@innopolis.university",
        name="Тестовый Пользователь",
    )

    async def _exchange(self: object, code: str) -> SSOProfile:
        if code != "good-code":
            from src.services.sso_client import SSOError

            raise SSOError("bad_code")
        return profile

    monkeypatch.setattr("src.services.sso_client.SSOClient.exchange_code", _exchange)
    return profile


async def test_callback_creates_guest(client: AsyncClient, fake_sso, clean_users) -> None:
    resp = await client.post("/api/auth/sso/callback", json={"code": "good-code"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["accessToken"]
    assert data["refreshToken"]
    assert data["user"]["email"] == "test.user@innopolis.university"
    assert data["user"]["name"] == "Тестовый Пользователь"
    assert data["user"]["role"] == "GUEST"
    assert data["user"]["canSudo"] is False


async def test_callback_bad_code(client: AsyncClient, fake_sso, clean_users) -> None:
    resp = await client.post("/api/auth/sso/callback", json={"code": "bad"})
    assert resp.status_code == 401
    assert resp.json()["detail"]["error"]["code"] == "UNAUTHORIZED"


async def test_callback_keeps_role_on_relogin(client: AsyncClient, fake_sso, clean_users) -> None:
    first = await client.post("/api/auth/sso/callback", json={"code": "good-code"})
    user_id = first.json()["data"]["user"]["id"]

    factory = get_session_factory()
    async with factory() as session:
        user = await session.get(User, user_id)
        assert user is not None
        user.role = UserRole.MODERATOR
        user.can_sudo = True
        await session.commit()

    second = await client.post("/api/auth/sso/callback", json={"code": "good-code"})
    body = second.json()["data"]["user"]
    assert body["role"] == "MODERATOR"
    assert body["canSudo"] is True
    assert body["id"] == user_id


async def test_me_requires_token(client: AsyncClient) -> None:
    resp = await client.get("/api/users/me")
    assert resp.status_code == 401
    assert resp.json()["detail"]["error"]["code"] == "UNAUTHORIZED"


async def test_me_with_token(client: AsyncClient, fake_sso, clean_users) -> None:
    login = await client.post("/api/auth/sso/callback", json={"code": "good-code"})
    token = login.json()["data"]["accessToken"]
    resp = await client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["email"] == "test.user@innopolis.university"
    assert body["role"] == "GUEST"
    assert body["clubIds"] == []


async def test_refresh_flow(client: AsyncClient, fake_sso, clean_users) -> None:
    login = await client.post("/api/auth/sso/callback", json={"code": "good-code"})
    refresh = login.json()["data"]["refreshToken"]
    resp = await client.post("/api/auth/refresh", json={"refreshToken": refresh})
    assert resp.status_code == 200
    assert resp.json()["data"]["accessToken"]


async def test_refresh_rejects_access_token(client: AsyncClient, fake_sso, clean_users) -> None:
    login = await client.post("/api/auth/sso/callback", json={"code": "good-code"})
    access = login.json()["data"]["accessToken"]
    resp = await client.post("/api/auth/refresh", json={"refreshToken": access})
    assert resp.status_code == 401


async def test_email_conflict(client: AsyncClient, monkeypatch: pytest.MonkeyPatch, clean_users) -> None:
    factory = get_session_factory()
    async with factory() as session:
        session.add(
            User(
                sso_id="other-sso",
                email="taken@innopolis.university",
                name="Другой",
                role=UserRole.GUEST,
                can_sudo=False,
                created_at=datetime.now(UTC),
            )
        )
        await session.commit()

    async def _exchange(self: object, code: str) -> SSOProfile:
        return SSOProfile(
            sso_id="sso-new",
            email="taken@innopolis.university",
            name="Конфликт",
        )

    monkeypatch.setattr("src.services.sso_client.SSOClient.exchange_code", _exchange)
    resp = await client.post("/api/auth/sso/callback", json={"code": "good-code"})
    assert resp.status_code == 401
