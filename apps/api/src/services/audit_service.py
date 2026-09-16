"""Audit logging with SHA-256 hash chain.

Every state change MUST go through AuditService.log().
The chain starts from genesis prev_hash of 64 zeros.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import AuditLog

GENESIS_HASH = "0" * 64


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def compute_hash(
    *,
    prev_hash: str,
    entity_type: str,
    entity_id: str,
    action: str,
    old_value: dict[str, Any] | None,
    new_value: dict[str, Any] | None,
    performed_by_id: str,
    performed_by_role: str,
    performed_at: datetime,
    reason: str | None,
) -> str:
    body = {
        "prev_hash": prev_hash,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": action,
        "old_value": old_value,
        "new_value": new_value,
        "performed_by_id": performed_by_id,
        "performed_by_role": performed_by_role,
        "performed_at": performed_at.isoformat(),
        "reason": reason,
    }
    return hashlib.sha256(_canonical_json(body).encode("utf-8")).hexdigest()


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _last_hash(self) -> str:
        result = await self._session.execute(
            select(AuditLog.hash).order_by(AuditLog.performed_at.desc(), AuditLog.id.desc()).limit(1)
        )
        last = result.scalar_one_or_none()
        return last if last is not None else GENESIS_HASH

    async def log(
        self,
        *,
        entity_type: str,
        entity_id: str,
        action: str,
        performed_by_id: str,
        performed_by_role: str,
        old_value: dict[str, Any] | None = None,
        new_value: dict[str, Any] | None = None,
        reason: str | None = None,
        performed_at: datetime | None = None,
    ) -> AuditLog:
        prev_hash = await self._last_hash()
        performed_at = performed_at or datetime.now(UTC)
        entry_hash = compute_hash(
            prev_hash=prev_hash,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            old_value=old_value,
            new_value=new_value,
            performed_by_id=performed_by_id,
            performed_by_role=performed_by_role,
            performed_at=performed_at,
            reason=reason,
        )
        entry = AuditLog(
            prev_hash=prev_hash,
            hash=entry_hash,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            old_value=old_value,
            new_value=new_value,
            performed_by_id=performed_by_id,
            performed_by_role=performed_by_role,
            performed_at=performed_at,
            reason=reason,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def verify_chain(self) -> bool:
        result = await self._session.execute(
            select(AuditLog).order_by(AuditLog.performed_at.asc(), AuditLog.id.asc())
        )
        prev = GENESIS_HASH
        for row in result.scalars().all():
            if row.prev_hash != prev:
                return False
            expected = compute_hash(
                prev_hash=row.prev_hash,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                action=row.action,
                old_value=row.old_value,
                new_value=row.new_value,
                performed_by_id=row.performed_by_id,
                performed_by_role=row.performed_by_role,
                performed_at=row.performed_at,
                reason=row.reason,
            )
            if expected != row.hash:
                return False
            prev = row.hash
        return True
