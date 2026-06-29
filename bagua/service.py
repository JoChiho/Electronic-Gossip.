"""起卦服务层：CLI / GUI 共用统一入口。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from bagua.bazi import maybe_auto_bazi
from bagua.character import divinate_by_character
from bagua.divination import (
    divinate_by_numbers,
    divinate_by_random,
    divinate_by_time,
    divinate_coin,
    divinate_manual,
)
from bagua.hexagram import build_hexagram
from bagua.models import DivinationMethod, DivinationResult, UserContext
from bagua.prompt import generate_ai_prompt
from bagua.timezone import format_datetime_with_tz, now_in_timezone
from bagua.yarrow import divinate_yarrow

if TYPE_CHECKING:
    from _random import Random


def _format_divination_time_for_prompt(
    *,
    method: DivinationMethod,
    dt: datetime,
    tz,
    calendar_mode: str,
    lunar_input: str | None,
    resolved_note: str | None = None,
) -> str:
    if method != "time":
        return format_datetime_with_tz(dt, tz)

    lines = []
    if resolved_note:
        lines.append(resolved_note)
    else:
        lines.append(format_datetime_with_tz(dt, tz))
        if calendar_mode == "lunar" and lunar_input:
            lines.append(f"农历输入：{lunar_input}")
    return "\n".join(lines)


def _build_time_prompt_note(resolved) -> str:
    parts = [resolved.user_input_note, resolved.calculation_note]
    if resolved.true_solar_note:
        parts.append(resolved.true_solar_note)
    return "\n".join(parts)


def perform_divination(
    method: DivinationMethod,
    context: UserContext,
    *,
    coin_tosses: list[list[int]] | None = None,
    divination_datetime: datetime | None = None,
    number_inputs: list[int] | None = None,
    manual_upper: int | None = None,
    manual_lower: int | None = None,
    manual_changing: int | None = None,
    coin_mode: str = "manual",
    auto_bazi: bool = True,
    yarrow_show_process: bool = False,
    character_text: str | None = None,
    character_strategy: str = "auto",
    character_stroke_mode: str = "kangxi",
    rng: Random | None = None,
) -> DivinationResult:
    """
    执行完整起卦流程并生成 AI 提示词。

    卦象由铜钱/时间/随机算法生成；八字仅写入提示词供 AI 参考，不参与演卦。
    """
    dt_now = now_in_timezone(context.divination_tz)
    prompt_context = context
    bazi_note = ""

    if auto_bazi and not context.bazi.strip() and context.birth_datetime.strip():
        bazi, bazi_note = maybe_auto_bazi(
            context.birth_datetime,
            context.bazi,
            context.birth_tz,
            auto=True,
            longitude=context.birth_longitude,
            use_true_solar=context.use_true_solar_birth,
        )
        if bazi.strip():
            prompt_context = UserContext(
                question=context.question,
                bazi=bazi,
                birth_datetime=context.birth_datetime,
                birth_tz=context.birth_tz,
                divination_tz=context.divination_tz,
                coin_mode=context.coin_mode,
                calendar_mode=context.calendar_mode,
                lunar_input=context.lunar_input,
                include_hexagram_texts=context.include_hexagram_texts,
                birth_longitude=context.birth_longitude,
                divination_longitude=context.divination_longitude,
                use_true_solar_birth=context.use_true_solar_birth,
                use_true_solar_divination=context.use_true_solar_divination,
            )

    process_log: str | None = None

    if method == "coin":
        values, method_desc = divinate_coin(
            coin_tosses=coin_tosses,
            coin_mode=coin_mode,
            rng=rng,
        )
        divination_time = format_datetime_with_tz(dt_now, context.divination_tz)
    elif method == "time":
        dt = divination_datetime or dt_now
        values, method_desc, resolved = divinate_by_time(
            dt,
            calendar_mode=context.calendar_mode,
            lunar_input=context.lunar_input,
            tz=context.divination_tz,
            longitude=context.divination_longitude,
            use_true_solar=context.use_true_solar_divination,
        )
        time_prompt_note = _build_time_prompt_note(resolved)
        divination_time = _format_divination_time_for_prompt(
            method=method,
            dt=dt,
            tz=context.divination_tz,
            calendar_mode=context.calendar_mode,
            lunar_input=context.lunar_input,
            resolved_note=time_prompt_note,
        )
    elif method == "random":
        values, method_desc = divinate_by_random(rng)
        divination_time = format_datetime_with_tz(dt_now, context.divination_tz)
    elif method == "number":
        if not number_inputs or len(number_inputs) not in (2, 3):
            raise ValueError("数字起卦需要 2 或 3 个正整数")
        n1, n2 = number_inputs[0], number_inputs[1]
        n3 = number_inputs[2] if len(number_inputs) == 3 else None
        values, method_desc = divinate_by_numbers(n1, n2, n3)
        divination_time = format_datetime_with_tz(dt_now, context.divination_tz)
    elif method == "manual":
        if manual_upper is None or manual_lower is None:
            raise ValueError("手动选卦需要指定上卦与下卦（1～8）")
        changing = None if not manual_changing else manual_changing
        values, method_desc = divinate_manual(manual_upper, manual_lower, changing)
        divination_time = format_datetime_with_tz(dt_now, context.divination_tz)
    elif method == "yarrow":
        values, method_desc, process_log = divinate_yarrow(
            rng,
            record_steps=yarrow_show_process,
        )
        divination_time = format_datetime_with_tz(dt_now, context.divination_tz)
    elif method == "character":
        if not character_text or not character_text.strip():
            raise ValueError("汉字起卦需要输入汉字")
        values, method_desc = divinate_by_character(
            character_text,
            strategy=character_strategy,
            stroke_mode=character_stroke_mode,
        )
        divination_time = format_datetime_with_tz(dt_now, context.divination_tz)
    else:
        raise ValueError(f"未知起卦方式: {method}")

    hexagram = build_hexagram(values)
    prompt = generate_ai_prompt(
        prompt_context,
        method_desc,
        divination_time,
        hexagram,
        time_uses_solar_term=context.calendar_mode == "solar",
        bazi_true_solar_note=bazi_note,
    )

    return DivinationResult(
        yao_values=values,
        hexagram=hexagram,
        method_desc=method_desc,
        divination_time=divination_time,
        prompt=prompt,
        process_log=process_log,
    )