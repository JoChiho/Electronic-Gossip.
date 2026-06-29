"""节气历起卦分量测试。"""

from datetime import datetime

from bagua.lunar_util import (
    resolve_time_divination_components,
    solar_term_components_from_datetime,
)
from bagua.timezone import get_timezone


def test_solar_term_month_changes_at_lichun():
    tz = get_timezone("Asia/Shanghai", "中国")
    before = datetime(2026, 2, 3, 12, 0, tzinfo=tz.tzinfo)
    after = datetime(2026, 2, 4, 12, 0, tzinfo=tz.tzinfo)
    st_before = solar_term_components_from_datetime(before)
    st_after = solar_term_components_from_datetime(after)
    assert st_before.month == 12
    assert st_after.month == 1
    assert st_before.year_gan_zhi != st_after.year_gan_zhi


def test_solar_mode_uses_solar_term_in_prompt_notes():
    tz = get_timezone("Asia/Shanghai", "中国")
    dt = datetime(2026, 6, 24, 14, 30, tzinfo=tz.tzinfo)
    resolved = resolve_time_divination_components(
        dt,
        calendar_mode="solar",
        tz=tz,
        use_true_solar=True,
    )
    assert "用户公历" in resolved.user_input_note
    assert "节气历" in resolved.calculation_note
    assert resolved.year > 0 and 1 <= resolved.month <= 12