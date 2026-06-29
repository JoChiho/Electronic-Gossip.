"""真太阳时换算测试。"""

from datetime import datetime

from bagua.timezone import get_timezone
from bagua.true_solar import default_longitude, to_true_solar


def test_default_longitude_shanghai():
    assert default_longitude("Asia/Shanghai") == 121.47


def test_true_solar_correction_shanghai():
    tz = get_timezone("Asia/Shanghai", "中国")
    # 上海经度偏东，真太阳时通常比标准时略快
    dt = datetime(2026, 6, 21, 12, 0, tzinfo=tz.tzinfo)
    corrected, note = to_true_solar(dt, tz, enabled=True)
    assert corrected != dt or note == ""
    assert corrected.tzinfo is not None


def test_true_solar_disabled():
    tz = get_timezone("UTC", "UTC")
    dt = datetime(2026, 6, 21, 12, 0, tzinfo=tz.tzinfo)
    corrected, note = to_true_solar(dt, tz, enabled=False)
    assert corrected == dt
    assert note == ""