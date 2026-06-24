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
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, available_timezones

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

# ---------------------------------------------------------------------------
# 八卦与六十四卦数据
# ---------------------------------------------------------------------------

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

BAGUA_DIR = Path.home() / ".bagua"
CONFIG_PATH = BAGUA_DIR / "config.json"
RECORDS_DIR = BAGUA_DIR / "records"

# 常用时区预设（IANA 名称, 显示名）
TIMEZONE_PRESETS: list[tuple[str, str]] = [
    ("Asia/Shanghai", "中国（北京时间 UTC+8）"),
    ("Asia/Hong_Kong", "中国香港（UTC+8）"),
    ("Asia/Taipei", "中国台湾（UTC+8）"),
    ("Asia/Tokyo", "日本（东京 UTC+9）"),
    ("Asia/Seoul", "韩国（首尔 UTC+9）"),
    ("Asia/Singapore", "新加坡（UTC+8）"),
    ("Europe/London", "英国（伦敦）"),
    ("Europe/Paris", "欧洲中部（巴黎）"),
    ("America/New_York", "美国东部（纽约）"),
    ("America/Los_Angeles", "美国西部（洛杉矶）"),
    ("UTC", "UTC（协调世界时）"),
]

console = Console()


# ---------------------------------------------------------------------------
# 用户配置（本地持久化）
# ---------------------------------------------------------------------------

@dataclass
class UserConfig:
    """保存在 ~/.bagua/config.json 的用户偏好。"""

    timezone: str = "Asia/Shanghai"
    region_label: str = "中国（北京时间 UTC+8）"
    question: str = ""
    bazi: str = ""
    birth_datetime: str = ""  # 本地时间字符串，如 1990-01-01 08:00
    coin_mode: str = "manual"  # manual | auto

    @classmethod
    def load(cls) -> UserConfig:
        if not CONFIG_PATH.exists():
            return cls()
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            known = {f.name for f in cls.__dataclass_fields__.values()}
            return cls(**{k: v for k, v in data.items() if k in known})
        except (json.JSONDecodeError, TypeError):
            console.print("[yellow]配置文件损坏，将使用默认设置[/yellow]")
            return cls()

    def save(self) -> None:
        BAGUA_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


@dataclass
class UserContext:
    """本次占卜使用的用户上下文。"""

    question: str
    bazi: str
    birth_datetime: str
    timezone: ZoneInfo
    region_label: str
    coin_mode: str


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class YaoInfo:
    position: int
    value: int
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
    question: str
    bazi: str
    birth_datetime: str
    method: str
    divination_time: str
    timezone: str
    hexagram: HexagramInfo
    prompt: str


# ---------------------------------------------------------------------------
# 时区工具
# ---------------------------------------------------------------------------

def _detect_system_timezone() -> str:
    try:
        tz = datetime.now().astimezone().tzinfo
        if tz is not None and hasattr(tz, "key"):
            return tz.key  # type: ignore[union-attr]
    except Exception:
        pass
    return "Asia/Shanghai"


def _resolve_timezone(name: str) -> ZoneInfo | None:
    try:
        ZoneInfo(name)
        return ZoneInfo(name)
    except Exception:
        return None


def _format_utc_offset(tz: ZoneInfo, dt: datetime | None = None) -> str:
    dt = dt or datetime.now(tz)
    offset = dt.utcoffset()
    if offset is None:
        return "UTC"
    total = int(offset.total_seconds())
    sign = "+" if total >= 0 else "-"
    hours, rem = divmod(abs(total), 3600)
    minutes = rem // 60
    if minutes:
        return f"UTC{sign}{hours}:{minutes:02d}"
    return f"UTC{sign}{hours}"


def format_datetime_with_tz(dt: datetime, tz: ZoneInfo, region_label: str) -> str:
    """格式化带时区标注的时间字符串。"""
    local = dt.astimezone(tz) if dt.tzinfo else dt.replace(tzinfo=tz)
    offset = _format_utc_offset(tz, local)
    return f"{local.strftime('%Y-%m-%d %H:%M:%S')} ({region_label}, {tz.key}, {offset})"


def _label_for_timezone(tz_name: str) -> str:
    for name, label in TIMEZONE_PRESETS:
        if name == tz_name:
            return label
    return tz_name


