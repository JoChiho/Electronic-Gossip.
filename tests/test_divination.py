"""起卦逻辑单元测试。"""

import random

from bagua.divination import (
    auto_coin_yao_values,
    coin_yao_values_from_tosses,
    divinate_by_numbers,
    divinate_by_random,
    divinate_by_time,
    divinate_coin,
    divinate_manual,
    parse_manual_changing,
    parse_number_input,
    parse_trigram_index,
    tosses_to_yao_value,
)
from bagua.hexagram import build_hexagram


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


def test_parse_number_input():
    assert parse_number_input("3 8 5") == [3, 8, 5]
    assert parse_number_input("3,8") == [3, 8]
    assert parse_number_input("3 8 0") is None
    assert parse_number_input("3") is None


def test_divinate_by_numbers_three_inputs():
    values, desc = divinate_by_numbers(3, 8, 5)
    assert values == [8, 8, 8, 7, 6, 7]
    assert build_hexagram(values).name == "火地晋"
    assert "离" in desc
    assert "坤" in desc
    assert "第5爻" in desc


def test_divinate_by_numbers_two_inputs():
    values, desc = divinate_by_numbers(3, 8)
    assert values == [8, 8, 8, 7, 6, 7]
    assert "(3+8)=11" in desc
    assert "第5爻" in desc


def test_parse_trigram_index():
    assert parse_trigram_index("1") == 1
    assert parse_trigram_index("1 乾 ☰") == 1
    assert parse_trigram_index("坤") == 8


def test_parse_manual_changing():
    assert parse_manual_changing(0) is None
    assert parse_manual_changing(3) == 3
    assert parse_manual_changing("三爻") == 3
    assert parse_manual_changing("无（静卦）") is None


def test_divinate_manual_qian_upper_kun_lower_line3():
    values, desc = divinate_manual(1, 8, 3)
    assert values == [8, 8, 6, 7, 7, 7]
    hexagram = build_hexagram(values)
    assert hexagram.name == "天地否"
    assert hexagram.changed_hexagram is not None
    assert hexagram.changed_hexagram.name == "天山遁"
    assert "乾" in desc and "坤" in desc


def test_divinate_manual_pure_qian_static():
    values, desc = divinate_manual(1, 1, None)
    assert values == [7, 7, 7, 7, 7, 7]
    hexagram = build_hexagram(values)
    assert hexagram.name == "乾为天"
    assert hexagram.changed_hexagram is None
    assert "无动爻" in desc


def test_divinate_by_time_formula_in_desc():
    from datetime import datetime

    from bagua.timezone import get_timezone

    tz = get_timezone("UTC")
    dt = datetime(2026, 1, 15, 9, 0, tzinfo=tz.tzinfo)
    _values, desc, _resolved = divinate_by_time(dt, tz=tz)
    assert "动爻第" in desc
    assert "上卦" in desc or "→上卦" in desc


def test_divinate_by_random_from_divination_module():
    rng = random.Random(99)
    values, desc = divinate_by_random(rng)
    assert len(values) == 6
    assert desc == "随机起卦"


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