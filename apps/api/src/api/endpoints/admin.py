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
from src.schemas.sudo import SudoActionDTO, SudoSuccess
from src.schemas.sync import SyncForceRequest, SyncQueued, SyncStatus
from src.services.sudo_service import (
    SudoReportNotFoundError,
    SudoValidationError,
    run_sudo_action,
)
from src.services.sync_service import debouncer

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/sudo", response_model=ApiSuccess[SudoSuccess])
async def sudo(
    payload: SudoActionDTO,
    user: Annotated[User, Depends(require_sudo)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiSuccess[SudoSuccess]:
    try:
        await run_sudo_action(session, user=user, payload=payload)
    except SudoReportNotFoundError:
        raise api_error(
            404, ErrorCode.REPORT_NOT_FOUND, "Report not found", message_key="report.not_found"
        ) from None
    except SudoValidationError as exc:
        raise api_error(400, ErrorCode.INVALID_STATUS_TRANSITION, str(exc)) from None
    return ApiSuccess(data=SudoSuccess())


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


@router.post("/sync/force", response_model=ApiSuccess[SyncQueued])
async def sync_force(
    user: Annotated[User, Depends(require_moderator)],
    body: SyncForceRequest | None = None,
) -> ApiSuccess[SyncQueued]:
    """api-contract: enqueue sync (optional semester in body)."""
    del user, body  # semester stored for future per-semester debouncer
    debouncer.notify_immediate()
    return ApiSuccess(data=SyncQueued())
