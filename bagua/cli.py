"""bagua 终端展示层（Rich + input），调用 service 层完成起卦。"""

from __future__ import annotations

from typing import Literal

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from bagua.args import parse_cli_args
from bagua.bazi import compute_bazi
from bagua.cli_guide import (
    METHOD_LABELS,
    show_calendar_mode_guide,
    show_coin_value_legend,
    show_completion_guide,
    show_method_guide,
    show_pre_result_summary,
    show_quick_start,
    show_random_guide,
    show_step,
    show_time_guide,
    show_user_fields_help,
)
from bagua.clipboard import copy_to_clipboard
from bagua.config import CONFIG_PATH, load_config, save_config
from bagua.data import YAO_POSITIONS, YAO_VALUE_NAMES
from bagua.divination import coin_tosses_to_display, parse_coin_input, simulate_coin_toss
from bagua.headless import dispatch_headless
from bagua.lunar_util import is_lunar_available, parse_lunar_datetime_input
from bagua.models import DivinationRecord, HexagramInfo, UserConfig, UserContext, YaoInfo
from bagua.records import save_record
from bagua.service import perform_divination
from bagua.timezone import (
    TIMEZONE_PRESETS,
    detect_system_timezone_name,
    format_datetime_with_tz,
    get_timezone,
    is_tzdata_available,
    label_for_timezone,
    now_in_timezone,
    parse_datetime_input,
    validate_timezone_name,
)
from bagua.user_prefs import (
    METHOD_KEY_TO_NUM,
    METHOD_NUM_TO_KEY,
    format_stored_coin_tosses,
    normalize_method,
    points_to_stored_coin_tosses,
    stored_coin_tosses_to_points,
)

console = Console(soft_wrap=True)


# ---------------------------------------------------------------------------
# 运行时与环境
# ---------------------------------------------------------------------------

def ensure_runtime() -> None:
    if is_tzdata_available():
        console.print(
            "[dim]时区：已启用 IANA 数据库，支持夏令时自动换算。[/dim]"
        )
        return
    console.print(
        Panel(
            "[yellow]未检测到 IANA 时区数据库（tzdata）。[/yellow]\n"
            "程序将使用预设地区的[bold]固定 UTC 偏移[/bold]作为回退，可正常运行。\n"
            "[yellow]固定偏移不支持夏令时切换。[/yellow]\n\n"
            "建议安装完整时区支持：\n"
            "  [cyan]pip install tzdata[/cyan]\n"
            "或重新安装依赖：\n"
            "  [cyan]pip install -r requirements.txt[/cyan]",
            title="[bold]时区提示[/bold]",
            border_style="yellow",
            box=box.ROUNDED,
        )
    )


def show_disclaimer() -> None:
    console.print(
        Panel(
            "[dim]本工具仅供娱乐与文化学习参考，不构成任何决策依据。[/dim]",
            title="[bold]bagua[/bold] · 易经八卦占卜",
            border_style="dim",
            box=box.ROUNDED,
        )
    )


# ---------------------------------------------------------------------------
# 用户输入
# ---------------------------------------------------------------------------

def select_timezone(current: str) -> tuple[str, str]:
    console.print("\n[bold]请选择时区 / 地区[/bold] [dim]（决定起卦时间的标注）[/dim]")
    for i, (tz_name, label) in enumerate(TIMEZONE_PRESETS, start=1):
        mark = " [green]← 当前[/green]" if tz_name == current else ""
        console.print(f"  [cyan]{i:>2}[/cyan]  {label}  [dim]({tz_name})[/dim]{mark}")
    console.print("  [cyan] 0[/cyan]  手动输入 IANA 时区名称（如 Europe/Berlin）")
    if not is_tzdata_available():
        console.print("  [dim]当前为固定偏移模式，自定义时区仅支持列表内预设[/dim]")
    console.print("  [dim]直接回车 = 保持当前时区[/dim]\n")

    while True:
        choice = console.input(f"请输入选项 [当前 {current}]: ").strip()
        if not choice:
            return current, label_for_timezone(current)
        if choice == "0":
            raw = console.input("IANA 时区名称: ").strip()
            if validate_timezone_name(raw):
                return raw, label_for_timezone(raw)
            console.print("[red]无效时区。请输入列表中的名称，或安装 tzdata 后重试。[/red]")
            continue
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(TIMEZONE_PRESETS):
                return TIMEZONE_PRESETS[idx - 1]
        console.print("[red]无效选项。请输入列表中的数字，或直接回车。[/red]")


