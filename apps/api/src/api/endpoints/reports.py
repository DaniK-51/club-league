from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.core.database import get_db
from src.core.errors import api_error
from src.models.entities import User
from src.schemas.common import ApiSuccess, ErrorCode
from src.schemas.report import CreateReportDTO, ReportResponse, SetCalculationDTO, UpdateReportDTO
from src.services.comments_service import (
    CommentEntry,
    CreateCommentDTO,
    add_report_comment,
    list_report_comments,
)
from src.services.report_service import (
    ReportNotFoundError,
    create_report,
    get_report,
    list_reports,
    report_to_response,
    set_calculation,
    soft_delete_report,
    submit_report,
    update_report,
)
from src.services.report_state import InvalidTransitionError

router = APIRouter(prefix="/reports", tags=["reports"])


def _map_report_errors(exc: Exception) -> None:
    if isinstance(exc, ReportNotFoundError):
        raise api_error(
            404, ErrorCode.REPORT_NOT_FOUND, "Report not found", message_key="report.not_found"
        ) from None
    if isinstance(exc, InvalidTransitionError):
        raise api_error(400, exc.code, str(exc)) from None


@router.post("", response_model=ApiSuccess[ReportResponse], status_code=201)
async def create(
    payload: CreateReportDTO,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiSuccess[ReportResponse]:
    try:
        report = await create_report(session, user=user, payload=payload)
    except (ReportNotFoundError, InvalidTransitionError) as exc:
        _map_report_errors(exc)
        raise
    return ApiSuccess(data=report_to_response(report))


@router.get("", response_model=ApiSuccess[list[ReportResponse]])
async def list_all(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    club_id: Annotated[str | None, Query(alias="clubId")] = None,
) -> ApiSuccess[list[ReportResponse]]:
    reports = await list_reports(session, user=user, club_id=club_id)
    return ApiSuccess(data=[report_to_response(r) for r in reports])


@router.get("/{report_id}", response_model=ApiSuccess[ReportResponse])
async def get_one(
    report_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiSuccess[ReportResponse]:
    try:
        report = await get_report(session, user=user, report_id=report_id)
    except (ReportNotFoundError, InvalidTransitionError) as exc:
        _map_report_errors(exc)
        raise
    return ApiSuccess(data=report_to_response(report))


@router.patch("/{report_id}", response_model=ApiSuccess[ReportResponse])
async def update(
    report_id: str,
    payload: UpdateReportDTO,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiSuccess[ReportResponse]:
    try:
        report = await update_report(session, user=user, report_id=report_id, payload=payload)
    except (ReportNotFoundError, InvalidTransitionError) as exc:
        _map_report_errors(exc)
        raise
    return ApiSuccess(data=report_to_response(report))


@router.patch("/{report_id}/calculation", response_model=ApiSuccess[ReportResponse])
async def set_calculation_method(
    report_id: str,
    payload: SetCalculationDTO,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiSuccess[ReportResponse]:
    """Set calculation method + manual points (no status change). Moderator only."""
    try:
        report = await set_calculation(session, user=user, report_id=report_id, payload=payload)
    except (ReportNotFoundError, InvalidTransitionError) as exc:
        _map_report_errors(exc)
        raise
    return ApiSuccess(data=report_to_response(report))


@router.post("/{report_id}/submit", response_model=ApiSuccess[ReportResponse])
async def submit(
    report_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiSuccess[ReportResponse]:
    try:
        report = await submit_report(session, user=user, report_id=report_id)
    except (ReportNotFoundError, InvalidTransitionError) as exc:
        _map_report_errors(exc)
        raise
    return ApiSuccess(data=report_to_response(report))


@router.delete("/{report_id}", response_model=ApiSuccess[dict[str, bool]])
async def delete_draft(
    report_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiSuccess[dict[str, bool]]:
    try:
        await soft_delete_report(session, user=user, report_id=report_id)
    except (ReportNotFoundError, InvalidTransitionError) as exc:
        _map_report_errors(exc)
        raise
    return ApiSuccess(data={"deleted": True})


@router.get("/{report_id}/comments", response_model=ApiSuccess[list[CommentEntry]])
async def report_comments(
    report_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiSuccess[list[CommentEntry]]:
    """GitHub-issues-style thread from audit_logs (docs: no separate chat table)."""
    try:
        report = await get_report(session, user=user, report_id=report_id)
    except (ReportNotFoundError, InvalidTransitionError) as exc:
        _map_report_errors(exc)
        raise
    del report
    entries = await list_report_comments(session, report_id=report_id)
    return ApiSuccess(data=entries)


@router.post("/{report_id}/comments", response_model=ApiSuccess[CommentEntry], status_code=201)
async def create_comment(
    report_id: str,
    payload: CreateCommentDTO,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiSuccess[CommentEntry]:
    """Add a regular comment (leader or moderator, any status except ARCHIVED)."""
    from src.models.enums import ReportStatus, UserRole

    report = await get_report(session, user=user, report_id=report_id)
    if report.status == ReportStatus.ARCHIVED:
        raise api_error(
            400,
            ErrorCode.INVALID_STATUS_TRANSITION,
            "Cannot comment on archived report",
        )
    if user.role == UserRole.GUEST:
        raise api_error(
            403,
            ErrorCode.FORBIDDEN,
            "Guests cannot comment",
            message_key="forbidden.insufficient_role",
        )
    entry = await add_report_comment(session, user=user, report_id=report_id, body=payload.body)
    return ApiSuccess(data=entry)
