"""起卦逻辑单元测试。"""

import random

from bagua.divination import (
    auto_coin_yao_values,
    coin_yao_values_from_tosses,
    divinate_by_time,
    divinate_coin,
    tosses_to_yao_value,
)


def test_tosses_to_yao_value():
    assert tosses_to_yao_value([3, 3, 3]) == 9
    assert tosses_to_yao_value([2, 2, 2]) == 6


def test_coin_yao_values_from_tosses():
    tosses = [[3, 3, 3], [3, 3, 2], [3, 2, 2], [2, 2, 2], [3, 2, 3], [2, 3, 2]]
    assert coin_yao_values_from_tosses(tosses) == [9, 8, 7, 6, 8, 7]


def test_auto_coin_yao_values():
    rng = random.Random(1)
    values = auto_coin_yao_values(rng)
    assert len(values) == 6
    assert all(v in (6, 7, 8, 9) for v in values)


def test_divinate_coin_requires_tosses_for_manual():
    try:
        divinate_coin(coin_mode="manual")
        assert False, "应抛出 ValueError"
    except ValueError:
        pass


def test_divinate_by_time_known_case():
    from datetime import datetime

    from bagua.timezone import get_timezone

    tz = get_timezone("UTC")
    dt = datetime(2026, 6, 24, 14, 30, tzinfo=tz.tzinfo)
    values, desc, _resolved = divinate_by_time(dt, tz=tz)
    assert len(values) == 6
    assert "节气历" in desc


def test_divinate_by_time_lunar_mode():
    from datetime import datetime

    from bagua.timezone import get_timezone

    tz = get_timezone("Asia/Shanghai", "中国")
    dt = datetime(2026, 6, 24, 14, 30, tzinfo=tz.tzinfo)
    values, desc, _resolved = divinate_by_time(
        dt, calendar_mode="lunar", tz=tz,
    )
    assert len(values) == 6
    assert "农历" in desc