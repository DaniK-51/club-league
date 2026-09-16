"""Report state machine (docs/04_ARCHITECTURE.md)."""

from __future__ import annotations

from src.models.enums import ReportStatus
from src.schemas.common import ErrorCode


class InvalidTransitionError(Exception):
    def __init__(self, current: ReportStatus, target: ReportStatus) -> None:
        self.current = current
        self.target = target
        self.code = ErrorCode.INVALID_STATUS_TRANSITION
        super().__init__(f"Cannot transition {current.value} -> {target.value}")


# Leader-driven transitions for Step 5 (moderation added in Step 6).
LEADER_TRANSITIONS: dict[ReportStatus, frozenset[ReportStatus]] = {
    ReportStatus.DRAFT: frozenset({ReportStatus.ON_MODERATION}),
    ReportStatus.CHANGES_REQUIRED: frozenset({ReportStatus.ON_MODERATION}),
    ReportStatus.APPROVED: frozenset({ReportStatus.COMPLETED, ReportStatus.DISPUTED}),
}

EDITABLE_STATUSES = frozenset({ReportStatus.DRAFT, ReportStatus.CHANGES_REQUIRED})


def ensure_leader_transition(current: ReportStatus, target: ReportStatus) -> None:
    allowed = LEADER_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise InvalidTransitionError(current, target)


def ensure_editable(current: ReportStatus) -> None:
    if current not in EDITABLE_STATUSES:
        raise InvalidTransitionError(current, current)
