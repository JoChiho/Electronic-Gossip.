#!/usr/bin/env python3
"""
bagua — 极简易经八卦占卜 CLI 工具

起卦 + 生成可复制给大模型的结构化解读提示词。
仅供娱乐参考，不调用任何外部 AI API。
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

# ---------------------------------------------------------------------------
# 八卦与六十四卦数据
# ---------------------------------------------------------------------------

# 索引顺序与梅花易数数理一致：1乾 2兑 3离 4震 5巽 6坎 7艮 8坤
TRIGRAMS: list[dict] = [
    {"name": "乾", "symbol": "☰", "lines": (1, 1, 1)},
    {"name": "兑", "symbol": "☱", "lines": (1, 1, 0)},
    {"name": "离", "symbol": "☲", "lines": (1, 0, 1)},
    {"name": "震", "symbol": "☳", "lines": (1, 0, 0)},
    {"name": "巽", "symbol": "☴", "lines": (0, 1, 1)},
    {"name": "坎", "symbol": "☵", "lines": (0, 1, 0)},
    {"name": "艮", "symbol": "☶", "lines": (0, 0, 1)},
    {"name": "坤", "symbol": "☷", "lines": (0, 0, 0)},
]

# 六十四卦名 [上卦索引][下卦索引]
HEXAGRAM_NAMES: list[list[str]] = [
    ["乾为天", "天泽履", "天火同人", "天雷无妄", "天风姤", "天水讼", "天山遁", "天地否"],
    ["泽天夬", "兑为泽", "泽火革", "泽雷随", "泽风大过", "泽水困", "泽山咸", "泽地萃"],
    ["火天大有", "火泽睽", "离为火", "火雷噬嗑", "火风鼎", "火水未济", "火山旅", "火地晋"],
    ["雷天大壮", "雷泽归妹", "雷火丰", "震为雷", "雷风恒", "雷水解", "雷山小过", "雷地豫"],
    ["风天小畜", "风泽中孚", "风火家人", "风雷益", "巽为风", "风水涣", "风山渐", "风地观"],
    ["水天需", "水泽节", "水火既济", "水雷屯", "水风井", "坎为水", "水山蹇", "水地比"],
    ["山天大畜", "山泽损", "山火贲", "山雷颐", "山风蛊", "山水蒙", "艮为山", "山地剥"],
    ["地天泰", "地泽临", "地火明夷", "地雷复", "地风升", "地水师", "地山谦", "坤为地"],
]

YAO_POSITIONS = ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"]
YAO_VALUE_NAMES = {6: "老阴", 7: "少阳", 8: "少阴", 9: "老阳"}

METHOD_LABELS = {
    "coin": "铜钱法",
    "time": "时间起卦",
    "random": "随机起卦",
}

RECORDS_DIR = Path.home() / ".bagua" / "records"

console = Console()


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class YaoInfo:
    """单爻信息（自下而上编号 1–6）。"""

    position: int
    value: int  # 6 / 7 / 8 / 9
    is_yang: bool
    is_changing: bool

    @property
    def label(self) -> str:
        return YAO_VALUE_NAMES[self.value]

    @property
    def position_name(self) -> str:
        return YAO_POSITIONS[self.position - 1]


@dataclass
class HexagramInfo:
    """卦象信息。"""

    name: str
    upper_trigram: dict
    lower_trigram: dict
    yaos: list[YaoInfo]
    changing_positions: list[int] = field(default_factory=list)
    changed_hexagram: HexagramInfo | None = None

    @property
    def has_changing(self) -> bool:
        return bool(self.changing_positions)


@dataclass
class DivinationRecord:
    """一次占卜的完整记录。"""

    question: str
    bazi: str
    method: str
    divination_time: str
    hexagram: HexagramInfo
    prompt: str


# ---------------------------------------------------------------------------
# 卦象计算
# ---------------------------------------------------------------------------

def _lines_to_trigram(lines: tuple[int, int, int]) -> dict:
    for tri in TRIGRAMS:
        if tri["lines"] == lines:
            return tri
    raise ValueError(f"无效三爻: {lines}")


def _yao_value_to_line(value: int) -> tuple[bool, bool]:
    """爻值 → (是否为阳爻, 是否为变爻)。"""
    if value == 6:
        return False, True
    if value == 7:
        return True, False
    if value == 8:
        return False, False
    if value == 9:
        return True, True
    raise ValueError(f"无效爻值: {value}")


def _build_hexagram(yao_values: list[int]) -> HexagramInfo:
    """由六个爻值（初爻→上爻）构建卦象。"""
    if len(yao_values) != 6:
        raise ValueError("需要恰好六个爻值")

    yaos: list[YaoInfo] = []
    binary: list[int] = []
    changing: list[int] = []

    for i, val in enumerate(yao_values, start=1):
        is_yang, is_changing = _yao_value_to_line(val)
        yaos.append(YaoInfo(position=i, value=val, is_yang=is_yang, is_changing=is_changing))
        binary.append(1 if is_yang else 0)
        if is_changing:
            changing.append(i)

    lower = _lines_to_trigram(tuple(binary[0:3]))
    upper = _lines_to_trigram(tuple(binary[3:6]))
    name = HEXAGRAM_NAMES[TRIGRAMS.index(upper)][TRIGRAMS.index(lower)]

    hexagram = HexagramInfo(
        name=name,
        upper_trigram=upper,
        lower_trigram=lower,
        yaos=yaos,
        changing_positions=changing,
    )

    if changing:
        changed_binary = []
        for y in yaos:
            if y.is_changing:
                changed_binary.append(0 if y.is_yang else 1)
            else:
                changed_binary.append(1 if y.is_yang else 0)
        changed_lower = _lines_to_trigram(tuple(changed_binary[0:3]))
        changed_upper = _lines_to_trigram(tuple(changed_binary[3:6]))
        changed_name = HEXAGRAM_NAMES[TRIGRAMS.index(changed_upper)][TRIGRAMS.index(changed_lower)]
        hexagram.changed_hexagram = HexagramInfo(
            name=changed_name,
            upper_trigram=changed_upper,
            lower_trigram=changed_lower,
            yaos=yaos,  # 保留原爻值供参考
            changing_positions=[],
        )

    return hexagram


def _meihua_trigram_number(n: int) -> int:
    """梅花易数取卦：余 0 则为 8（坤）。"""
    r = n % 8
    return 8 if r == 0 else r


def _meihua_changing_line(n: int) -> int:
    """动爻位置（1–6），余 0 则为 6。"""
    r = n % 6
    return 6 if r == 0 else r


def _trigram_by_number(num: int) -> dict:
    return TRIGRAMS[num - 1]


def _lines_from_trigrams(lower: dict, upper: dict, changing_line: int | None = None) -> list[int]:
    """由上下卦构建六爻值；若有动爻则标记为老阴/老阳。"""
    all_lines = list(lower["lines"]) + list(upper["lines"])
    values: list[int] = []
    for i, bit in enumerate(all_lines, start=1):
        if changing_line == i:
            values.append(9 if bit == 1 else 6)
        else:
            values.append(7 if bit == 1 else 8)
    return values


# ---------------------------------------------------------------------------
# 起卦方式
# ---------------------------------------------------------------------------

def divinate_by_coin() -> tuple[list[int], str]:
    """铜钱法：每爻投掷三枚硬币，共六次。"""
    console.print("\n[bold cyan]铜钱法起卦[/bold cyan]")
    console.print("每爻输入三枚硬币结果，[green]正[/green]=阳面，[yellow]反[/yellow]=阴面")
    console.print("示例：[green]正 反 正[/green]  或  [green]z f z[/green]\n")

    yao_values: list[int] = []
    for pos in range(1, 7):
        while True:
            raw = console.input(
                f"[bold]第 {pos} 爻[/bold]（{YAO_POSITIONS[pos - 1]}）三枚硬币 [正/反，空格分隔]: "
            ).strip()
            coins = _parse_coin_input(raw)
            if coins is None:
                console.print("[red]格式错误，请输入三个「正」或「反」[/red]")
                continue
            total = sum(coins)
            val = total  # 6 / 7 / 8 / 9
            yao_values.append(val)
            console.print(
                f"  → 爻值 [bold]{val}[/bold]（{YAO_VALUE_NAMES[val]}）\n"
            )
            break

    return yao_values, METHOD_LABELS["coin"]


def _parse_coin_input(raw: str) -> list[int] | None:
    """解析硬币输入，返回三枚硬币点数列表（正=3，反=2）。"""
    tokens = re.split(r"[\s,，、]+", raw.strip())
    if len(tokens) != 3:
        return None
    points: list[int] = []
    for t in tokens:
        t = t.lower()
        if t in ("正", "z", "yang", "y", "3"):
            points.append(3)
        elif t in ("反", "f", "yin", "n", "2"):
            points.append(2)
        else:
            return None
    if sum(points) not in (6, 7, 8, 9):
        return None
    return points


def divinate_by_time(dt: datetime | None = None) -> tuple[list[int], str]:
    """时间起卦（梅花易数）。"""
    if dt is None:
        dt = datetime.now()

    # 梅花易数常用农历数，此处用公历数字简化（年月日时）
    year = dt.year
    month = dt.month
    day = dt.day
    hour = (dt.hour // 2) % 12 + 1  # 时辰 1–12

    upper_num = _meihua_trigram_number(year + month + day)
    lower_num = _meihua_trigram_number(year + month + day + hour)
    changing = _meihua_changing_line(year + month + day + hour)

    lower = _trigram_by_number(lower_num)
    upper = _trigram_by_number(upper_num)
    values = _lines_from_trigrams(lower, upper, changing)

    detail = (
        f"年{year} + 月{month} + 日{day} = {year + month + day} → 上卦 {upper['name']}; "
        f"加时辰{hour} = {year + month + day + hour} → 下卦 {lower['name']}，动爻第{changing}爻"
    )
    return values, f"{METHOD_LABELS['time']}（{detail}）"


def divinate_by_random() -> tuple[list[int], str]:
    """随机起卦：直接生成六个爻值。"""
    values = [random.choice([6, 7, 8, 9]) for _ in range(6)]
    return values, METHOD_LABELS["random"]


def _parse_datetime_input(raw: str) -> datetime | None:
    """解析用户输入的时间字符串。"""
    raw = raw.strip()
    if not raw:
        return None
    for fmt in (
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# 显示
# ---------------------------------------------------------------------------

def _yao_line_display(yao: YaoInfo) -> Text:
    """渲染单条爻的图形。"""
    if yao.is_yang:
        line = Text("━━━━━━", style="bold white")
    else:
        line = Text("──────", style="white")

    if yao.is_changing:
        mark = Text(" ○ 变", style="bold yellow") if yao.is_yang else Text(" × 变", style="bold yellow")
        line.append(mark)
    return line


def display_hexagram(hexagram: HexagramInfo, title: str = "卦象") -> None:
    """在终端展示卦象。"""
    upper = hexagram.upper_trigram
    lower = hexagram.lower_trigram

    console.print()
    console.print(
        Panel(
            f"[bold magenta]{hexagram.name}[/bold magenta]",
            title=f"[bold]{title}[/bold]",
            border_style="magenta",
            box=box.ROUNDED,
        )
    )

    tri_table = Table(show_header=False, box=None, padding=(0, 2))
    tri_table.add_column("位置", style="dim")
    tri_table.add_column("卦象")
    tri_table.add_row("上卦", f"{upper['symbol']} [bold]{upper['name']}[/bold]")
    tri_table.add_row("下卦", f"{lower['symbol']} [bold]{lower['name']}[/bold]")
    console.print(tri_table)
    console.print()

    yao_table = Table(title="六爻（自下而上）", box=box.SIMPLE_HEAD, show_lines=True)
    yao_table.add_column("爻位", style="cyan", justify="center")
    yao_table.add_column("爻值", justify="center")
    yao_table.add_column("性质", justify="center")
    yao_table.add_column("图形", justify="left")

    for yao in hexagram.yaos:
        yao_table.add_row(
            yao.position_name,
            str(yao.value),
            yao.label,
            _yao_line_display(yao),
        )
    console.print(yao_table)

    if hexagram.has_changing and hexagram.changed_hexagram:
        chg = hexagram.changed_hexagram
        console.print()
        console.print(
            f"[yellow]变爻[/yellow]：第 {', '.join(str(p) for p in hexagram.changing_positions)} 爻 "
            f"→ 之卦 [bold]{chg.name}[/bold] "
            f"（{chg.upper_trigram['symbol']}{chg.upper_trigram['name']} / "
            f"{chg.lower_trigram['symbol']}{chg.lower_trigram['name']}）"
        )


# ---------------------------------------------------------------------------
# AI 提示词生成
# ---------------------------------------------------------------------------

def _format_yao_detail(yao: YaoInfo) -> str:
    yang_yin = "阳" if yao.is_yang else "阴"
    changing = "，变爻" if yao.is_changing else ""
    return f"{yao.position_name}：{yao.value}（{yao.label}，{yang_yin}{changing}）"


def _format_hexagram_block(hexagram: HexagramInfo, label: str) -> str:
    upper = hexagram.upper_trigram
    lower = hexagram.lower_trigram
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
    return "\n".join(lines)


def generate_ai_prompt(
    question: str,
    bazi: str,
    method: str,
    divination_time: str,
    hexagram: HexagramInfo,
) -> str:
    """生成可复制给大模型的结构化解读提示词。"""
    bazi_text = bazi.strip() if bazi.strip() else "（未提供）"
    question_text = question.strip() if question.strip() else "（未指定具体问题，请做综合解读）"

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
        "",
        "【起卦方法】",
        method,
        "",
        "【生辰八字】",
        bazi_text,
        "",
        _format_hexagram_block(hexagram, "本卦"),
    ]

    if hexagram.has_changing and hexagram.changed_hexagram:
        sections.append("")
        sections.append(_format_hexagram_block(hexagram.changed_hexagram, "之卦（变卦）"))
        sections.append("")
        sections.append(
            "【解读要求】\n"
            "1. 先阐释本卦卦义及上下卦关系，结合六爻（尤其变爻）分析当前态势。\n"
            "2. 若有之卦，说明事态发展趋势及变化方向。\n"
            "3. 针对用户问题给出明确、可执行的建议（工作、人际、决策等现代场景）。\n"
            "4. 语言简洁专业，避免空泛玄学，注重实际指导价值。\n"
            "5. 结尾用一两句话总结核心启示。"
        )
    else:
        sections.append("")
        sections.append(
            "【解读要求】\n"
            "1. 阐释本卦卦义及上下卦关系，结合六爻分析当前态势。\n"
            "2. 针对用户问题给出明确、可执行的建议（工作、人际、决策等现代场景）。\n"
            "3. 语言简洁专业，避免空泛玄学，注重实际指导价值。\n"
            "4. 结尾用一两句话总结核心启示。"
        )

    sections.append("════════════════════════════════════════")

    return "\n".join(sections)


def display_prompt(prompt: str) -> None:
    """用明显分隔符展示提示词，便于全选复制。"""
    console.print()
    console.print(Rule("[bold green]AI 解读提示词（可直接复制）[/bold green]", style="green"))
    console.print()
    # 使用 Panel 包裹，但主体为纯文本以便复制
    border = "═" * 42
    console.print(f"[dim]{border}[/dim]")
    console.print(prompt)
    console.print(f"[dim]{border}[/dim]")
    console.print()
    console.print("[dim]提示：选中上方文本区域，复制后粘贴至任意大模型对话框即可。[/dim]")


# ---------------------------------------------------------------------------
# 记录保存
# ---------------------------------------------------------------------------

def _hexagram_to_dict(hexagram: HexagramInfo) -> dict:
    data = {
        "name": hexagram.name,
        "upper_trigram": hexagram.upper_trigram["name"],
        "lower_trigram": hexagram.lower_trigram["name"],
        "changing_positions": hexagram.changing_positions,
        "yaos": [
            {
                "position": y.position,
                "value": y.value,
                "label": y.label,
                "is_yang": y.is_yang,
                "is_changing": y.is_changing,
            }
            for y in hexagram.yaos
        ],
    }
    if hexagram.changed_hexagram:
        data["changed_hexagram"] = {
            "name": hexagram.changed_hexagram.name,
            "upper_trigram": hexagram.changed_hexagram.upper_trigram["name"],
            "lower_trigram": hexagram.changed_hexagram.lower_trigram["name"],
        }
    return data


def save_record(record: DivinationRecord) -> Path:
    """保存占卜记录到 ~/.bagua/records/。"""
    RECORDS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = RECORDS_DIR / f"bagua_{ts}.json"
    payload = {
        "question": record.question,
        "bazi": record.bazi,
        "method": record.method,
        "divination_time": record.divination_time,
        "hexagram": _hexagram_to_dict(record.hexagram),
        "prompt": record.prompt,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def show_disclaimer() -> None:
    console.print(
        Panel(
            "[dim]本工具仅供娱乐与文化学习参考，不构成任何决策依据。[/dim]",
            title="[bold]bagua[/bold] · 易经八卦占卜",
            border_style="dim",
            box=box.ROUNDED,
        )
    )


def ask_question_and_bazi() -> tuple[str, str]:
    console.print()
    question = console.input("[bold]请输入占卜问题[/bold]（可留空）: ").strip()
    bazi = console.input("[bold]请输入生辰八字[/bold]（可选，可留空）: ").strip()
    return question, bazi


def select_method() -> Literal["coin", "time", "random"]:
    console.print()
    console.print("[bold]请选择起卦方式：[/bold]")
    console.print("  [cyan]1[/cyan]  铜钱法（推荐，交互投掷）")
    console.print("  [cyan]2[/cyan]  时间起卦（梅花易数）")
    console.print("  [cyan]3[/cyan]  随机起卦（快速模式）")
    console.print()

    mapping = {"1": "coin", "2": "time", "3": "random"}
    while True:
        choice = console.input("请输入选项 [1/2/3]: ").strip()
        if choice in mapping:
            return mapping[choice]  # type: ignore[return-value]
        console.print("[red]无效选项，请输入 1、2 或 3[/red]")


def run_divination(method: str) -> tuple[list[int], str, str]:
    """执行起卦，返回 (爻值列表, 方法描述, 起卦时间字符串)。"""
    divination_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if method == "coin":
        values, method_desc = divinate_by_coin()
    elif method == "time":
        console.print()
        use_now = console.input("使用当前时间？[Y/n]: ").strip().lower()
        if use_now in ("", "y", "yes"):
            dt = datetime.now()
        else:
            raw = console.input("请输入时间（如 2026-06-24 14:30）: ").strip()
            dt = _parse_datetime_input(raw)
            if dt is None:
                console.print("[yellow]时间格式无效，改用当前时间[/yellow]")
                dt = datetime.now()
            divination_time = dt.strftime("%Y-%m-%d %H:%M:%S")
        values, method_desc = divinate_by_time(dt)
        console.print(f"\n[dim]{method_desc}[/dim]")
    else:
        values, method_desc = divinate_by_random()
        console.print("\n[dim]已随机生成六爻[/dim]")

    return values, method_desc, divination_time


def main() -> None:
    show_disclaimer()
    question, bazi = ask_question_and_bazi()
    method = select_method()
    yao_values, method_desc, divination_time = run_divination(method)

    hexagram = _build_hexagram(yao_values)
    display_hexagram(hexagram)

    prompt = generate_ai_prompt(question, bazi, method_desc, divination_time, hexagram)
    display_prompt(prompt)

    console.print()
    save_choice = console.input("是否保存本次占卜记录？[y/N]: ").strip().lower()
    if save_choice in ("y", "yes"):
        record = DivinationRecord(
            question=question,
            bazi=bazi,
            method=method_desc,
            divination_time=divination_time,
            hexagram=hexagram,
            prompt=prompt,
        )
        path = save_record(record)
        console.print(f"[green]已保存至 {path}[/green]")

    console.print()
    console.print(Rule(style="dim"))
    console.print("[dim]感谢使用 bagua。愿君子以自强不息。[/dim]")


if __name__ == "__main__":
    main()