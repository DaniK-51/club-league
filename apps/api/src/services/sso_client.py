from __future__ import annotations

from dataclasses import dataclass

import httpx

from src.core.config import get_settings


class SSOError(Exception):
    pass


@dataclass(frozen=True)
class SSOProfile:
    sso_id: str
    email: str
    name: str


class SSOClient:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> SSOClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def exchange_code(self, code: str) -> SSOProfile:
        settings = get_settings()
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)
            self._owns_client = True

        try:
            token_resp = await self._client.post(
                settings.sso_token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.sso_redirect_uri,
                    "client_id": settings.sso_client_id,
                    "client_secret": settings.sso_client_secret,
                },
            )
        except httpx.HTTPError as exc:
            raise SSOError("sso_token_unreachable") from exc

        if token_resp.status_code != 200:
            raise SSOError("sso_token_exchange_failed")
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise SSOError("sso_token_missing")

        try:
            userinfo_resp = await self._client.get(
                settings.sso_userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        except httpx.HTTPError as exc:
            raise SSOError("sso_userinfo_unreachable") from exc

        if userinfo_resp.status_code != 200:
            raise SSOError("sso_userinfo_failed")
        info = userinfo_resp.json()

        sso_id = str(info.get("sub") or "").strip()
        email = str(info.get("email") or "").strip()
        name = str(info.get("name") or "").strip()
        if not sso_id or not email or not name:
            raise SSOError("sso_profile_incomplete")
        return SSOProfile(sso_id=sso_id, email=email, name=name)
