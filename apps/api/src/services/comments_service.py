"""GitHub-issues-style comment thread extracted from audit_logs (no separate table).

Docs: chat is dynamically pulled from audit; comment + status_changed events.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.entities import AuditLog


class CommentEntry(BaseModel):
    id: str
    action: str
    authorName: str
    authorRole: str
    body: str
    oldValue: dict | None = None
    newValue: dict | None = None
    createdAt: datetime


async def list_report_comments(
    session: AsyncSession,
    *,
    report_id: str,
) -> list[CommentEntry]:
    result = await session.execute(
        select(AuditLog)
        .options(selectinload(AuditLog.performed_by))
        .where(
            AuditLog.entity_type == "report",
            AuditLog.entity_id == report_id,
            AuditLog.action.in_(["created", "updated", "status_changed", "points_updated", "deleted", "sudo_action"]),
        )
        .order_by(AuditLog.seq.asc())
    )
    entries: list[CommentEntry] = []
    for row in result.scalars().all():
        author = row.performed_by
        body_parts: list[str] = []
        if row.reason:
            body_parts.append(row.reason)
        if isinstance(row.new_value, dict):
            mod_comment = row.new_value.get("moderation_comment")
            if mod_comment and (not body_parts or mod_comment not in body_parts):
                body_parts.append(str(mod_comment))
            if not body_parts:
                status = row.new_value.get("status")
                if status:
                    body_parts.append(f"status → {status}")
                elif row.action == "points_updated":
                    body_parts.append(f"final_points → {row.new_value.get('final_points')}")
        if not body_parts:
            body_parts.append(row.action)
        entries.append(
            CommentEntry(
                id=row.id,
                action=row.action,
                authorName=author.name if author else "unknown",
                authorRole=row.performed_by_role,
                body="\n".join(body_parts),
                oldValue=row.old_value,
                newValue=row.new_value,
                createdAt=row.performed_at,
            )
        )
    return entries
