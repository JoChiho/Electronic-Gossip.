"""卦象计算测试。"""

from bagua.cli import build_hexagram, parse_coin_input


def test_pure_yang_hexagram():
    h = build_hexagram([7, 7, 7, 7, 7, 7])
    assert h.name == "乾为天"
    assert not h.has_changing


def test_changing_lines():
    h = build_hexagram([7, 8, 9, 6, 7, 8])
    assert h.has_changing
    assert h.changed_hexagram is not None
    assert h.changed_hexagram.name == "泽雷随"


def test_coin_input_121():
    assert parse_coin_input("1 2 1") == [3, 2, 3]


def test_coin_input_invalid():
    assert parse_coin_input("1 2") is None
    assert parse_coin_input("a b c") is None