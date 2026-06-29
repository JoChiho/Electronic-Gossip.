"""AI 解读提示词生成。"""

from __future__ import annotations

from bagua.hexagram_texts import get_hexagram_summary
from bagua.models import HexagramInfo, UserContext
from bagua.timezone import TimezoneInfo, format_utc_offset
from bagua.yao_texts import format_yao_texts_block


def _format_birth_block(
    birth_datetime: str,
    tz: TimezoneInfo,
    *,
    true_solar_note: str = "",
) -> str:
    if not birth_datetime.strip():
        return "（未提供）"
    offset = format_utc_offset(tz.tzinfo)
    fallback = " [固定偏移回退]" if tz.using_fallback else ""
    base = f"{birth_datetime}（出生时区 {tz.region_label}, {tz.iana_name}, {offset}{fallback}）"
    if true_solar_note:
        return f"{base}\n  {true_solar_note}"
    return base


def _hexagram_text_line(hexagram: HexagramInfo, *, include_texts: bool) -> str | None:
    if not include_texts:
        return None
    summary = get_hexagram_summary(hexagram.name)
    if not summary:
        return None
    return f"  卦辞摘要：{summary}"


def _ti_yong_lines(hexagram: HexagramInfo) -> list[str]:
    """梅花易数体用：动爻所在卦为用，另一卦为体。"""
    if not hexagram.changing_positions:
        return [
            "  体用（静卦）：下卦为内、上卦为外；可以下卦为体、上卦为用作参考。",
        ]
    lines: list[str] = []
    for pos in hexagram.changing_positions:
        if pos <= 3:
            lines.append(
                f"  第{pos}爻动：下卦（{hexagram.lower_trigram['name']}）为用，"
                f"上卦（{hexagram.upper_trigram['name']}）为体。",
            )
        else:
            lines.append(
                f"  第{pos}爻动：上卦（{hexagram.upper_trigram['name']}）为用，"
                f"下卦（{hexagram.lower_trigram['name']}）为体。",
            )
    if len(hexagram.changing_positions) > 1:
        lines.append("  多爻动：以变爻为机，兼参本卦与之卦，勿机械套用单一体用。")
    return lines


def _method_guidance(method: str) -> list[str]:
    if "铜钱法" in method:
        return [
            "【方法论·铜钱法】",
            "自下而上六次投掷，三钱法：阳面计3、阴面计2，和为6/7/8/9。",
            "6老阴、9老阳为变爻；7少阳、8少阴为静爻。卦象由投掷结果独立生成，",
            "与八字无演算关系。",
        ]
    if "时间起卦" in method:
        return [
            "【方法论·梅花易数时间卦】",
            "上卦＝(年+月+日) mod 8（余0取坤8）；下卦＝(年+月+日+时) mod 8；",
            "动爻＝(年+月+日+时) mod 6（余0取上爻6）。",
            "公历模式已换算节气历（立春换年、寅月起月）并校正真太阳时；",
            "农历模式沿用用户输入的阴历数字。",
        ]
    if "随机起卦" in method:
        return [
            "【方法论·随机卦】",
            "随机生成六爻，仅作参考；解读宜侧重卦象象征与问题本身，",
            "不宜过度附会术数细节。",
        ]
    if "数字起卦" in method:
        return [
            "【方法论·梅花报数】",
            "报数两数：上卦＝第一数 mod 8（余0取坤8），下卦＝第二数 mod 8；",
            "动爻＝(第一数+第二数) mod 6（余0取上爻6）。",
            "报数三数：上卦、下卦同上；动爻＝第三数 mod 6。",
            "体用规则同梅花易数：动爻所在卦为用，另一卦为体。",
        ]
    if "手动选卦" in method:
        return [
            "【方法论·手动选卦】",
            "用户直接指定上卦、下卦（乾1…坤8）与可选动爻；",
            "无动爻时六爻均为静爻（7少阳/8少阴），本卦与之卦相同。",
            "有动爻时按老阴6、老阳9标记变爻，并生成之卦。",
        ]
    if "蓍草法" in method:
        return [
            "【方法论·大衍蓍草】",
            "本卦由大衍筮法程序模拟生成（非实体蓍草演算）。",
            "五十蓍草取一，用四十九；每爻三变（分二、挂一、揲四、归奇），",
            "三变余数 24/28/32/36 对应爻值 6/7/8/9；",
            "大衍概率为 6(1/16)、7(5/16)、8(7/16)、9(3/16)，与三钱法略有不同。",
        ]
    if "汉字起卦" in method:
        return [
            "【方法论·梅花字课】",
            "以汉字笔画数起卦（默认康熙字典笔画，可选简体）；",
            "未收录字以 Unicode 码点回退取数（见 method_desc 标注）。",
            "单字：上卦＝笔画，下卦＝笔画+1，动爻＝两数之和 mod 6；",
            "两字/三字与梅花报数同法；总笔画策略以总笔画与字数起卦。",
        ]
    return []


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
    if include_texts:
        lines.extend(
            format_yao_texts_block(
                hexagram.name,
                highlight_positions=set(hexagram.changing_positions),
            )
        )
    return "\n".join(lines)


