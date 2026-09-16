from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.models.enums import ReportStatus


class ModerateReportDTO(BaseModel):
    status: Literal[
        ReportStatus.APPROVED,
        ReportStatus.CHANGES_REQUIRED,
        ReportStatus.CLOSED,
    ]
    finalPoints: int | None = Field(default=None, ge=0)
    comment: str = ""


class DisputeReportDTO(BaseModel):
    comment: str = Field(min_length=1)
