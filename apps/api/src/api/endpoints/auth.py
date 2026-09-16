from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_user_by_id, get_user_club_ids
from src.core.database import get_db
from src.core.errors import api_error
from src.core.security import TokenError, create_token_pair, decode_token
from src.models.entities import User
from src.schemas.auth import (
    LoginResponse,
    RefreshDTO,
    SSOLoginDTO,
    user_to_me,
)
from src.schemas.common import ApiSuccess, ErrorCode
from src.services.auth_service import EmailConflictError, upsert_user_from_sso
from src.services.sso_client import SSOClient, SSOError

router = APIRouter(prefix="/auth", tags=["auth"])


async def _login_response(session: AsyncSession, user: User) -> ApiSuccess[LoginResponse]:
    access, refresh = create_token_pair(
        user_id=user.id,
        role=user.role,
        can_sudo=user.can_sudo,
    )
    club_ids = await get_user_club_ids(session, user.id)
    return ApiSuccess(
        data=LoginResponse(
            accessToken=access,
            refreshToken=refresh,
            user=user_to_me(user, club_ids),
        )
    )


@router.post("/sso/callback", response_model=ApiSuccess[LoginResponse])
async def sso_callback(
    payload: SSOLoginDTO,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiSuccess[LoginResponse]:
    async with SSOClient() as sso:
        try:
            profile = await sso.exchange_code(payload.code)
        except SSOError:
            raise api_error(401, ErrorCode.UNAUTHORIZED, "SSO authentication failed") from None

    try:
        user = await upsert_user_from_sso(session, profile)
    except EmailConflictError:
        raise api_error(
            401,
            ErrorCode.UNAUTHORIZED,
            "Email already linked to another SSO account",
        ) from None
    await session.commit()
    return await _login_response(session, user)


@router.post("/refresh", response_model=ApiSuccess[LoginResponse])
async def refresh_tokens(
    payload: RefreshDTO,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiSuccess[LoginResponse]:
    try:
        token_payload = decode_token(payload.refreshToken, expected_type="refresh")
    except TokenError:
        raise api_error(401, ErrorCode.UNAUTHORIZED, "Invalid refresh token") from None

    user = await get_user_by_id(session, str(token_payload["sub"]))
    if user is None:
        raise api_error(401, ErrorCode.UNAUTHORIZED, "User not found")
    return await _login_response(session, user)
