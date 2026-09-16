"""Pydantic schemas for JSONB rule configs (rules-catalog.md v2)."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

RuleType = Literal["tiered", "scale", "binary"]


class TierRange(BaseModel):
    """One tier. Either `count` (exact) or `min`/`max` range (`max=None` = open)."""

    model_config = {"extra": "forbid"}

    count: int | None = Field(default=None, ge=0)
    min: int | None = Field(default=None, ge=0)
    max: int | None = Field(default=None, ge=0)
    pts: int = Field(ge=0)

    @model_validator(mode="after")
    def _check_bounds(self) -> TierRange:
        if self.count is not None:
            if self.min is not None or self.max is not None:
                raise ValueError("use either count or min/max, not both")
            return self
        if self.min is None:
            raise ValueError("tier requires count or min")
        if self.max is not None and self.max < self.min:
            raise ValueError("max must be >= min")
        return self

    def matches(self, value: int) -> bool:
        if self.count is not None:
            return value == self.count
        assert self.min is not None
        if value < self.min:
            return False
        return self.max is None or value <= self.max


class TieredConfig(BaseModel):
    """C8 / A4 style: points by item count."""

    model_config = {"extra": "forbid"}

    tiers: list[TierRange] = Field(min_length=1)
    count_field: str = "count"

    @field_validator("tiers")
    @classmethod
    def _non_empty_tiers(cls, value: list[TierRange]) -> list[TierRange]:
        if not value:
            raise ValueError("tiers must not be empty")
        return value


class ScaleConfig(BaseModel):
    """C6 / S1 / T1 style: named level → points."""

    model_config = {"extra": "forbid"}

    levels: dict[str, int] = Field(min_length=1)
    level_field: str = "level"

    @field_validator("levels")
    @classmethod
    def _positive_levels(cls, value: dict[str, int]) -> dict[str, int]:
        for key, pts in value.items():
            if not key.strip():
                raise ValueError("level key must be non-empty")
            if pts < 0:
                raise ValueError(f"points for level {key!r} must be >= 0")
        return value


class BinaryConfig(BaseModel):
    """C3 / T3 style: variant name → points.

    Stored JSONB may be flat (`{"passive": 100, "active": 350}`); use
    `from_flat_dict` when loading from DB.
    """

    model_config = {"extra": "forbid"}

    options: dict[str, int] = Field(min_length=1)
    variant_field: str = "variant"

    @field_validator("options")
    @classmethod
    def _positive_options(cls, value: dict[str, int]) -> dict[str, int]:
        for key, pts in value.items():
            if not key.strip():
                raise ValueError("option key must be non-empty")
            if pts < 0:
                raise ValueError(f"points for option {key!r} must be >= 0")
        return value

    @classmethod
    def from_flat_dict(
        cls,
        raw: dict[str, Any],
        *,
        variant_field: str = "variant",
    ) -> BinaryConfig:
        if "options" in raw and isinstance(raw["options"], dict):
            return cls.model_validate(raw)
        return cls(options=dict(raw), variant_field=variant_field)


class CalculationResult(BaseModel):
    points: Annotated[int, Field(ge=0)]
    rule_type: RuleType
    breakdown: dict[str, Any] = Field(default_factory=dict)


class UnknownRuleTypeError(Exception):
    def __init__(self, rule_type: str) -> None:
        self.rule_type = rule_type
        super().__init__(f"unknown rule_type: {rule_type}")


class RuleValidationError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class ReportDataError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


def parse_rule_config(
    rule_type: str, config: dict[str, Any]
) -> TieredConfig | ScaleConfig | BinaryConfig | Any:
    """Validate JSONB config for a known rule_type."""
    if rule_type == "tiered":
        return TieredConfig.model_validate(config)
    if rule_type == "scale":
        return ScaleConfig.model_validate(config)
    if rule_type == "binary":
        return BinaryConfig.from_flat_dict(config)
    if rule_type == "combined_cap":
        from src.services.caps import CombinedCapConfig

        return CombinedCapConfig.model_validate(config)
    raise UnknownRuleTypeError(rule_type)