def select_timezone(current: str) -> tuple[str, str]:
    """交互选择时区，返回 (iana_name, region_label)。"""
    console.print("\n[bold]请选择时区 / 地区：[/bold]")
    for i, (tz_name, label) in enumerate(TIMEZONE_PRESETS, start=1):
        mark = " [green]← 当前[/green]" if tz_name == current else ""
        console.print(f"  [cyan]{i:>2}[/cyan]  {label}  [dim]({tz_name})[/dim]{mark}")
    console.print(f"  [cyan] 0[/cyan]  手动输入 IANA 时区名称（如 Europe/Berlin）")
    console.print()

    while True:
        choice = console.input(f"请输入选项 [默认 {current}，直接回车沿用]: ").strip()
        if not choice:
            return current, _label_for_timezone(current)
        if choice == "0":
            raw = console.input("IANA 时区名称: ").strip()
            if _resolve_timezone(raw):
                return raw, _label_for_timezone(raw)
            console.print("[red]无效时区，请重试[/red]")
            continue
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(TIMEZONE_PRESETS):
                tz_name, label = TIMEZONE_PRESETS[idx - 1]
                return tz_name, label
        console.print("[red]无效选项[/red]")


def _parse_datetime_input(raw: str, tz: ZoneInfo) -> datetime | None:
    raw = raw.strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y-%m-%d"):
        try:
            naive = datetime.strptime(raw, fmt)
            return naive.replace(tzinfo=tz)
        except ValueError:
            continue
    return None


def now_in_tz(tz: ZoneInfo) -> datetime:
    return datetime.now(tz)


# ---------------------------------------------------------------------------
# 用户信息与配置交互
# ---------------------------------------------------------------------------

def _prompt_with_default(label: str, default: str, hint: str = "") -> str:
    hint_text = f" [dim]({hint})[/dim]" if hint else ""
    default_hint = f" [dim][{default}][/dim]" if default else ""
    raw = console.input(f"[bold]{label}[/bold]{hint_text}{default_hint}: ").strip()
    return raw if raw else default


def setup_user_context(config: UserConfig) -> tuple[UserContext, UserConfig]:
    """加载或更新用户信息，返回本次上下文与待保存配置。"""
    tz = _resolve_timezone(config.timezone) or ZoneInfo("Asia/Shanghai")

    if CONFIG_PATH.exists() and any([config.question, config.bazi, config.birth_datetime]):
        console.print()
        console.print(
            Panel(
                f"时区：{config.region_label} ({config.timezone})\n"
                f"出生时间：{config.birth_datetime or '（未设置）'}\n"
                f"生辰八字：{config.bazi or '（未设置）'}\n"
                f"默认问题：{config.question or '（未设置）'}",
                title="[bold]已保存的用户信息[/bold]",
                border_style="cyan",
                box=box.ROUNDED,
            )
        )
        use_saved = console.input("使用已保存信息？[Y/n]: ").strip().lower()
        if use_saved in ("", "y", "yes"):
            return (
                UserContext(
                    question=config.question,
                    bazi=config.bazi,
                    birth_datetime=config.birth_datetime,
                    timezone=tz,
                    region_label=config.region_label,
                    coin_mode=config.coin_mode,
                ),
                config,
            )

    console.print("\n[bold]设置用户信息[/bold] [dim]（可直接回车跳过或沿用默认值）[/dim]")

    change_tz = console.input(
        f"修改时区？当前 {config.region_label} [y/N]: "
    ).strip().lower()
    if change_tz in ("y", "yes"):
        tz_name, region_label = select_timezone(config.timezone)
        config.timezone = tz_name
        config.region_label = region_label
        tz = ZoneInfo(tz_name)

    config.birth_datetime = _prompt_with_default(
        "出生日期时间",
        config.birth_datetime,
        f"本地时间，{config.region_label}，如 1990-01-01 08:00",
    )
    config.bazi = _prompt_with_default("生辰八字", config.bazi, "可选")
    config.question = _prompt_with_default("占卜问题", config.question, "可留空")

    ctx = UserContext(
        question=config.question,
        bazi=config.bazi,
        birth_datetime=config.birth_datetime,
        timezone=tz,
        region_label=config.region_label,
        coin_mode=config.coin_mode,
    )
    return ctx, config


# ---------------------------------------------------------------------------
# 卦象计算
# ---------------------------------------------------------------------------

def _lines_to_trigram(lines: tuple[int, int, int]) -> dict:
    for tri in TRIGRAMS:
        if tri["lines"] == lines:
            return tri
    raise ValueError(f"无效三爻: {lines}")


def _yao_value_to_line(value: int) -> tuple[bool, bool]:
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
            yaos=yaos,
            changing_positions=[],
        )

    return hexagram


def _meihua_trigram_number(n: int) -> int:
    r = n % 8
    return 8 if r == 0 else r


def _meihua_changing_line(n: int) -> int:
    r = n % 6
    return 6 if r == 0 else r


def _trigram_by_number(num: int) -> dict:
    return TRIGRAMS[num - 1]


def _lines_from_trigrams(lower: dict, upper: dict, changing_line: int | None = None) -> list[int]:
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

def _simulate_three_coins() -> tuple[list[int], int]:
    """随机模拟三枚铜钱，返回 (点数列表, 爻值)。"""
    points = [random.choice([2, 3]) for _ in range(3)]
    return points, sum(points)


