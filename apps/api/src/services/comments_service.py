"""GitHub-issues-style comment thread extracted from audit_logs (no separate table).

Docs: chat is dynamically pulled from audit; comment + status_changed events.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.entities import AuditLog, User
from src.services.audit_service import AuditService


class CommentEntry(BaseModel):
    id: str
    action: str
    authorName: str
    authorRole: str
    body: str
    oldValue: dict | None = None
    newValue: dict | None = None
    displayData: dict[str, Any] | None = None
    createdAt: datetime


class CreateCommentDTO(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


_COMMENT_ACTIONS = [
    "created",
    "updated",
    "status_changed",
    "points_updated",
    "deleted",
    "sudo_action",
    "comment",
    "calculation_updated",
]


def _build_body(row: AuditLog) -> str:
    """Build human-readable body from audit entry.

    Priority: display_data.summary > reason > new_value fields > action
    """
    # 1. display_data.summary — preferred for rendering
    if isinstance(row.display_data, dict):
        summary = row.display_data.get("summary")
        if summary:
            return str(summary)

    # 2. Regular comment: body lives in new_value.body
    if row.action == "comment" and isinstance(row.new_value, dict):
        return str(row.new_value.get("body", ""))

    # 3. Fallback: build from reason / new_value
    body_parts: list[str] = []
    if row.reason:
        body_parts.append(row.reason)
    if isinstance(row.new_value, dict):
        mod_comment = row.new_value.get("moderation_comment")
        if mod_comment and (not body_parts or mod_comment not in body_parts):
            body_parts.append(str(mod_comment))
        if row.action == "calculation_updated":
            method = row.new_value.get("calculation_method", "auto")
            pts = row.new_value.get("manual_points")
            body_parts.append(
                f"calculation → {method}" + (f" ({pts} pts)" if pts is not None else "")
            )
        elif not body_parts:
            status = row.new_value.get("status")
            if status:
                body_parts.append(f"status → {status}")
            elif row.action == "points_updated":
                body_parts.append(f"final_points → {row.new_value.get('final_points')}")
    if not body_parts:
        body_parts.append(row.action)
    return "\n".join(body_parts)


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
            AuditLog.action.in_(_COMMENT_ACTIONS),
        )
        .order_by(AuditLog.seq.asc())
    )
    entries: list[CommentEntry] = []
    for row in result.scalars().all():
        author = row.performed_by
        entries.append(
            CommentEntry(
                id=row.id,
                action=row.action,
                authorName=author.name if author else "unknown",
                authorRole=row.performed_by_role,
                body=_build_body(row),
                oldValue=row.old_value,
                newValue=row.new_value,
                displayData=row.display_data,
                createdAt=row.performed_at,
            )
        )
    return entries


async def add_report_comment(
    session: AsyncSession,
    *,
    user: User,
    report_id: str,
    body: str,
) -> CommentEntry:
    """Write a regular comment into audit_logs (action='comment')."""
    audit = AuditService(session)
    entry = await audit.log(
        entity_type="report",
        entity_id=report_id,
        action="comment",
        performed_by_id=user.id,
        performed_by_role=user.role.value,
        old_value=None,
        new_value={"body": body},
        display_data={
            "title": "Comment",
            "summary": body,
        },
    )
    await session.commit()
    return CommentEntry(
        id=entry.id,
        action=entry.action,
        authorName=user.name,
        authorRole=user.role.value,
        body=body,
        oldValue=None,
        newValue={"body": body},
        displayData=entry.display_data,
        createdAt=entry.performed_at,
    )
