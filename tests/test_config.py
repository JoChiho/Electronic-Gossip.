"""配置持久化测试。"""

import json

from bagua.cli import UserConfig, CONFIG_PATH


def test_user_config_roundtrip(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    monkeypatch.setattr("bagua.cli.CONFIG_PATH", config_file)
    monkeypatch.setattr("bagua.cli.BAGUA_DIR", tmp_path)

    cfg = UserConfig(
        timezone="Asia/Tokyo",
        region_label="日本",
        question="测试问题",
        bazi="甲子",
        birth_datetime="1990-01-01 08:00",
        coin_mode="auto",
    )
    cfg.save()

    loaded = UserConfig.load()
    assert loaded.timezone == "Asia/Tokyo"
    assert loaded.question == "测试问题"
    assert loaded.coin_mode == "auto"