from enum import StrEnum
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorCode(StrEnum):
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    SUDO_REQUIRED = "SUDO_REQUIRED"
    NOT_CLUB_LEADER = "NOT_CLUB_LEADER"

    INVALID_URL_FORMAT = "INVALID_URL_FORMAT"
    DOMAIN_NOT_ALLOWED = "DOMAIN_NOT_ALLOWED"
    DUPLICATE_LINK = "DUPLICATE_LINK"
    INVALID_ACTIVITY_DATE = "INVALID_ACTIVITY_DATE"

    REPORT_NOT_FOUND = "REPORT_NOT_FOUND"
    INVALID_STATUS_TRANSITION = "INVALID_STATUS_TRANSITION"
    COMMENT_REQUIRED = "COMMENT_REQUIRED"
    RULES_VERSION_NOT_FOUND = "RULES_VERSION_NOT_FOUND"
    PERIOD_NOT_FOUND = "PERIOD_NOT_FOUND"
    ALREADY_ARCHIVED = "ALREADY_ARCHIVED"

    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    YANDEX_SYNC_FAILED = "YANDEX_SYNC_FAILED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"


class ErrorBody(BaseModel):
    code: ErrorCode
    message: str


class ApiError(BaseModel):
    error: ErrorBody


class ApiSuccess(BaseModel, Generic[T]):
    data: T


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    env: str
    database: Literal["ok", "error"]


class ErrorResponse(BaseModel):
    """OpenAPI helper for documenting error payloads."""

    error: ErrorBody = Field(
        examples=[
            {
                "error": {
                    "code": ErrorCode.DOMAIN_NOT_ALLOWED,
                    "message": "Domain not in whitelist",
                }
            }
        ]
    )
