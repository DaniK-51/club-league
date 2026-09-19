from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class PeriodOut(BaseModel):
    id: str
    name: str
    startDate: str
    endDate: str
    isArchived: bool
    reportCount: int


class CreatePeriodDTO(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    startDate: str
    endDate: str

    @model_validator(mode="after")
    def _check_dates(self) -> CreatePeriodDTO:
        if self.endDate <= self.startDate:
            raise ValueError("endDate must be after startDate")
        return self


class UpdatePeriodDTO(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    startDate: str | None = None
    endDate: str | None = None

    @model_validator(mode="after")
    def _check_dates(self) -> UpdatePeriodDTO:
        if (
            self.startDate is not None
            and self.endDate is not None
            and self.endDate <= self.startDate
        ):
            raise ValueError("endDate must be after startDate")
        return self