def _prompt_with_default(label: str, default: str, hint: str = "") -> str:
    hint_text = f" [dim]{hint}[/dim]" if hint else ""
    if default:
        console.print(f"[bold]{label}[/bold]{hint_text}")
        raw = console.input(f"  直接回车沿用 [dim]{default}[/dim]，或输入新值: ").strip()
    else:
        raw = console.input(f"[bold]{label}[/bold]{hint_text}: ").strip()
    return raw if raw else default


def setup_user_context(config: UserConfig) -> tuple[UserContext, UserConfig]:
    show_step(console, 1, "个人信息")
    tz = get_timezone(config.timezone, config.region_label)

    if CONFIG_PATH.exists() and any([config.question, config.bazi, config.birth_datetime]):
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
        console.print("[dim]直接回车 = 沿用以上信息；输入 n = 重新填写[/dim]")
        use_saved = console.input("使用已保存信息？[Y/n]: ").strip().lower()
        if use_saved in ("", "y", "yes"):
            console.print("[green]✓[/green] 已沿用保存的信息")
            return (
                UserContext(
                    question=config.question,
                    bazi=config.bazi,
                    birth_datetime=config.birth_datetime,
                    tz=tz,
                    coin_mode=config.coin_mode,
                    calendar_mode=config.calendar_mode,
                    include_hexagram_texts=config.include_hexagram_texts,
                    longitude=config.longitude,
                    use_true_solar=config.use_true_solar,
                ),
                config,
            )

    show_user_fields_help(console)

    if console.input(f"需要修改时区？当前 [bold]{config.region_label}[/bold] [y/N]: ").strip().lower() in ("y", "yes"):
        tz_name, region_label = select_timezone(config.timezone)
        config.timezone = tz_name
        config.region_label = region_label
        tz = get_timezone(tz_name, region_label)

    config.birth_datetime = _prompt_with_default(
        "出生日期时间",
        config.birth_datetime,
        "可选 · 格式 1990-01-01 08:00",
    )
    config.bazi = _prompt_with_default("生辰八字", config.bazi, "可选 · 如 庚午年 辛巳月 甲子日")
    if config.auto_bazi and not config.bazi.strip() and config.birth_datetime.strip():
        computed = compute_bazi(config.birth_datetime, tz)
        if computed:
            config.bazi = computed
            console.print(f"[green]✓[/green] 已自动排八字：{computed}")
    config.question = _prompt_with_default("占卜问题", config.question, "建议填写 · 如「近期是否该跳槽」")

    console.print("[green]✓[/green] 个人信息已确认")
    return (
        UserContext(
            question=config.question,
            bazi=config.bazi,
            birth_datetime=config.birth_datetime,
            tz=tz,
            coin_mode=config.coin_mode,
            calendar_mode=config.calendar_mode,
            include_hexagram_texts=config.include_hexagram_texts,
            longitude=config.longitude,
            use_true_solar=config.use_true_solar,
        ),
        config,
    )


def select_method(default: str = "coin") -> Literal["coin", "time", "random"]:
    show_step(console, 2, "选择起卦方式")
    show_method_guide(console)
    default = normalize_method(default)
    default_label = METHOD_LABELS[default]
    console.print(f"[dim]直接回车 = 沿用上次：{default_label}[/dim]")
    console.print("[dim]或输入 1–3 选择其他方式[/dim]\n")

    mapping = {**METHOD_NUM_TO_KEY, "": default}
    while True:
        choice = console.input(f"你的选择 [1/2/3，默认 {METHOD_KEY_TO_NUM[default]}]: ").strip()
        if choice in mapping:
            picked = mapping[choice]
            console.print(f"[green]✓[/green] 已选择：{METHOD_LABELS[picked]}")
            return picked  # type: ignore[return-value]
        console.print("[red]请输入 1、2、3，或直接回车。[/red]")


