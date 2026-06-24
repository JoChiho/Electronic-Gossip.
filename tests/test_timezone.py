"""时区模块测试。"""

from datetime import datetime, timezone as dt_timezone

import pytest

from bagua.timezone import (
    get_default_timezone,
    get_timezone,
    is_tzdata_available,
    format_datetime_with_tz,
    validate_timezone_name,
    parse_datetime_input,
)


def test_get_timezone_never_raises():
    tz = get_timezone("Asia/Shanghai", "中国")
    assert tz.iana_name == "Asia/Shanghai"
    assert tz.tzinfo is not None


def test_get_default_timezone():
    tz = get_default_timezone()
    assert tz.iana_name == "Asia/Shanghai"


def test_format_datetime_with_tz():
    tz = get_timezone("UTC", "UTC")
    dt = datetime(2026, 6, 24, 14, 30, 0, tzinfo=tz.tzinfo)
    result = format_datetime_with_tz(dt, tz)
    assert "2026-06-24 14:30:00" in result
    assert "UTC" in result


def test_parse_datetime_input():
    tz = get_timezone("Asia/Shanghai")
    dt = parse_datetime_input("2026-06-24 14:30", tz)
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 6
    assert dt.day == 24


def test_validate_preset_timezone():
    assert validate_timezone_name("Asia/Shanghai") is True
    assert validate_timezone_name("Invalid/Zone") is False


def test_fallback_mode_works_without_tzdata(monkeypatch):
    monkeypatch.setattr("bagua.timezone._tzdata_available", False)
    tz = get_timezone("Asia/Shanghai")
    assert tz.using_fallback is True
    now = datetime.now(tz.tzinfo)
    assert now.utcoffset().total_seconds() == 8 * 3600