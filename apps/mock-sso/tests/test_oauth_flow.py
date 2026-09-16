from httpx import AsyncClient
from src.config import settings


async def _get_code(client: AsyncClient, email: str = "leader@innopolis.university") -> str:
    resp = await client.post(
        "/authorize",
        data={
            "client_id": settings.client_id,
            "redirect_uri": "http://127.0.0.1:5173/auth/callback",
            "email": email,
            "state": "xyz",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert "code=" in location
    assert "state=xyz" in location
    return location.split("code=")[1].split("&")[0]


async def test_oauth_full_flow(client: AsyncClient) -> None:
    code = await _get_code(client)
    token_resp = await client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "http://127.0.0.1:5173/auth/callback",
            "client_id": settings.client_id,
            "client_secret": settings.client_secret,
        },
    )
    assert token_resp.status_code == 200
    access_token = token_resp.json()["access_token"]

    userinfo = await client.get(
        "/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert userinfo.status_code == 200
    body = userinfo.json()
    assert body["sub"] == "sso-leader-1"
    assert body["email"] == "leader@innopolis.university"
    assert body["name"]
    assert "role" not in body
    assert "can_sudo" not in body


async def test_code_single_use(client: AsyncClient) -> None:
    code = await _get_code(client)
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": "http://127.0.0.1:5173/auth/callback",
        "client_id": settings.client_id,
        "client_secret": settings.client_secret,
    }
    first = await client.post("/token", data=payload)
    assert first.status_code == 200
    second = await client.post("/token", data=payload)
    assert second.status_code == 400


async def test_userinfo_requires_bearer(client: AsyncClient) -> None:
    resp = await client.get("/userinfo")
    assert resp.status_code == 401
