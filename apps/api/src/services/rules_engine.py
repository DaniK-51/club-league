"""RulesEngine — points from report_data + JSONB config (rules-catalog.md v2).

Per-report calculation. Monthly caps (C4/C7/C9/C11, G1) applied at rating aggregation.
"""

from __future__ import annotations

from typing import Any

from src.schemas.rules import (
    BinaryConfig,
    BinaryWithMonthlyCapConfig,
    BonusCondition,
    CalculationResult,
    DiscretionaryConfig,
    FixedMonthlyWithPerUnitConfig,
    FixedPerEventWithMonthlyCapConfig,
    PerPersonPerMonthConfig,
    PerUnitWithBonusConfig,
    ReportDataError,
    RuleValidationError,
    ScaleConfig,
    ScaleSplitModeConfig,
    ScaleWithBonusMapConfig,
    ScaleWithConditionalBonusConfig,
    ScaleWithConditionalModifierConfig,
    ScaleWithFrequencyLimitConfig,
    TieredConfig,
    TieredWithBonusConfig,
    parse_rule_config,
)


def _require_int(data: dict[str, Any], field: str, *, default: int | None = None) -> int:
    if field not in data:
        if default is not None:
            return default
        raise ReportDataError(f"missing report field {field!r}")
    value = data[field]
    if isinstance(value, bool) or not isinstance(value, int):
        if isinstance(value, float) and value.is_integer():
            return int(value)
        raise ReportDataError(f"report field {field!r} must be an integer")
    return value


def _optional_int(data: dict[str, Any], field: str) -> int | None:
    if field not in data or data[field] is None:
        return None
    return _require_int(data, field)


def _require_str(data: dict[str, Any], field: str) -> str:
    if field not in data:
        raise ReportDataError(f"missing report field {field!r}")
    value = data[field]
    if not isinstance(value, str) or not value.strip():
        raise ReportDataError(f"report field {field!r} must be a non-empty string")
    return value.strip()


def _optional_bool(data: dict[str, Any], field: str, default: bool = False) -> bool:
    if field not in data or data[field] is None:
        return default
    value = data[field]
    if not isinstance(value, bool):
        raise ReportDataError(f"report field {field!r} must be a boolean")
    return value


def _condition_met(cond: BonusCondition, data: dict[str, Any]) -> bool:
    raw = data.get(cond.field)
    if raw is None:
        return False
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ReportDataError(f"condition field {cond.field!r} must be numeric")
    left = float(raw)
    right = float(cond.value)
    ops = {
        ">": left > right,
        ">=": left >= right,
        "<": left < right,
        "<=": left <= right,
        "==": left == right,
        "!=": left != right,
    }
    return ops[cond.operator]


def _scale_points(levels: dict[str, int], level_field: str, data: dict[str, Any]) -> tuple[str, int]:
    level = _require_str(data, level_field)
    if level not in levels:
        raise RuleValidationError(f"unknown level {level!r}; allowed: {sorted(levels)}")
    return level, levels[level]


def calculate_tiered(config: TieredConfig, data: dict[str, Any]) -> CalculationResult:
    count = _require_int(data, config.count_field)
    if count < 0:
        raise ReportDataError(f"{config.count_field} must be >= 0")
    for tier in config.tiers:
        if tier.matches(count):
            return CalculationResult(
                points=tier.pts,
                rule_type="tiered",
                breakdown={"count": count, "pts": tier.pts},
            )
    raise RuleValidationError(f"no tier matches count={count}")


def calculate_tiered_with_bonus(
    config: TieredWithBonusConfig, data: dict[str, Any]
) -> CalculationResult:
    count = _require_int(data, config.count_field)
    for tier in config.tiers:
        if tier.matches(count):
            pts = tier.pts
            bonus = 0
            if tier.bonus_pts and config.bonus_condition and _condition_met(
                config.bonus_condition, data
            ):
                bonus = tier.bonus_pts
            return CalculationResult(
                points=pts + bonus,
                rule_type="tiered_with_bonus",
                breakdown={"count": count, "pts": pts, "bonus": bonus},
            )
    raise RuleValidationError(f"no tier matches count={count}")


def calculate_scale(config: ScaleConfig, data: dict[str, Any]) -> CalculationResult:
    level, pts = _scale_points(config.levels, config.level_field, data)
    return CalculationResult(
        points=pts, rule_type="scale", breakdown={"level": level, "pts": pts}
    )


