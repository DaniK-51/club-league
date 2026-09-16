"""RulesEngine — points calculation from report_data + JSONB rule config.

Only v2 criteria (rules-catalog.md). Three base types in this step:
  - tiered  (C8, A4)
  - scale   (C6, S1, T1, …)
  - binary  (C3, T3)

Caps / combined caps / bonuses are applied in later steps.
"""

from __future__ import annotations

from typing import Any

from src.schemas.rules import (
    BinaryConfig,
    CalculationResult,
    ReportDataError,
    RuleValidationError,
    ScaleConfig,
    TieredConfig,
    parse_rule_config,
)


def _require_int(data: dict[str, Any], field: str) -> int:
    if field not in data:
        raise ReportDataError(f"missing report field {field!r}")
    value = data[field]
    if isinstance(value, bool) or not isinstance(value, int):
        if isinstance(value, float) and value.is_integer():
            return int(value)
        raise ReportDataError(f"report field {field!r} must be an integer, got {type(value).__name__}")
    return value


def _require_str(data: dict[str, Any], field: str) -> str:
    if field not in data:
        raise ReportDataError(f"missing report field {field!r}")
    value = data[field]
    if not isinstance(value, str) or not value.strip():
        raise ReportDataError(f"report field {field!r} must be a non-empty string")
    return value.strip()


def calculate_tiered(config: TieredConfig, report_data: dict[str, Any]) -> CalculationResult:
    count = _require_int(report_data, config.count_field)
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


def calculate_scale(config: ScaleConfig, report_data: dict[str, Any]) -> CalculationResult:
    level = _require_str(report_data, config.level_field)
    if level not in config.levels:
        raise RuleValidationError(
            f"unknown level {level!r}; allowed: {sorted(config.levels)}"
        )
    pts = config.levels[level]
    return CalculationResult(
        points=pts,
        rule_type="scale",
        breakdown={"level": level, "pts": pts},
    )


def calculate_binary(config: BinaryConfig, report_data: dict[str, Any]) -> CalculationResult:
    variant = _require_str(report_data, config.variant_field)
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


_HANDLERS = {
    "tiered": calculate_tiered,
    "scale": calculate_scale,
    "binary": calculate_binary,
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
        handler = _HANDLERS[rule_type]
        return handler(parsed, report_data)  # type: ignore[arg-type]

    def validate_config(self, rule_type: str, config: dict[str, Any]) -> None:
        parse_rule_config(rule_type, config)
