"""CLI/GUI 共用的用户偏好读写辅助。"""

from __future__ import annotations

from bagua.divination import parse_coin_input
from bagua.divination.registry import METHOD_CLI_NUM_TO_KEY, METHOD_KEY_TO_CLI_NUM

METHOD_NUM_TO_KEY = METHOD_CLI_NUM_TO_KEY
METHOD_KEY_TO_NUM = METHOD_KEY_TO_CLI_NUM


def normalize_method(method: str, *, default: str = "coin") -> str:
    if method in METHOD_KEY_TO_NUM:
        return method
    return default


def stored_coin_tosses_to_points(stored: list[list[str]] | None) -> list[list[int]] | None:
    """将配置中的 1/2 铜钱输入转为起卦点数（3/2）。"""
    if not stored or len(stored) != 6:
        return None
    tosses: list[list[int]] = []
    for row in stored:
        if len(row) != 3:
            return None
        raw = " ".join(row)
        points = parse_coin_input(raw)
        if points is None:
            return None
        tosses.append(points)
    return tosses


def points_to_stored_coin_tosses(tosses: list[list[int]]) -> list[list[str]]:
    """起卦点数写回配置格式。"""
    rows: list[list[str]] = []
    for toss in tosses:
        rows.append(["1" if p == 3 else "2" for p in toss])
    return rows


def format_stored_coin_tosses(stored: list[list[str]] | None) -> str:
    if not stored:
        return ""
    parts: list[str] = []
    for i, row in enumerate(stored, start=1):
        if len(row) == 3:
            parts.append(f"第{i}爻 {' '.join(row)}")
    return "；".join(parts)