def _select_coin_mode(default: str) -> str:
    console.print("\n[bold]铜钱法 · 投掷方式[/bold]")
    console.print("  [cyan]1[/cyan]  手动输入 — 自己掷币，每爻输入三个 1 或 2")
    console.print("  [cyan]2[/cyan]  自动模拟 — 程序代掷，适合快速出卦")
    default_label = "手动" if default == "manual" else "自动"
    console.print(f"  [dim]直接回车 = 沿用上次：{default_label}[/dim]\n")

    mapping = {"1": "manual", "2": "auto", "": default}
    while True:
        choice = console.input("请选择 [1/2]: ").strip()
        if choice in mapping:
            label = "手动输入" if mapping[choice] == "manual" else "自动模拟"
            console.print(f"[green]✓[/green] {label}")
            return mapping[choice]
        console.print("[red]请输入 1、2，或直接回车。[/red]")


def collect_coin_tosses(coin_mode: str, config: UserConfig) -> tuple[list[list[int]], str]:
    mode = _select_coin_mode(coin_mode)
    tosses: list[list[int]] = []

    console.print()
    if mode == "manual":
        saved = stored_coin_tosses_to_points(config.coin_tosses)
        if saved:
            summary = format_stored_coin_tosses(config.coin_tosses)
            console.print(f"[dim]上次保存的铜钱输入：{summary}[/dim]")
            if console.input("使用上次保存的铜钱输入？[Y/n]: ").strip().lower() not in ("n", "no"):
                console.print("[green]✓[/green] 已沿用保存的铜钱输入")
                return saved, mode

        show_coin_value_legend(console)
        console.print()
        for pos in range(1, 7):
            while True:
                console.print(f"[dim]进度 {pos}/6[/dim]")
                raw = console.input(
                    f"[bold]第 {pos} 爻[/bold]（{YAO_POSITIONS[pos - 1]}）输入三个 1 或 2: "
                ).strip()
                coins = parse_coin_input(raw)
                if coins is None:
                    console.print(
                        "[red]格式不对。[/red] 需要恰好三个数字，用空格隔开，"
                        "例如 [bold]1 2 1[/bold]（1=阳面，2=阴面）"
                    )
                    continue
                tosses.append(coins)
                val = sum(coins)
                console.print(
                    f"  [green]✓[/green] {coin_tosses_to_display(coins)} "
                    f"→ 爻值 [bold]{val}[/bold]（{YAO_VALUE_NAMES[val]}）\n"
                )
                break
    else:
        console.print("[dim]自动模拟中，共六爻…[/dim]\n")
        for pos in range(1, 7):
            points = simulate_coin_toss()
            tosses.append(points)
            val = sum(points)
            console.print(
                f"  [{pos}/6] {YAO_POSITIONS[pos - 1]}: {coin_tosses_to_display(points)} "
                f"→ [bold]{val}[/bold]（{YAO_VALUE_NAMES[val]}）"
            )

    return tosses, mode


def _select_calendar_mode(default: str) -> str:
    if not is_lunar_available():
        console.print("[dim]农历功能未安装（pip install lunar-python），将使用公历起卦[/dim]")
        return "solar"
    show_calendar_mode_guide(console)
    default_label = "农历" if default == "lunar" else "公历"
    console.print(f"  [dim]直接回车 = 沿用上次：{default_label}[/dim]\n")
    mapping = {"1": "solar", "2": "lunar", "": default}
    while True:
        choice = console.input("历法选择 [1/2]: ").strip()
        if choice in mapping:
            label = "公历起卦" if mapping[choice] == "solar" else "农历起卦"
            console.print(f"[green]✓[/green] {label}")
            return mapping[choice]
        console.print("[red]请输入 1、2，或直接回车。[/red]")