def calculate_scale_with_frequency_limit(
    config: ScaleWithFrequencyLimitConfig, data: dict[str, Any]
) -> CalculationResult:
    level, pts = _scale_points(config.levels, config.level_field, data)
    return CalculationResult(
        points=pts,
        rule_type="scale_with_frequency_limit",
        breakdown={"level": level, "pts": pts, "max_per_month": config.max_per_month},
    )


def calculate_scale_with_conditional_bonus(
    config: ScaleWithConditionalBonusConfig, data: dict[str, Any]
) -> CalculationResult:
    level, pts = _scale_points(config.levels, config.level_field, data)
    bonus = 0
    if _optional_bool(data, config.focus_field, False):
        bonus = config.full_club_focus_bonus.get(level, 0)
    return CalculationResult(
        points=pts + bonus,
        rule_type="scale_with_conditional_bonus",
        breakdown={"level": level, "pts": pts, "bonus": bonus},
    )


def calculate_scale_with_league_bonus(
    config: ScaleWithBonusMapConfig, data: dict[str, Any]
) -> CalculationResult:
    level, pts = _scale_points(config.levels, config.level_field, data)
    bonus = 0
    if _optional_bool(data, config.bonus_field, False):
        bonus = config.bonus.get(level, 0)
    return CalculationResult(
        points=pts + bonus,
        rule_type="scale_with_league_bonus",
        breakdown={"level": level, "pts": pts, "bonus": bonus},
    )


def calculate_scale_split_mode(
    config: ScaleSplitModeConfig, data: dict[str, Any]
) -> CalculationResult:
    mode = _require_str(data, config.mode_field)
    if mode not in {"individual", "team"}:
        raise RuleValidationError("mode must be 'individual' or 'team'")
    levels = config.individual if mode == "individual" else config.team
    level, pts = _scale_points(levels, config.level_field, data)
    return CalculationResult(
        points=pts,
        rule_type="scale_split_mode",
        breakdown={"mode": mode, "level": level, "pts": pts},
    )


def calculate_scale_with_conditional_modifier(
    config: ScaleWithConditionalModifierConfig, data: dict[str, Any]
) -> CalculationResult:
    mode = _require_str(data, config.mode_field)
    if mode not in {"individual", "team"}:
        raise RuleValidationError("mode must be 'individual' or 'team'")
    levels = config.individual if mode == "individual" else config.team
    level, pts = _scale_points(levels, config.level_field, data)
    factor = 1.0
    if (
        config.host_win_modifier
        and _optional_bool(data, config.is_host_field, False)
        and _condition_met(config.host_win_modifier, data)
    ):
        factor = config.host_win_factor
    total = int(pts * factor)
    return CalculationResult(
        points=total,
        rule_type="scale_with_conditional_modifier",
        breakdown={"mode": mode, "level": level, "pts": pts, "factor": factor},
    )


def calculate_binary(config: BinaryConfig, data: dict[str, Any]) -> CalculationResult:
    variant = _require_str(data, config.variant_field)
    if variant not in config.options:
        raise RuleValidationError(
            f"unknown variant {variant!r}; allowed: {sorted(config.options)}"
        )
    pts = config.options[variant]
    return CalculationResult(
        points=pts,
        rule_type="binary",
        breakdown={"variant": variant, "pts": pts},
    )


def calculate_binary_with_monthly_cap(
    config: BinaryWithMonthlyCapConfig, data: dict[str, Any]
) -> CalculationResult:
    variant = _require_str(data, config.variant_field)
    if variant not in config.options:
        raise RuleValidationError(
            f"unknown variant {variant!r}; allowed: {sorted(config.options)}"
        )
    pts = config.options[variant]
    return CalculationResult(
        points=pts,
        rule_type="binary_with_monthly_cap",
        breakdown={"variant": variant, "pts": pts, "monthly_cap": config.monthly_cap},
    )


def calculate_per_unit_with_bonus(
    config: PerUnitWithBonusConfig, data: dict[str, Any]
) -> CalculationResult:
    partners = _require_int(data, config.partners_field)
    if partners < 1:
        raise ReportDataError("partners must be >= 1")
    cross = _optional_bool(data, config.cross_type_field, False)
    pts = config.base_per_partner * partners + (config.cross_type_bonus if cross else 0)
    return CalculationResult(
        points=pts,
        rule_type="per_unit_with_bonus",
        breakdown={"partners": partners, "cross_type": cross, "pts": pts},
    )


