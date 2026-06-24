"""GUI 展示格式化测试。"""

from bagua.gui_display import format_hexagram_display, yao_line_text
from bagua.hexagram import build_hexagram
from bagua.models import YaoInfo


def test_yao_line_text():
    yang = YaoInfo(1, 9, True, True)
    yin = YaoInfo(2, 8, False, False)
    assert "━━━━━━" in yao_line_text(yang)
    assert "○变" in yao_line_text(yang)
    assert "──────" in yao_line_text(yin)


def test_format_hexagram_display():
    h = build_hexagram([7, 7, 7, 7, 7, 7])
    text = format_hexagram_display(h)
    assert "乾为天" in text
    assert "上卦" in text
    assert "六爻" in text