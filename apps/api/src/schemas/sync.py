from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from src.services.sync_service import ClubTotal


class SyncStatus(BaseModel):
    pending: bool
    lastRunAt: datetime | None
    lastError: str | None
    runCount: int
    debounceSeconds: int


class RatingClub(BaseModel):
    id: str
    name: str
    totalPoints: int
    breakdown: dict[str, int] = Field(default_factory=dict)


class RatingResponse(BaseModel):
    semester: str
    clubs: list[RatingClub]


def club_total_to_rating(item: ClubTotal) -> RatingClub:
    return RatingClub(
        id=item.club_id,
        name=item.club_name,
        totalPoints=item.total_points,
        breakdown=dict(item.breakdown),
    )
