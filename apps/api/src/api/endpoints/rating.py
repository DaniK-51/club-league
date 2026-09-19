from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.schemas.common import ApiSuccess
from src.schemas.period import PeriodOut
from src.schemas.sync import RatingResponse, club_total_to_rating
from src.services.period_service import list_periods_public
from src.services.sync_service import compute_rating

router = APIRouter(prefix="/rating", tags=["rating"])
# Public periods for rating page filter (guests need archived periods too).
public_router = APIRouter(tags=["rating"])


@public_router.get("/periods", response_model=ApiSuccess[list[PeriodOut]])
async def public_list_periods(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiSuccess[list[PeriodOut]]:
    """All periods (active + archived). No auth — used by public rating filter."""
    return ApiSuccess(data=await list_periods_public(session))


@router.get("", response_model=ApiSuccess[RatingResponse])
async def get_rating(
    session: Annotated[AsyncSession, Depends(get_db)],
    period: Annotated[str | None, Query()] = None,
    semester: Annotated[str | None, Query()] = None,
) -> ApiSuccess[RatingResponse]:
    """Public club rating. `period` takes priority over `semester`."""
    totals = await compute_rating(session, period_name=period, semester=semester)
    return ApiSuccess(
        data=RatingResponse(clubs=[club_total_to_rating(t) for t in totals])
    )
