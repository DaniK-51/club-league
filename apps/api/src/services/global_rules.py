"""Load G1 combined_cap and other global rules from DB."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import Criteria, CriteriaRule, RulesVersion
from src.schemas.rules import CombinedCapConfig, parse_rule_config

DEFAULT_G1 = CombinedCapConfig(
    criteria_codes=["C4", "C5"],
    max_percent_of_total_monthly=15,
)


async def load_combined_caps(
    session: AsyncSession, *, semester: str | None = None
) -> list[CombinedCapConfig]:
    version_q = select(RulesVersion)
    if semester:
        version_q = version_q.where(RulesVersion.semester == semester)
    version = await session.scalar(version_q.order_by(RulesVersion.valid_from.desc()).limit(1))
    if version is None:
        return [DEFAULT_G1]

    result = await session.execute(
        select(CriteriaRule.rule_type, CriteriaRule.config)
        .join(Criteria, Criteria.id == CriteriaRule.criteria_id)
        .where(
            CriteriaRule.version_id == version.id,
            CriteriaRule.rule_type == "combined_cap",
        )
    )
    caps: list[CombinedCapConfig] = []
    for rule_type, config in result.all():
        parsed = parse_rule_config(str(rule_type), dict(config or {}))
        if isinstance(parsed, CombinedCapConfig):
            caps.append(parsed)
    return caps or [DEFAULT_G1]