def _coins_to_display(points: list[int]) -> str:
    return " ".join("1" if p == 3 else "2" for p in points)


def _parse_coin_input(raw: str) -> list[int] | None:
    """
    解析硬币输入，返回三枚硬币点数列表。
    主输入方式：1=阳面（字），2=阴面（花）；兼容 正/反、3/2。
    """
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


def _select_coin_mode(default: str) -> str:
    console.print("\n[bold]铜钱法投掷方式：[/bold]")
    console.print("  [cyan]1[/cyan]  手动输入（每爻输入三个 1 或 2）")
    console.print("  [cyan]2[/cyan]  自动模拟（程序随机投掷三枚铜钱）")
    default_label = "手动" if default == "manual" else "自动"
    console.print(f"  [dim]直接回车沿用上次选择：{default_label}[/dim]\n")

    mapping = {"1": "manual", "2": "auto", "": default}
    while True:
        choice = console.input("请选择 [1/2]: ").strip()
        if choice in mapping:
            return mapping[choice]
        console.print("[red]无效选项，请输入 1 或 2[/red]")


def divinate_by_coin(coin_mode: str) -> tuple[list[int], str, str]:
    """铜钱法起卦，支持手动输入与自动模拟。"""
    mode = _select_coin_mode(coin_mode)
    yao_values: list[int] = []

    console.print("\n[bold cyan]铜钱法起卦[/bold cyan]")
    if mode == "manual":
        console.print("每爻输入三枚硬币：[green]1[/green]=阳面（字）  [yellow]2[/yellow]=阴面（花）")
        console.print("示例：[green]1 2 1[/green]  或  [green]2 2 2[/green]\n")
    else:
        console.print("[dim]自动模拟投掷，每爻随机生成结果…[/dim]\n")

    for pos in range(1, 7):
        if mode == "auto":
            points, val = _simulate_three_coins()
            yao_values.append(val)
            console.print(
                f"  第 {pos} 爻（{YAO_POSITIONS[pos - 1]}）: {_coins_to_display(points)} "
                f"→ [bold]{val}[/bold]（{YAO_VALUE_NAMES[val]}）"
            )
            continue

        while True:
            raw = console.input(
                f"[bold]第 {pos} 爻[/bold]（{YAO_POSITIONS[pos - 1]}）[1/2，空格分隔]: "
            ).strip()
            coins = _parse_coin_input(raw)
            if coins is None:
                console.print("[red]格式错误，请输入三个 1 或 2，如：1 2 1[/red]")
                continue
            val = sum(coins)
            yao_values.append(val)
            console.print(f"  → 爻值 [bold]{val}[/bold]（{YAO_VALUE_NAMES[val]}）\n")
            break

    suffix = "手动投掷" if mode == "manual" else "自动模拟"
    return yao_values, f"{METHOD_LABELS['coin']}（{suffix}）", mode


def divinate_by_time(dt: datetime) -> tuple[list[int], str]:
    year = dt.year
    month = dt.month
    day = dt.day
    hour = (dt.hour // 2) % 12 + 1

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
    values = [random.choice([6, 7, 8, 9]) for _ in range(6)]
    return values, METHOD_LABELS["random"]


# ---------------------------------------------------------------------------
# 显示
# ---------------------------------------------------------------------------

def _yao_line_display(yao: YaoInfo) -> Text:
    if yao.is_yang:
        line = Text("━━━━━━", style="bold white")
    else:
        line = Text("──────", style="white")

    if yao.is_changing:
        mark = Text(" ○ 变", style="bold yellow") if yao.is_yang else Text(" × 变", style="bold yellow")
        line.append(mark)
    return line


def display_hexagram(hexagram: HexagramInfo, title: str = "卦象") -> None:
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

def _format_birth_block(birth_datetime: str, tz: ZoneInfo, region_label: str) -> str:
    if not birth_datetime.strip():
        return "（未提供）"
    offset = _format_utc_offset(tz)
    return f"{birth_datetime}（{region_label}, {tz.key}, {offset}）"


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
    ctx: UserContext,
    method: str,
    divination_time: str,
    hexagram: HexagramInfo,
) -> str:
    question_text = ctx.question.strip() or "（未指定具体问题，请做综合解读）"
    bazi_text = ctx.bazi.strip() or "（未提供）"
    birth_text = _format_birth_block(ctx.birth_datetime, ctx.timezone, ctx.region_label)

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
        "【出生时间】",
        birth_text,
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
            "3. 结合用户出生时间与八字信息（如有）辅助分析。\n"
            "4. 针对用户问题给出明确、可执行的建议（工作、人际、决策等现代场景）。\n"
            "5. 语言简洁专业，避免空泛玄学，注重实际指导价值。\n"
            "6. 结尾用一两句话总结核心启示。"
        )
    else:
        sections.append("")
        sections.append(
            "【解读要求】\n"
            "1. 阐释本卦卦义及上下卦关系，结合六爻分析当前态势。\n"
            "2. 结合用户出生时间与八字信息（如有）辅助分析。\n"
            "3. 针对用户问题给出明确、可执行的建议（工作、人际、决策等现代场景）。\n"
            "4. 语言简洁专业，避免空泛玄学，注重实际指导价值。\n"
            "5. 结尾用一两句话总结核心启示。"
        )

    sections.append("════════════════════════════════════════")
    return "\n".join(sections)


