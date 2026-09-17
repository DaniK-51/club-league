"""Period helpers for semester → date range (Europe/Moscow)."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

BUSINESS_TZ = ZoneInfo("Europe/Moscow")

# semester format: "2026-fall" | "2026-spring" | "2026-summer"
_FALL = (9, 1)  # Sep 1 – Dec 31
_SPRING = (1, 1)  # Jan 1 – May 31
_SUMMER = (6, 1)  # Jun 1 – Aug 31


def semester_range(semester: str) -> tuple[datetime, datetime] | None:
    """Parse `YYYY-{fall|spring|summer}` → [start, end) UTC datetimes."""
    try:
        year_s, season = semester.split("-", 1)
        year = int(year_s)
    except ValueError:
        return None
    season = season.lower()
    if season == "fall":
        start = datetime(year, 9, 1, tzinfo=BUSINESS_TZ)
        end = datetime(year + 1, 1, 1, tzinfo=BUSINESS_TZ)
    elif season == "spring":
        start = datetime(year, 1, 1, tzinfo=BUSINESS_TZ)
        end = datetime(year, 6, 1, tzinfo=BUSINESS_TZ)
    elif season == "summer":
        start = datetime(year, 6, 1, tzinfo=BUSINESS_TZ)
        end = datetime(year, 9, 1, tzinfo=BUSINESS_TZ)
    else:
        return None
    return start, end


def month_key(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BUSINESS_TZ)
    local = dt.astimezone(BUSINESS_TZ)
    return f"{local.year:04d}-{local.month:02d}"
