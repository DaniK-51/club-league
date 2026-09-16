from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import User
from src.models.enums import UserRole
from src.services.sso_client import SSOProfile


class EmailConflictError(Exception):
    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(email)


async def upsert_user_from_sso(session: AsyncSession, profile: SSOProfile) -> User:
    """Upsert by sso_id. SSO owns email/name only — never role/can_sudo."""
    existing_by_sso = await session.execute(
        select(User).where(User.sso_id == profile.sso_id)
    )
    user = existing_by_sso.scalar_one_or_none()

    if user is None:
        email_owner = await session.execute(select(User).where(User.email == profile.email))
        other = email_owner.scalar_one_or_none()
        if other is not None and other.sso_id != profile.sso_id:
            raise EmailConflictError(profile.email)
        user = User(
            sso_id=profile.sso_id,
            email=profile.email,
            name=profile.name,
            role=UserRole.GUEST,
            can_sudo=False,
            created_at=datetime.now(UTC),
        )
        session.add(user)
    else:
        if user.email != profile.email:
            email_owner = await session.execute(
                select(User).where(User.email == profile.email)
            )
            other = email_owner.scalar_one_or_none()
            if other is not None and other.id != user.id:
                raise EmailConflictError(profile.email)
        user.email = profile.email
        user.name = profile.name

    await session.flush()
    return user
