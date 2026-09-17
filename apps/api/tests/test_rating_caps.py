"""Monthly caps + auto-complete unit tests."""

from __future__ import annotations

from src.services.rating_caps import apply_monthly_caps


def test_monthly_cap_truncates() -> None:
    caps = {"C4": 500, "C11": 700}
    points = {"C4": 900, "C8": 1000, "C11": 1400}
    result = apply_monthly_caps(points, caps)
    assert result["C4"] == 500
    assert result["C11"] == 700
    assert result["C8"] == 1000


def test_monthly_cap_noop_when_under() -> None:
    caps = {"C4": 500}
    points = {"C4": 100}
    assert apply_monthly_caps(points, caps) == points


def test_cap_from_frequency_limit() -> None:
    from src.services.rating_caps import _cap_from_config

    cap = _cap_from_config(
        "scale_with_frequency_limit",
        {"levels": {"city": 100, "abroad": 500}, "max_per_month": 1},
    )
    assert cap == 500
    assert _cap_from_config("scale", {"levels": {"a": 1}}) is None
