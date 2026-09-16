"""Monthly per-criteria caps from CriteriaRule configs (catalog limits).

Applied after summing COMPLETED points per club, before G1 combined_cap.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import Criteria, CriteriaRule, RulesVersion


def _cap_from_config(rule_type: str, config: dict[str, Any]) -> int | None:
    if rule_type in {"binary_with_monthly_cap", "fixed_per_event_with_monthly_cap"}:
        cap = config.get("monthly_cap")
        return int(cap) if isinstance(cap, (int, float)) else None
    if rule_type == "scale_with_frequency_limit":
        levels = config.get("levels") or {}
        if not isinstance(levels, dict) or not levels:
            return None
        # Frequency limit is on count, not points; approximate point cap as
        # max(level) * max_per_month so a single club cannot exceed it monthly.
        try:
            max_pts = max(int(v) for v in levels.values())
            max_per_month = int(config.get("max_per_month") or 1)
        except (TypeError, ValueError):
            return None
        return max_pts * max_per_month
    return None


async def load_monthly_caps(session: AsyncSession, *, semester: str | None = None) -> dict[str, int]:
    """criteria_code → monthly point cap (if configured)."""
    version_q = select(RulesVersion)
    if semester:
        version_q = version_q.where(RulesVersion.semester == semester)
    version = await session.scalar(version_q.order_by(RulesVersion.valid_from.desc()).limit(1))
    if version is None:
        return {}

    result = await session.execute(
        select(Criteria.code, CriteriaRule.rule_type, CriteriaRule.config)
        .join(Criteria, Criteria.id == CriteriaRule.criteria_id)
        .where(CriteriaRule.version_id == version.id)
    )
    caps: dict[str, int] = {}
    for code, rule_type, config in result.all():
        cfg = dict(config or {})
        cap = _cap_from_config(str(rule_type), cfg)
        if cap is not None:
            caps[str(code)] = cap
    return caps


def apply_monthly_caps(
    points_by_criteria: dict[str, int],
    caps: dict[str, int],
) -> dict[str, int]:
    result = dict(points_by_criteria)
    for code, cap in caps.items():
        if code in result and result[code] > cap:
            result[code] = cap
    return result
