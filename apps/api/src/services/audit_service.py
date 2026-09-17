"""Audit logging with SHA-256 hash chain.

Every state change MUST go through AuditService.log().
Chain order is `audit_logs.seq` (DB identity). Genesis prev_hash = 64 zeros.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import AuditLog, SudoAction, User
from src.models.enums import UserRole

GENESIS_HASH = "0" * 64


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


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


def user_public_snapshot(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "sso_id": user.sso_id,
        "email": user.email,
        "name": user.name,
        "role": user.role.value if isinstance(user.role, UserRole) else str(user.role),
        "can_sudo": user.can_sudo,
    }


class ChainBrokenError(Exception):
    def __init__(self, detail: str, *, seq: int | None = None) -> None:
        self.seq = seq
        super().__init__(detail)


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _last_hash(self) -> str:
        # Serialize concurrent appends so prev_hash never forks.
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext('club_league_audit_chain'))")
        )
        result = await self._session.execute(
            select(AuditLog.hash).order_by(AuditLog.seq.desc()).limit(1)
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

    async def log_user_created(self, user: User) -> AuditLog:
        return await self.log(
            entity_type="user",
            entity_id=user.id,
            action="created",
            performed_by_id=user.id,
            performed_by_role=user.role.value,
            old_value=None,
            new_value=user_public_snapshot(user),
        )

    async def log_user_profile_updated(
        self,
        user: User,
        *,
        old_snapshot: dict[str, Any],
    ) -> AuditLog:
        return await self.log(
            entity_type="user",
            entity_id=user.id,
            action="updated",
            performed_by_id=user.id,
            performed_by_role=user.role.value,
            old_value=old_snapshot,
            new_value=user_public_snapshot(user),
        )

    async def log_sudo_action(
        self,
        *,
        performed_by: User,
        action: str,
        entity_type: str,
        entity_id: str,
        old_value: dict[str, Any] | None,
        new_value: dict[str, Any] | None,
        reason: str,
    ) -> tuple[SudoAction, AuditLog]:
        if not reason or not reason.strip():
            raise ValueError("sudo action requires non-empty reason")
        if performed_by.role != UserRole.MODERATOR or not performed_by.can_sudo:
            raise PermissionError("sudo logging requires moderator with can_sudo")

        now = datetime.now(UTC)
        sudo_row = SudoAction(
            performed_by_id=performed_by.id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
            reason=reason.strip(),
            performed_at=now,
        )
        self._session.add(sudo_row)
        await self._session.flush()

        audit_row = await self.log(
            entity_type=entity_type,
            entity_id=entity_id,
            action="sudo_action",
            performed_by_id=performed_by.id,
            performed_by_role=performed_by.role.value,
            old_value=old_value,
            new_value={**(new_value or {}), "sudo_action": action},
            reason=reason.strip(),
            performed_at=now,
        )
        return sudo_row, audit_row

    async def verify_chain(self) -> None:
        """Raise ChainBrokenError if the hash chain is invalid."""
        result = await self._session.execute(select(AuditLog).order_by(AuditLog.seq.asc()))
        prev = GENESIS_HASH
        for row in result.scalars().all():
            if row.prev_hash != prev:
                raise ChainBrokenError(f"prev_hash mismatch at seq={row.seq}", seq=row.seq)
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
                raise ChainBrokenError(f"hash mismatch at seq={row.seq}", seq=row.seq)
            prev = row.hash

    async def is_chain_valid(self) -> bool:
        try:
            await self.verify_chain()
            return True
        except ChainBrokenError:
            return False
