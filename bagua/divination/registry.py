"""起卦方式注册表与说明文案。

v1.0.0 起卦方式已冻结：本注册表列出的七种方式为稳定 API；
新增起卦体系计划在 v2.0+ 评估（见 docs/DIVINATION_METHODS_PLAN.md）。
"""

from __future__ import annotations

from dataclasses import dataclass

from bagua.data import METHOD_LABELS
from bagua.models import DivinationMethod


@dataclass(frozen=True)
class DivinationMethodInfo:
    key: DivinationMethod
    label: str
    summary: str
    detail: str
    suitable_for: str
    cli_num: str


DIVINATION_METHODS: tuple[DivinationMethodInfo, ...] = (
    DivinationMethodInfo(
        key="coin",
        label=METHOD_LABELS["coin"],
        summary="三枚铜钱掷六次，可手动输入或自动模拟",
        detail="每爻三枚铜钱，1=阳面、2=阴面；点数和 6/7/8/9 对应老阴、少阳、少阴、老阳。",
        suitable_for="想要参与感、传统体验",
        cli_num="1",
    ),
    DivinationMethodInfo(
        key="time",
        label=METHOD_LABELS["time"],
        summary="梅花易数，以年月日时推算卦象",
        detail="公历输入自动换算节气历；可选农历模式与起卦地真太阳时校正。",
        suitable_for="有明确起卦时刻",
        cli_num="2",
    ),
    DivinationMethodInfo(
        key="random",
        label=METHOD_LABELS["random"],
        summary="一键随机生成六爻",
        detail="程序直接抽取六爻值，非传统术数流程；提示词中会标明工具向用途。",
        suitable_for="快速摸鱼、日常灵感",
        cli_num="3",
    ),
    DivinationMethodInfo(
        key="number",
        label=METHOD_LABELS["number"],
        summary="梅花报数，输入 2～3 个正整数",
        detail="上卦＝第一数 mod 8，下卦＝第二数 mod 8；两数时动爻＝(n1+n2) mod 6，三数时动爻＝第三数 mod 6。",
        suitable_for="心中已有数字、测数起卦",
        cli_num="4",
    ),
    DivinationMethodInfo(
        key="manual",
        label=METHOD_LABELS["manual"],
        summary="直接选上卦、下卦与动爻（可无）",
        detail="八卦序号乾1…坤8；动爻可选 1～6，选「无」则为全静卦（7/8）。",
        suitable_for="已知卦象、教学对照",
        cli_num="5",
    ),
    DivinationMethodInfo(
        key="yarrow",
        label=METHOD_LABELS["yarrow"],
        summary="大衍筮法程序模拟（非实体蓍草）",
        detail="五十蓍草取一，用四十九；每爻三变：分二、挂一、揲四、归奇。概率遵循大衍理论分布。",
        suitable_for="体验传统演卦流程",
        cli_num="6",
    ),
    DivinationMethodInfo(
        key="character",
        label=METHOD_LABELS["character"],
        summary="梅花字课，以汉字笔画起卦",
        detail="默认康熙字典笔画；未收录字以码点回退。策略可配置 auto / first_two / first_three / total。",
        suitable_for="测字、一字一词问事",
        cli_num="7",
    ),
)

METHOD_BY_KEY: dict[DivinationMethod, DivinationMethodInfo] = {m.key: m for m in DIVINATION_METHODS}
METHOD_CLI_NUM_TO_KEY: dict[str, DivinationMethod] = {m.cli_num: m.key for m in DIVINATION_METHODS}
METHOD_KEY_TO_CLI_NUM: dict[DivinationMethod, str] = {m.key: m.cli_num for m in DIVINATION_METHODS}


def method_help_text(key: DivinationMethod | None = None) -> str:
    """生成 GUI/文档用的起卦方式说明。"""
    if key is not None:
        info = METHOD_BY_KEY[key]
        return (
            f"{info.label}\n"
            f"{'─' * 24}\n"
            f"{info.summary}\n\n"
            f"{info.detail}\n\n"
            f"适合：{info.suitable_for}"
        )
    blocks: list[str] = []
    for info in DIVINATION_METHODS:
        blocks.append(
            f"【{info.label}】\n"
            f"{info.summary}\n"
            f"{info.detail}\n"
            f"适合：{info.suitable_for}"
        )
    return "\n\n".join(blocks)