def _interpretation_requirements(hexagram: HexagramInfo) -> str:
    common = (
        "八字、出生时间仅作背景参考，**不参与卦象演算**；"
        "勿将八字五行与卦象生克混为一谈。"
    )
    if hexagram.has_changing and hexagram.changed_hexagram:
        return (
            "【解读要求】\n"
            "1. 先述本卦卦义，分析上下卦互动及六爻态势，**变爻为事态机枢**须重点阐释。\n"
            "2. 说明体用关系（见上），体卦主现状、用卦主动变之机。\n"
            "3. 结合之卦，述发展趋向：何者将变、何者可守。\n"
            "4. 卦辞摘要与所附爻辞原文供参，解读时请引用并阐释，勿捏造经文。\n"
            f"5. {common}\n"
            "6. 针对用户问题给出明确、可执行的建议（工作、人际、决策等现代场景）。\n"
            "7. 语言简洁专业，避免空泛玄学，注重实际指导价值。\n"
            "8. 结尾用一两句话总结核心启示。"
        )
    return (
        "【解读要求】\n"
        "1. 阐释本卦卦义及上下卦关系，结合六爻分析当前态势（静卦无变爻）。\n"
        "2. 说明体用参考（见上），以卦象整体气象为主。\n"
        "3. 卦辞摘要与所附六爻爻辞原文供参，勿捏造经文。\n"
        f"4. {common}\n"
        "5. 针对用户问题给出明确、可执行的建议（工作、人际、决策等现代场景）。\n"
        "6. 语言简洁专业，避免空泛玄学，注重实际指导价值。\n"
        "7. 结尾用一两句话总结核心启示。"
    )


def generate_ai_prompt(
    ctx: UserContext,
    method: str,
    divination_time: str,
    hexagram: HexagramInfo,
    *,
    time_uses_solar_term: bool = False,
    bazi_true_solar_note: str = "",
) -> str:
    question_text = ctx.question.strip() or "（未指定具体问题，请做综合解读）"
    bazi_text = ctx.bazi.strip() or "（未提供）"
    birth_text = _format_birth_block(
        ctx.birth_datetime,
        ctx.birth_tz,
        true_solar_note=bazi_true_solar_note,
    )

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
            "（说明：用户以公历习惯输入时刻；起卦计算已换算为节气历（立春换年、寅月起月）",
            "并校正真太阳时。年/月/日/时数字以节气历为准，勿将公历月日直接代入卦数。）",
        ]
    elif ctx.calendar_mode == "lunar":
        sections += [
            "",
            "（说明：起卦采用用户输入的农历年月日时数字，与公历节气历口径不同；",
            "解读时以起卦方法栏中的具体数字为准。）",
        ]
    sections += [
        "",
        "【起卦方法】",
        method,
    ]
    sections += [""] + _method_guidance(method)
    sections += [
        "",
        "【出生时间】",
        birth_text,
        "",
        "【生辰八字】",
        bazi_text,
        "",
        format_hexagram_block(hexagram, "本卦", include_texts=ctx.include_hexagram_texts),
        "",
        "【体用】",
        *_ti_yong_lines(hexagram),
    ]

    if hexagram.has_changing and hexagram.changed_hexagram:
        sections += [
            "",
            format_hexagram_block(
                hexagram.changed_hexagram,
                "之卦（变卦）",
                include_texts=ctx.include_hexagram_texts,
            ),
        ]

    sections += ["", _interpretation_requirements(hexagram)]
    sections.append("════════════════════════════════════════")
    return "\n".join(sections)