def collect_divination_params(
    method: str,
    ctx: UserContext,
    config: UserConfig,
) -> tuple[list[list[int]] | None, object | None, str, UserContext]:
    show_step(console, 3, "起卦操作")

    coin_tosses: list[list[int]] | None = None
    divination_datetime = None
    coin_mode = ctx.coin_mode
    lunar_input: str | None = None
    calendar_mode = ctx.calendar_mode

    if method == "coin":
        coin_tosses, coin_mode = collect_coin_tosses(ctx.coin_mode, config)
        if coin_mode == "manual" and coin_tosses:
            config.coin_tosses = points_to_stored_coin_tosses(coin_tosses)
    elif method == "time":
        calendar_mode = _select_calendar_mode(config.calendar_mode)
        config.calendar_mode = calendar_mode
        dt_now = now_in_timezone(ctx.tz)
        show_time_guide(console, ctx.tz.region_label, format_datetime_with_tz(dt_now, ctx.tz))
        console.print()
        use_now_prompt = "使用当前时间起卦？[Y/n]: " if config.use_current_time else "使用当前时间起卦？[y/N]: "
        if config.use_current_time:
            use_now = console.input(use_now_prompt).strip().lower() not in ("n", "no")
        else:
            use_now = console.input(use_now_prompt).strip().lower() in ("y", "yes")
        config.use_current_time = use_now
        if use_now:
            divination_datetime = dt_now
            console.print("[green]✓[/green] 将使用当前时间")
        else:
            if calendar_mode == "lunar":
                default_lunar = config.time_input or ""
                hint = f" [dim]上次 {default_lunar}[/dim]" if default_lunar else ""
                raw = console.input(f"请输入农历时间（如 2026-05-10 14:30）{hint}: ").strip()
                raw = raw or default_lunar
                if parse_lunar_datetime_input(raw) is None:
                    console.print("[yellow]农历格式无效，已自动改用当前时间[/yellow]")
                    divination_datetime = dt_now
                    config.use_current_time = True
                else:
                    lunar_input = raw
                    config.time_input = raw
                    divination_datetime = dt_now
                    console.print(f"[green]✓[/green] 将使用农历输入：{raw}")
            else:
                default_time = config.time_input or ""
                raw = _prompt_with_default("公历起卦时间", default_time, "如 2026-06-24 14:30")
                divination_datetime = parse_datetime_input(raw, ctx.tz)
                if divination_datetime is None:
                    console.print("[yellow]时间格式无效，已自动改用当前时间[/yellow]")
                    divination_datetime = dt_now
                    config.use_current_time = True
                else:
                    config.time_input = raw
                    console.print(f"[green]✓[/green] 将使用 {format_datetime_with_tz(divination_datetime, ctx.tz)}")
    elif method == "random":
        show_random_guide(console)
        console.print("[green]✓[/green] 准备随机起卦")

    updated_ctx = UserContext(
        question=ctx.question,
        bazi=ctx.bazi,
        birth_datetime=ctx.birth_datetime,
        tz=ctx.tz,
        coin_mode=coin_mode,
        calendar_mode=calendar_mode,
        lunar_input=lunar_input,
        include_hexagram_texts=ctx.include_hexagram_texts,
        longitude=ctx.longitude,
        use_true_solar=ctx.use_true_solar,
    )
    return coin_tosses, divination_datetime, coin_mode, updated_ctx


# ---------------------------------------------------------------------------
# 展示
# ---------------------------------------------------------------------------

def _yao_line_display(yao: YaoInfo) -> Text:
    line = Text("━━━━━━" if yao.is_yang else "──────", style="bold white" if yao.is_yang else "white")
    if yao.is_changing:
        mark = Text(" ○ 变", style="bold yellow") if yao.is_yang else Text(" × 变", style="bold yellow")
        line.append(mark)
    return line


def display_hexagram(hexagram: HexagramInfo, title: str = "卦象") -> None:
    upper, lower = hexagram.upper_trigram, hexagram.lower_trigram
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
    console.print("[dim]六爻自下而上阅读；带「变」的为变爻，会影响之卦。[/dim]")
    console.print()

    yao_table = Table(title="六爻（自下而上）", box=box.SIMPLE_HEAD, show_lines=True)
    yao_table.add_column("爻位", style="cyan", justify="center")
    yao_table.add_column("爻值", justify="center")
    yao_table.add_column("性质", justify="center")
    yao_table.add_column("图形", justify="left")
    for yao in hexagram.yaos:
        yao_table.add_row(yao.position_name, str(yao.value), yao.label, _yao_line_display(yao))
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


