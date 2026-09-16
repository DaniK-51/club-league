"""Yandex Disk WebDAV upload client + debouncer tests."""

from __future__ import annotations

import base64
from collections.abc import Iterator

import httpx
import pytest
from src.core.config import get_settings
from src.services.sync_service import ClubTotal, SyncDebouncer
from src.services.yandex_sheets import (
    NullYandexClient,
    YandexDiskError,
    YandexWebDavClient,
    _normalize_remote_path,
    encode_csv_rows,
)


@pytest.fixture
def yandex_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("YANDEX_WEBDAV_USERNAME", "testuser")
    monkeypatch.setenv("YANDEX_WEBDAV_PASSWORD", "apppassword16chr")
    monkeypatch.setenv("YANDEX_WEBDAV_BASE", "https://webdav.test")
    monkeypatch.setenv("YANDEX_DISK_PATH", "club-league/rating.csv")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class _RecordingWriter:
    def __init__(self) -> None:
        self.calls: list[list[list[object]]] = []

    async def write_rows(self, values: list[list[object]]) -> None:
        self.calls.append(values)


def _mock_transport(handler) -> httpx.MockTransport:  # type: ignore[no-untyped-def]
    return httpx.MockTransport(handler)


def test_encode_csv_utf8_bom() -> None:
    data = encode_csv_rows([["Клуб", "Баллы"], ["A", 10]])
    assert data.startswith(b"\xef\xbb\xbf")
    assert "Клуб".encode() in data


def test_normalize_path() -> None:
    assert _normalize_remote_path("disk:/a/b.csv") == "a/b.csv"
    assert _normalize_remote_path("/a/b.csv") == "a/b.csv"
    assert _normalize_remote_path("a/b.csv") == "a/b.csv"


async def test_mkcol_then_put_with_basic_auth(yandex_env: None) -> None:
    events: list[str] = []
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "MKCOL":
            events.append(f"MKCOL {request.url.path}")
            captured["auth"] = request.headers.get("Authorization", "")
            return httpx.Response(201)
        if request.method == "PUT":
            events.append(f"PUT {request.url.path}")
            captured["body"] = request.content
            captured["overwrite"] = request.headers.get("Overwrite", "")
            return httpx.Response(201)
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=_mock_transport(handler))
    webdav = YandexWebDavClient(client, max_retries=0, base_delay=0.01)
    path = await webdav.upload_bytes(encode_csv_rows([["Rank", "Club"], [1, "Alpha"]]))
    assert path == "club-league/rating.csv"
    assert events[0].startswith("MKCOL")
    assert events[1] == "PUT /club-league/rating.csv"
    expected = base64.b64encode(b"testuser:apppassword16chr").decode()
    assert captured["auth"] == f"Basic {expected}"
    assert captured["overwrite"] == "T"
    assert b"Alpha" in captured["body"]  # type: ignore[operator]
    await client.aclose()


async def test_mkcol_405_treated_as_exists(yandex_env: None) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "MKCOL":
            return httpx.Response(405)
        if request.method == "PUT":
            return httpx.Response(204)
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=_mock_transport(handler))
    webdav = YandexWebDavClient(client, max_retries=0, base_delay=0.01)
    await webdav.write_rows([["x"]])
    await client.aclose()


async def test_retry_on_5xx(yandex_env: None) -> None:
    state = {"put_fails": 2}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "MKCOL":
            return httpx.Response(201)
        if state["put_fails"] > 0:
            state["put_fails"] -= 1
            return httpx.Response(500, text="boom")
        return httpx.Response(201)

    client = httpx.AsyncClient(transport=_mock_transport(handler))
    webdav = YandexWebDavClient(client, max_retries=3, base_delay=0.01)
    await webdav.write_rows([["x"]])
    assert state["put_fails"] == 0
    await client.aclose()


async def test_401_no_retry(yandex_env: None) -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(401, text="Unauthorized")

    client = httpx.AsyncClient(transport=_mock_transport(handler))
    webdav = YandexWebDavClient(client, max_retries=5, base_delay=0.01)
    with pytest.raises(YandexDiskError) as exc:
        await webdav.write_rows([["x"]])
    assert exc.value.status_code == 401
    assert calls["n"] == 1
    await client.aclose()


async def test_missing_username(yandex_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("YANDEX_WEBDAV_USERNAME", "")
    get_settings.cache_clear()
    client = httpx.AsyncClient(transport=_mock_transport(lambda r: httpx.Response(201)))
    webdav = YandexWebDavClient(client, max_retries=0, base_delay=0.01)
    with pytest.raises(YandexDiskError, match="USERNAME"):
        await webdav.write_rows([["x"]])
    get_settings.cache_clear()
    await client.aclose()


async def test_null_client_records_csv() -> None:
    null = NullYandexClient()
    await null.write_rows([["Club", 1]])
    assert null.written == [[["Club", 1]]]
    assert null.uploads and null.uploads[0].startswith(b"\xef\xbb\xbf")


async def test_debouncer_flush_uses_writer(monkeypatch: pytest.MonkeyPatch) -> None:
    writer = _RecordingWriter()
    d = SyncDebouncer(debounce_seconds=1)

    async def fake_compute(session: object, *, semester: str) -> list[ClubTotal]:
        return [
            ClubTotal(club_id="c1", club_name="Club", total_points=10, breakdown={"C8": 10})
        ]

    monkeypatch.setattr("src.services.sync_service.compute_rating", fake_compute)
    totals = await d.flush(writer=writer)  # type: ignore[arg-type]
    assert len(totals) == 1
    assert writer.calls[0][0] == ["Rank", "Club", "Total", "Semester", "Breakdown"]
    assert d.run_count == 1
