"""AI 解读提示词生成。"""

from __future__ import annotations

from bagua.hexagram_texts import get_hexagram_summary
from bagua.models import HexagramInfo, UserContext
from bagua.timezone import TimezoneInfo, format_utc_offset


def _format_birth_block(birth_datetime: str, tz: TimezoneInfo) -> str:
    if not birth_datetime.strip():
        return "（未提供）"
    offset = format_utc_offset(tz.tzinfo)
    fallback = " [固定偏移回退]" if tz.using_fallback else ""
    return f"{birth_datetime}（{tz.region_label}, {tz.iana_name}, {offset}{fallback}）"


def _hexagram_text_line(hexagram: HexagramInfo, *, include_texts: bool) -> str | None:
    if not include_texts:
        return None
    summary = get_hexagram_summary(hexagram.name)
    if not summary:
        return None
    return f"  卦辞摘要：{summary}"


def format_hexagram_block(hexagram: HexagramInfo, label: str, *, include_texts: bool = False) -> str:
    upper, lower = hexagram.upper_trigram, hexagram.lower_trigram
    lines = [
        f"【{label}】{hexagram.name}",
        f"  上卦：{upper['name']} {upper['symbol']}",
        f"  下卦：{lower['name']} {lower['symbol']}",
        "  六爻（自下而上）：",
    ]
    for yao in hexagram.yaos:
        graphic = "━━━━━━ 阳" if yao.is_yang else "────── 阴"
        if yao.is_changing:
            graphic += " [变爻]"
        lines.append(f"    {yao.position_name}：{graphic}  爻值{yao.value}（{yao.label}）")
    if hexagram.changing_positions:
        lines.append(f"  变爻位置：第 {', '.join(str(p) for p in hexagram.changing_positions)} 爻")
    text_line = _hexagram_text_line(hexagram, include_texts=include_texts)
    if text_line:
        lines.append(text_line)
    return "\n".join(lines)


def generate_ai_prompt(
    ctx: UserContext,
    method: str,
    divination_time: str,
    hexagram: HexagramInfo,
    *,
    time_uses_solar_term: bool = False,
) -> str:
    question_text = ctx.question.strip() or "（未指定具体问题，请做综合解读）"
    bazi_text = ctx.bazi.strip() or "（未提供）"
    birth_text = _format_birth_block(ctx.birth_datetime, ctx.tz)

    sections = [
        "你是一位精通《易经》的学者，同时具备现代心理学与决策分析素养。",
        "请根据以下起卦信息，从专业、实用、贴近现代生活的角度进行解读，并针对用户问题给出具体建议。",
        "",
        "════════════════════════════════════════",
        "【用户问题】",
        question_text,
        "",
        "【起卦时间】",
        divination_time,
    ]
    if time_uses_solar_term:
        sections += [
            "",
            "（说明：用户以公历习惯输入时刻；起卦计算已换算为节气历并校正真太阳时，",
            "请按节气历口径解读，勿将公历月日数字直接当作卦数。）",
        ]
    sections += [
        "",
        "【起卦方法】",
        method,
        "",
        "【出生时间】",
        birth_text,
        "",
        "【生辰八字】",
        bazi_text,
        "",
        format_hexagram_block(hexagram, "本卦", include_texts=ctx.include_hexagram_texts),
    ]

    if hexagram.has_changing and hexagram.changed_hexagram:
        sections += [
            "",
            format_hexagram_block(
                hexagram.changed_hexagram,
                "之卦（变卦）",
                include_texts=ctx.include_hexagram_texts,
            ),
            "",
            "【解读要求】\n"
            "1. 先阐释本卦卦义及上下卦关系，结合六爻（尤其变爻）分析当前态势。\n"
            "2. 若有之卦，说明事态发展趋势及变化方向。\n"
            "3. 结合用户出生时间与八字信息（如有）辅助分析。\n"
            "4. 针对用户问题给出明确、可执行的建议（工作、人际、决策等现代场景）。\n"
            "5. 语言简洁专业，避免空泛玄学，注重实际指导价值。\n"
            "6. 结尾用一两句话总结核心启示。",
        ]
    else:
        sections += [
            "",
            "【解读要求】\n"
            "1. 阐释本卦卦义及上下卦关系，结合六爻分析当前态势。\n"
            "2. 结合用户出生时间与八字信息（如有）辅助分析。\n"
            "3. 针对用户问题给出明确、可执行的建议（工作、人际、决策等现代场景）。\n"
            "4. 语言简洁专业，避免空泛玄学，注重实际指导价值。\n"
            "5. 结尾用一两句话总结核心启示。",
        ]

    sections.append("════════════════════════════════════════")
    return "\n".join(sections)