# Changelog

本文件记录 bagua 各版本变更，格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [1.0.0] - 2026-06-29

### Added

- **v1.0 稳定版**：七种起卦方式功能冻结（铜钱 / 时间 / 随机 / 数字 / 手动 / 蓍草 / 汉字）
- 发版说明：后续 v1.x 以修复与小改进为主，新起卦体系纳入 v2.0 规划

### Changed

- README 版本历史与功能列表更新至 v1.0
- `docs/PROJECT_STATUS.md`、`docs/WORKFLOW.txt`、`DIVINATION_METHODS_PLAN.md` 标记路线图完成
- 发版检查清单：124 项 pytest 全绿，`check_release` 通过

## [0.12.0] - 2026-06-29

### Added

- **Phase E 横切**：`bagua/divination/` 子模块包 + `DIVINATION_METHODS` 注册表
- CLI 交互步骤 ② 默认沿用 `last_method`（与 GUI 对齐），输入 `n` 可换方式
- GUI「起卦说明」帮助窗口（Notebook 分页，含七种方式详情）
- README / `PROJECT_STATUS` 起卦方式对照表
- 随机起卦与注册表单测补充（`test_divination_registry.py`）

### Changed

- 原 `bagua/divination.py` 拆分为 `coin` / `time` / `number` / `manual` / `random` / `common` / `registry`
- `user_prefs` 起卦序号映射改由注册表统一维护

## [0.11.0] - 2026-06-29

### Added

- **汉字起卦**（梅花字课）：以汉字笔画数起卦，复用梅花 mod 8 / mod 6
- 笔画口径：**康熙字典**（默认）/ **简体**；字表 `bagua/data/strokes.json`
- 未收录字以 Unicode 码点回退取数（method_desc 标注）
- 策略：`auto` / `first_two` / `first_three` / `total`
- CLI：`bagua -m character --chars "问事" --stroke-mode kangxi`；交互选项 7
- GUI：汉字输入 + 策略/笔画 Combobox + 笔画预览
- 模块 `bagua/character.py`、`bagua/stroke_data.py`

## [0.10.2] - 2026-06-29

### Added

- **蓍草法**（大衍筮法程序模拟）：分二、挂一、揲四、归奇，三变得一爻
- 模块 `bagua/yarrow.py`；`divinate_yarrow(rng, record_steps=...)`
- CLI：`bagua -m yarrow`；`--yarrow-show-process` 输出演卦过程；交互选项 6
- GUI：起卦方式「蓍草法」+「显示演卦过程」展开区
- AI 提示词【方法论·大衍蓍草】注明非实体蓍草
- `UserConfig.yarrow_show_process`；`DivinationResult.process_log`

## [0.10.1] - 2026-06-29

### Added

- **手动选卦**：直接指定上卦、下卦（乾1…坤8）与可选动爻
- 无动爻时全静卦（7/8），本卦与之卦相同
- CLI：`bagua -m manual --upper 1 --lower 8 --changing 3`（`--changing 0` 为静卦）
- GUI：上卦/下卦/动爻 Combobox；`UserConfig.manual_upper` / `manual_lower` / `manual_changing`
- AI 提示词【方法论·手动选卦】

## [0.10.0] - 2026-06-29

### Added

- **数字起卦**（梅花报数）：2～3 个正整数起卦，复用梅花 mod 8 / mod 6 规则
- CLI：`bagua -m number --nums "3 8 5"`；交互模式选项 4
- GUI：起卦方式「数字起卦」+ 三数输入区（第三数可选）
- AI 提示词【方法论·梅花报数】；`method_desc` 展示取卦公式
- `UserConfig.number_inputs` 持久化报数

## [0.9.3] - 2026-06-29

### Added

- **六十四卦爻辞全文**（384 条《周易》原文，`yao_texts_data.py`）
- AI 提示词与 Markdown 导出附带爻辞；变爻以 ★ 标注
- 构建脚本 `scripts/build_yao_texts.py`（数据来源 open-iching）

## [0.9.2] - 2026-06-29

### Added

- 历史记录**搜索**：CLI `--list-records --search <关键词>`；GUI 历史窗口搜索框
- 历史记录**导出 Markdown**：`--export-record` / `--export-records`（支持 `-o` 与 `--search` 筛选）
- GUI 历史窗口：「导出所选」「导出列表」按钮
- 模块 `record_markdown.py`：记录转 Markdown 纯逻辑

