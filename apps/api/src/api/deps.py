from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.errors import api_error
from src.core.security import TokenError, decode_token
from src.models.entities import ClubLeader, User
from src.models.enums import UserRole
from src.schemas.common import ErrorCode


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise api_error(401, ErrorCode.UNAUTHORIZED, "Missing bearer token")
    token = authorization[7:].strip()
    try:
        payload = decode_token(token, expected_type="access")
    except TokenError:
        raise api_error(401, ErrorCode.UNAUTHORIZED, "Invalid or expired token") from None

    user_id = str(payload["sub"])
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise api_error(401, ErrorCode.UNAUTHORIZED, "User not found")
    return user


async def get_user_club_ids(session: AsyncSession, user_id: str) -> frozenset[str]:
    result = await session.execute(select(ClubLeader.club_id).where(ClubLeader.user_id == user_id))
    return frozenset(row[0] for row in result.all())


def require_role(*roles: UserRole):
    async def dependency(
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if user.role not in roles:
            raise api_error(403, ErrorCode.FORBIDDEN, "Insufficient role")
        return user

    return dependency


async def require_moderator(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    if user.role != UserRole.MODERATOR:
        raise api_error(403, ErrorCode.FORBIDDEN, "Moderator role required")
    return user


async def require_sudo(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    if user.role != UserRole.MODERATOR or not user.can_sudo:
        raise api_error(403, ErrorCode.SUDO_REQUIRED, "Sudo privileges required")
    return user
