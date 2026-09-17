from enum import StrEnum


class UserRole(StrEnum):
    GUEST = "GUEST"
    CLUB_LEADER = "CLUB_LEADER"
    MODERATOR = "MODERATOR"


class ClubCategory(StrEnum):
    SPORT = "SPORT"
    TECH = "TECH"
    ART = "ART"
    SPECIAL_INTEREST = "SPECIAL_INTEREST"


class ReportStatus(StrEnum):
    DRAFT = "DRAFT"
    ON_MODERATION = "ON_MODERATION"
    CHANGES_REQUIRED = "CHANGES_REQUIRED"
    APPROVED = "APPROVED"
    DISPUTED = "DISPUTED"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"
