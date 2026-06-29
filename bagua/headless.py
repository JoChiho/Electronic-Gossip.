"""CLI 非交互模式与记录管理命令。"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.table import Table

from bagua.args import CliArgs
from bagua.character import parse_character_input
from bagua.clipboard import copy_to_clipboard
from bagua.config import build_user_context, load_config, save_config
from bagua.divination import parse_manual_changing, parse_number_input
from bagua.gui_display import format_hexagram_display
from bagua.models import DivinationRecord, UserConfig, UserContext
from bagua.records import (
    delete_record,
    export_record_markdown,
    export_records_markdown,
    list_records,
    load_record_json,
    save_record,
    search_records,
)
from bagua.service import perform_divination
from bagua.timezone import label_for_timezone, parse_datetime_input
from bagua.user_prefs import stored_coin_tosses_to_points

console = Console()
stderr_console = Console(stderr=True)


def _config_to_context(config: UserConfig, args: CliArgs) -> UserContext:
    if args.timezone:
        config.timezone = args.timezone
        config.region_label = label_for_timezone(args.timezone)
    if getattr(args, "divination_timezone", None):
        config.divination_timezone = args.divination_timezone
        config.divination_region_label = label_for_timezone(args.divination_timezone)

    calendar_mode = args.calendar or config.calendar_mode
    lunar_input = args.lunar_at
    if lunar_input is None and calendar_mode == "lunar" and config.time_input:
        lunar_input = config.time_input

    ctx = build_user_context(config, calendar_mode=calendar_mode, lunar_input=lunar_input)

    overrides: dict = {}
    if args.question is not None:
        overrides["question"] = args.question
    if args.bazi is not None:
        overrides["bazi"] = args.bazi
    if args.birth_datetime is not None:
        overrides["birth_datetime"] = args.birth_datetime
    if args.coin_mode:
        overrides["coin_mode"] = args.coin_mode
    if overrides:
        ctx = UserContext(**{**ctx.__dict__, **overrides})
    return ctx


def _resolve_divination_datetime(
    args: CliArgs,
    config: UserConfig,
    ctx: UserContext,
) -> tuple[object | None, str | None]:
    """解析时间起卦时刻，返回 (divination_dt, lunar_input)。"""
    if args.method != "time":
        return None, ctx.lunar_input

    if ctx.calendar_mode == "lunar":
        from bagua.lunar_util import parse_lunar_datetime_input

        if args.lunar_at:
            if parse_lunar_datetime_input(args.lunar_at) is None:
                raise ValueError(f"农历时间格式无效：{args.lunar_at}")
            return None, args.lunar_at
        if ctx.lunar_input and parse_lunar_datetime_input(ctx.lunar_input):
            return None, ctx.lunar_input
        if config.use_current_time:
            return None, None
        raise ValueError("农历起卦需 --lunar-at 或在 config.json 中设置 time_input")

    if args.at:
        dt = parse_datetime_input(args.at, ctx.divination_tz)
        if dt is None:
            raise ValueError(f"时间格式无效：{args.at}")
        return dt, None
    if config.use_current_time:
        return None, None
    if config.time_input:
        dt = parse_datetime_input(config.time_input, ctx.divination_tz)
        if dt is None:
            raise ValueError(f"config 中 time_input 无效：{config.time_input}")
        return dt, None
    return None, None


def _resolve_number_inputs(args: CliArgs, config: UserConfig) -> list[int] | None:
    if args.method != "number":
        return None
    if args.nums:
        numbers = parse_number_input(args.nums)
        if numbers is None:
            raise ValueError(f'数字格式无效：{args.nums}，请使用 2～3 个正整数，如 "3 8 5"')
        return numbers
    stored = [s.strip() for s in (config.number_inputs or []) if s.strip()]
    if len(stored) == 3:
        numbers = parse_number_input(" ".join(stored))
        if numbers is not None:
            return numbers
    if len(stored) >= 2:
        numbers = parse_number_input(" ".join(stored[:2]))
        if numbers is not None:
            return numbers
    raise ValueError(
        '数字起卦需要 --nums "3 8 5" 或在 config.json 中设置有效的 number_inputs'
    )


def _resolve_manual_selection(
    args: CliArgs,
    config: UserConfig,
) -> tuple[int, int, int | None]:
    if args.method != "manual":
        raise ValueError("internal: manual selection resolver called for wrong method")

    upper = args.upper if args.upper is not None else config.manual_upper
    lower = args.lower if args.lower is not None else config.manual_lower
    changing_raw = args.changing if args.changing is not None else config.manual_changing

    if not 1 <= upper <= 8 or not 1 <= lower <= 8:
        raise ValueError("上卦与下卦序号须在 1～8（乾1…坤8）")

    changing = parse_manual_changing(changing_raw)
    if changing is None and changing_raw not in (None, 0, "0"):
        if isinstance(changing_raw, int) or (isinstance(changing_raw, str) and changing_raw.strip().isdigit()):
            raise ValueError("动爻须在 1～6，或 0 表示无动爻")
        raise ValueError(f"动爻无效：{changing_raw}")

    if args.upper is None and args.lower is None and args.changing is None:
        if not 1 <= config.manual_upper <= 8 or not 1 <= config.manual_lower <= 8:
            raise ValueError(
                "手动选卦需要 --upper / --lower，或在 config.json 中设置 manual_upper / manual_lower"
            )

    return upper, lower, changing


def _resolve_character_options(
    args: CliArgs,
    config: UserConfig,
) -> tuple[str, str, str]:
    if args.method != "character":
        raise ValueError("internal: character resolver called for wrong method")

    text = args.chars or config.character_input
    parsed = parse_character_input(text or "")
    if parsed is None:
        raise ValueError('汉字起卦需要 --chars "问事" 或在 config.json 中设置 character_input')

    strategy = args.char_strategy or config.character_strategy or "auto"
    stroke_mode = args.stroke_mode or config.character_stroke_mode or "kangxi"
    return parsed, strategy, stroke_mode


def _resolve_coin_tosses(args: CliArgs, config: UserConfig) -> list[list[int]] | None:
    coin_mode = args.coin_mode or config.coin_mode
    if args.method != "coin" or coin_mode != "manual":
        return None
    tosses = stored_coin_tosses_to_points(config.coin_tosses)
    if tosses is None:
        raise ValueError(
            "铜钱手动模式需要 config.json 中有效的 coin_tosses，"
            "请先在 CLI/GUI 录入，或使用 --coin-mode auto"
        )
    return tosses


def _should_copy(args: CliArgs, config: UserConfig) -> bool:
    if args.no_copy:
        return False
    if args.copy:
        return True
    return config.auto_copy_prompt


def _update_config_from_args(
    config: UserConfig,
    args: CliArgs,
    ctx: UserContext,
) -> UserConfig:
    config.question = ctx.question
    config.bazi = ctx.bazi
    config.birth_datetime = ctx.birth_datetime
    config.timezone = ctx.birth_tz.iana_name
    config.region_label = ctx.birth_tz.region_label
    config.divination_timezone = ctx.divination_tz.iana_name
    config.divination_region_label = ctx.divination_tz.region_label
    if args.method:
        config.last_method = args.method
    if args.method == "coin" and args.coin_mode:
        config.coin_mode = args.coin_mode
    if args.method == "number" and args.nums:
        numbers = parse_number_input(args.nums)
        if numbers:
            padded = [str(n) for n in numbers]
            while len(padded) < 3:
                padded.append("")
            config.number_inputs = padded[:3]
    if args.method == "manual":
        if args.upper is not None:
            config.manual_upper = args.upper
        if args.lower is not None:
            config.manual_lower = args.lower
        if args.changing is not None:
            config.manual_changing = args.changing
    if args.calendar:
        config.calendar_mode = args.calendar
    if args.auto_bazi is not None:
        config.auto_bazi = args.auto_bazi
    if args.yarrow_show_process is not None:
        config.yarrow_show_process = args.yarrow_show_process
    if args.method == "character":
        if args.chars:
            parsed = parse_character_input(args.chars)
            if parsed:
                config.character_input = parsed
        if args.char_strategy:
            config.character_strategy = args.char_strategy
        if args.stroke_mode:
            config.character_stroke_mode = args.stroke_mode
    return config


def run_list_records(*, search: str | None = None) -> int:
    records = search_records(search) if search and search.strip() else list_records()
    if not records:
        if search and search.strip():
            console.print(f"[dim]未找到匹配「{search}」的记录。[/dim]")
        else:
            console.print("[dim]暂无占卜记录。[/dim]")
        return 0

    title = "占卜历史记录"
    if search and search.strip():
        title = f"占卜历史记录 · 搜索「{search.strip()}」"
    table = Table(title=title, show_lines=True)
    table.add_column("#", justify="right", style="cyan")
    table.add_column("时间", style="dim")
    table.add_column("卦名")
    table.add_column("问题")
    table.add_column("文件", style="dim")

    for i, rec in enumerate(records, start=1):
        table.add_row(
            str(i),
            rec.saved_at or rec.divination_time,
            rec.hexagram_name,
            rec.question or "（无）",
            rec.filename,
        )
    console.print(table)
    console.print("[dim]查看：bagua --show-record <序号或文件名>[/dim]")
    console.print("[dim]导出：bagua --export-record <ID> -o out.md[/dim]")
    return 0


def run_export_record(identifier: str, *, output: str | None = None) -> int:
    out_path = Path(output).expanduser() if output else None
    path = export_record_markdown(identifier, out_path)
    if path is None:
        console.print(f"[red]未找到记录或导出失败：{identifier}[/red]")
        return 1
    console.print(f"[green]已导出 Markdown：{path}[/green]")
    return 0


def run_export_records(*, search: str | None = None, output: str | None = None) -> int:
    out_path = Path(output).expanduser() if output else None
    path = export_records_markdown(query=search, output_path=out_path)
    if path is None:
        if search and search.strip():
            console.print(f"[dim]未找到匹配「{search}」的记录，未生成文件。[/dim]")
        else:
            console.print("[dim]暂无占卜记录可导出。[/dim]")
        return 1
    console.print(f"[green]已导出 {path}[/green]")
    return 0


def run_show_record(identifier: str) -> int:
    data = load_record_json(identifier)
    if data is None:
        console.print(f"[red]未找到记录：{identifier}[/red]")
        return 1

    console.print(f"[bold]起卦时间[/bold]：{data.get('divination_time', '')}")
    console.print(f"[bold]起卦方法[/bold]：{data.get('method', '')}")
    console.print(f"[bold]问题[/bold]：{data.get('question', '')}")
    hexagram = data.get("hexagram", {})
    console.print(f"[bold]卦名[/bold]：{hexagram.get('name', '')}")
    console.print()
    console.print(data.get("prompt", ""))
    return 0


def run_delete_record(identifier: str) -> int:
    path = delete_record(identifier)
    if path is None:
        console.print(f"[red]未找到记录：{identifier}[/red]")
        return 1
    console.print(f"[green]已删除：{path.name}[/green]")
    return 0


def run_headless_divination(args: CliArgs) -> int:
    if args.method is None:
        console.print("[red]非交互起卦需要 --method[/red]")
        return 1

    config = load_config()
    ctx = _config_to_context(config, args)

    try:
        divination_dt, lunar_input = _resolve_divination_datetime(args, config, ctx)
        coin_tosses = _resolve_coin_tosses(args, config)
        number_inputs = _resolve_number_inputs(args, config)
        manual_upper = manual_lower = manual_changing = None
        if args.method == "manual":
            manual_upper, manual_lower, manual_changing = _resolve_manual_selection(args, config)
        character_text = character_strategy = character_stroke_mode = None
        if args.method == "character":
            character_text, character_strategy, character_stroke_mode = _resolve_character_options(
                args, config,
            )
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1

    if lunar_input and lunar_input != ctx.lunar_input:
        ctx = UserContext(
            question=ctx.question,
            bazi=ctx.bazi,
            birth_datetime=ctx.birth_datetime,
            birth_tz=ctx.birth_tz,
            divination_tz=ctx.divination_tz,
            coin_mode=ctx.coin_mode,
            calendar_mode=ctx.calendar_mode,
            lunar_input=lunar_input,
            include_hexagram_texts=ctx.include_hexagram_texts,
            birth_longitude=ctx.birth_longitude,
            divination_longitude=ctx.divination_longitude,
            use_true_solar_birth=ctx.use_true_solar_birth,
            use_true_solar_divination=ctx.use_true_solar_divination,
        )

    auto_bazi = config.auto_bazi if args.auto_bazi is None else args.auto_bazi
    coin_mode = args.coin_mode or config.coin_mode
    yarrow_show_process = (
        config.yarrow_show_process
        if args.yarrow_show_process is None
        else args.yarrow_show_process
    )
    result = perform_divination(
        args.method,
        ctx,
        coin_tosses=coin_tosses,
        divination_datetime=divination_dt,
        number_inputs=number_inputs,
        manual_upper=manual_upper,
        manual_lower=manual_lower,
        manual_changing=manual_changing,
        coin_mode=coin_mode,
        auto_bazi=auto_bazi,
        yarrow_show_process=yarrow_show_process,
        character_text=character_text,
        character_strategy=character_strategy or "auto",
        character_stroke_mode=character_stroke_mode or "kangxi",
    )

    config = _update_config_from_args(config, args, ctx)
    save_config(config)

    if args.output == "prompt":
        console.print(result.prompt)
    elif args.output == "hexagram":
        console.print(format_hexagram_display(result.hexagram))
    else:
        console.print(f"起卦时间：{result.divination_time}")
        console.print(f"起卦方法：{result.method_desc}")
        console.print()
        console.print(format_hexagram_display(result.hexagram))
        if result.process_log:
            console.print()
            console.print(result.process_log)
        console.print()
        console.print(result.prompt)

    if _should_copy(args, config):
        if copy_to_clipboard(result.prompt):
            stderr_console.print("\n[green]提示词已复制到剪贴板[/green]")
        else:
            stderr_console.print("\n[yellow]剪贴板复制失败[/yellow]")

    if args.save_record:
        path = save_record(
            DivinationRecord(
                question=ctx.question,
                bazi=ctx.bazi,
                birth_datetime=ctx.birth_datetime,
                method=result.method_desc,
                divination_time=result.divination_time,
                timezone=ctx.divination_tz.iana_name,
                hexagram=result.hexagram,
                prompt=result.prompt,
            )
        )
        stderr_console.print(f"[green]已保存至 {path}[/green]")

    return 0


def dispatch_headless(args: CliArgs) -> int:
    if args.list_records:
        return run_list_records(search=args.search)
    if args.export_record:
        return run_export_record(args.export_record, output=args.markdown_out)
    if args.export_records:
        return run_export_records(search=args.search, output=args.markdown_out)
    if args.show_record:
        return run_show_record(args.show_record)
    if args.delete_record:
        return run_delete_record(args.delete_record)
    if args.method:
        return run_headless_divination(args)
    return 1