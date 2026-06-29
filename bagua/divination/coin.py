"""铜钱法起卦。"""

from __future__ import annotations

import random
import re
from typing import TYPE_CHECKING

from bagua.data import METHOD_LABELS

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