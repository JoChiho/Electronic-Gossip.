"""bagua — 极简易经八卦占卜 CLI 工具。"""

__version__ = "0.9.0"

from bagua.divination import parse_coin_input
from bagua.hexagram import build_hexagram
from bagua.models import UserConfig
from bagua.service import perform_divination

__all__ = [
    "__version__",
    "UserConfig",
    "build_hexagram",
    "parse_coin_input",
    "perform_divination",
]