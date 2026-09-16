"""Unit tests for all 17 rule types (rules-catalog.md v2)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.schemas.rules import (
    ReportDataError,
    RuleValidationError,
    parse_rule_config,
)
from src.services.rules_engine import RulesEngine


@pytest.fixture
def engine() -> RulesEngine:
    return RulesEngine()


# ─── tiered_with_bonus (C1) ─────────────────────────────────────────────────

C1_TIERS = {
    "tiers": [
        {"min": 5, "max": 15, "pts": 400, "bonus_pts": 200},
        {"min": 15, "max": 50, "pts": 600, "bonus_pts": 300},
        {"min": 50, "max": 100, "pts": 800, "bonus_pts": 400},
        {"min": 100, "max": None, "pts": 1000, "bonus_pts": 500},
    ],
    "bonus_condition": {"field": "external_guests_percent", "operator": ">=", "value": 10},
}


def test_tiered_with_bonus_no_bonus(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="tiered_with_bonus",
        config=C1_TIERS,
        report_data={"count": 20, "external_guests_percent": 5},
    )
    assert r.points == 600
    assert r.breakdown["bonus"] == 0


def test_tiered_with_bonus_with_bonus(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="tiered_with_bonus",
        config=C1_TIERS,
        report_data={"count": 20, "external_guests_percent": 15},
    )
    assert r.points == 900  # 600 + 300
    assert r.breakdown["bonus"] == 300


def test_tiered_with_bonus_no_condition_field(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="tiered_with_bonus",
        config=C1_TIERS,
        report_data={"count": 10},
    )
    assert r.points == 400
    assert r.breakdown["bonus"] == 0


def test_tiered_with_bonus_negative_count(engine: RulesEngine) -> None:
    with pytest.raises(ReportDataError):
        engine.calculate(
            rule_type="tiered_with_bonus",
            config=C1_TIERS,
            report_data={"count": -1},
        )


# ─── per_unit_with_bonus (C2) ───────────────────────────────────────────────

C2 = {"base_per_partner": 300, "cross_type_bonus": 50}


def test_per_unit_no_cross(engine: RulesEngine) -> None:
    r = engine.calculate(rule_type="per_unit_with_bonus", config=C2, report_data={"partners": 3})
    assert r.points == 900
    assert r.breakdown["cross_type"] is False


def test_per_unit_with_cross(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="per_unit_with_bonus",
        config=C2,
        report_data={"partners": 2, "cross_type": True},
    )
    assert r.points == 650  # 300*2 + 50
    assert r.breakdown["cross_type"] is True


def test_per_unit_zero_partners(engine: RulesEngine) -> None:
    with pytest.raises(ReportDataError):
        engine.calculate(rule_type="per_unit_with_bonus", config=C2, report_data={"partners": 0})


def test_per_unit_missing_partners(engine: RulesEngine) -> None:
    with pytest.raises(ReportDataError):
        engine.calculate(rule_type="per_unit_with_bonus", config=C2, report_data={})


# ─── binary_with_monthly_cap (C4) ───────────────────────────────────────────

C4 = {"options": {"not_informative": 10, "informative": 50}, "monthly_cap": 500}


def test_binary_with_monthly_cap(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="binary_with_monthly_cap",
        config=C4,
        report_data={"variant": "informative"},
    )
    assert r.points == 50
    assert r.breakdown["monthly_cap"] == 500


def test_binary_with_monthly_cap_flat(engine: RulesEngine) -> None:
    """Flat JSONB form also accepted."""
    r = engine.calculate(
        rule_type="binary_with_monthly_cap",
        config={"not_informative": 10, "informative": 50, "monthly_cap": 500},
        report_data={"variant": "not_informative"},
    )
    assert r.points == 10


def test_binary_with_monthly_cap_unknown(engine: RulesEngine) -> None:
    with pytest.raises(RuleValidationError):
        engine.calculate(
            rule_type="binary_with_monthly_cap",
            config=C4,
            report_data={"variant": "spam"},
        )


# ─── fixed_monthly_with_per_unit (C5) ───────────────────────────────────────

C5 = {"base_monthly": 200, "per_extra_social": 50}


def test_fixed_monthly_base_only(engine: RulesEngine) -> None:
    r = engine.calculate(rule_type="fixed_monthly_with_per_unit", config=C5, report_data={})
    assert r.points == 200
    assert r.breakdown["extra"] == 0


def test_fixed_monthly_with_extras(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="fixed_monthly_with_per_unit",
        config=C5,
        report_data={"extra_socials": 3},
    )
    assert r.points == 350  # 200 + 50*3


def test_fixed_monthly_with_cap(engine: RulesEngine) -> None:
    cfg = {**C5, "monthly_cap": 300}
    r = engine.calculate(
        rule_type="fixed_monthly_with_per_unit",
        config=cfg,
        report_data={"extra_socials": 5},
    )
    assert r.points == 300


def test_fixed_monthly_negative_extra(engine: RulesEngine) -> None:
    with pytest.raises(ReportDataError):
        engine.calculate(
            rule_type="fixed_monthly_with_per_unit",
            config=C5,
            report_data={"extra_socials": -1},
        )


# ─── scale_with_frequency_limit (C7) ────────────────────────────────────────

C7 = {
    "levels": {"city": 100, "kazan": 200, "abroad": 500},
    "max_per_month": 1,
}


def test_scale_with_frequency_limit(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="scale_with_frequency_limit",
        config=C7,
        report_data={"level": "kazan"},
    )
    assert r.points == 200
    assert r.breakdown["max_per_month"] == 1


def test_scale_with_frequency_limit_unknown(engine: RulesEngine) -> None:
    with pytest.raises(RuleValidationError):
        engine.calculate(
            rule_type="scale_with_frequency_limit",
            config=C7,
            report_data={"level": "mars"},
        )


# ─── scale_with_conditional_bonus (C9) ──────────────────────────────────────

C9 = {
    "levels": {"student": 100, "iu": 200, "federal": 500},
    "full_club_focus_bonus": {"student": 150, "iu": 250, "federal": 600},
    "max_full_focus_per_month": 5,
}


def test_c9_no_focus(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="scale_with_conditional_bonus",
        config=C9,
        report_data={"level": "iu"},
    )
    assert r.points == 200
    assert r.breakdown["bonus"] == 0


def test_c9_with_focus(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="scale_with_conditional_bonus",
        config=C9,
        report_data={"level": "iu", "full_club_focus": True},
    )
    assert r.points == 450  # 200 + 250
    assert r.breakdown["bonus"] == 250


def test_c9_focus_without_bonus_for_level(engine: RulesEngine) -> None:
    cfg = {**C9, "full_club_focus_bonus": {"student": 150}}
    r = engine.calculate(
        rule_type="scale_with_conditional_bonus",
        config=cfg,
        report_data={"level": "iu", "full_club_focus": True},
    )
    assert r.points == 200


def test_c9_invalid_focus_type(engine: RulesEngine) -> None:
    with pytest.raises(ReportDataError):
        engine.calculate(
            rule_type="scale_with_conditional_bonus",
            config=C9,
            report_data={"level": "iu", "full_club_focus": "yes"},
        )


# ─── discretionary (C10) ────────────────────────────────────────────────────

C10 = {"min": 50, "max": 300}


def test_discretionary_defaults_to_min(engine: RulesEngine) -> None:
    r = engine.calculate(rule_type="discretionary", config=C10, report_data={})
    assert r.points == 50
    assert r.breakdown["requested"] is None


def test_discretionary_within_range(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="discretionary", config=C10, report_data={"points": 200}
    )
    assert r.points == 200


def test_discretionary_clamps_high(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="discretionary", config=C10, report_data={"points": 999}
    )
    assert r.points == 300


def test_discretionary_clamps_low(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="discretionary", config=C10, report_data={"points": 0}
    )
    assert r.points == 50


# ─── fixed_per_event_with_monthly_cap (C11) ─────────────────────────────────

C11 = {"per_event": 350, "monthly_cap": 700}


def test_fixed_per_event(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="fixed_per_event_with_monthly_cap", config=C11, report_data={}
    )
    assert r.points == 350
    assert r.breakdown["monthly_cap"] == 700


# ─── scale_with_league_bonus (S2) ───────────────────────────────────────────

S2 = {
    "levels": {"internal_city": 200, "kazan": 400, "regional": 600, "rf": 1000, "world": 1500},
    "bonus": {"internal_city": 0, "kazan": 50, "regional": 150, "rf": 250, "world": 500},
    "bonus_field": "league",
}


def test_s2_no_league(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="scale_with_league_bonus",
        config=S2,
        report_data={"level": "kazan"},
    )
    assert r.points == 400
    assert r.breakdown["bonus"] == 0


def test_s2_with_league(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="scale_with_league_bonus",
        config=S2,
        report_data={"level": "kazan", "league": True},
    )
    assert r.points == 450  # 400 + 50


def test_s2_league_zero_bonus(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="scale_with_league_bonus",
        config=S2,
        report_data={"level": "internal_city", "league": True},
    )
    assert r.points == 200  # bonus 0


# ─── scale_with_conditional_modifier (S3) ───────────────────────────────────

S3 = {
    "individual": {"city": 200, "kazan": 400, "regional": 600, "rf": 1000, "world": 1500},
    "team": {"city": 300, "kazan": 500, "regional": 700, "rf": 1500, "world": 3000},
    "host_win_modifier": {"field": "host_underdog", "operator": ">=", "value": 1},
    "host_win_factor": 0.5,
}


def test_s3_individual_no_modifier(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="scale_with_conditional_modifier",
        config=S3,
        report_data={"mode": "individual", "level": "kazan"},
    )
    assert r.points == 400
    assert r.breakdown["factor"] == 1.0


def test_s3_team_no_modifier(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="scale_with_conditional_modifier",
        config=S3,
        report_data={"mode": "team", "level": "world"},
    )
    assert r.points == 3000


def test_s3_host_win_modifier_applies(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="scale_with_conditional_modifier",
        config=S3,
        report_data={
            "mode": "team",
            "level": "kazan",
            "is_host": True,
            "host_underdog": 1,
        },
    )
    assert r.points == 250  # 500 * 0.5
    assert r.breakdown["factor"] == 0.5


def test_s3_host_not_underdog(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="scale_with_conditional_modifier",
        config=S3,
        report_data={
            "mode": "team",
            "level": "kazan",
            "is_host": True,
            "host_underdog": 0,
        },
    )
    assert r.points == 500
    assert r.breakdown["factor"] == 1.0


def test_s3_invalid_mode(engine: RulesEngine) -> None:
    with pytest.raises(RuleValidationError):
        engine.calculate(
            rule_type="scale_with_conditional_modifier",
            config=S3,
            report_data={"mode": "duo", "level": "city"},
        )


# ─── per_person_per_month (S4 / I4) ─────────────────────────────────────────

S4 = {"per_trainer_per_month": 100, "max_trainers": 3}


def test_s4_trainers_within_cap(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="per_person_per_month", config=S4, report_data={"trainers": 2}
    )
    assert r.points == 200
    assert r.breakdown["trainers"] == 2


def test_s4_trainers_over_cap(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="per_person_per_month", config=S4, report_data={"trainers": 5}
    )
    assert r.points == 300  # capped at 3
    assert r.breakdown["trainers"] == 3


def test_s4_zero_trainers(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="per_person_per_month", config=S4, report_data={"trainers": 0}
    )
    assert r.points == 0


I4 = {"per_leader_per_month": 100, "max_leaders": 3}


def test_i4_leaders_within_cap(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="per_person_per_month", config=I4, report_data={"leaders": 2}
    )
    assert r.points == 200
    assert r.breakdown["leaders"] == 2


def test_i4_leaders_over_cap(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="per_person_per_month", config=I4, report_data={"leaders": 5}
    )
    assert r.points == 300
    assert r.breakdown["leaders"] == 3


def test_per_person_missing_field(engine: RulesEngine) -> None:
    with pytest.raises(ReportDataError):
        engine.calculate(rule_type="per_person_per_month", config=S4, report_data={})


# ─── binary_scale (T3) ──────────────────────────────────────────────────────

T3 = {"local_meetup": 200, "large_conference": 400}


def test_binary_scale_maps_to_binary(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="binary_scale", config=T3, report_data={"variant": "large_conference"}
    )
    assert r.points == 400
    assert r.rule_type == "binary_scale"  # normalized label


def test_binary_scale_unknown_variant(engine: RulesEngine) -> None:
    with pytest.raises(RuleValidationError):
        engine.calculate(
            rule_type="binary_scale", config=T3, report_data={"variant": "webinar"}
        )


# ─── scale_split_mode (A2 / I2) ─────────────────────────────────────────────

A2 = {
    "individual": {"city": 200, "kazan": 400, "rf": 1000, "world": 1500},
    "team": {"city": 400, "kazan": 500, "rf": 1500, "world_offline": 3000, "world_online": 2000},
}


def test_split_mode_individual(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="scale_split_mode",
        config=A2,
        report_data={"mode": "individual", "level": "kazan"},
    )
    assert r.points == 400
    assert r.breakdown["mode"] == "individual"


def test_split_mode_team(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="scale_split_mode",
        config=A2,
        report_data={"mode": "team", "level": "world_offline"},
    )
    assert r.points == 3000
    assert r.breakdown["mode"] == "team"


def test_split_mode_invalid_mode(engine: RulesEngine) -> None:
    with pytest.raises(RuleValidationError):
        engine.calculate(
            rule_type="scale_split_mode",
            config=A2,
            report_data={"mode": "trio", "level": "city"},
        )


def test_split_mode_invalid_level_for_mode(engine: RulesEngine) -> None:
    with pytest.raises(RuleValidationError):
        engine.calculate(
            rule_type="scale_split_mode",
            config=A2,
            report_data={"mode": "individual", "level": "world_offline"},
        )


# ─── combined_cap (G1) ──────────────────────────────────────────────────────

G1 = {"criteria_codes": ["C4", "C5"], "max_percent_of_total_monthly": 15}


def test_combined_cap_valid_config() -> None:
    cfg = parse_rule_config("combined_cap", G1)
    assert cfg.criteria_codes == ["C4", "C5"]
    assert cfg.max_percent_of_total_monthly == 15


def test_combined_cap_not_calculable_per_report(engine: RulesEngine) -> None:
    with pytest.raises(RuleValidationError):
        engine.calculate(rule_type="combined_cap", config=G1, report_data={"count": 1})


# ─── error helpers ───────────────────────────────────────────────────────────

def test_require_int_rejects_string(engine: RulesEngine) -> None:
    with pytest.raises(ReportDataError):
        engine.calculate(
            rule_type="tiered",
            config={"tiers": [{"count": 1, "pts": 10}]},
            report_data={"count": "one"},
        )


def test_require_int_accepts_float_whole(engine: RulesEngine) -> None:
    r = engine.calculate(
        rule_type="tiered",
        config={"tiers": [{"count": 1, "pts": 10}]},
        report_data={"count": 1.0},
    )
    assert r.points == 10


def test_condition_met_operator_gt() -> None:
    from src.schemas.rules import BonusCondition
    from src.services.rules_engine import _condition_met

    cond = BonusCondition(field="x", operator=">", value=5)
    assert _condition_met(cond, {"x": 6}) is True
    assert _condition_met(cond, {"x": 5}) is False
    assert _condition_met(cond, {}) is False
