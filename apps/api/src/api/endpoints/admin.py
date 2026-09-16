from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import require_moderator, require_sudo
from src.core.config import get_settings
from src.core.database import get_db
from src.core.errors import api_error
from src.models.entities import User
from src.schemas.common import ApiSuccess, ErrorCode
from src.schemas.sudo import SudoActionDTO, SudoResult
from src.schemas.sync import SyncStatus
from src.services.sudo_service import (
    SudoReportNotFoundError,
    SudoValidationError,
    run_sudo_action,
)
from src.services.sync_service import debouncer
from src.services.yandex_sheets import YandexSheetsError

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/sudo", response_model=ApiSuccess[SudoResult])
async def sudo(
    payload: SudoActionDTO,
    user: Annotated[User, Depends(require_sudo)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiSuccess[SudoResult]:
    try:
        report = await run_sudo_action(session, user=user, payload=payload)
    except SudoReportNotFoundError:
        raise api_error(404, ErrorCode.REPORT_NOT_FOUND, "Report not found") from None
    except SudoValidationError as exc:
        raise api_error(400, ErrorCode.INVALID_STATUS_TRANSITION, str(exc)) from None
    return ApiSuccess(
        data=SudoResult(
            reportId=report.id,
            action=payload.action,
            status=report.status,
            finalPoints=report.final_points,
            isDeleted=report.is_deleted,
        )
    )


@router.get("/sync/status", response_model=ApiSuccess[SyncStatus])
async def sync_status(
    user: Annotated[User, Depends(require_moderator)],
) -> ApiSuccess[SyncStatus]:
    settings = get_settings()
    return ApiSuccess(
        data=SyncStatus(
            pending=debouncer.pending,
            lastRunAt=debouncer.last_run_at,
            lastError=debouncer.last_error,
            runCount=debouncer.run_count,
            debounceSeconds=settings.sync_debounce_seconds,
        )
    )


@router.post("/sync/force", response_model=ApiSuccess[SyncStatus])
async def sync_force(
    user: Annotated[User, Depends(require_moderator)],
) -> ApiSuccess[SyncStatus]:
    """Force immediate Yandex sync (ignores 1h debounce)."""
    try:
        await debouncer.flush()
    except YandexSheetsError as exc:
        raise api_error(502, ErrorCode.YANDEX_SYNC_FAILED, str(exc)) from None
    settings = get_settings()
    return ApiSuccess(
        data=SyncStatus(
            pending=debouncer.pending,
            lastRunAt=debouncer.last_run_at,
            lastError=debouncer.last_error,
            runCount=debouncer.run_count,
            debounceSeconds=settings.sync_debounce_seconds,
        )
    )

