from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from src.models.enums import ClubCategory


class CriteriaRuleOut(BaseModel):
    id: str
    ruleType: str
    config: dict[str, Any]
    priority: int
    versionId: str
    semester: str


class CriteriaOut(BaseModel):
    id: str
    code: str
    nameRu: str
    nameEn: str
    category: ClubCategory | None
    rules: list[CriteriaRuleOut]


class UpdateRuleDTO(BaseModel):
    """Admin updates JSONB config (validated by rule_type)."""

    config: dict[str, Any] | None = None
    priority: int | None = None
    ruleType: str | None = None


class RuleOut(BaseModel):
    id: str
    criteriaId: str
    criteriaCode: str
    ruleType: str
    config: dict[str, Any]
    priority: int
    versionId: str
    semester: str


class AuditLogOut(BaseModel):
    id: str
    seq: int
    entityType: str
    entityId: str
    action: str
    oldValue: dict[str, Any] | None
    newValue: dict[str, Any] | None
    displayData: dict[str, Any] | None = None
    performedByName: str
    performedByRole: str
    performedAt: datetime
    reason: str | None
    hash: str


class AuditListResponse(BaseModel):
    items: list[AuditLogOut]
    total: int
    limit: int
    offset: int
