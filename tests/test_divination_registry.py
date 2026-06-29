"""起卦注册表与随机起卦测试。"""

import random

from bagua.divination import DIVINATION_METHODS, divinate_by_random, method_help_text
from bagua.divination.registry import METHOD_BY_KEY, METHOD_CLI_NUM_TO_KEY


def test_divination_methods_registry_complete():
    keys = {m.key for m in DIVINATION_METHODS}
    assert keys == {"coin", "time", "random", "number", "manual", "yarrow", "character"}
    assert len(METHOD_CLI_NUM_TO_KEY) == 7
    assert METHOD_BY_KEY["coin"].cli_num == "1"


def test_method_help_text_all_and_single():
    all_text = method_help_text()
    assert "铜钱法" in all_text
    assert "汉字起卦" in all_text
    coin_text = method_help_text("coin")
    assert "三枚铜钱" in coin_text
    assert "铜钱法" in coin_text


def test_divinate_by_random_length():
    values, desc = divinate_by_random()
    assert len(values) == 6
    assert all(v in (6, 7, 8, 9) for v in values)
    assert desc == "随机起卦"


def test_divinate_by_random_reproducible():
    rng1 = random.Random(7)
    rng2 = random.Random(7)
    v1, _ = divinate_by_random(rng1)
    v2, _ = divinate_by_random(rng2)
    assert v1 == v2


def test_divinate_by_random_distribution_sample():
    rng = random.Random(0)
    counter = {6: 0, 7: 0, 8: 0, 9: 0}
    for _ in range(600):
        values, _ = divinate_by_random(rng)
        for v in values:
            counter[v] += 1
    assert all(count > 0 for count in counter.values())