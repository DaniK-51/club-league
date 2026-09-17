from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.services.sync_service import ClubTotal


class SyncStatus(BaseModel):
    """Internal status for GET /admin/sync/status (not in api-contract.ts)."""

    pending: bool
    lastRunAt: datetime | None
    lastError: str | None
    runCount: int
    debounceSeconds: int


class SyncQueued(BaseModel):
    """api-contract.ts: POST /admin/sync/force → { status: 'queued' }."""

    status: Literal["queued"] = "queued"


class SyncForceRequest(BaseModel):
    """api-contract.ts: body { semester?: string }."""

    semester: str | None = None


class RatingClub(BaseModel):
    id: str
    name: str
    totalPoints: int
    breakdown: dict[str, int] = Field(default_factory=dict)


class RatingResponse(BaseModel):
    """api-contract.ts: { clubs: [...] }."""

    clubs: list[RatingClub]


def club_total_to_rating(item: ClubTotal) -> RatingClub:
    return RatingClub(
        id=item.club_id,
        name=item.club_name,
        totalPoints=item.total_points,
        breakdown=dict(item.breakdown),
    )
