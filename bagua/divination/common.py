"""梅花易数与八卦组合的共用工具。"""

from __future__ import annotations

from bagua.data import TRIGRAMS


def meihua_trigram_number(n: int) -> int:
    r = n % 8
    return 8 if r == 0 else r


def meihua_changing_line(n: int) -> int:
    r = n % 6
    return 6 if r == 0 else r


def trigram_by_number(num: int) -> dict:
    return TRIGRAMS[num - 1]


def lines_from_trigrams(lower: dict, upper: dict, changing_line: int | None = None) -> list[int]:
    all_lines = list(lower["lines"]) + list(upper["lines"])
    values: list[int] = []
    for i, bit in enumerate(all_lines, start=1):
        if changing_line == i:
            values.append(9 if bit == 1 else 6)
        else:
            values.append(7 if bit == 1 else 8)
    return values