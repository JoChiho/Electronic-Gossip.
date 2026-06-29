# bagua 项目状态（持续更新）

> 本文档记录项目现状、版本历史、已知限制与后续方向。  
> 每次发版或完成重要里程碑后请更新本节。  
> 最后更新：**2026-06-29** · 维护人：开发团队

---

## 快速概览

| 项目 | 说明 |
|------|------|
| 名称 | **bagua** — 易经八卦占卜 CLI/GUI |
| 当前版本 | **v1.0.0**（稳定版） |
| 定位 | 起卦 → 生成 AI 提示词 → 用户自行粘贴大模型解读 |
| 入口 | `bagua`（CLI）/ `bagua-gui`（GUI）/ `dist/*.exe`（Windows 免安装） |
| 测试 | pytest **120+** 项（目标：发版前全绿） |
| 路线图 | 阶段 0–5 + 起卦扩展 Phase A–E 已完成；v1.x 维护模式 |

---

## 架构一览

```
展示层   cli.py · cli_guide.py · gui_app.py · gui_forms.py · gui_history.py · headless.py
服务层   service.perform_divination()
逻辑层   divination/ · hexagram · prompt · bazi · lunar_util · yarrow · character
数据层   data · hexagram_texts · models
基础设施 config · records · timezone · clipboard
```

**原则**：逻辑层不依赖 Rich/ Tkinter；CLI 与 GUI 共用服务层，不重复实现起卦算法。

---

## 已交付功能

### 起卦与易学

- 铜钱法（手动 1/2、自动模拟）
- 时间起卦（公历 / 农历梅花易数）
- 随机起卦
- 数字起卦（梅花报数，2～3 个正整数）
- 手动选卦（指定上下卦 + 可选动爻，支持全静卦）
- 蓍草法（大衍筮法程序模拟，可选演卦过程展示）
- 汉字起卦（梅花字课，康熙/简体笔画，多字策略可配置）
- 八字自动排盘（lunar-python）
- 六十四卦卦辞摘要 + 爻辞全文（写入 AI 提示词与 Markdown 导出）

### CLI

- 四步交互引导、窄终端防重叠布局
- 非交互：`--method` / `-q` / `--copy` / `--calendar lunar` 等
- 起卦后默认自动复制提示词
- 历史记录：`--list-records` / `--show-record` / `--delete-record` / `--search` / Markdown 导出

### GUI

- 深色金色主题（`gui_theme.py`）
- 左右分栏：输入区 + 卦象/提示词
- 卦象 Canvas 绘制、历史记录窗口（搜索、导出 Markdown）
- **设定自动保存**至 `~/.bagua/config.json`（含起卦方式、铜钱输入、时间选项等）
- 起卦后可选自动复制提示词
- 起卦区「起卦说明」帮助（七种方式分页说明）

### 起卦方式对照表

| 代码键 | 名称 | CLI | 模块 | 状态 |
|--------|------|-----|------|------|
| `coin` | 铜钱法 | 1 | `divination/coin.py` | ✅ |
| `time` | 时间起卦 | 2 | `divination/time.py` | ✅ |
| `random` | 随机起卦 | 3 | `divination/random.py` | ✅ |
| `number` | 数字起卦 | 4 | `divination/number.py` | ✅ |
| `manual` | 手动选卦 | 5 | `divination/manual.py` | ✅ |
| `yarrow` | 蓍草法 | 6 | `yarrow.py` | ✅ |
| `character` | 汉字起卦 | 7 | `character.py` | ✅ |

注册表：`bagua/divination/registry.py`（`DIVINATION_METHODS`）。CLI/GUI 共用 `last_method` 记忆上次方式。

### 发布（v0.7.0 起）

- PyInstaller 双版本：`bagua.exe`（控制台）、`bagua-gui.exe`（无窗口）
- 构建脚本：`scripts/build.ps1` / `scripts/build.sh`
- 打 tag `v*` 时 GitHub Actions 自动构建 Release zip

---

## 配置与数据路径

| 路径 | 内容 |
|------|------|
| `~/.bagua/config.json` | 用户偏好（CLI/GUI 共用） |
| `~/.bagua/records/*.json` | 占卜历史记录 |

`UserConfig` 主要字段：`question`、`bazi`、`birth_datetime`、`timezone`、`coin_mode`、`calendar_mode`、`last_method`、`use_current_time`、`time_input`、`coin_tosses`、`number_inputs`、`manual_upper`、`manual_lower`、`manual_changing`、`auto_copy_prompt`、`auto_bazi` 等。

---

## 版本历史（摘要）

