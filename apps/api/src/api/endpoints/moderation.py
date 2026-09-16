from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.core.database import get_db
from src.core.errors import api_error
from src.models.entities import User
from src.schemas.common import ApiSuccess, ErrorCode
from src.schemas.moderation import DisputeReportDTO, ModerateReportDTO
from src.schemas.report import ReportResponse
from src.services.moderation_service import (
    complete_report,
    dispute_report,
    moderate_report,
)
from src.services.report_service import (
    ReportNotFoundError,
    report_to_response,
)
from src.services.report_state import InvalidTransitionError

router = APIRouter(prefix="/reports", tags=["moderation"])


def _map_errors(exc: Exception) -> None:
    if isinstance(exc, ReportNotFoundError):
        raise api_error(404, ErrorCode.REPORT_NOT_FOUND, "Report not found") from None
    if isinstance(exc, InvalidTransitionError):
        raise api_error(400, exc.code, str(exc)) from None


@router.patch("/{report_id}/moderate", response_model=ApiSuccess[ReportResponse])
async def moderate(
    report_id: str,
    payload: ModerateReportDTO,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiSuccess[ReportResponse]:
    try:
        report = await moderate_report(session, user=user, report_id=report_id, payload=payload)
    except (ReportNotFoundError, InvalidTransitionError) as exc:
        _map_errors(exc)
        raise
    return ApiSuccess(data=report_to_response(report))


@router.post("/{report_id}/dispute", response_model=ApiSuccess[ReportResponse])
async def dispute(
    report_id: str,
    payload: DisputeReportDTO,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiSuccess[ReportResponse]:
    try:
        report = await dispute_report(session, user=user, report_id=report_id, payload=payload)
    except (ReportNotFoundError, InvalidTransitionError) as exc:
        _map_errors(exc)
        raise
    return ApiSuccess(data=report_to_response(report))


@router.post("/{report_id}/complete", response_model=ApiSuccess[ReportResponse])
async def complete(
    report_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiSuccess[ReportResponse]:
    try:
        report = await complete_report(session, user=user, report_id=report_id)
    except (ReportNotFoundError, InvalidTransitionError) as exc:
        _map_errors(exc)
        raise
    return ApiSuccess(data=report_to_response(report))
