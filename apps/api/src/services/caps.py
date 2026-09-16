"""Global caps from rules-catalog (G1 combined_cap C4+C5)."""

from __future__ import annotations

from src.schemas.rules import CombinedCapConfig

__all__ = ["CombinedCapConfig", "apply_combined_cap"]


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
