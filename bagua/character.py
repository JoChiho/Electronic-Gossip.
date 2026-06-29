"""汉字起卦（测字 / 字课）纯逻辑。"""

from __future__ import annotations

from bagua.data import METHOD_LABELS
from bagua.divination import divinate_by_numbers
from bagua.stroke_data import (
    STROKE_MODES,
    format_stroke_preview,
    get_stroke_count,
)

CHARACTER_STRATEGIES = ("auto", "first_two", "first_three", "total")
STRATEGY_LABELS = {
    "auto": "自动（1字拆两数 / 2字 / 3字+）",
    "first_two": "前两字笔画",
    "first_three": "前三字笔画",
    "total": "总笔画 + 字数",
}


def extract_han_chars(text: str) -> list[str]:
    """提取文本中的 CJK 统一汉字（忽略空格与标点）。"""
    return [ch for ch in text if "\u4e00" <= ch <= "\u9fff"]


def resolve_strokes(text: str, *, stroke_mode: str = "kangxi") -> tuple[list[str], list[int], list[str]]:
    chars = extract_han_chars(text)
    if not chars:
        raise ValueError("请输入至少一个汉字")
    if stroke_mode not in STROKE_MODES:
        raise ValueError(f"笔画口径须为 {STROKE_MODES}")

    strokes: list[int] = []
    sources: list[str] = []
    for ch in chars:
        count, src = get_stroke_count(ch, stroke_mode)
        strokes.append(count)
        sources.append(src)
    return chars, strokes, sources


def character_to_numbers(
    text: str,
    *,
    strategy: str = "auto",
    stroke_mode: str = "kangxi",
) -> tuple[int, int, int | None, list[str], list[int], list[str], str]:
    """
    将汉字文本转为梅花报数三整数。

    返回 (n1, n2, n3, chars, strokes, sources, strategy_note)。
    """
    if strategy not in CHARACTER_STRATEGIES:
        raise ValueError(f"起卦策略须为 {CHARACTER_STRATEGIES}")

    chars, strokes, sources = resolve_strokes(text, stroke_mode=stroke_mode)
    effective = strategy
    if strategy == "auto":
        if len(chars) == 1:
            effective = "single"
        elif len(chars) == 2:
            effective = "first_two"
        else:
            effective = "first_three"

    if effective == "single":
        s = strokes[0]
        n1, n2, n3 = s, s + 1, None
        note = f"单字测字：上卦取笔画{s}，下卦取笔画+1={s + 1}，动爻取({s}+{s + 1})"
    elif effective == "first_two":
        if len(chars) < 2:
            raise ValueError("前两字策略需要至少 2 个汉字")
        n1, n2, n3 = strokes[0], strokes[1], None
        note = f"前两字：{chars[0]}({strokes[0]})→上卦，{chars[1]}({strokes[1]})→下卦"
    elif effective == "first_three":
        if len(chars) < 3:
            raise ValueError("前三字策略需要至少 3 个汉字")
        n1, n2, n3 = strokes[0], strokes[1], strokes[2]
        note = (
            f"前三字：{chars[0]}({strokes[0]})→上卦，"
            f"{chars[1]}({strokes[1]})→下卦，{chars[2]}({strokes[2]})→动爻"
        )
    elif effective == "total":
        total = sum(strokes)
        n1, n2, n3 = total, len(chars), None
        note = f"总笔画{total}+字数{len(chars)}：总笔画→上卦，字数→下卦"
    else:
        raise ValueError(f"未知策略：{effective}")

    return n1, n2, n3, chars, strokes, sources, note


def parse_character_input(raw: str) -> str | None:
    text = raw.strip()
    if not text:
        return None
    if not extract_han_chars(text):
        return None
    return text


def divinate_by_character(
    text: str,
    *,
    strategy: str = "auto",
    stroke_mode: str = "kangxi",
) -> tuple[list[int], str]:
    n1, n2, n3, chars, strokes, sources, strategy_note = character_to_numbers(
        text,
        strategy=strategy,
        stroke_mode=stroke_mode,
    )
    values, number_desc = divinate_by_numbers(n1, n2, n3)
    formula = number_desc.split("梅花报数：", 1)[-1].rstrip("）")

    stroke_preview = format_stroke_preview(chars, strokes, sources, stroke_mode)
    strategy_label = STRATEGY_LABELS.get(strategy, strategy)
    text_clean = "".join(chars)
    detail = (
        f"字课「{text_clean}」；{stroke_preview}；策略{strategy_label}；"
        f"{strategy_note}；{formula}"
    )
    method_desc = f"{METHOD_LABELS['character']}（{detail}）"
    return values, method_desc