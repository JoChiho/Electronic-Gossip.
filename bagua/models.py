"""领域数据模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from bagua.data import YAO_POSITIONS, YAO_VALUE_NAMES
from bagua.timezone import TimezoneInfo

DivinationMethod = Literal["coin", "time", "random"]
CoinMode = Literal["manual", "auto"]


@dataclass
class UserConfig:
    timezone: str = "Asia/Shanghai"
    region_label: str = "中国（北京时间 UTC+8）"
    question: str = ""
    bazi: str = ""
    birth_datetime: str = ""
    coin_mode: str = "manual"
    auto_copy_prompt: bool = True
    calendar_mode: str = "solar"
    auto_bazi: bool = True
    include_hexagram_texts: bool = True
    last_method: str = "coin"
    use_current_time: bool = True
    time_input: str = ""
    coin_tosses: list[list[str]] = field(
        default_factory=lambda: [["1", "1", "1"] for _ in range(6)]
    )
    longitude: float | None = None
    use_true_solar: bool = True


@dataclass
class UserContext:
    question: str
    bazi: str
    birth_datetime: str
    tz: TimezoneInfo
    coin_mode: str
    calendar_mode: str = "solar"
    lunar_input: str | None = None
    include_hexagram_texts: bool = True
    longitude: float | None = None
    use_true_solar: bool = True


@dataclass
class YaoInfo:
    position: int
    value: int
    is_yang: bool
    is_changing: bool

    @property
    def label(self) -> str:
        return YAO_VALUE_NAMES[self.value]

    @property
    def position_name(self) -> str:
        return YAO_POSITIONS[self.position - 1]


@dataclass
class HexagramInfo:
    name: str
    upper_trigram: dict
    lower_trigram: dict
    yaos: list[YaoInfo]
    changing_positions: list[int] = field(default_factory=list)
    changed_hexagram: HexagramInfo | None = None

    @property
    def has_changing(self) -> bool:
        return bool(self.changing_positions)


@dataclass
class DivinationRecord:
    question: str
    bazi: str
    birth_datetime: str
    method: str
    divination_time: str
    timezone: str
    hexagram: HexagramInfo
    prompt: str


@dataclass
class DivinationResult:
    """起卦服务层统一返回结构。"""

    yao_values: list[int]
    hexagram: HexagramInfo
    method_desc: str
    divination_time: str
    prompt: str