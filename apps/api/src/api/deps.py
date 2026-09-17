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
from src.policies.common import ensure_moderator, ensure_sudo
from src.schemas.common import ErrorCode


async def get_user_by_id(session: AsyncSession, user_id: str) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise api_error(
            401, ErrorCode.UNAUTHORIZED, "Missing bearer token", message_key="unauthorized.missing_token"
        )
    token = authorization[7:].strip()
    try:
        payload = decode_token(token, expected_type="access")
    except TokenError:
        raise api_error(
            401, ErrorCode.UNAUTHORIZED, "Invalid token", message_key="unauthorized.invalid_token"
        ) from None

    user = await get_user_by_id(session, str(payload["sub"]))
    if user is None:
        raise api_error(
            401, ErrorCode.UNAUTHORIZED, "User not found", message_key="unauthorized.user_not_found"
        )
    return user


async def get_user_club_ids(session: AsyncSession, user_id: str) -> frozenset[str]:
    result = await session.execute(select(ClubLeader.club_id).where(ClubLeader.user_id == user_id))
    return frozenset(row[0] for row in result.all())


def require_role(*roles: UserRole):
    async def dependency(
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if user.role not in roles:
            raise api_error(
                403, ErrorCode.FORBIDDEN, "Insufficient role", message_key="forbidden.insufficient_role"
            )
        return user

    return dependency


async def require_moderator(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    ensure_moderator(user)
    return user


async def require_sudo(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    ensure_sudo(user)
    return user