def display_prompt(prompt: str, *, auto_copy: bool = True) -> bool:
    """展示提示词，并按需自动复制到剪贴板。返回是否复制成功。"""
    console.print()
    console.print(Rule("[bold green]步骤 4/4 · AI 解读提示词[/bold green]", style="green"))
    console.print()
    border = "─" * 40
    console.print(f"[dim]{border}[/dim]")
    console.print(prompt)
    console.print(f"[dim]{border}[/dim]")
    console.print()

    if not auto_copy:
        console.print("[dim]提示：可手动选中上方文本复制[/dim]")
        return False

    if copy_to_clipboard(prompt):
        console.print("[bold green]✓ 已自动复制到剪贴板[/bold green]  [dim]可直接 Ctrl+V 粘贴到大模型[/dim]")
        return True

    console.print("[yellow]自动复制失败[/yellow]  [dim]请手动选中上方文本，Ctrl+C 复制[/dim]")
    return False


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run_interactive() -> None:
    show_disclaimer()
    ensure_runtime()

    config = load_config()
    first_run = not CONFIG_PATH.exists()
    if first_run:
        detected = detect_system_timezone_name()
        config.timezone = detected
        config.region_label = label_for_timezone(detected)

    show_quick_start(console, first_run=first_run)

    ctx, config = setup_user_context(config)
    method = select_method(config.last_method)

    coin_tosses, divination_dt, coin_mode, ctx = collect_divination_params(method, ctx, config)

    show_pre_result_summary(
        console,
        METHOD_LABELS[method],
        ctx.question,
        ctx.tz.region_label,
    )

    result = perform_divination(
        method,
        ctx,
        coin_tosses=coin_tosses,
        divination_datetime=divination_dt,
        coin_mode=coin_mode if method == "coin" else ctx.coin_mode,
        auto_bazi=config.auto_bazi,
    )

    if method == "time":
        console.print(f"\n[dim]{result.method_desc}[/dim]")

    config.coin_mode = coin_mode if method == "coin" else ctx.coin_mode
    config.last_method = method
    config.question = ctx.question
    config.bazi = ctx.bazi
    config.birth_datetime = ctx.birth_datetime
    config.timezone = ctx.tz.iana_name
    config.region_label = ctx.tz.region_label
    config.calendar_mode = ctx.calendar_mode
    save_config(config)
    console.print(f"\n[dim]偏好已保存至 {CONFIG_PATH}[/dim]")

    show_step(console, 4, "查看结果")
    display_hexagram(result.hexagram)
    copied = display_prompt(result.prompt, auto_copy=config.auto_copy_prompt)
    show_completion_guide(console, auto_copied=copied)

    console.print()
    console.print("[dim]是否保存本次占卜？输入 y 保存，直接回车跳过[/dim]")
    if console.input("保存记录？[y/N]: ").strip().lower() in ("y", "yes"):
        record = DivinationRecord(
            question=ctx.question,
            bazi=ctx.bazi,
            birth_datetime=ctx.birth_datetime,
            method=result.method_desc,
            divination_time=result.divination_time,
            timezone=ctx.tz.iana_name,
            hexagram=result.hexagram,
            prompt=result.prompt,
        )
        path = save_record(record)
        console.print(f"[green]✓ 已保存至 {path}[/green]")
        console.print("[dim]日后可用 bagua --list-records 查看[/dim]")

    console.print()
    console.print(Rule(style="dim"))
    console.print("[dim]感谢使用 bagua。愿君子以自强不息。[/dim]")


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_cli_args(argv)
        if not args.interactive:
            return dispatch_headless(args)
        run_interactive()
        return 0
    except KeyboardInterrupt:
        console.print("\n[dim]已取消。下次可直接运行 bagua 继续，或使用 bagua -m random 快速起卦。[/dim]")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())