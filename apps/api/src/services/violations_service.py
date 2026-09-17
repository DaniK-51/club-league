"""Access violation logging (AGENTS security rule 4)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import AccessViolation


async def log_access_violation(
    session: AsyncSession,
    *,
    user_id: str | None,
    path: str,
    method: str,
    detail: str,
) -> None:
    session.add(
        AccessViolation(
            user_id=user_id,
            path=path[:512],
            method=method[:16],
            detail=detail,
            occurred_at=datetime.now(UTC),
        )
    )
    await session.commit()
