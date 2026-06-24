"""GUI 卦象文本格式化（纯函数，无 Tk 依赖）。"""

from __future__ import annotations

from bagua.models import HexagramInfo


def yao_line_text(yao) -> str:
    line = "━━━━━━" if yao.is_yang else "──────"
    if yao.is_changing:
        line += " ○变" if yao.is_yang else " ×变"
    return line


def format_hexagram_display(hexagram: HexagramInfo) -> str:
    upper, lower = hexagram.upper_trigram, hexagram.lower_trigram
    lines = [
        f"【{hexagram.name}】",
        f"上卦：{upper['symbol']} {upper['name']}",
        f"下卦：{lower['symbol']} {lower['name']}",
        "",
        "六爻（自下而上）：",
    ]
    for yao in hexagram.yaos:
        lines.append(
            f"  {yao.position_name}  爻值{yao.value}（{yao.label}）  {yao_line_text(yao)}"
        )
    if hexagram.has_changing and hexagram.changed_hexagram:
        chg = hexagram.changed_hexagram
        lines += [
            "",
            f"变爻：第 {', '.join(str(p) for p in hexagram.changing_positions)} 爻",
            f"之卦：{chg.name}（{chg.upper_trigram['symbol']}{chg.upper_trigram['name']} / "
            f"{chg.lower_trigram['symbol']}{chg.lower_trigram['name']}）",
        ]
    return "\n".join(lines)