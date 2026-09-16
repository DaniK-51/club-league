"""Pydantic schemas for JSONB rule configs (docs/shared/rules-catalog.md v2)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

RuleType = Literal[
    "tiered",
    "scale",
    "binary",
    "binary_scale",
    "tiered_with_bonus",
    "per_unit_with_bonus",
    "binary_with_monthly_cap",
    "fixed_monthly_with_per_unit",
    "scale_with_frequency_limit",
    "scale_with_conditional_bonus",
    "discretionary",
    "fixed_per_event_with_monthly_cap",
    "scale_with_league_bonus",
    "scale_with_conditional_modifier",
    "per_person_per_month",
    "scale_split_mode",
    "combined_cap",
]


class TierRange(BaseModel):
    """One tier. Either `count` (exact) or `min`/`max` range (`max=None` = open)."""

    model_config = {"extra": "forbid"}

    count: int | None = Field(default=None, ge=0)
    min: int | None = Field(default=None, ge=0)
    max: int | None = Field(default=None, ge=0)
    pts: int = Field(ge=0)
    bonus_pts: int | None = Field(default=None, ge=0)

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


class BonusCondition(BaseModel):
    model_config = {"extra": "forbid"}

    field: str
    operator: Literal[">", ">=", "<", "<=", "==", "!="]
    value: float | int


class TieredConfig(BaseModel):
    model_config = {"extra": "forbid"}

    tiers: list[TierRange] = Field(min_length=1)
    count_field: str = "count"

    @field_validator("tiers")
    @classmethod
    def _non_empty_tiers(cls, value: list[TierRange]) -> list[TierRange]:
        if not value:
            raise ValueError("tiers must not be empty")
        return value


class TieredWithBonusConfig(TieredConfig):
    bonus_condition: BonusCondition | None = None
    bonus_field: str = "count"


class ScaleConfig(BaseModel):
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


class ScaleWithBonusMapConfig(ScaleConfig):
    bonus: dict[str, int] = Field(default_factory=dict)
    bonus_field: str = "bonus"


class ScaleWithFrequencyLimitConfig(ScaleConfig):
    max_per_month: int = Field(ge=1)


class ScaleWithConditionalBonusConfig(BaseModel):
    model_config = {"extra": "forbid"}

    levels: dict[str, int] = Field(min_length=1)
    full_club_focus_bonus: dict[str, int] = Field(min_length=1)
    max_full_focus_per_month: int = Field(ge=1)
    level_field: str = "level"
    focus_field: str = "full_club_focus"


class ScaleSplitModeConfig(BaseModel):
    model_config = {"extra": "forbid"}

    individual: dict[str, int] = Field(min_length=1)
    team: dict[str, int] = Field(min_length=1)
    mode_field: str = "mode"
    level_field: str = "level"


class ScaleWithConditionalModifierConfig(BaseModel):
    model_config = {"extra": "forbid"}

    individual: dict[str, int] = Field(min_length=1)
    team: dict[str, int] = Field(min_length=1)
    host_win_modifier: BonusCondition | None = None
    host_win_factor: float = Field(default=0.5, gt=0, le=1)
    mode_field: str = "mode"
    level_field: str = "level"
    is_host_field: str = "is_host"


class BinaryConfig(BaseModel):
    """C3 / T3. Stored JSONB may be flat (`{"passive": 100, "active": 350}`)."""

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


class BinaryWithMonthlyCapConfig(BinaryConfig):
    monthly_cap: int = Field(ge=0)


class PerUnitWithBonusConfig(BaseModel):
    model_config = {"extra": "forbid"}

    base_per_partner: int = Field(ge=0)
    cross_type_bonus: int = Field(default=0, ge=0)
    partners_field: str = "partners"
    cross_type_field: str = "cross_type"


class FixedMonthlyWithPerUnitConfig(BaseModel):
    model_config = {"extra": "forbid"}

    base_monthly: int = Field(ge=0)
    per_extra_social: int = Field(ge=0)
    extra_field: str = "extra_socials"
    monthly_cap: int | None = Field(default=None, ge=0)


class DiscretionaryConfig(BaseModel):
    model_config = {"extra": "forbid"}

    min: int = Field(ge=0)
    max: int = Field(ge=0)
    points_field: str = "points"

    @model_validator(mode="after")
    def _check_range(self) -> DiscretionaryConfig:
        if self.max < self.min:
            raise ValueError("max must be >= min")
        return self


class FixedPerEventWithMonthlyCapConfig(BaseModel):
    model_config = {"extra": "forbid"}

    per_event: int = Field(ge=0)
    monthly_cap: int = Field(ge=0)


class PerPersonPerMonthConfig(BaseModel):
    model_config = {"extra": "forbid"}

    per_trainer_per_month: int | None = Field(default=None, ge=0)
    max_trainers: int | None = Field(default=None, ge=1)
    trainers_field: str = "trainers"
    # I4: per_leader_per_month / max_leaders — same math
    per_leader_per_month: int | None = Field(default=None, ge=0)
    max_leaders: int | None = Field(default=None, ge=1)
    leaders_field: str = "leaders"

    @model_validator(mode="after")
    def _require_one_mode(self) -> PerPersonPerMonthConfig:
        has_trainers = self.per_trainer_per_month is not None and self.max_trainers is not None
        has_leaders = self.per_leader_per_month is not None and self.max_leaders is not None
        if not has_trainers and not has_leaders:
            raise ValueError("need per_trainer_per_month+max_trainers or per_leader_per_month+max_leaders")
        return self


class CombinedCapConfig(BaseModel):
    """G1: listed criteria sum ≤ max_percent of monthly total."""

    model_config = {"extra": "forbid"}

    criteria_codes: list[str] = Field(min_length=1)
    max_percent_of_total_monthly: float = Field(gt=0, le=100)

    @field_validator("criteria_codes")
    @classmethod
    def _unique_codes(cls, value: list[str]) -> list[str]:
        cleaned = [code.strip() for code in value if code.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("criteria_codes must be unique")
        if not cleaned:
            raise ValueError("criteria_codes must not be empty")
        return cleaned


class CalculationResult(BaseModel):
    points: int = Field(ge=0)
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


def parse_rule_config(rule_type: str, config: dict[str, Any]) -> BaseModel:
    """Validate JSONB config for a known rule_type."""
    mapping: dict[str, type[BaseModel]] = {
        "tiered": TieredConfig,
        "scale": ScaleConfig,
        "binary": BinaryConfig,
        "binary_scale": BinaryConfig,
        "binary_with_monthly_cap": BinaryWithMonthlyCapConfig,
        "tiered_with_bonus": TieredWithBonusConfig,
        "per_unit_with_bonus": PerUnitWithBonusConfig,
        "fixed_monthly_with_per_unit": FixedMonthlyWithPerUnitConfig,
        "scale_with_frequency_limit": ScaleWithFrequencyLimitConfig,
        "scale_with_conditional_bonus": ScaleWithConditionalBonusConfig,
        "discretionary": DiscretionaryConfig,
        "fixed_per_event_with_monthly_cap": FixedPerEventWithMonthlyCapConfig,
        "scale_with_league_bonus": ScaleWithBonusMapConfig,
        "scale_with_conditional_modifier": ScaleWithConditionalModifierConfig,
        "per_person_per_month": PerPersonPerMonthConfig,
        "scale_split_mode": ScaleSplitModeConfig,
        "combined_cap": CombinedCapConfig,
    }
    cls = mapping.get(rule_type)
    if cls is None:
        raise UnknownRuleTypeError(rule_type)
    if rule_type in {"binary", "binary_scale", "binary_with_monthly_cap"} and (
        "options" not in config
    ):
        if rule_type == "binary_with_monthly_cap":
            options = {k: v for k, v in config.items() if isinstance(v, int) and k != "monthly_cap"}
            rest = {k: v for k, v in config.items() if k == "monthly_cap"}
            return cls.model_validate({"options": options, **rest})
        return cls.from_flat_dict(config)
    return cls.model_validate(config)
