"""随机起卦（工具向，非传统术数）。"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from bagua.data import METHOD_LABELS

if TYPE_CHECKING:
    from _random import Random


def divinate_by_random(rng: Random | None = None) -> tuple[list[int], str]:
    r = rng or random
    return [r.choice([6, 7, 8, 9]) for _ in range(6)], METHOD_LABELS["random"]