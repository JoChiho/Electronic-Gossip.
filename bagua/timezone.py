"""时区解析与格式化（兼容 Windows 无 tzdata 场景）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zoneinfo import ZoneInfo

# 预设时区在 tzdata 不可用时的固定 UTC 偏移（小时）
PRESET_UTC_OFFSET_HOURS: dict[str, int] = {
    "Asia/Shanghai": 8,
    "Asia/Hong_Kong": 8,
    "Asia/Taipei": 8,
    "Asia/Tokyo": 9,
    "Asia/Seoul": 9,
    "Asia/Singapore": 8,
    "Europe/London": 0,
    "Europe/Paris": 1,
    "America/New_York": -5,
    "America/Los_Angeles": -8,
    "UTC": 0,
}

TIMEZONE_PRESETS: list[tuple[str, str]] = [
    ("Asia/Shanghai", "中国（北京时间 UTC+8）"),
    ("Asia/Hong_Kong", "中国香港（UTC+8）"),
    ("Asia/Taipei", "中国台湾（UTC+8）"),
    ("Asia/Tokyo", "日本（东京 UTC+9）"),
    ("Asia/Seoul", "韩国（首尔 UTC+9）"),
    ("Asia/Singapore", "新加坡（UTC+8）"),
    ("Europe/London", "英国（伦敦）"),
    ("Europe/Paris", "欧洲中部（巴黎）"),
    ("America/New_York", "美国东部（纽约）"),
    ("America/Los_Angeles", "美国西部（洛杉矶）"),
    ("UTC", "UTC（协调世界时）"),
]

_tzdata_available: bool | None = None


@dataclass(frozen=True)
class TimezoneInfo:
    """统一时区句柄，兼容 ZoneInfo 与固定偏移回退。"""

    iana_name: str
    region_label: str
    tzinfo: ZoneInfo | dt_timezone
    using_fallback: bool = False

    @property
    def key(self) -> str:
        return self.iana_name


def is_tzdata_available() -> bool:
    """检测 IANA 时区数据库是否可用（Windows 需安装 tzdata 包）。"""
    global _tzdata_available
    if _tzdata_available is not None:
        return _tzdata_available
    try:
        from zoneinfo import ZoneInfo

        ZoneInfo("UTC")
        _tzdata_available = True
    except Exception:
        _tzdata_available = False
    return _tzdata_available


def label_for_timezone(iana_name: str) -> str:
    for name, label in TIMEZONE_PRESETS:
        if name == iana_name:
            return label
    return iana_name


def _fixed_timezone(iana_name: str) -> dt_timezone:
    hours = PRESET_UTC_OFFSET_HOURS.get(iana_name, 0)
    return dt_timezone(timedelta(hours=hours), name=iana_name)


def get_timezone(iana_name: str, region_label: str = "") -> TimezoneInfo:
    """
    解析时区，永不抛异常。
    优先使用 zoneinfo；失败时回退到预设固定 UTC 偏移。
    """
    label = region_label or label_for_timezone(iana_name)
    if is_tzdata_available():
        try:
            from zoneinfo import ZoneInfo

            return TimezoneInfo(iana_name, label, ZoneInfo(iana_name), using_fallback=False)
        except Exception:
            pass
    return TimezoneInfo(iana_name, label, _fixed_timezone(iana_name), using_fallback=True)


def get_default_timezone() -> TimezoneInfo:
    return get_timezone("Asia/Shanghai", "中国（北京时间 UTC+8）")


def detect_system_timezone_name() -> str:
    """尽力检测系统时区 IANA 名称，失败则返回 Asia/Shanghai。"""
    if not is_tzdata_available():
        return "Asia/Shanghai"
    try:
        from zoneinfo import available_timezones

        tz = datetime.now().astimezone().tzinfo
        if tz is not None and hasattr(tz, "key"):
            key = tz.key  # type: ignore[union-attr]
            if key in available_timezones():
                return key
    except Exception:
        pass
    return "Asia/Shanghai"


def format_utc_offset(tzinfo: ZoneInfo | dt_timezone, dt: datetime | None = None) -> str:
    if dt is None:
        dt = datetime.now(tzinfo)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=tzinfo)
    else:
        dt = dt.astimezone(tzinfo)

    offset = dt.utcoffset()
    if offset is None:
        return "UTC"
    total = int(offset.total_seconds())
    sign = "+" if total >= 0 else "-"
    hours, rem = divmod(abs(total), 3600)
    minutes = rem // 60
    if minutes:
        return f"UTC{sign}{hours}:{minutes:02d}"
    return f"UTC{sign}{hours}"


def format_datetime_with_tz(dt: datetime, tz: TimezoneInfo) -> str:
    local = dt.astimezone(tz.tzinfo) if dt.tzinfo else dt.replace(tzinfo=tz.tzinfo)
    offset = format_utc_offset(tz.tzinfo, local)
    fallback_note = " [固定偏移回退]" if tz.using_fallback else ""
    return (
        f"{local.strftime('%Y-%m-%d %H:%M:%S')} "
        f"({tz.region_label}, {tz.iana_name}, {offset}{fallback_note})"
    )


def parse_datetime_input(raw: str, tz: TimezoneInfo) -> datetime | None:
    raw = raw.strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y-%m-%d"):
        try:
            naive = datetime.strptime(raw, fmt)
            return naive.replace(tzinfo=tz.tzinfo)
        except ValueError:
            continue
    return None


def now_in_timezone(tz: TimezoneInfo) -> datetime:
    return datetime.now(tz.tzinfo)


def validate_timezone_name(iana_name: str) -> bool:
    if is_tzdata_available():
        try:
            from zoneinfo import ZoneInfo

            ZoneInfo(iana_name)
            return True
        except Exception:
            return False
    return iana_name in PRESET_UTC_OFFSET_HOURS