"""Admin audit log listing (from audit_logs)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.entities import AuditLog
from src.schemas.criteria import AuditListResponse, AuditLogOut


async def list_audit_logs(
    session: AsyncSession,
    *,
    entity_type: str | None = None,
    entity_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> AuditListResponse:
    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    filters = []
    if entity_type:
        filters.append(AuditLog.entity_type == entity_type)
    if entity_id:
        filters.append(AuditLog.entity_id == entity_id)

    total = await session.scalar(
        select(func.count()).select_from(AuditLog).where(*filters) if filters else select(func.count()).select_from(AuditLog)
    )

    query = (
        select(AuditLog)
        .options(selectinload(AuditLog.performed_by))
        .order_by(AuditLog.seq.desc())
        .limit(limit)
        .offset(offset)
    )
    if filters:
        query = query.where(*filters)

    result = await session.execute(query)
    items = [
        AuditLogOut(
            id=row.id,
            seq=row.seq,
            entityType=row.entity_type,
            entityId=row.entity_id,
            action=row.action,
            oldValue=row.old_value,
            newValue=row.new_value,
            performedByName=row.performed_by.name if row.performed_by else "unknown",
            performedByRole=row.performed_by_role,
            performedAt=row.performed_at,
            reason=row.reason,
            hash=row.hash,
        )
        for row in result.scalars().all()
    ]
    return AuditListResponse(items=items, total=int(total or 0), limit=limit, offset=offset)
