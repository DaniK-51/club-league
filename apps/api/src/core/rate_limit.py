"""Simple in-memory rate limiter (configurable; AGENTS: not hardcoded)."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from src.core.config import get_settings
from src.core.errors import api_error
from src.schemas.common import ErrorCode


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> None:
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return
        now = time.monotonic()
        window = settings.rate_limit_window_seconds
        limit = settings.rate_limit_max_requests
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > window:
                q.popleft()
            if len(q) >= limit:
                raise api_error(
                    429,
                    ErrorCode.RATE_LIMITED,
                    "Too many requests",
                    message_key="rate.limited",
                )
            q.append(now)


limiter = RateLimiter()


def enforce_rate_limit(scope: str, identity: str) -> None:
    limiter.check(f"{scope}:{identity}")
