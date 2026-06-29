"""时间起卦（梅花易数）。"""

from __future__ import annotations

from datetime import datetime

from bagua.data import METHOD_LABELS
from bagua.divination.common import (
    lines_from_trigrams,
    meihua_changing_line,
    meihua_trigram_number,
    trigram_by_number,
)
from bagua.lunar_util import (
    CalendarMode,
    ResolvedTimeComponents,
    resolve_time_divination_components,
)
from bagua.timezone import TimezoneInfo


def divinate_by_time(
    dt: datetime,
    *,
    calendar_mode: CalendarMode = "solar",
    lunar_input: str | None = None,
    tz: TimezoneInfo | None = None,
    longitude: float | None = None,
    use_true_solar: bool = True,
) -> tuple[list[int], str, ResolvedTimeComponents]:
    resolved = resolve_time_divination_components(
        dt,
        calendar_mode=calendar_mode,
        lunar_input=lunar_input,
        tz=tz,
        longitude=longitude,
        use_true_solar=use_true_solar,
    )
    year, month, day, hour = resolved.year, resolved.month, resolved.day, resolved.hour

    upper_num = meihua_trigram_number(year + month + day)
    lower_num = meihua_trigram_number(year + month + day + hour)
    changing = meihua_changing_line(year + month + day + hour)

    lower = trigram_by_number(lower_num)
    upper = trigram_by_number(upper_num)
    values = lines_from_trigrams(lower, upper, changing)

    sum_ymd = year + month + day
    sum_ymdh = sum_ymd + hour
    formula = (
        f"年{year}+月{month}+日{day}={sum_ymd}→上卦{upper['name']}；"
        f"加时{hour}={sum_ymdh}→下卦{lower['name']}，动爻第{changing}爻"
    )
    mode_label = "农历" if calendar_mode == "lunar" else "公历输入·节气历算卦"
    detail = f"{resolved.user_input_note}；{resolved.calculation_note}；梅花易数：{formula}"
    if resolved.true_solar_note:
        detail = f"{detail}；{resolved.true_solar_note}"
    method_desc = f"{METHOD_LABELS['time']}（{mode_label}：{detail}）"
    return values, method_desc, resolved