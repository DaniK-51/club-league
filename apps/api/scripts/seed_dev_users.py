"""Seed local dev data: moderator, club, leader. Does not touch SSO.

Usage:
    uv run python -m scripts.seed_dev_users
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select
from src.core.database import dispose_engine, get_session_factory
from src.models.entities import Club, ClubLeader, User
from src.models.enums import ClubCategory, UserRole


async def seed() -> None:
    factory = get_session_factory()
    async with factory() as session:
        now = datetime.now(UTC)

        moderator = await session.scalar(
            select(User).where(User.email == "moderator@innopolis.university")
        )
        if moderator is None:
            moderator = User(
                sso_id="sso-mod-1",
                email="moderator@innopolis.university",
                name="Тимофей Модератор",
                role=UserRole.MODERATOR,
                can_sudo=True,
                created_at=now,
            )
            session.add(moderator)
        else:
            moderator.role = UserRole.MODERATOR
            moderator.can_sudo = True

        leader = await session.scalar(
            select(User).where(User.email == "leader@innopolis.university")
        )
        if leader is None:
            leader = User(
                sso_id="sso-leader-1",
                email="leader@innopolis.university",
                name="Лидер Клуба",
                role=UserRole.CLUB_LEADER,
                can_sudo=False,
                created_at=now,
            )
            session.add(leader)
            await session.flush()
        else:
            leader.role = UserRole.CLUB_LEADER
            await session.flush()

        club = await session.scalar(select(Club).where(Club.name == "Dev Sport Club"))
        if club is None:
            club = Club(name="Dev Sport Club", category=ClubCategory.SPORT)
            session.add(club)
            await session.flush()

        link = await session.scalar(
            select(ClubLeader).where(
                ClubLeader.club_id == club.id,
                ClubLeader.user_id == leader.id,
            )
        )
        if link is None:
            session.add(ClubLeader(club_id=club.id, user_id=leader.id, is_primary=True))

        await session.commit()
        print(f"Seeded moderator={moderator.email} leader={leader.email} club={club.name}")


async def main() -> None:
    try:
        await seed()
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
