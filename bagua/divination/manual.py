"""手动选卦。"""

from __future__ import annotations

import re

from bagua.data import METHOD_LABELS, TRIGRAMS, YAO_POSITIONS
from bagua.divination.common import lines_from_trigrams, trigram_by_number


def parse_trigram_index(raw: str) -> int | None:
    """解析八卦序号 1～8（乾1…坤8）。"""
    text = raw.strip()
    if not text:
        return None
    head = re.split(r"[\s,，、]+", text)[0]
    if re.fullmatch(r"[1-8]", head):
        return int(head)
    for i, tri in enumerate(TRIGRAMS, start=1):
        if text.startswith(tri["name"]) or head == tri["name"]:
            return i
    return None


def parse_manual_changing(raw: str | int | None) -> int | None:
    """解析动爻：0 / 空 / 无 → None（静卦）；1～6 为动爻位。"""
    if raw is None:
        return None
    if isinstance(raw, int):
        return None if raw == 0 else raw
    text = raw.strip()
    if not text or text in ("0", "无", "无（静卦）", "静卦", "none"):
        return None
    if re.fullmatch(r"[1-6]", text):
        return int(text)
    for i, name in enumerate(YAO_POSITIONS, start=1):
        if text == name or text.endswith(name):
            return i
    return None


def divinate_manual(
    upper_idx: int,
    lower_idx: int,
    changing_line: int | None = None,
) -> tuple[list[int], str]:
    """手动选定上下卦与可选动爻；无动爻时六爻均为静爻（7/8）。"""
    if not 1 <= upper_idx <= 8 or not 1 <= lower_idx <= 8:
        raise ValueError("八卦序号须在 1～8（乾1…坤8）")
    if changing_line is not None and not 1 <= changing_line <= 6:
        raise ValueError("动爻须在 1～6")

    upper = trigram_by_number(upper_idx)
    lower = trigram_by_number(lower_idx)
    values = lines_from_trigrams(lower, upper, changing_line)

    if changing_line is None:
        changing_desc = "无动爻（全静卦）"
    else:
        changing_desc = f"动爻第{changing_line}爻（{YAO_POSITIONS[changing_line - 1]}）"
    detail = (
        f"上卦{upper_idx} {upper['name']}{upper['symbol']}；"
        f"下卦{lower_idx} {lower['name']}{lower['symbol']}；{changing_desc}"
    )
    method_desc = f"{METHOD_LABELS['manual']}（{detail}）"
    return values, method_desc