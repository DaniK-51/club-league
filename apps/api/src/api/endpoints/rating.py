from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.database import get_db
from src.schemas.common import ApiSuccess
from src.schemas.sync import RatingResponse, club_total_to_rating
from src.services.sync_service import compute_rating

router = APIRouter(prefix="/rating", tags=["rating"])


@router.get("", response_model=ApiSuccess[RatingResponse])
async def get_rating(
    session: Annotated[AsyncSession, Depends(get_db)],
    semester: Annotated[str | None, Query()] = None,
) -> ApiSuccess[RatingResponse]:
    """Public club rating (api-contract: { clubs: [...] })."""
    settings = get_settings()
    sem = semester or settings.current_semester
    totals = await compute_rating(session, semester=sem)
    return ApiSuccess(
        data=RatingResponse(clubs=[club_total_to_rating(t) for t in totals])
    )
