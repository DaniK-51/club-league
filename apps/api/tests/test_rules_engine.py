"""Unit tests for RulesEngine (tiered, scale, binary) + JSONB validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from src.schemas.rules import (
    BinaryConfig,
    ReportDataError,
    RuleValidationError,
    TieredConfig,
    UnknownRuleTypeError,
    parse_rule_config,
)
from src.services.rules_engine import RulesEngine

C8_TIERED = {
    "tiers": [
        {"count": 1, "pts": 250},
        {"min": 2, "max": 5, "pts": 500},
        {"min": 6, "max": 10, "pts": 800},
        {"min": 11, "max": None, "pts": 1000},
    ]
}

C6_SCALE = {
    "levels": {
        "local": 100,
        "regional": 200,
        "national": 400,
        "world": 500,
    }
}

C3_BINARY = {"passive": 100, "active": 350}


@pytest.fixture
def engine() -> RulesEngine:
    return RulesEngine()


# --- tiered ---


@pytest.mark.parametrize(
    ("count", "expected"),
    [(0, 0), (1, 250), (2, 500), (5, 500), (6, 800), (10, 800), (11, 1000), (100, 1000)],
)
def test_tiered_boundaries(engine: RulesEngine, count: int, expected: int) -> None:
    # C8 has no 0-tier — 0 falls through. Use a config with open low tier for 0.
    config = C8_TIERED
    if count == 0:
        config = {
            "tiers": [
                {"min": 0, "max": 1, "pts": 0},
                {"count": 1, "pts": 250},
                {"min": 2, "max": 5, "pts": 500},
                {"min": 6, "max": 10, "pts": 800},
                {"min": 11, "max": None, "pts": 1000},
            ]
        }
    result = engine.calculate(
        rule_type="tiered", config=config, report_data={"count": count}
    )
    assert result.points == expected
    assert result.rule_type == "tiered"
    assert result.breakdown["count"] == count


def test_tiered_no_matching_tier(engine: RulesEngine) -> None:
    with pytest.raises(RuleValidationError):
        engine.calculate(
            rule_type="tiered",
            config={"tiers": [{"min": 5, "max": 10, "pts": 100}]},
            report_data={"count": 2},
        )


def test_tiered_missing_count(engine: RulesEngine) -> None:
    with pytest.raises(ReportDataError):
        engine.calculate(rule_type="tiered", config=C8_TIERED, report_data={})


def test_tiered_custom_field_name(engine: RulesEngine) -> None:
    config = {**C8_TIERED, "count_field": "items"}
    result = engine.calculate(
        rule_type="tiered", config=config, report_data={"items": 3}
    )
    assert result.points == 500


# --- scale ---


def test_scale_known_level(engine: RulesEngine) -> None:
    result = engine.calculate(
        rule_type="scale", config=C6_SCALE, report_data={"level": "regional"}
    )
    assert result.points == 200
    assert result.breakdown["level"] == "regional"


def test_scale_unknown_level(engine: RulesEngine) -> None:
    with pytest.raises(RuleValidationError):
        engine.calculate(
            rule_type="scale", config=C6_SCALE, report_data={"level": "galaxy"}
        )


def test_scale_missing_level(engine: RulesEngine) -> None:
    with pytest.raises(ReportDataError):
        engine.calculate(rule_type="scale", config=C6_SCALE, report_data={})


# --- binary ---


def test_binary_variants(engine: RulesEngine) -> None:
    assert (
        engine.calculate(
            rule_type="binary", config=C3_BINARY, report_data={"variant": "active"}
        ).points
        == 350
    )
    assert (
        engine.calculate(
            rule_type="binary", config=C3_BINARY, report_data={"variant": "passive"}
        ).points
        == 100
    )


def test_binary_unknown_variant(engine: RulesEngine) -> None:
    with pytest.raises(RuleValidationError):
        engine.calculate(
            rule_type="binary", config=C3_BINARY, report_data={"variant": "hybrid"}
        )


def test_binary_from_flat_and_wrapped() -> None:
    flat = BinaryConfig.from_flat_dict({"a": 1, "b": 2})
    assert flat.options == {"a": 1, "b": 2}
    wrapped = BinaryConfig.from_flat_dict({"options": {"a": 1}, "variant_field": "kind"})
    assert wrapped.variant_field == "kind"
    assert wrapped.options == {"a": 1}


# --- config validation ---


def test_parse_unknown_rule_type() -> None:
    with pytest.raises(UnknownRuleTypeError):
        parse_rule_config("magic", {})


def test_tiered_config_rejects_both_count_and_minmax() -> None:
    with pytest.raises(ValidationError):
        TieredConfig.model_validate(
            {"tiers": [{"count": 1, "min": 1, "max": 2, "pts": 10}]}
        )


def test_tiered_config_requires_min_or_count() -> None:
    with pytest.raises(ValidationError):
        TieredConfig.model_validate({"tiers": [{"pts": 10}]})


def test_tiered_config_rejects_max_lt_min() -> None:
    with pytest.raises(ValidationError):
        TieredConfig.model_validate({"tiers": [{"min": 5, "max": 2, "pts": 10}]})


def test_scale_config_rejects_negative_points() -> None:
    with pytest.raises(ValidationError):
        parse_rule_config("scale", {"levels": {"local": -1}})


def test_binary_config_rejects_negative_points() -> None:
    with pytest.raises(ValidationError):
        parse_rule_config("binary", {"active": -5})


def test_engine_validate_config_ok(engine: RulesEngine) -> None:
    engine.validate_config("tiered", C8_TIERED)
    engine.validate_config("scale", C6_SCALE)
    engine.validate_config("binary", C3_BINARY)


# --- catalog examples smoke ---


def test_catalog_c8_and_c6_and_c3(engine: RulesEngine) -> None:
    assert (
        engine.calculate(
            rule_type="tiered", config=C8_TIERED, report_data={"count": 1}
        ).points
        == 250
    )
    assert (
        engine.calculate(
            rule_type="scale", config=C6_SCALE, report_data={"level": "world"}
        ).points
        == 500
    )
    assert (
        engine.calculate(
            rule_type="binary", config=C3_BINARY, report_data={"variant": "active"}
        ).points
        == 350
    )
