"""Seed v2 criteria + rules for the three base rule types (C3/C6/C8).

Usage:
    uv run python -m scripts.seed_rules
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select
from src.core.database import dispose_engine, get_session_factory
from src.models.entities import Criteria, CriteriaRule, RulesVersion
from src.models.enums import ClubCategory
from src.schemas.rules import parse_rule_config

SEMESTER = "2026-fall"

CRITERIA: list[dict[str, object]] = [
    {
        "code": "C3",
        "name_ru": "Внутреннее кампусное мероприятие",
        "name_en": "Internal campus event",
        "category": None,
        "rule_type": "binary",
        "config": {"passive": 100, "active": 350},
    },
    {
        "code": "C6",
        "name_ru": "Внешний спикер",
        "name_en": "External speaker",
        "category": None,
        "rule_type": "scale",
        "config": {
            "levels": {
                "local": 100,
                "regional": 200,
                "national": 400,
                "world": 500,
            }
        },
    },
    {
        "code": "C8",
        "name_ru": "Образовательный контент",
        "name_en": "Educational content",
        "category": None,
        "rule_type": "tiered",
        "config": {
            "tiers": [
                {"count": 1, "pts": 250},
                {"min": 2, "max": 5, "pts": 500},
                {"min": 6, "max": 10, "pts": 800},
                {"min": 11, "max": None, "pts": 1000},
            ]
        },
    },
    {
        "code": "C4",
        "name_ru": "Пост в соцсетях",
        "name_en": "Social media post",
        "category": None,
        "rule_type": "binary",
        "config": {"not_informative": 10, "informative": 50},
    },
    {
        "code": "C5",
        "name_ru": "Эстетика соцсетей",
        "name_en": "Social media aesthetics",
        "category": None,
        "rule_type": "binary",
        "config": {"standard": 200, "premium": 300},
    },
    {
        "code": "G1",
        "name_ru": "Потолок соцсетей",
        "name_en": "Social media combined cap",
        "category": None,
        "rule_type": "combined_cap",
        "config": {
            "criteria_codes": ["C4", "C5"],
            "max_percent_of_total_monthly": 15,
        },
    },
]


async def seed() -> None:
    factory = get_session_factory()
    async with factory() as session:
        version = await session.scalar(
            select(RulesVersion).where(RulesVersion.semester == SEMESTER)
        )
        if version is None:
            version = RulesVersion(semester=SEMESTER, valid_from=datetime.now(UTC))
            session.add(version)
            await session.flush()

        for item in CRITERIA:
            code = str(item["code"])
            rule_type = str(item["rule_type"])
            config = dict(item["config"])  # type: ignore[arg-type]
            parse_rule_config(rule_type, config)  # fail fast if catalog drifts

            criteria = await session.scalar(select(Criteria).where(Criteria.code == code))
            if criteria is None:
                category = item["category"]
                criteria = Criteria(
                    code=code,
                    name_ru=str(item["name_ru"]),
                    name_en=str(item["name_en"]),
                    category=category if isinstance(category, ClubCategory) else None,
                )
                session.add(criteria)
                await session.flush()

            existing = await session.scalar(
                select(CriteriaRule).where(
                    CriteriaRule.criteria_id == criteria.id,
                    CriteriaRule.version_id == version.id,
                )
            )
            if existing is None:
                session.add(
                    CriteriaRule(
                        criteria_id=criteria.id,
                        rule_type=rule_type,
                        config=config,
                        priority=0,
                        version_id=version.id,
                    )
                )
            else:
                existing.rule_type = rule_type
                existing.config = config

        await session.commit()
        print(f"Seeded rules version={SEMESTER} codes={[str(i['code']) for i in CRITERIA]}")


async def main() -> None:
    try:
        await seed()
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
