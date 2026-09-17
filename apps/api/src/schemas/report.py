from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator

from src.core.config import BUSINESS_TZ, get_settings
from src.models.enums import ReportStatus


class LinkOut(BaseModel):
    url: str
    domain: str


class CreateReportDTO(BaseModel):
    """Matches docs/shared/api-contract.ts CreateReportDTO."""

    criteriaId: str = Field(min_length=1)
    activityDate: str = Field(min_length=1)  # ISO 8601
    reportData: dict[str, Any] = Field(default_factory=dict)
    links: list[str] = Field(min_length=1)

    @field_validator("activityDate")
    @classmethod
    def _parse_date(cls, value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("activityDate must be ISO 8601") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=ZoneInfo("Europe/Moscow"))
        return parsed.isoformat()


class UpdateReportDTO(BaseModel):
    activityDate: str | None = None
    reportData: dict[str, Any] | None = None
    links: list[str] | None = None

    @field_validator("activityDate")
    @classmethod
    def _parse_date(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("activityDate must be ISO 8601") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=ZoneInfo("Europe/Moscow"))
        return parsed.isoformat()


class ReportResponse(BaseModel):
    """Strict contract — no extra fields (api-contract.ts)."""

    id: str
    clubName: str
    criteriaCode: str
    activityDate: str
    isOverdue: bool
    status: ReportStatus
    calculatedPoints: int | None
    finalPoints: int | None
    links: list[LinkOut]
    reportData: dict[str, Any] = Field(default_factory=dict)


def parse_activity_date(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=BUSINESS_TZ)
    return parsed


def is_overdue(activity_date: datetime, *, now: datetime | None = None) -> bool:
    """Soft warning only — leaders can still submit overdue reports."""
    settings = get_settings()
    current = now or datetime.now(UTC)
    if activity_date.tzinfo is None:
        activity_date = activity_date.replace(tzinfo=BUSINESS_TZ)
    deadline = activity_date.timestamp() + settings.deadline_soft_warning_days * 86400
    return current.timestamp() > deadline
