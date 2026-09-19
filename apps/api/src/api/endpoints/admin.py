from __future__ import annotations

from typing import Annotated, Never

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import require_moderator, require_sudo
from src.core.config import get_settings
from src.core.database import get_db
from src.core.errors import api_error
from src.models.entities import User
from src.models.enums import ClubCategory
from src.schemas.common import ApiSuccess, ErrorCode
from src.schemas.criteria import AuditListResponse, CriteriaOut, RuleOut, UpdateRuleDTO
from src.schemas.period import CreatePeriodDTO, PeriodOut, UpdatePeriodDTO
from src.schemas.sudo import SudoActionDTO, SudoSuccess
from src.schemas.sync import SyncForceRequest, SyncQueued, SyncStatus
from src.services.audit_query import list_audit_logs
from src.services.criteria_service import (
    RuleNotFoundError,
    get_rule,
    list_criteria,
    update_rule,
)
from src.services.period_service import (
    PeriodNotFoundError,
    create_period,
    delete_period,
    list_periods,
    update_period,
)
from src.services.sudo_service import (
    SudoReportNotFoundError,
    SudoValidationError,
    run_sudo_action,
)
from src.services.sync_service import debouncer

router = APIRouter(prefix="/admin", tags=["admin"])


def _not_found(code: ErrorCode, message: str) -> Never:
    """Raise a 404 API envelope for missing admin resources."""
    raise api_error(404, code, message)


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
    del user, body
    debouncer.notify_immediate()
    return ApiSuccess(data=SyncQueued())


@router.get("/rules/{rule_id}", response_model=ApiSuccess[RuleOut])
async def admin_get_rule(
    rule_id: str,
    user: Annotated[User, Depends(require_moderator)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiSuccess[RuleOut]:
    del user
    try:
        rule = await get_rule(session, rule_id)
    except RuleNotFoundError:
        _not_found(ErrorCode.RULES_VERSION_NOT_FOUND, "Rule not found")
    return ApiSuccess(data=rule)


@router.patch("/rules/{rule_id}", response_model=ApiSuccess[RuleOut])
async def admin_update_rule(
    rule_id: str,
    payload: UpdateRuleDTO,
    user: Annotated[User, Depends(require_moderator)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiSuccess[RuleOut]:
    """Manager edits rule JSONB without code deploy (user story 5)."""
    try:
        rule = await update_rule(session, user=user, rule_id=rule_id, payload=payload)
    except RuleNotFoundError:
        _not_found(ErrorCode.RULES_VERSION_NOT_FOUND, "Rule not found")
    return ApiSuccess(data=rule)


@router.get("/audit", response_model=ApiSuccess[AuditListResponse])
async def admin_audit_list(
    user: Annotated[User, Depends(require_moderator)],
    session: Annotated[AsyncSession, Depends(get_db)],
    entity_type: Annotated[str | None, Query(alias="entityType")] = None,
    entity_id: Annotated[str | None, Query(alias="entityId")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ApiSuccess[AuditListResponse]:
    del user
    result = await list_audit_logs(
        session,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
        offset=offset,
    )
    return ApiSuccess(data=result)


# ─── Periods CRUD (moderator) ────────────────────────────────────────────


@router.get("/periods", response_model=ApiSuccess[list[PeriodOut]])
async def admin_list_periods(
    user: Annotated[User, Depends(require_moderator)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiSuccess[list[PeriodOut]]:
    items = await list_periods(session, user=user)
    return ApiSuccess(data=items)


@router.post("/periods", response_model=ApiSuccess[PeriodOut], status_code=201)
async def admin_create_period(
    payload: CreatePeriodDTO,
    user: Annotated[User, Depends(require_moderator)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiSuccess[PeriodOut]:
    item = await create_period(session, user=user, payload=payload)
    return ApiSuccess(data=item)


@router.patch("/periods/{period_id}", response_model=ApiSuccess[PeriodOut])
async def admin_update_period(
    period_id: str,
    payload: UpdatePeriodDTO,
    user: Annotated[User, Depends(require_moderator)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiSuccess[PeriodOut]:
    try:
        item = await update_period(session, user=user, period_id=period_id, payload=payload)
    except PeriodNotFoundError:
        _not_found(ErrorCode.PERIOD_NOT_FOUND, "Period not found")
    return ApiSuccess(data=item)


@router.delete("/periods/{period_id}", response_model=ApiSuccess[dict[str, bool]])
async def admin_delete_period(
    period_id: str,
    user: Annotated[User, Depends(require_moderator)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiSuccess[dict[str, bool]]:
    try:
        await delete_period(session, user=user, period_id=period_id)
    except PeriodNotFoundError:
        _not_found(ErrorCode.PERIOD_NOT_FOUND, "Period not found")
    return ApiSuccess(data={"success": True})


criteria_router = APIRouter(tags=["criteria"])


@criteria_router.get("/criteria", response_model=ApiSuccess[list[CriteriaOut]])
async def public_criteria(
    session: Annotated[AsyncSession, Depends(get_db)],
    semester: Annotated[str | None, Query()] = None,
    category: Annotated[ClubCategory | None, Query()] = None,
) -> ApiSuccess[list[CriteriaOut]]:
    """Active criteria catalog (v2) for report form and rating UI."""
    items = await list_criteria(session, semester=semester, category=category)
    return ApiSuccess(data=items)