### Changed

- GUI 主表单：出生/起卦地点与经纬度展示（真太阳时）
- GUI 布局：AI 提示词全宽主区域、复制工具栏

## [0.9.1] - 2026-06-29

### Added

- **出生时区**与**起卦时区**拆分（GUI 时间起卦区 / CLI 分步设置）
- 出生经度 / 起卦经度分开配置；八字与起卦真太阳时独立开关
- 八字排盘支持出生地真太阳时（仅影响八字，不参与卦象演算）

### Changed

- 旧版 `longitude` / `use_true_solar` 配置自动迁移为起卦字段

## [0.9.0] - 2026-06-29

### Added

- 时间起卦：公历输入不变，算卦自动换算**节气历**（立春换年、寅月起算）
- **真太阳时**校正（经度修正 + 时差方程）；设置面板可配经度与开关
- AI 提示词展示用户公历时刻 + 节气历算卦分量，并注明解读口径

### Changed

- 公历时间起卦不再直接用公历月日数字；农历显式输入模式保持原逻辑

## [0.8.1] - 2026-06-29

### Changed

- 拆分 `gui.py`：`gui_app.py`（主窗口）、`gui_forms.py`（表单与配置）、`gui_history.py`、`gui_constants.py`
- CI 接入 `ruff` 静态检查与 `mypy` 类型检查
- 发版脚本增加 `check_release.py` 版本与 CHANGELOG 一致性校验

## [0.8.0] - 2026-06-24

### Added

- CLI/GUI 配置互通：起卦方式、铜钱输入、时间选项跨入口共享
- GUI 设置面板：自动排盘 / 自动复制 / 卦辞开关
- 非交互模式读取 config；`--no-copy` 关闭自动复制
- Windows 安装说明：`docs/WINDOWS_INSTALL.md`

## [0.7.0] - 2026-06-24

### Added

- PyInstaller 双版本：`bagua.exe` + `bagua-gui.exe`
- 构建脚本：`scripts/build.ps1` / `scripts/build.sh`
- Release CI：push tag `v*` 自动构建 zip
- 项目状态文档：`docs/PROJECT_STATUS.md`

## [0.6.0] - 2026-06-24

### Added

- 八字自动排盘：出生时间 → 八字；CLI/GUI 均支持
- 农历时间起卦：`--calendar lunar` / GUI 历法切换
- 卦辞摘要：AI 提示词附带本卦/之卦卦辞要点
- 夏令时提示：tzdata 可用时自动 DST；回退模式明确提示

## [0.5.0] - 2026-06-24

### Added

- CLI 非交互参数：`--method` / `-q` / `--save` / `--copy` 等
- 历史记录管理：`--list-records` / `--show-record` / `--delete-record`
- GUI 历史记录：历史窗口查看、加载提示词、删除
- GUI 卦象 Canvas：六爻图形化绘制
- 剪贴板优化：`clipboard.py` 多平台回退

## [0.4.0] - 2026-06-24

### Added

- Tkinter GUI：图形界面起卦、复制提示词、保存记录
- 双入口：`python -m bagua`（CLI）/ `python -m bagua.gui`（GUI）

## [0.3.0] - 2026-06-24

### Changed

- 架构重构：拆分 service / divination / hexagram 等模块，CLI 瘦身
- `perform_divination()`：CLI 与 GUI 共用统一起卦入口
- 测试增至 20 项：含 test_service.py、test_divination.py

## [0.2.1] - 2026-06-24

### Fixed

- Windows 启动崩溃 `ZoneInfoNotFoundError`：添加 `tzdata` 依赖 + 固定偏移回退

### Changed

- 铜钱法自动模拟；输入改为 `1`/`2`
- 时区地区选择 + 完整标注
- 用户信息持久化至 `~/.bagua/config.json`
- pytest + GitHub Actions CI

[0.9.3]: https://github.com/example/bagua/compare/v0.9.2...v0.9.3
[0.9.2]: https://github.com/example/bagua/compare/v0.9.1...v0.9.2
[0.9.1]: https://github.com/example/bagua/compare/v0.9.0...v0.9.1
[0.9.0]: https://github.com/example/bagua/compare/v0.8.1...v0.9.0
[0.8.1]: https://github.com/example/bagua/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/example/bagua/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/example/bagua/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/example/bagua/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/example/bagua/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/example/bagua/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/example/bagua/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/example/bagua/releases/tag/v0.2.1