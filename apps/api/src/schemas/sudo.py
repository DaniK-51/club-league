from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.models.enums import ReportStatus


class SudoActionDTO(BaseModel):
    action: Literal["force_status", "restore_deleted", "override_points"]
    targetReportId: str = Field(min_length=1)
    newValue: Any
    reason: str = Field(min_length=1)


class SudoResult(BaseModel):
    reportId: str
    action: str
    status: ReportStatus
    finalPoints: int | None
    isDeleted: bool
