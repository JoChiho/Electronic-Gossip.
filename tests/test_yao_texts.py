"""爻辞数据测试。"""

from bagua.data import HEXAGRAM_NAMES
from bagua.yao_texts import format_yao_texts_block, get_hexagram_yao_texts, get_yao_text
from bagua.yao_texts_data import YAO_TEXTS


def test_all_hexagrams_have_six_yao_texts():
    names = {HEXAGRAM_NAMES[u][l] for u in range(8) for l in range(8)}
    assert set(YAO_TEXTS.keys()) == names
    for name, texts in YAO_TEXTS.items():
        assert len(texts) == 6, name


def test_get_yao_text_qian():
    assert get_yao_text("乾为天", 1) == "潜龙，勿用。"
    assert get_hexagram_yao_texts("乾为天")[5] == "亢龙有悔。"


def test_format_yao_texts_highlight():
    lines = format_yao_texts_block("乾为天", highlight_positions={1, 6})
    assert any("初爻 ★" in line for line in lines)
    assert any("上爻 ★" in line for line in lines)


def test_prompt_includes_yao_texts():
    from datetime import datetime

    from bagua.models import UserContext
    from bagua.service import perform_divination
    from bagua.timezone import get_timezone

    tz = get_timezone("UTC")
    ctx = UserContext(
        question="测试",
        bazi="",
        birth_datetime="",
        birth_tz=tz,
        divination_tz=tz,
        coin_mode="manual",
        include_hexagram_texts=True,
    )
    dt = datetime(2026, 6, 24, 14, 30, tzinfo=tz.tzinfo)
    result = perform_divination("time", ctx, divination_datetime=dt)
    assert "爻辞（《周易》原文）" in result.prompt
    assert "潜龙" in result.prompt or "元亨" in result.prompt