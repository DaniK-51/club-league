"""Seed all v2 criteria from docs/shared/rules-catalog.md.

Usage:
    uv run python -m scripts.seed_rules
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import dispose_engine, get_session_factory
from src.models.entities import Criteria, CriteriaRule, Period, Report, RulesVersion
from src.models.enums import ClubCategory
from src.schemas.rules import parse_rule_config
from src.services.period_service import resolve_period_for_date

SEMESTER = "2026-fall"
_BUSINESS_TZ = ZoneInfo("Europe/Moscow")

_DEFAULT_PERIODS: list[tuple[str, datetime, datetime]] = [
    ("2026-fall", datetime(2026, 9, 1, tzinfo=_BUSINESS_TZ), datetime(2027, 1, 1, tzinfo=_BUSINESS_TZ)),
    ("2026-spring", datetime(2026, 1, 1, tzinfo=_BUSINESS_TZ), datetime(2026, 6, 1, tzinfo=_BUSINESS_TZ)),
    ("2026-summer", datetime(2026, 6, 1, tzinfo=_BUSINESS_TZ), datetime(2026, 9, 1, tzinfo=_BUSINESS_TZ)),
]

# Full v2 catalog — values from rules-catalog.md
CRITERIA: list[dict[str, Any]] = [
    # Common
    {
        "code": "C1",
        "name_ru": "Мероприятие клуба",
        "name_en": "Club organized an event",
        "category": None,
        "rule_type": "tiered_with_bonus",
        "config": {
            "tiers": [
                {"min": 5, "max": 15, "pts": 400, "bonus_pts": 200},
                {"min": 15, "max": 50, "pts": 600, "bonus_pts": 300},
                {"min": 50, "max": 100, "pts": 800, "bonus_pts": 400},
                {"min": 100, "max": None, "pts": 1000, "bonus_pts": 500},
            ],
            "bonus_condition": {
                "field": "external_guests_percent",
                "operator": ">=",
                "value": 10,
            },
        },
    },
    {
        "code": "C2",
        "name_ru": "Совместное мероприятие",
        "name_en": "Joint event",
        "category": None,
        "rule_type": "per_unit_with_bonus",
        "config": {"base_per_partner": 300, "cross_type_bonus": 50},
    },
    {
        "code": "C3",
        "name_ru": "Внутреннее кампусное мероприятие",
        "name_en": "Internal campus event",
        "category": None,
        "rule_type": "binary",
        "config": {"passive": 100, "active": 350},
    },
    {
        "code": "C4",
        "name_ru": "Пост в соцсетях",
        "name_en": "Social media post",
        "category": None,
        "rule_type": "binary_with_monthly_cap",
        "config": {
            "options": {"not_informative": 10, "informative": 50},
            "monthly_cap": 500,
        },
    },
    {
        "code": "C5",
        "name_ru": "Эстетика соцсетей",
        "name_en": "Social media aesthetics",
        "category": None,
        "rule_type": "fixed_monthly_with_per_unit",
        "config": {"base_monthly": 200, "per_extra_social": 50},
    },
    {
        "code": "C6",
        "name_ru": "Внешний спикер",
        "name_en": "External speaker",
        "category": None,
        "rule_type": "scale",
        "config": {
            "levels": {"local": 100, "regional": 200, "national": 400, "world": 500}
        },
    },
    {
        "code": "C7",
        "name_ru": "Посещение внешнего мероприятия",
        "name_en": "Visited external event",
        "category": None,
        "rule_type": "scale_with_frequency_limit",
        "config": {
            "levels": {
                "city": 100,
                "kazan": 200,
                "other_rt": 300,
                "other_rf": 400,
                "abroad": 500,
            },
            "max_per_month": 1,
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
        "code": "C9",
        "name_ru": "Упоминание в СМИ",
        "name_en": "Mentioned in media",
        "category": None,
        "rule_type": "scale_with_conditional_bonus",
        "config": {
            "levels": {
                "student": 100,
                "iu": 200,
                "city": 300,
                "region": 400,
                "federal": 500,
            },
            "full_club_focus_bonus": {
                "student": 150,
                "iu": 250,
                "city": 350,
                "region": 500,
                "federal": 600,
            },
            "max_full_focus_per_month": 5,
        },
    },
    {
        "code": "C10",
        "name_ru": "Помощь менеджеру",
        "name_en": "Assistance to manager",
        "category": None,
        "rule_type": "discretionary",
        "config": {"min": 50, "max": 300},
    },
    {
        "code": "C11",
        "name_ru": "Тимбилдинг",
        "name_en": "Team building",
        "category": None,
        "rule_type": "fixed_per_event_with_monthly_cap",
        "config": {"per_event": 350, "monthly_cap": 700},
    },
    # Sport
    {
        "code": "S1",
        "name_ru": "Личные соревнования",
        "name_en": "Individual competition",
        "category": ClubCategory.SPORT,
        "rule_type": "scale",
        "config": {
            "levels": {
                "city": 100,
                "kazan": 200,
                "regional": 400,
                "rf": 1000,
                "world": 1400,
            }
        },
    },
    {
        "code": "S2",
        "name_ru": "Командные соревнования",
        "name_en": "Team competition",
        "category": ClubCategory.SPORT,
        "rule_type": "scale_with_league_bonus",
        "config": {
            "levels": {
                "internal_city": 200,
                "kazan": 400,
                "regional": 600,
                "rf": 1000,
                "world": 1500,
            },
            "bonus": {
                "internal_city": 0,
                "kazan": 50,
                "regional": 150,
                "rf": 250,
                "world": 500,
            },
            "bonus_field": "league",
        },
    },
    {
        "code": "S3",
        "name_ru": "Победа в соревновании",
        "name_en": "Competition win",
        "category": ClubCategory.SPORT,
        "rule_type": "scale_with_conditional_modifier",
        "config": {
            "individual": {
                "city": 200,
                "kazan": 400,
                "regional": 600,
                "rf": 1000,
                "world": 1500,
            },
            "team": {
                "city": 300,
                "kazan": 500,
                "regional": 700,
                "rf": 1500,
                "world": 3000,
            },
            "host_win_modifier": {
                "field": "host_underdog",
                "operator": ">=",
                "value": 1,
            },
            "host_win_factor": 0.5,
        },
    },
    {
        "code": "S4",
        "name_ru": "Регулярные тренировки",
        "name_en": "Regular training",
        "category": ClubCategory.SPORT,
        "rule_type": "per_person_per_month",
        "config": {"per_trainer_per_month": 100, "max_trainers": 3},
    },
    # Tech
    {
        "code": "T1",
        "name_ru": "Хакатон/олимпиада (участие)",
        "name_en": "Hackathon participation",
        "category": ClubCategory.TECH,
        "rule_type": "scale",
        "config": {
            "levels": {
                "internal_city": 200,
                "kazan": 400,
                "regional": 600,
                "rf": 1000,
                "world": 1500,
            }
        },
    },
    {
        "code": "T2",
        "name_ru": "Хакатон/олимпиада (победа)",
        "name_en": "Hackathon win",
        "category": ClubCategory.TECH,
        "rule_type": "scale",
        "config": {
            "levels": {
                "city": 300,
                "kazan": 500,
                "regional": 700,
                "rf": 1500,
                "world": 3000,
            }
        },
    },
    {
        "code": "T3",
        "name_ru": "Выступление на конференции",
        "name_en": "Conference presentation",
        "category": ClubCategory.TECH,
        "rule_type": "binary_scale",
        "config": {"local_meetup": 200, "large_conference": 400},
    },
    # Art
    {
        "code": "A1",
        "name_ru": "Конкурс/фестиваль (участие)",
        "name_en": "Festival participation",
        "category": ClubCategory.ART,
        "rule_type": "scale",
        "config": {
            "levels": {
                "city": 200,
                "kazan": 400,
                "regional": 600,
                "rf": 1000,
                "world": 1400,
            }
        },
    },
    {
        "code": "A2",
        "name_ru": "Конкурс/фестиваль (победа)",
        "name_en": "Festival win",
        "category": ClubCategory.ART,
        "rule_type": "scale_split_mode",
        "config": {
            "individual": {
                "city": 200,
                "kazan": 400,
                "regional": 600,
                "rf": 1000,
                "world": 1500,
            },
            "team": {
                "city": 400,
                "kazan": 500,
                "regional": 700,
                "rf": 1500,
                "world_offline": 3000,
                "world_online": 2000,
            },
        },
    },
    {
        "code": "A3",
        "name_ru": "Публичный перформанс",
        "name_en": "Public performance",
        "category": ClubCategory.ART,
        "rule_type": "scale",
        "config": {
            "levels": {
                "campus": 300,
                "city": 500,
                "regional": 800,
                "federal": 1200,
            }
        },
    },
    {
        "code": "A4",
        "name_ru": "Художественный контент",
        "name_en": "Artistic content",
        "category": ClubCategory.ART,
        "rule_type": "tiered",
        "config": {
            "tiers": [
                {"count": 1, "pts": 200},
                {"min": 2, "max": 5, "pts": 400},
                {"min": 6, "max": 10, "pts": 700},
                {"min": 11, "max": None, "pts": 1000},
            ]
        },
    },
    # Special Interest
    {
        "code": "I1",
        "name_ru": "Турнир по профилю (участие)",
        "name_en": "Profile tournament",
        "category": ClubCategory.SPECIAL_INTEREST,
        "rule_type": "scale",
        "config": {
            "levels": {
                "city": 200,
                "kazan": 400,
                "regional": 600,
                "rf": 1000,
                "world": 1400,
            }
        },
    },
    {
        "code": "I2",
        "name_ru": "Турнир по профилю (победа)",
        "name_en": "Profile tournament win",
        "category": ClubCategory.SPECIAL_INTEREST,
        "rule_type": "scale_split_mode",
        "config": {
            "individual": {
                "city": 200,
                "kazan": 400,
                "regional": 600,
                "rf": 1000,
                "world": 1500,
            },
            "team": {
                "city": 400,
                "kazan": 500,
                "regional": 700,
                "rf": 1500,
                "world_offline": 3000,
                "world_online": 2000,
            },
        },
    },
    {
        "code": "I3",
        "name_ru": "Открытое публичное мероприятие",
        "name_en": "Open public event",
        "category": ClubCategory.SPECIAL_INTEREST,
        "rule_type": "scale",
        "config": {
            "levels": {
                "campus": 300,
                "city": 500,
                "regional": 800,
                "federal": 1200,
            }
        },
    },
    {
        "code": "I4",
        "name_ru": "Регулярные встречи",
        "name_en": "Regular meetings",
        "category": ClubCategory.SPECIAL_INTEREST,
        "rule_type": "per_person_per_month",
        "config": {"per_leader_per_month": 100, "max_leaders": 3},
    },
    # Global
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


async def _seed_default_periods(session: AsyncSession) -> None:
    for name, start, end in _DEFAULT_PERIODS:
        existing = await session.scalar(select(Period).where(Period.name == name))
        if existing is None:
            now = datetime.now(UTC)
            session.add(
                Period(
                    name=name,
                    start_date=start,
                    end_date=end,
                    is_archived=False,
                    created_at=now,
                    updated_at=now,
                )
            )
    await session.flush()


async def _backfill_report_periods(session: AsyncSession) -> None:
    result = await session.execute(
        select(Report).where(Report.period_id.is_(None), Report.is_deleted.is_(False))
    )
    for report in result.scalars().all():
        period = await resolve_period_for_date(session, report.activity_date)
        if period is not None:
            report.period_id = period.id
    await session.flush()


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

        await _seed_default_periods(session)
        await _backfill_report_periods(session)

        for item in CRITERIA:
            code = str(item["code"])
            rule_type = str(item["rule_type"])
            config = dict(item["config"])
            parse_rule_config(rule_type, config)

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
        print(
            f"Seeded rules version={SEMESTER} count={len(CRITERIA)} "
            f"codes={[str(i['code']) for i in CRITERIA]} periods=default-2026"
        )


async def main() -> None:
    try:
        await seed()
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
