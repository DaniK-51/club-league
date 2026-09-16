"""Yandex Disk WebDAV client — upload rating CSV (overwrite).

Yandex Disk WebDAV:
  Base: https://webdav.yandex.ru/
  Auth: HTTP Basic (Yandex login + **application password**, not account password)
  PUT   /<path>/rating.csv     — replace file
  MKCOL /<path>/               — create parent folder if missing

The 16-char `YANDEX_OAUTH_TOKEN` from disk settings is a WebDAV app password.
System DB remains the single source of truth; Disk is a read-only mirror file.

Dev: `YANDEX_SHEETS_ENABLED=false` → NullYandexClient (no network).
"""

from __future__ import annotations

import asyncio
import base64
import csv
import io
import logging
from typing import Any, Protocol
from urllib.parse import quote

import httpx

from src.core.config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_REMOTE_PATH = "club-league/rating.csv"


class YandexDiskError(Exception):
    def __init__(
        self,
        message: str,
        *,
        attempts: int = 0,
        status_code: int | None = None,
    ) -> None:
        self.attempts = attempts
        self.status_code = status_code
        super().__init__(message)


class SheetsWriter(Protocol):
    """Writer used by SyncDebouncer."""

    async def write_rows(self, values: list[list[Any]]) -> None: ...


def encode_csv_rows(values: list[list[Any]]) -> bytes:
    """UTF-8 CSV with BOM so Excel opens Cyrillic correctly."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    for row in values:
        writer.writerow(["" if cell is None else cell for cell in row])
    return buffer.getvalue().encode("utf-8-sig")


def _normalize_remote_path(path: str) -> str:
    """`disk:/a/b.csv` or `/a/b.csv` or `a/b.csv` → `a/b.csv`."""
    p = path.strip()
    if p.startswith("disk:"):
        p = p[5:]
    return p.strip("/")


class NullYandexClient:
    """No-op writer used when sync is disabled (dev / tests)."""

    def __init__(self) -> None:
        self.written: list[list[Any]] = []
        self.uploads: list[bytes] = []

    async def write_rows(self, values: list[list[Any]]) -> None:
        self.written.append(values)
        self.uploads.append(encode_csv_rows(values))
        logger.info("NullYandexClient stored %s rows (sync disabled)", len(values))


class YandexWebDavClient:
    """Uploads rating CSV via WebDAV, replacing the previous file."""

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        *,
        max_retries: int | None = None,
        base_delay: float | None = None,
    ) -> None:
        settings = get_settings()
        self._client = client
        self._owns_client = client is None
        self._max_retries = (
            max_retries if max_retries is not None else settings.sync_max_retries
        )
        self._base_delay = (
            base_delay if base_delay is not None else settings.sync_retry_base_seconds
        )

    async def __aenter__(self) -> YandexWebDavClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
            self._owns_client = True
        return self._client

    def _auth_header(self) -> dict[str, str]:
        settings = get_settings()
        user = settings.yandex_webdav_username
        password = settings.yandex_webdav_password or settings.yandex_oauth_token
        if not user:
            raise YandexDiskError("YANDEX_WEBDAV_USERNAME is not configured")
        if not password:
            raise YandexDiskError("YANDEX_WEBDAV_PASSWORD is not configured")
        raw = f"{user}:{password}".encode()
        return {"Authorization": f"Basic {base64.b64encode(raw).decode('ascii')}"}

    def _base_url(self) -> str:
        settings = get_settings()
        return settings.yandex_webdav_base.rstrip("/") + "/"

    def _file_url(self, remote_path: str) -> str:
        parts = [_normalize_remote_path(remote_path)]
        encoded = "/".join(quote(part, safe="") for part in parts[0].split("/"))
        return self._base_url() + encoded

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        content: bytes | None = None,
        ok_statuses: frozenset[int] | None = None,
    ) -> httpx.Response:
        client = self._ensure_client()
        ok = ok_statuses or frozenset({200, 201, 204, 207})
        last_error: Exception | None = None
        attempts = 0

        for attempt in range(self._max_retries + 1):
            attempts = attempt + 1
            try:
                response = await client.request(
                    method, url, headers=headers, content=content
                )
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning("WebDAV HTTP error attempt=%s: %s", attempts, exc)
            else:
                if response.status_code in ok or response.status_code < 400:
                    return response
                last_error = YandexDiskError(
                    f"HTTP {response.status_code}: {response.text[:300]}",
                    attempts=attempts,
                    status_code=response.status_code,
                )
                if response.status_code not in {429} and response.status_code < 500:
                    raise last_error

            if attempt < self._max_retries:
                await asyncio.sleep(self._base_delay * (2**attempt))

        raise YandexDiskError(
            f"webdav request failed after {attempts} attempts: {last_error}",
            attempts=attempts,
        ) from last_error

    async def ensure_parent_dirs(self, remote_path: str) -> None:
        """MKCOL each parent collection (405 = already exists)."""
        normalized = _normalize_remote_path(remote_path)
        parts = normalized.split("/")
        if len(parts) <= 1:
            return
        headers = self._auth_header()
        current = ""
        for part in parts[:-1]:
            current = f"{current}/{part}" if current else part
            url = self._base_url() + "/".join(
                quote(p, safe="") for p in current.split("/")
            )
            # 201 created, 405/301 already exists
            await self._request_with_retry(
                "MKCOL",
                url,
                headers=headers,
                ok_statuses=frozenset({201, 405, 301, 409}),
            )

    async def upload_bytes(self, data: bytes, *, remote_path: str | None = None) -> str:
        settings = get_settings()
        path = _normalize_remote_path(remote_path or settings.yandex_disk_path)
        await self.ensure_parent_dirs(path)
        url = self._file_url(path)
        headers = {
            **self._auth_header(),
            "Content-Type": "text/csv; charset=utf-8",
            "Overwrite": "T",
        }
        await self._request_with_retry(
            "PUT",
            url,
            headers=headers,
            content=data,
            ok_statuses=frozenset({200, 201, 204}),
        )
        logger.info("WebDAV uploaded bytes=%s path=%s", len(data), path)
        return path

    async def write_rows(self, values: list[list[Any]]) -> None:
        await self.upload_bytes(encode_csv_rows(values))


def build_client() -> SheetsWriter:
    settings = get_settings()
    if not settings.yandex_sheets_enabled:
        return NullYandexClient()
    has_password = bool(settings.yandex_webdav_password or settings.yandex_oauth_token)
    if not settings.yandex_webdav_username or not has_password:
        logger.warning(
            "Yandex sync enabled but WebDAV credentials incomplete — using Null client"
        )
        return NullYandexClient()
    return YandexWebDavClient()


# Aliases for existing imports
YandexSheetsError = YandexDiskError
YandexSheetsClient = YandexWebDavClient
YandexDiskClient = YandexWebDavClient
