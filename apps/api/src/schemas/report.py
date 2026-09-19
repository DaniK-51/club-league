from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator, model_validator

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
    """Contract — api-contract.ts + frontend report-detail additions."""

    id: str
    clubName: str
    criteriaCode: str
    activityDate: str
    isOverdue: bool
    status: ReportStatus
    calculatedPoints: int | None
    finalPoints: int | None
    calculationMethod: str = "auto"
    manualPoints: int | None = None
    links: list[LinkOut]
    reportData: dict[str, Any] = Field(default_factory=dict)


class SetCalculationDTO(BaseModel):
    """PATCH /api/reports/:id/calculation — no status change."""

    method: Literal["auto", "manual"]
    manualPoints: int | None = Field(default=None, ge=0)
    reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _validate_manual(self) -> SetCalculationDTO:
        if self.method == "manual" and self.manualPoints is None:
            raise ValueError("manualPoints required when method=manual")
        return self


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