def display_prompt(prompt: str) -> None:
    console.print()
    console.print(Rule("[bold green]AI 解读提示词（可直接复制）[/bold green]", style="green"))
    console.print()
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
    RECORDS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = RECORDS_DIR / f"bagua_{ts}.json"
    payload = {
        "question": record.question,
        "bazi": record.bazi,
        "birth_datetime": record.birth_datetime,
        "method": record.method,
        "divination_time": record.divination_time,
        "timezone": record.timezone,
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


def select_method() -> Literal["coin", "time", "random"]:
    console.print()
    console.print("[bold]请选择起卦方式：[/bold]")
    console.print("  [cyan]1[/cyan]  铜钱法（推荐）")
    console.print("  [cyan]2[/cyan]  时间起卦（梅花易数）")
    console.print("  [cyan]3[/cyan]  随机起卦（快速模式）")
    console.print()

    mapping = {"1": "coin", "2": "time", "3": "random"}
    while True:
        choice = console.input("请输入选项 [1/2/3]: ").strip()
        if choice in mapping:
            return mapping[choice]  # type: ignore[return-value]
        console.print("[red]无效选项，请输入 1、2 或 3[/red]")


def run_divination(
    method: str,
    ctx: UserContext,
) -> tuple[list[int], str, str, str, UserContext]:
    """执行起卦，返回 (爻值, 方法描述, 起卦时间字符串, 新coin_mode, 更新后的ctx)。"""
    dt_now = now_in_tz(ctx.timezone)
    divination_time = format_datetime_with_tz(dt_now, ctx.timezone, ctx.region_label)
    coin_mode = ctx.coin_mode

    if method == "coin":
        values, method_desc, coin_mode = divinate_by_coin(ctx.coin_mode)
    elif method == "time":
        console.print()
        use_now = console.input("使用当前时间？[Y/n]: ").strip().lower()
        if use_now in ("", "y", "yes"):
            dt = dt_now
        else:
            raw = console.input(
                f"请输入时间（如 2026-06-24 14:30，按 {ctx.region_label} 理解）: "
            ).strip()
            dt = _parse_datetime_input(raw, ctx.timezone)
            if dt is None:
                console.print("[yellow]时间格式无效，改用当前时间[/yellow]")
                dt = dt_now
            divination_time = format_datetime_with_tz(dt, ctx.timezone, ctx.region_label)
        values, method_desc = divinate_by_time(dt)
        console.print(f"\n[dim]{method_desc}[/dim]")
    else:
        values, method_desc = divinate_by_random()
        console.print("\n[dim]已随机生成六爻[/dim]")

    ctx.coin_mode = coin_mode
    return values, method_desc, divination_time, coin_mode, ctx


def main() -> None:
    show_disclaimer()

    config = UserConfig.load()
    if not CONFIG_PATH.exists():
        detected = _detect_system_timezone()
        if detected in available_timezones():
            config.timezone = detected
            config.region_label = _label_for_timezone(detected)

    ctx, config = setup_user_context(config)

    method = select_method()
    yao_values, method_desc, divination_time, coin_mode, ctx = run_divination(method, ctx)

    config.coin_mode = coin_mode
    config.question = ctx.question
    config.bazi = ctx.bazi
    config.birth_datetime = ctx.birth_datetime
    config.timezone = ctx.timezone.key
    config.region_label = ctx.region_label
    config.save()
    console.print(f"\n[dim]用户偏好已保存至 {CONFIG_PATH}[/dim]")

    hexagram = _build_hexagram(yao_values)
    display_hexagram(hexagram)

    prompt = generate_ai_prompt(ctx, method_desc, divination_time, hexagram)
    display_prompt(prompt)

    console.print()
    save_choice = console.input("是否保存本次占卜记录？[y/N]: ").strip().lower()
    if save_choice in ("y", "yes"):
        record = DivinationRecord(
            question=ctx.question,
            bazi=ctx.bazi,
            birth_datetime=ctx.birth_datetime,
            method=method_desc,
            divination_time=divination_time,
            timezone=ctx.timezone.key,
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