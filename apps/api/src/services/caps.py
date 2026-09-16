"""Global caps from rules-catalog (G1 combined_cap C4+C5)."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class CombinedCapConfig(BaseModel):
    """G1: C4 + C5 ≤ max_percent_of_total_monthly % of club monthly total."""

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


def apply_combined_cap(
    points_by_criteria: dict[str, int],
    config: CombinedCapConfig,
) -> dict[str, int]:
    """Cap the sum of listed criteria to max_percent of the monthly total.

    Non-listed criteria are unchanged. If the capped group already fits,
    values are returned as-is. Otherwise each capped item is scaled down
    proportionally so their sum equals the allowed budget.
    """
    total = sum(points_by_criteria.values())
    if total <= 0:
        return dict(points_by_criteria)

    budget = int(total * config.max_percent_of_total_monthly / 100.0)
    capped_sum = sum(points_by_criteria.get(code, 0) for code in config.criteria_codes)
    if capped_sum <= budget:
        return dict(points_by_criteria)

    result = dict(points_by_criteria)
    if capped_sum == 0:
        return result

    # Scale each capped criterion so the group sum equals budget.
    scale = budget / capped_sum
    assigned = 0
    codes = [c for c in config.criteria_codes if points_by_criteria.get(c, 0) > 0]
    for i, code in enumerate(codes):
        raw = points_by_criteria[code] * scale
        value = int(raw)
        if i == len(codes) - 1:
            value = budget - assigned
        else:
            assigned += value
        result[code] = max(0, value)
    return result
