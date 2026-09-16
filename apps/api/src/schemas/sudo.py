from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class SudoActionDTO(BaseModel):
    action: Literal["force_status", "restore_deleted", "override_points"]
    targetReportId: str = Field(min_length=1)
    newValue: Any
    reason: str = Field(min_length=1)


class SudoSuccess(BaseModel):
    """api-contract.ts: POST /admin/sudo → { success: true }."""

    success: Literal[True] = True
