from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_user_club_ids
from src.core.database import get_db
from src.models.entities import User
from src.schemas.auth import MeResponse
from src.schemas.common import ApiSuccess

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=ApiSuccess[MeResponse])
async def me(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiSuccess[MeResponse]:
    club_ids = await get_user_club_ids(session, user.id)
    return ApiSuccess(
        data=MeResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            canSudo=user.can_sudo,
            clubIds=sorted(club_ids),
        )
    )