| 版本 | 日期 | 要点 |
|------|------|------|
| **v1.0.0** | 2026-06-29 | 稳定版：七种起卦方式冻结；文档与发版验证 |
| **v0.12.0** | 2026-06-29 | Phase E：`divination/` 子模块 + 注册表；CLI last_method；GUI 起卦说明 |
| **v0.11.0** | 2026-06-29 | 汉字起卦；`character.py` + `strokes.json`；笔画预览 |
| v0.10.2 | 2026-06-29 | 蓍草法（大衍模拟）；`yarrow.py`；演卦过程日志 |
| v0.10.1 | 2026-06-29 | 手动选卦；CLI `--upper/--lower/--changing`；GUI 八卦 Combobox |
| v0.10.0 | 2026-06-29 | 数字起卦（梅花报数）；CLI `--nums`；GUI 报数输入区 |
| v0.9.3 | 2026-06-29 | 六十四卦爻辞全文数据，提示词/导出集成 |
| v0.9.2 | 2026-06-29 | 历史记录搜索、Markdown 导出；GUI 地点/提示词区优化 |
| v0.9.1 | 2026-06-29 | 出生/起卦时区拆分；八字真太阳时独立；经度分设 |
| v0.9.0 | 2026-06-29 | P3-A：公历输入 + 节气历算卦 + 真太阳时 + 提示词口径说明 |
| v0.8.1 | 2026-06-29 | P2 可维护性：GUI 模块拆分、ruff/mypy CI、CHANGELOG 发版联动 |
| v0.8.0 | 2026-06-24 | P1 体验统一：CLI/GUI 配置互通、设置面板、Windows 安装说明 |
| v0.7.0 | 2026-06-24 | 阶段 5：PyInstaller 打包、Release CI、本状态文档 |
| v0.6.0 | 2026-06-24 | 八字排盘、农历起卦、卦辞摘要 |
| v0.5.x | 2026-06-24 | CLI 引导优化、剪贴板、自动复制 |
| v0.5.0 | 2026-06-24 | CLI 参数、历史记录、GUI Canvas |
| v0.4.0 | 2026-06-24 | Tkinter GUI 双入口 |
| v0.3.0 | 2026-06-24 | 架构重构、service 层 |

详细变更见 [README.md](../README.md#问题记录与版本历史)。

---

## 已知限制

- 公历时间起卦已换算节气历；农历显式输入模式仍用阴历数字
- 八字排盘不含大运、流年
- 不内置 AI API 调用（设计选择）
- Windows 未签名 exe 可能触发 SmartScreen，需「仍要运行」或自行签名
- GUI 基于 Tkinter，跨平台视觉一致性有限
- 固定偏移时区回退不支持夏令时（请安装 `tzdata`）

---

## 质量现状

| 项 | 状态 |
|----|------|
| 单元测试 | ✅ 核心逻辑覆盖 |
| CI（push/PR） | ✅ Ubuntu + Windows × Py 3.10/3.12/3.14 |
| Release CI | ✅ tag `v*` 触发 Windows 构建 |
| GUI 集成测试 | ⚠️ 仅 Canvas 回归，无完整 E2E |
| 类型检查 / lint | ✅ ruff + mypy（遗留模块渐进收紧） |

---

## 后续建议（按优先级）

### P1 — 体验统一

- [x] CLI 读取 `last_method`、`coin_tosses`、`use_current_time`、`time_input` 等 GUI 已保存字段
- [x] 非交互模式：`coin_mode` / 时间 / 手动铜钱 读取 config；`auto_copy_prompt` 默认生效（`--no-copy` 可关）
- [x] GUI「设置」面板（自动排盘 / 自动复制 / 卦辞开关）
- [x] Windows 安装说明：[WINDOWS_INSTALL.md](WINDOWS_INSTALL.md)（SmartScreen 处理指引）
- [ ] 代码签名（需购买证书，暂未实施）

### P2 — 可维护性

- [x] 拆分 `gui.py`（`gui_app` / `gui_forms` / `gui_history` / `gui_constants`）
- [x] 引入 `ruff` + `mypy` 至 CI（`Makefile lint` / `typecheck`）
- [x] `CHANGELOG.md` 与发版脚本联动（`scripts/check_release.py`）

### P3 — 功能深化

- [x] 节气换月、真太阳时（v0.9.0：公历输入 → 节气历算卦 + 提示词展示）
- [x] 历史记录搜索、导出 Markdown（v0.9.2）
- [x] 爻辞全文数据（v0.9.3）

### P4 — 起卦方式扩展

- [x] 数字起卦 v0.10.0
- [x] 手动选卦 v0.10.1
- [x] 蓍草法 v0.10.2
- [x] 汉字起卦 v0.11.0
- [x] Phase E 横切（子模块、CLI/GUI 对齐、文档、测试、帮助）v0.12.0

详细任务与勾选进度见 [DIVINATION_METHODS_PLAN.md](DIVINATION_METHODS_PLAN.md)。

### 版本规划

```
v0.10.x–v0.12.0  起卦方式扩展 + Phase E 横切   ✅ 已完成
v1.0.0           功能冻结与稳定版               ✅ 当前
v1.x             修复、文档、小改进（无新起卦体系）
v2.0+            六爻纳甲 / 物象起卦等（见 DIVINATION_METHODS_PLAN 第三梯队）
```

---

## 发版检查清单（v1.0.0）

- [x] `pytest tests/ -v` 全绿（124 项，忽略 `test_gui_dpi` 本机 Tk 问题时 124 passed）
- [x] bump `pyproject.toml` + `bagua/__init__.py` 版本号 → **1.0.0**
- [x] 更新本文件「快速概览」与「版本历史」
- [x] 更新 `README.md` / `WORKFLOW.txt` / `CHANGELOG.md`
- [ ] `.\scripts\build.ps1` 本地构建通过（发版机执行）
- [ ] `git tag v1.0.0 && git push origin v1.0.0` 触发 Release
- [ ] 验证 Release zip 内 exe 可运行

---

## 相关文档

- [WORKFLOW.txt](WORKFLOW.txt) — 开发流程与任务拆解
- [WINDOWS_INSTALL.md](WINDOWS_INSTALL.md) — Windows exe 安装与 SmartScreen
- [README.md](../README.md) — 用户手册与安装说明
- [DIVINATION_METHODS_PLAN.md](DIVINATION_METHODS_PLAN.md) — 起卦方式扩展计划与进度
- [CLEANUP.txt](CLEANUP.txt) — 目录清理记录（如有）

---

*下一版更新时：修改文首日期、版本号、测试数量，并在「版本历史」追加一行。*