def calculate_fixed_monthly_with_per_unit(
    config: FixedMonthlyWithPerUnitConfig, data: dict[str, Any]
) -> CalculationResult:
    extra = _require_int(data, config.extra_field, default=0)
    if extra < 0:
        raise ReportDataError("extra_socials must be >= 0")
    pts = config.base_monthly + config.per_extra_social * extra
    if config.monthly_cap is not None:
        pts = min(pts, config.monthly_cap)
    return CalculationResult(
        points=pts,
        rule_type="fixed_monthly_with_per_unit",
        breakdown={"extra": extra, "pts": pts},
    )


def calculate_discretionary(
    config: DiscretionaryConfig, data: dict[str, Any]
) -> CalculationResult:
    requested = _optional_int(data, config.points_field)
    pts = config.min if requested is None else max(config.min, min(config.max, requested))
    return CalculationResult(
        points=pts,
        rule_type="discretionary",
        breakdown={"requested": requested, "pts": pts, "min": config.min, "max": config.max},
    )


def calculate_fixed_per_event_with_monthly_cap(
    config: FixedPerEventWithMonthlyCapConfig, data: dict[str, Any]
) -> CalculationResult:
    return CalculationResult(
        points=config.per_event,
        rule_type="fixed_per_event_with_monthly_cap",
        breakdown={"per_event": config.per_event, "monthly_cap": config.monthly_cap},
    )


def calculate_per_person_per_month(
    config: PerPersonPerMonthConfig, data: dict[str, Any]
) -> CalculationResult:
    # I4: per_leader_per_month / leaders; S4: per_trainer_per_month / trainers
    if config.per_leader_per_month is not None:
        rate = config.per_leader_per_month
        cap = config.max_leaders or 1
        field = config.leaders_field
        key = "leaders"
    else:
        rate = config.per_trainer_per_month or 0
        cap = config.max_trainers or 1
        field = config.trainers_field
        key = "trainers"
    people = _require_int(data, field)
    if people < 0:
        raise ReportDataError(f"{field} must be >= 0")
    counted = min(people, cap)
    pts = rate * counted
    return CalculationResult(
        points=pts,
        rule_type="per_person_per_month",
        breakdown={key: counted, "pts": pts, "rate": rate},
    )


_HANDLERS: dict[str, Any] = {
    "tiered": calculate_tiered,
    "tiered_with_bonus": calculate_tiered_with_bonus,
    "scale": calculate_scale,
    "scale_with_frequency_limit": calculate_scale_with_frequency_limit,
    "scale_with_conditional_bonus": calculate_scale_with_conditional_bonus,
    "scale_with_league_bonus": calculate_scale_with_league_bonus,
    "scale_split_mode": calculate_scale_split_mode,
    "scale_with_conditional_modifier": calculate_scale_with_conditional_modifier,
    "binary": calculate_binary,
    "binary_scale": calculate_binary,
    "binary_with_monthly_cap": calculate_binary_with_monthly_cap,
    "per_unit_with_bonus": calculate_per_unit_with_bonus,
    "fixed_monthly_with_per_unit": calculate_fixed_monthly_with_per_unit,
    "discretionary": calculate_discretionary,
    "fixed_per_event_with_monthly_cap": calculate_fixed_per_event_with_monthly_cap,
    "per_person_per_month": calculate_per_person_per_month,
}


class RulesEngine:
    """Stateless calculator: config JSONB + report_data → points."""

    def calculate(
        self,
        *,
        rule_type: str,
        config: dict[str, Any],
        report_data: dict[str, Any],
    ) -> CalculationResult:
        parsed = parse_rule_config(rule_type, config)
        handler = _HANDLERS.get(rule_type)
        if handler is None:
            raise RuleValidationError(f"rule_type {rule_type!r} is not calculable per-report")
        result: CalculationResult = handler(parsed, report_data)
        if result.rule_type != rule_type:
            # binary_scale reuses binary handler — normalize label
            result = CalculationResult(
                points=result.points,
                rule_type=rule_type,  # type: ignore[arg-type]
                breakdown=result.breakdown,
            )
        return result

    def validate_config(self, rule_type: str, config: dict[str, Any]) -> None:
        parse_rule_config(rule_type, config)
