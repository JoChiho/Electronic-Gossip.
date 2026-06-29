"""农历与历法换算（基于 lunar-python，纯逻辑层）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bagua.timezone import TimezoneInfo, format_datetime_with_tz
from bagua.true_solar import to_true_solar

try:
    from lunar_python import Lunar, Solar
except ImportError:  # pragma: no cover - 测试环境会安装依赖
    Lunar = None  # type: ignore[misc, assignment]
    Solar = None  # type: ignore[misc, assignment]

CalendarMode = str  # "solar" | "lunar"

_TIME_ZHI = ("子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥")


@dataclass(frozen=True)
class LunarComponents:
    """梅花易数起卦用的农历数字分量。"""

    year: int
    month: int
    day: int
    hour: int
    label: str
    is_leap_month: bool = False


@dataclass(frozen=True)
class SolarTermComponents:
    """节气历分量（梅花易数起卦用）。"""

    year: int
    month: int
    day: int
    hour: int
    label: str
    year_gan_zhi: str
    month_gan_zhi: str
    hour_zhi: str


@dataclass(frozen=True)
class ResolvedTimeComponents:
    """时间起卦解析结果（含用户输入与算卦口径说明）。"""

    year: int
    month: int
    day: int
    hour: int
    user_input_note: str
    calculation_note: str
    true_solar_note: str = ""


def is_lunar_available() -> bool:
    return Lunar is not None and Solar is not None


def _require_lunar() -> None:
    if not is_lunar_available():
        raise RuntimeError("农历功能需要安装 lunar-python：pip install lunar-python")


def _solar_term_month_number(month_zhi_index: int) -> int:
    """地支月序 → 节气月数（寅月=1，丑月=12）。"""
    return ((month_zhi_index + 10) % 12) + 1


def solar_term_components_from_datetime(dt: datetime) -> SolarTermComponents:
    """由公历时刻提取节气历数字分量（立春换年、节气换月）。"""
    _require_lunar()
    solar = Solar.fromYmdHms(
        dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second,
    )
    lunar = solar.getLunar()
    hour_idx = lunar.getTimeZhiIndex() + 1
    return SolarTermComponents(
        year=lunar.getYear(),
        month=_solar_term_month_number(lunar.getMonthZhiIndexExact()),
        day=lunar.getDay(),
        hour=hour_idx,
        label=lunar.toString(),
        year_gan_zhi=lunar.getYearInGanZhiExact(),
        month_gan_zhi=lunar.getMonthInGanZhiExact(),
        hour_zhi=_TIME_ZHI[hour_idx - 1],
    )


def solar_datetime_to_lunar(dt: datetime) -> LunarComponents:
    """将公历时刻转为农历分量（含时辰序号 1–12）。"""
    _require_lunar()
    local = dt
    solar = Solar.fromYmdHms(
        local.year, local.month, local.day, local.hour, local.minute, local.second,
    )
    lunar = solar.getLunar()
    month = lunar.getMonth()
    return LunarComponents(
        year=lunar.getYear(),
        month=abs(month),
        day=lunar.getDay(),
        hour=lunar.getTimeZhiIndex() + 1,
        label=lunar.toString(),
        is_leap_month=month < 0,
    )


def lunar_datetime_to_components(
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
) -> LunarComponents:
    """由农历年月日时分构建分量。"""
    _require_lunar()
    lunar = Lunar.fromYmdHms(year, month, day, hour, minute, 0)
    m = lunar.getMonth()
    return LunarComponents(
        year=lunar.getYear(),
        month=abs(m),
        day=lunar.getDay(),
        hour=lunar.getTimeZhiIndex() + 1,
        label=lunar.toString(),
        is_leap_month=m < 0,
    )


def parse_lunar_datetime_input(raw: str) -> tuple[int, int, int, int, int] | None:
    """
    解析农历日期时间字符串，返回 (年, 月, 日, 时, 分)。
    支持格式：YYYY-MM-DD HH:MM、YYYY-MM-DD、YYYY/MM/DD HH:MM
    """
    raw = raw.strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y-%m-%d"):
        try:
            naive = datetime.strptime(raw, fmt)
            return naive.year, naive.month, naive.day, naive.hour, naive.minute
        except ValueError:
            continue
    return None


def _format_solar_term_label(st: SolarTermComponents) -> str:
    return f"{st.year_gan_zhi}年 {st.month_gan_zhi}月 {st.label} {st.hour_zhi}时"


def resolve_time_divination_components(
    dt: datetime,
    *,
    calendar_mode: CalendarMode = "solar",
    lunar_input: str | None = None,
    tz: TimezoneInfo | None = None,
    longitude: float | None = None,
    use_true_solar: bool = True,
) -> ResolvedTimeComponents:
    """
    解析时间起卦用的年月日时数字与描述。

    公历模式（默认）：用户输入公历，算卦使用节气历数字 + 可选真太阳时校正。
    农历模式：用户显式输入农历数字，沿用阴历分量（仍可做真太阳时校正）。
    """
    if calendar_mode == "lunar":
        _require_lunar()
        if lunar_input:
            parsed = parse_lunar_datetime_input(lunar_input)
            if parsed is None:
                raise ValueError("农历时间格式无效，请使用如 2026-05-10 14:30")
            y, m, d, h, mi = parsed
            comp = lunar_datetime_to_components(y, m, d, h, mi)
            user_note = f"用户农历输入：{lunar_input}"
        else:
            comp = solar_datetime_to_lunar(dt)
            user_note = f"用户公历：{dt.strftime('%Y-%m-%d %H:%M')}"

        calc_dt = dt
        true_solar_note = ""
        if tz is not None:
            calc_dt, true_solar_note = to_true_solar(
                dt, tz, longitude, enabled=use_true_solar,
            )
            if not lunar_input:
                comp = solar_datetime_to_lunar(calc_dt)

        leap = "（闰月）" if comp.is_leap_month else ""
        calc_note = (
            f"农历起卦数：年{comp.year} 月{comp.month} 日{comp.day} 时{comp.hour}"
            f"（{comp.label}{leap}）"
        )
        return ResolvedTimeComponents(
            year=comp.year,
            month=comp.month,
            day=comp.day,
            hour=comp.hour,
            user_input_note=user_note,
            calculation_note=calc_note,
            true_solar_note=true_solar_note,
        )

    # 公历输入 → 节气历算卦
    if tz is None:
        raise ValueError("公历节气历起卦需要时区信息")

    user_note = f"用户公历：{format_datetime_with_tz(dt, tz)}"
    calc_dt, true_solar_note = to_true_solar(dt, tz, longitude, enabled=use_true_solar)
    st = solar_term_components_from_datetime(calc_dt)
    calc_note = (
        f"节气历（算卦口径）：{_format_solar_term_label(st)}；"
        f"起卦数 年{st.year}+月{st.month}+日{st.day}+时{st.hour}"
    )
    return ResolvedTimeComponents(
        year=st.year,
        month=st.month,
        day=st.day,
        hour=st.hour,
        user_input_note=user_note,
        calculation_note=calc_note,
        true_solar_note=true_solar_note,
    )