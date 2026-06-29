"""起卦服务层测试。"""

import random
from datetime import datetime

from bagua.models import UserContext
from bagua.service import perform_divination
from bagua.timezone import get_timezone


def _ctx() -> UserContext:
    tz = get_timezone("Asia/Shanghai", "中国")
    return UserContext(
        question="工作运势",
        bazi="甲子",
        birth_datetime="1990-01-01 08:00",
        tz=tz,
        coin_mode="manual",
    )


def test_perform_divination_random():
    rng = random.Random(42)
    result = perform_divination("random", _ctx(), rng=rng)
    assert len(result.yao_values) == 6
    assert result.hexagram.name
    assert "随机起卦" in result.method_desc
    assert "工作运势" in result.prompt
    assert "Asia/Shanghai" in result.divination_time


def test_perform_divination_coin_manual():
    tosses = [[3, 3, 3], [3, 2, 2], [2, 2, 2], [3, 3, 2], [2, 3, 3], [3, 2, 3]]
    result = perform_divination("coin", _ctx(), coin_tosses=tosses, coin_mode="manual")
    assert result.yao_values == [9, 7, 6, 8, 8, 8]
    assert "手动投掷" in result.method_desc


def test_perform_divination_coin_auto():
    rng = random.Random(0)
    result = perform_divination("coin", _ctx(), coin_mode="auto", rng=rng)
    assert len(result.yao_values) == 6
    assert "自动模拟" in result.method_desc


def test_perform_divination_time():
    tz = get_timezone("UTC", "UTC")
    ctx = UserContext(question="", bazi="", birth_datetime="", tz=tz, coin_mode="manual")
    dt = datetime(2026, 6, 24, 14, 30, tzinfo=tz.tzinfo)
    result = perform_divination("time", ctx, divination_datetime=dt)
    assert result.hexagram.name
    assert "时间起卦" in result.method_desc
    assert "节气历" in result.method_desc
    assert "用户公历" in result.divination_time
    assert "节气历" in result.prompt


def test_perform_divination_auto_bazi():
    tz = get_timezone("Asia/Shanghai", "中国")
    ctx = UserContext(
        question="测试",
        bazi="",
        birth_datetime="1990-05-15 08:30",
        tz=tz,
        coin_mode="manual",
    )
    result = perform_divination("random", ctx, rng=random.Random(1), auto_bazi=True)
    assert "庚午" in result.prompt


def test_prompt_includes_hexagram_text():
    tz = get_timezone("UTC", "UTC")
    ctx = UserContext(
        question="",
        bazi="",
        birth_datetime="",
        tz=tz,
        coin_mode="manual",
        include_hexagram_texts=True,
    )
    dt = datetime(2026, 6, 24, 14, 30, tzinfo=tz.tzinfo)
    result = perform_divination("time", ctx, divination_datetime=dt)
    assert "卦辞摘要" in result.prompt