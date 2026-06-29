"""起卦纯逻辑（无终端 I/O）。"""

from __future__ import annotations

import random
import re
from datetime import datetime
from typing import TYPE_CHECKING

from bagua.data import METHOD_LABELS, TRIGRAMS
from bagua.lunar_util import (
    CalendarMode,
    ResolvedTimeComponents,
    resolve_time_divination_components,
)
from bagua.timezone import TimezoneInfo

if TYPE_CHECKING:
    from _random import Random


def parse_coin_input(raw: str) -> list[int] | None:
    """解析三枚硬币输入，返回点数列表（阳=3，阴=2）。"""
    tokens = re.split(r"[\s,，、]+", raw.strip())
    if len(tokens) != 3:
        return None
    points: list[int] = []
    for t in tokens:
        t = t.lower()
        if t in ("1", "正", "z", "yang", "y", "3"):
            points.append(3)
        elif t in ("2", "反", "f", "yin", "n"):
            points.append(2)
        else:
            return None
    if sum(points) not in (6, 7, 8, 9):
        return None
    return points


def tosses_to_yao_value(tosses: list[int]) -> int:
    if len(tosses) != 3 or sum(tosses) not in (6, 7, 8, 9):
        raise ValueError("每爻需要恰好三枚硬币，点数之和为 6/7/8/9")
    return sum(tosses)


def simulate_coin_toss(rng: Random | None = None) -> list[int]:
    r = rng or random
    return [r.choice([2, 3]) for _ in range(3)]


def coin_tosses_to_display(tosses: list[int]) -> str:
    return " ".join("1" if p == 3 else "2" for p in tosses)


def auto_coin_yao_values(rng: Random | None = None) -> list[int]:
    return [tosses_to_yao_value(simulate_coin_toss(rng)) for _ in range(6)]


def coin_yao_values_from_tosses(coin_tosses: list[list[int]]) -> list[int]:
    if len(coin_tosses) != 6:
        raise ValueError("铜钱法需要恰好六爻投掷结果")
    return [tosses_to_yao_value(toss) for toss in coin_tosses]


def divinate_coin(
    *,
    coin_tosses: list[list[int]] | None = None,
    coin_mode: str = "auto",
    rng: Random | None = None,
) -> tuple[list[int], str]:
    if coin_tosses is not None:
        values = coin_yao_values_from_tosses(coin_tosses)
        suffix = "自动模拟" if coin_mode == "auto" else "手动投掷"
    elif coin_mode == "auto":
        values = auto_coin_yao_values(rng)
        suffix = "自动模拟"
    else:
        raise ValueError("铜钱法手动模式需要提供 coin_tosses")
    return values, f"{METHOD_LABELS['coin']}（{suffix}）"


def _meihua_trigram_number(n: int) -> int:
    r = n % 8
    return 8 if r == 0 else r


def _meihua_changing_line(n: int) -> int:
    r = n % 6
    return 6 if r == 0 else r


def _trigram_by_number(num: int) -> dict:
    return TRIGRAMS[num - 1]


def _lines_from_trigrams(lower: dict, upper: dict, changing_line: int | None = None) -> list[int]:
    all_lines = list(lower["lines"]) + list(upper["lines"])
    values: list[int] = []
    for i, bit in enumerate(all_lines, start=1):
        if changing_line == i:
            values.append(9 if bit == 1 else 6)
        else:
            values.append(7 if bit == 1 else 8)
    return values


def divinate_by_time(
    dt: datetime,
    *,
    calendar_mode: CalendarMode = "solar",
    lunar_input: str | None = None,
    tz: TimezoneInfo | None = None,
    longitude: float | None = None,
    use_true_solar: bool = True,
) -> tuple[list[int], str, ResolvedTimeComponents]:
    resolved = resolve_time_divination_components(
        dt,
        calendar_mode=calendar_mode,
        lunar_input=lunar_input,
        tz=tz,
        longitude=longitude,
        use_true_solar=use_true_solar,
    )
    year, month, day, hour = resolved.year, resolved.month, resolved.day, resolved.hour

    upper_num = _meihua_trigram_number(year + month + day)
    lower_num = _meihua_trigram_number(year + month + day + hour)
    changing = _meihua_changing_line(year + month + day + hour)

    lower = _trigram_by_number(lower_num)
    upper = _trigram_by_number(upper_num)
    values = _lines_from_trigrams(lower, upper, changing)

    sum_ymd = year + month + day
    sum_ymdh = sum_ymd + hour
    formula = (
        f"年{year}+月{month}+日{day}={sum_ymd}→上卦{upper['name']}；"
        f"加时{hour}={sum_ymdh}→下卦{lower['name']}，动爻第{changing}爻"
    )
    mode_label = "农历" if calendar_mode == "lunar" else "公历输入·节气历算卦"
    detail = f"{resolved.user_input_note}；{resolved.calculation_note}；梅花易数：{formula}"
    if resolved.true_solar_note:
        detail = f"{detail}；{resolved.true_solar_note}"
    method_desc = f"{METHOD_LABELS['time']}（{mode_label}：{detail}）"
    return values, method_desc, resolved


def divinate_by_random(rng: Random | None = None) -> tuple[list[int], str]:
    r = rng or random
    return [r.choice([6, 7, 8, 9]) for _ in range(6)], METHOD_LABELS["random"]