"""FastAPI dependency auth tests (require_moderator / require_sudo / require_role)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from src.api.deps import get_current_user, require_moderator, require_role, require_sudo
from src.core.database import get_session_factory
from src.core.security import create_access_token
from src.models.entities import User
from src.models.enums import UserRole
from starlette.exceptions import HTTPException as StarletteHTTPException

authz_app = FastAPI()


@authz_app.exception_handler(StarletteHTTPException)
async def _http_err(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and "error" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "INTERNAL_SERVER_ERROR", "message": str(detail)}},
    )


@authz_app.get("/mod-only")
async def mod_only(user: User = Depends(require_moderator)) -> dict[str, str]:
    return {"role": user.role.value}


@authz_app.get("/sudo-only")
async def sudo_only(user: User = Depends(require_sudo)) -> dict[str, str]:
    return {"role": user.role.value}


@authz_app.get("/leader-only")
async def leader_only(user: User = Depends(require_role(UserRole.CLUB_LEADER))) -> dict[str, str]:
    return {"role": user.role.value}


@authz_app.get("/guest-ok")
async def guest_ok(user: User = Depends(get_current_user)) -> dict[str, str]:
    return {"id": user.id}


@pytest.fixture
async def dep_client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=authz_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _create_user(email: str, role: UserRole, *, can_sudo: bool = False) -> str:
    factory = get_session_factory()
    async with factory() as session:
        user = User(
            sso_id=f"sso-{email}",
            email=email,
            name=email,
            role=role,
            can_sudo=can_sudo,
            created_at=datetime.now(UTC),
        )
        session.add(user)
        await session.commit()
        return user.id


async def _delete_user(email: str) -> None:
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(delete(User).where(User.email == email))
        await session.commit()


async def test_require_moderator_forbidden_for_leader(dep_client: AsyncClient) -> None:
    uid = await _create_user("dep.leader@x.test", UserRole.CLUB_LEADER)
    token = create_access_token(user_id=uid, role=UserRole.CLUB_LEADER, can_sudo=False)
    resp = await dep_client.get("/mod-only", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"
    await _delete_user("dep.leader@x.test")


async def test_require_moderator_ok(dep_client: AsyncClient) -> None:
    uid = await _create_user("dep.mod@x.test", UserRole.MODERATOR)
    token = create_access_token(user_id=uid, role=UserRole.MODERATOR, can_sudo=True)
    resp = await dep_client.get("/mod-only", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    await _delete_user("dep.mod@x.test")


async def test_require_sudo_forbidden_without_flag(dep_client: AsyncClient) -> None:
    uid = await _create_user("dep.mod.nosudo@x.test", UserRole.MODERATOR, can_sudo=False)
    token = create_access_token(user_id=uid, role=UserRole.MODERATOR, can_sudo=False)
    resp = await dep_client.get("/sudo-only", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "SUDO_REQUIRED"
    await _delete_user("dep.mod.nosudo@x.test")


async def test_require_sudo_ok(dep_client: AsyncClient) -> None:
    uid = await _create_user("dep.sudo@x.test", UserRole.MODERATOR, can_sudo=True)
    token = create_access_token(user_id=uid, role=UserRole.MODERATOR, can_sudo=True)
    resp = await dep_client.get("/sudo-only", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    await _delete_user("dep.sudo@x.test")


async def test_require_role_wrong_role(dep_client: AsyncClient) -> None:
    uid = await _create_user("dep.guest@x.test", UserRole.GUEST)
    token = create_access_token(user_id=uid, role=UserRole.GUEST, can_sudo=False)
    resp = await dep_client.get("/leader-only", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    await _delete_user("dep.guest@x.test")


async def test_get_current_user_missing_token(dep_client: AsyncClient) -> None:
    resp = await dep_client.get("/guest-ok")
    assert resp.status_code == 401


async def test_get_current_user_unknown_sub(dep_client: AsyncClient) -> None:
    token = create_access_token(
        user_id="00000000-0000-0000-0000-000000000000",
        role=UserRole.GUEST,
        can_sudo=False,
    )
    resp = await dep_client.get("/guest-ok", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"
