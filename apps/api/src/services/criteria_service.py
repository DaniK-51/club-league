from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.errors import api_error
from src.models.entities import Criteria, CriteriaRule, RulesVersion, User
from src.models.enums import ClubCategory
from src.policies.common import ensure_moderator
from src.schemas.common import ErrorCode
from src.schemas.criteria import CriteriaOut, CriteriaRuleOut, RuleOut, UpdateRuleDTO
from src.schemas.rules import RuleValidationError, UnknownRuleTypeError, parse_rule_config
from src.services.audit_service import AuditService


class RuleNotFoundError(Exception):
    pass


async def _active_version(session: AsyncSession, semester: str | None = None) -> RulesVersion | None:
    q = select(RulesVersion)
    if semester:
        q = q.where(RulesVersion.semester == semester)
    return await session.scalar(q.order_by(RulesVersion.valid_from.desc()).limit(1))


async def list_criteria(
    session: AsyncSession,
    *,
    semester: str | None = None,
    category: ClubCategory | None = None,
) -> list[CriteriaOut]:
    """Public catalog for report form / admin UI (active rules version)."""
    version = await _active_version(session, semester)
    if version is None:
        return []

    result = await session.execute(
        select(Criteria)
        .options(selectinload(Criteria.rules))
        .order_by(Criteria.code.asc())
    )
    items: list[CriteriaOut] = []
    for criteria in result.scalars().all():
        if category is not None and criteria.category != category:
            continue
        active_rules = [
            CriteriaRuleOut(
                id=rule.id,
                ruleType=rule.rule_type,
                config=dict(rule.config or {}),
                priority=rule.priority,
                versionId=rule.version_id,
                semester=version.semester,
            )
            for rule in criteria.rules
            if rule.version_id == version.id
        ]
        items.append(
            CriteriaOut(
                id=criteria.id,
                code=criteria.code,
                nameRu=criteria.name_ru,
                nameEn=criteria.name_en,
                category=criteria.category,
                rules=active_rules,
            )
        )
    return items


async def get_rule(session: AsyncSession, rule_id: str) -> RuleOut:
    rule = await session.scalar(
        select(CriteriaRule)
        .options(selectinload(CriteriaRule.criteria), selectinload(CriteriaRule.version))
        .where(CriteriaRule.id == rule_id)
    )
    if rule is None:
        raise RuleNotFoundError(rule_id)
    return RuleOut(
        id=rule.id,
        criteriaId=rule.criteria_id,
        criteriaCode=rule.criteria.code if rule.criteria else "",
        ruleType=rule.rule_type,
        config=dict(rule.config or {}),
        priority=rule.priority,
        versionId=rule.version_id,
        semester=rule.version.semester if rule.version else "",
    )


async def update_rule(
    session: AsyncSession,
    *,
    user: User,
    rule_id: str,
    payload: UpdateRuleDTO,
) -> RuleOut:
    ensure_moderator(user)

    rule = await session.scalar(
        select(CriteriaRule)
        .options(selectinload(CriteriaRule.criteria), selectinload(CriteriaRule.version))
        .where(CriteriaRule.id == rule_id)
    )
    if rule is None:
        raise RuleNotFoundError(rule_id)

    old_snapshot = {
        "rule_type": rule.rule_type,
        "config": dict(rule.config or {}),
        "priority": rule.priority,
    }

    new_type = payload.ruleType or rule.rule_type
    new_config = payload.config if payload.config is not None else dict(rule.config or {})
    try:
        parse_rule_config(new_type, new_config)
    except (UnknownRuleTypeError, RuleValidationError, ValueError) as exc:
        raise api_error(400, ErrorCode.VALIDATION_ERROR, f"Invalid config: {exc}") from None

    rule.rule_type = new_type
    rule.config = new_config
    if payload.priority is not None:
        rule.priority = payload.priority
    await session.flush()

    await AuditService(session).log(
        entity_type="rule",
        entity_id=rule.id,
        action="updated",
        performed_by_id=user.id,
        performed_by_role=user.role.value,
        old_value=old_snapshot,
        new_value={
            "rule_type": rule.rule_type,
            "config": dict(rule.config or {}),
            "priority": rule.priority,
        },
        display_data={
            "title": "Rule updated",
            "summary": f"{rule.criteria.code if rule.criteria else 'rule'} {rule.rule_type} config updated",
            "rule_type": rule.rule_type,
            "criteria_code": rule.criteria.code if rule.criteria else None,
        },
    )
    await session.commit()

    return RuleOut(
        id=rule.id,
        criteriaId=rule.criteria_id,
        criteriaCode=rule.criteria.code if rule.criteria else "",
        ruleType=rule.rule_type,
        config=dict(rule.config or {}),
        priority=rule.priority,
        versionId=rule.version_id,
        semester=rule.version.semester if rule.version else "",
    )
