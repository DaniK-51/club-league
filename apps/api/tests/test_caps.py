from __future__ import annotations

import pytest
from pydantic import ValidationError
from src.services.caps import CombinedCapConfig, apply_combined_cap

G1 = CombinedCapConfig(
    criteria_codes=["C4", "C5"],
    max_percent_of_total_monthly=15,
)


def test_no_cap_when_within_budget() -> None:
    # total 1000, budget 150; C4+C5=100 → ok
    points = {"C4": 40, "C5": 60, "C8": 900}
    assert apply_combined_cap(points, G1) == points


def test_cap_scales_group_down() -> None:
    # total 1000, budget 150; C4+C5=400 → scale to 150
    points = {"C4": 100, "C5": 300, "C8": 600}
    result = apply_combined_cap(points, G1)
    assert result["C4"] + result["C5"] == 150
    assert result["C8"] == 600
    assert result["C4"] == 37  # 100 * 150/400 = 37.5 → 37
    assert result["C5"] == 113  # remainder


def test_zero_total() -> None:
    assert apply_combined_cap({"C4": 0, "C5": 0}, G1) == {"C4": 0, "C5": 0}


def test_config_validation() -> None:
    with pytest.raises(ValidationError):
        CombinedCapConfig(criteria_codes=[], max_percent_of_total_monthly=15)
    with pytest.raises(ValidationError):
        CombinedCapConfig(criteria_codes=["C4", "C4"], max_percent_of_total_monthly=15)
    with pytest.raises(ValidationError):
        CombinedCapConfig(criteria_codes=["C4"], max_percent_of_total_monthly=0)
