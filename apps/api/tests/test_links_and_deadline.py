from __future__ import annotations

import pytest
from src.schemas.common import ErrorCode
from src.schemas.report import is_overdue, parse_activity_date
from src.services.link_validation import LinkValidationError, validate_links


def test_valid_google_docs() -> None:
    links = validate_links(["https://docs.google.com/document/d/abc"])
    assert links[0][1] == "docs.google.com"


def test_subdomain_allowed() -> None:
    links = validate_links(["https://www.youtube.com/watch?v=x"])
    assert links[0][1] == "www.youtube.com"


def test_rejects_unknown_domain() -> None:
    with pytest.raises(LinkValidationError) as exc:
        validate_links(["https://evil.example.com/phish"])
    assert exc.value.code == ErrorCode.DOMAIN_NOT_ALLOWED


def test_rejects_bad_url() -> None:
    with pytest.raises(LinkValidationError) as exc:
        validate_links(["not-a-url"])
    assert exc.value.code == ErrorCode.INVALID_URL_FORMAT


def test_rejects_duplicates() -> None:
    with pytest.raises(LinkValidationError) as exc:
        validate_links(
            [
                "https://t.me/club/1",
                "https://t.me/club/1",
            ]
        )
    assert exc.value.code == ErrorCode.DUPLICATE_LINK


def test_rejects_empty_list() -> None:
    with pytest.raises(LinkValidationError):
        validate_links([])


def test_soft_deadline_warning() -> None:
    from datetime import UTC, datetime, timedelta

    old = datetime.now(UTC) - timedelta(days=8)
    fresh = datetime.now(UTC) - timedelta(days=1)
    assert is_overdue(old) is True
    assert is_overdue(fresh) is False


def test_parse_activity_date_naive_assumes_moscow() -> None:
    dt = parse_activity_date("2026-09-01T12:00:00")
    assert dt.tzinfo is not None
    assert dt.utcoffset() is not None
