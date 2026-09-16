"""Link whitelist validation — external proof URLs only, no uploads."""

from __future__ import annotations

from urllib.parse import urlparse

from src.core.config import get_settings
from src.schemas.common import ErrorCode


class LinkValidationError(Exception):
    def __init__(self, code: ErrorCode, message: str) -> None:
        self.code = code
        super().__init__(message)


def extract_domain(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise LinkValidationError(
            ErrorCode.INVALID_URL_FORMAT,
            f"Invalid URL: {url!r}",
        )
    host = parsed.hostname
    if not host:
        raise LinkValidationError(
            ErrorCode.INVALID_URL_FORMAT,
            f"Invalid URL host: {url!r}",
        )
    return host.lower()


def is_domain_allowed(domain: str, allowed: frozenset[str]) -> bool:
    if domain in allowed:
        return True
    # allow subdomains of whitelist entries (e.g. docs.google.com)
    return any(domain.endswith(f".{root}") for root in allowed)


def validate_link(url: str, *, allowed: frozenset[str] | None = None) -> str:
    """Return normalized domain or raise LinkValidationError."""
    domains = allowed if allowed is not None else get_settings().allowed_domains
    domain = extract_domain(url)
    if not is_domain_allowed(domain, domains):
        raise LinkValidationError(
            ErrorCode.DOMAIN_NOT_ALLOWED,
            f"Domain not allowed: {domain}",
        )
    return domain


def validate_links(urls: list[str], *, allowed: frozenset[str] | None = None) -> list[tuple[str, str]]:
    """Validate list of URLs; reject duplicates. Returns [(url, domain), ...]."""
    if not urls:
        raise LinkValidationError(
            ErrorCode.INVALID_URL_FORMAT,
            "At least one proof link is required",
        )
    seen: set[str] = set()
    result: list[tuple[str, str]] = []
    for raw in urls:
        url = raw.strip()
        if not url:
            raise LinkValidationError(ErrorCode.INVALID_URL_FORMAT, "Empty URL")
        normalized = url.rstrip("/")
        if normalized in seen:
            raise LinkValidationError(
                ErrorCode.DUPLICATE_LINK,
                f"Duplicate link: {url}",
            )
        seen.add(normalized)
        domain = validate_link(url, allowed=allowed)
        result.append((url, domain))
    return result
