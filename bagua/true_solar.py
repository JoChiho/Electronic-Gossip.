"""真太阳时换算（经度修正 + 时差方程）。"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from bagua.timezone import TimezoneInfo

# 预设时区代表经度（度，东经为正）
PRESET_LONGITUDES: dict[str, float] = {
    "Asia/Shanghai": 121.47,
    "Asia/Hong_Kong": 114.17,
    "Asia/Taipei": 121.56,
    "Asia/Tokyo": 139.69,
    "Asia/Seoul": 126.98,
    "Asia/Singapore": 103.85,
    "Europe/London": -0.13,
    "Europe/Paris": 2.35,
    "America/New_York": -74.01,
    "America/Los_Angeles": -118.24,
    "UTC": 0.0,
}


def default_longitude(iana_name: str) -> float:
    return PRESET_LONGITUDES.get(iana_name, 120.0)


def standard_meridian_degrees(dt: datetime) -> float:
    """时区中央经线（度，东经为正）。"""
    offset = dt.utcoffset()
    if offset is None:
        return 0.0
    return offset.total_seconds() / 3600 * 15.0


def equation_of_time_minutes(day_of_year: int) -> float:
    """时差方程近似值（分钟）。"""
    b = 2 * math.pi * (day_of_year - 81) / 365.0
    return 229.18 * (
        0.000075
        + 0.001868 * math.cos(b)
        - 0.032077 * math.sin(b)
        - 0.014615 * math.cos(2 * b)
        - 0.040849 * math.sin(2 * b)
    )


def to_true_solar(
    dt: datetime,
    tz: TimezoneInfo,
    longitude: float | None = None,
    *,
    enabled: bool = True,
) -> tuple[datetime, str]:
    """
    将标准时区时刻换算为真太阳时。

    Returns:
        (校正后时刻, 说明文字；未校正时说明为空)
    """
    if not enabled:
        return dt, ""

    lon = longitude if longitude is not None else default_longitude(tz.iana_name)
    local = dt.astimezone(tz.tzinfo) if dt.tzinfo else dt.replace(tzinfo=tz.tzinfo)
    meridian = standard_meridian_degrees(local)
    lon_correction_min = (lon - meridian) * 4.0
    eot_min = equation_of_time_minutes(local.timetuple().tm_yday)
    total_min = lon_correction_min + eot_min
    corrected = local + timedelta(minutes=total_min)

    if abs(total_min) < 0.5:
        return corrected, ""

    direction = "东经" if lon >= 0 else "西经"
    abs_lon = abs(lon)
    note = (
        f"真太阳时 {corrected.strftime('%Y-%m-%d %H:%M')}"
        f"（{direction}{abs_lon:.2f}°，修正{total_min:+.1f}分）"
    )
    return corrected, note