"""数字起卦（梅花报数）。"""

from __future__ import annotations

import re

from bagua.data import METHOD_LABELS
from bagua.divination.common import (
    lines_from_trigrams,
    meihua_changing_line,
    meihua_trigram_number,
    trigram_by_number,
)


def parse_number_input(raw: str) -> list[int] | None:
    """解析 2～3 个正整数，用于梅花报数起卦。"""
    tokens = [t for t in re.split(r"[\s,，、]+", raw.strip()) if t]
    if len(tokens) not in (2, 3):
        return None
    numbers: list[int] = []
    for t in tokens:
        if not re.fullmatch(r"\d+", t):
            return None
        n = int(t)
        if n < 1:
            return None
        numbers.append(n)
    return numbers


def divinate_by_numbers(n1: int, n2: int, n3: int | None = None) -> tuple[list[int], str]:
    """梅花报数：两数动爻取 n1+n2，三数动爻取 n3。"""
    if n1 < 1 or n2 < 1 or (n3 is not None and n3 < 1):
        raise ValueError("报数须为正整数")

    upper_num = meihua_trigram_number(n1)
    lower_num = meihua_trigram_number(n2)
    upper = trigram_by_number(upper_num)
    lower = trigram_by_number(lower_num)

    if n3 is not None:
        changing = meihua_changing_line(n3)
        formula = (
            f"上卦{n1}%8={upper_num}→{upper['name']}；"
            f"下卦{n2}%8={lower_num}→{lower['name']}；"
            f"动爻{n3}%6=第{changing}爻"
        )
    else:
        changing = meihua_changing_line(n1 + n2)
        sum_n = n1 + n2
        formula = (
            f"上卦{n1}%8={upper_num}→{upper['name']}；"
            f"下卦{n2}%8={lower_num}→{lower['name']}；"
            f"动爻({n1}+{n2})={sum_n}，{sum_n}%6=第{changing}爻"
        )

    values = lines_from_trigrams(lower, upper, changing)
    method_desc = f"{METHOD_LABELS['number']}（梅花报数：{formula}）"
    return values, method_desc