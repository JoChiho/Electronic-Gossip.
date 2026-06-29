# bagua

极简易经八卦占卜 CLI/GUI 工具。起卦后生成可复制给大模型的结构化解读提示词。

> **当前稳定版 v1.0.0** — 七种起卦方式已冻结；仅供娱乐与文化学习参考，不构成任何决策依据。

## 功能

- **七种起卦方式**：铜钱法、时间起卦、随机起卦、数字起卦、手动选卦、蓍草法、汉字起卦
- **卦象展示**：卦名、上下卦符号、六爻图形与变爻标注
- **AI 提示词**：结构化输出，可直接复制到大模型
- **本地持久化**：时区、出生时间、八字、默认问题自动保存
- **跨平台时区**：Windows 自动安装 `tzdata`，缺失时回退固定 UTC 偏移
- **八字排盘**：填写出生时间可自动排八字（lunar-python）
- **农历起卦**：时间起卦支持公历 / 农历梅花易数模式
- **卦辞摘要**：AI 提示词附带六十四卦卦辞要点

## 快速开始

```bash
git clone https://github.com/JoChiho/Electronic-Gossip.git
cd Electronic-Gossip

# Windows 推荐
.\scripts\setup.ps1

# 或手动安装
pip install -r requirements.txt
python bagua.py
```

也可使用模块方式运行：

```bash
python -m bagua          # CLI
python -m bagua.gui      # GUI（Tkinter）
bagua-gui                # pip install -e . 后
```

## 开发工作流

### 环境初始化

```powershell
# Windows：创建 venv + 安装开发依赖
.\scripts\setup.ps1 -Dev
```

```bash
# macOS / Linux
make install-dev
```

### 常用命令

| 命令 | 说明 |
|------|------|
| `make test` | 运行单元测试 |
| `make run` | 启动 CLI |
| `pytest tests/ -v` | 直接运行测试 |
| `make clean` | 清理 `__pycache__` |
| `.\scripts\build.ps1` | 构建 Windows exe（CLI + GUI） |
| `make build` | 同上（需已安装 build 依赖） |

### 项目结构

```
Electronic-Gossip/
├── bagua/                  # Python 包
│   ├── __init__.py
│   ├── __main__.py         # python -m bagua
│   ├── cli.py              # 终端展示层（Rich + input）
│   ├── gui.py              # Tkinter 图形界面
│   ├── gui_display.py      # GUI 卦象文本格式化
│   ├── service.py          # perform_divination() 统一入口
│   ├── hexagram.py         # 卦象构建
│   ├── divination/         # 起卦纯逻辑子模块 + 注册表
│   │   ├── coin.py · time.py · number.py · manual.py · random.py
│   │   └── registry.py     # DIVINATION_METHODS 起卦方式说明
│   ├── prompt.py           # AI 提示词生成
│   ├── config.py           # 配置与记录持久化
│   ├── models.py / data.py
│   └── timezone.py         # 时区解析（含 Windows 兼容）
├── tests/                  # 单元测试
├── docs/
│   ├── WORKFLOW.txt        # 开发工作流程与路线图
│   └── PROJECT_STATUS.md   # 项目状态（持续更新）
├── packaging/              # PyInstaller spec
├── scripts/setup.ps1       # Windows 环境脚本
├── scripts/build.ps1       # Windows 打包脚本
├── .github/workflows/ci.yml
├── bagua.py                # 向后兼容入口
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
└── Makefile
```

### CI

推送至 `main` 或提交 PR 时，GitHub Actions 会在 Ubuntu / Windows 上运行测试（Python 3.10 / 3.12 / 3.14）。

## 使用说明

### 起卦方式对照表

| 代码键 | 名称 | CLI 交互 | 要点 | 适合场景 |
|--------|------|----------|------|----------|
| `coin` | 铜钱法 | 1 | 三钱法，手动 1/2 或自动模拟 | 参与感、传统体验 |
| `time` | 时间起卦 | 2 | 梅花易数年月日时；公历/农历 | 有明确起卦时刻 |
| `random` | 随机起卦 | 3 | 工具向，非传统术数 | 快速摸鱼、灵感 |
| `number` | 数字起卦 | 4 | 梅花报数，2～3 个正整数 | 心中已有数字 |
| `manual` | 手动选卦 | 5 | 乾1…坤8 + 可选动爻 | 已知卦象、教学 |
| `yarrow` | 蓍草法 | 6 | 大衍筮法程序模拟 | 体验演卦流程 |
| `character` | 汉字起卦 | 7 | 梅花字课，康熙/简体笔画 | 测字、一字问事 |

CLI/GUI 均会记住 `last_method`；交互模式默认沿用上次方式（对齐 GUI）。GUI 起卦区可点「起卦说明」查看详情。

### 铜钱法

| 输入 | 含义 |
|------|------|
| `1` | 阳面（字） |
| `2` | 阴面（花） |

示例：`1 2 1`。可选择**手动输入**或**自动模拟**。

### 时区

- 启动时可选择地区/时区
- 时间输出含 IANA 名称与 UTC 偏移
- 配置保存在 `~/.bagua/config.json`

**Windows 注意**：`zoneinfo` 需要 `tzdata` 包。已列入 `requirements.txt`；若未安装，程序会使用固定偏移回退，不会崩溃。

```bash
pip install tzdata   # 手动补装
```

### 交互模式引导

直接运行 `bagua` 会显示分步引导（① 个人信息 → ② 起卦方式 → ③ 起卦操作 → ④ 复制提示词），
每步均有说明面板、输入示例与错误提示。步骤 ② 默认沿用 `last_method`（与 GUI 一致），输入 `n` 可换方式。

### 非交互 CLI（快速摸鱼）

```bash
# 随机起卦，只输出提示词
bagua --method random --question "工作运势" --output prompt

# 自动保存记录 + 复制到剪贴板
bagua -m random -q "要不要跳槽" --save --copy

# 时间起卦（公历）
bagua -m time --at "2026-06-24 14:30" -q "项目进展"

# 农历时间起卦
bagua -m time --calendar lunar --lunar-at "2026-05-10 14:30" -q "项目进展"

# 历史记录
bagua --list-records
bagua --show-record 1
bagua --delete-record bagua_20260624_120000.json
```

### 配置示例

```json
{
  "timezone": "Asia/Shanghai",
  "region_label": "中国（北京时间 UTC+8）",
  "question": "近期工作是否该跳槽？",
  "bazi": "庚午年 辛巳月 甲子日 丙寅时",
  "birth_datetime": "1990-05-15 08:30",
  "coin_mode": "auto"
}
```

## Windows 免安装版（exe）

### 从 Release 下载（推荐）

在 [GitHub Releases](https://github.com/JoChiho/Electronic-Gossip/releases) 下载 `bagua-vX.Y.Z-win64.zip`，解压后：

| 文件 | 说明 |
|------|------|
| `bagua.exe` | 命令行版（双击或终端运行） |
| `bagua-gui.exe` | 图形界面版（无控制台窗口） |

配置与记录仍保存在 `~/.bagua/`。首次运行若遇 SmartScreen 提示，请参阅 **[docs/WINDOWS_INSTALL.md](docs/WINDOWS_INSTALL.md)**。

### 自行打包

```powershell
# 安装构建依赖 + 运行测试 + 生成 exe
.\scripts\setup.ps1 -Dev
.\scripts\build.ps1

# 可选：打成 Release zip
.\scripts\package_release.ps1
```

产物位于 `dist/bagua.exe` 与 `dist/bagua-gui.exe`。

推送版本 tag 可触发自动 Release 构建：

```bash
git tag v1.0.0
git push origin v1.0.0
```

### 项目状态文档

开发进展、已知限制与后续规划见 **[docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md)**（每次发版更新）。

## 问题记录与版本历史

### v1.0.0（当前稳定版）

| 变更 | 说明 |
|------|------|
| 功能冻结 | 七种起卦方式定版；v1.x 以维护与小改进为主 |
| Phase E | `divination/` 子模块 + 注册表；CLI `last_method`；GUI 起卦说明 |
| 起卦扩展 | v0.10 数字 / v0.10.1 手动 / v0.10.2 蓍草 / v0.11 汉字 |
| 测试 | 124 项 pytest；`scripts/check_release.py` 发版校验 |

### v0.12.0

| 变更 | 说明 |
|------|------|
| 横切任务 | 起卦逻辑拆包、文档对照表、随机起卦单测补全 |

### v0.9.x

| 变更 | 说明 |
|------|------|
| 节气历算卦 | 公历输入习惯不变，起卦自动换算节气历 |
| 真太阳时 | 经度 + 时差方程校正；设置面板可配置 |
| 爻辞全文 | v0.9.3 六十四卦爻辞写入提示词与 Markdown 导出 |

### v0.8.1

| 变更 | 说明 |
|------|------|
| GUI 模块拆分 | `gui_app` / `gui_forms` / `gui_history` / `gui_constants` |
| 代码质量 | CI 接入 ruff + mypy；`Makefile lint` / `typecheck` |
| 发版联动 | `CHANGELOG.md` + `scripts/check_release.py` |

### v0.8.0

| 变更 | 说明 |
|------|------|
| CLI/GUI 配置互通 | 起卦方式、铜钱输入、时间选项跨入口共享 |
| GUI 设置面板 | 自动排盘 / 自动复制 / 卦辞开关 |
| 非交互增强 | 读取 config；`--no-copy` 关闭自动复制 |
| Windows 安装说明 | `docs/WINDOWS_INSTALL.md` |

### v0.7.0

| 变更 | 说明 |
|------|------|
| PyInstaller 双版本 | `bagua.exe` + `bagua-gui.exe` |
| 构建脚本 | `scripts/build.ps1` / `Makefile build` |
| Release CI | push tag `v*` 自动构建 zip |
| 项目状态文档 | `docs/PROJECT_STATUS.md` |

### v0.6.0

| 变更 | 说明 |
|------|------|
| 八字自动排盘 | 出生时间 → 八字；CLI/GUI 均支持 |
| 农历时间起卦 | `--calendar lunar` / GUI 历法切换 |
| 卦辞摘要 | AI 提示词附带本卦/之卦卦辞要点 |
| 夏令时提示 | tzdata 可用时自动 DST；回退模式明确提示 |

### v0.5.0

| 变更 | 说明 |
|------|------|
| CLI 非交互参数 | `--method` / `-q` / `--save` / `--copy` 等 |
| 历史记录管理 | `--list-records` / `--show-record` / `--delete-record` |
| GUI 历史记录 | 历史窗口：查看、加载提示词、删除 |
| GUI 卦象 Canvas | 六爻图形化绘制 |
| 剪贴板优化 | `clipboard.py` 多平台回退 |

### v0.4.0

| 变更 | 说明 |
|------|------|
| Tkinter GUI | 图形界面起卦、复制提示词、保存记录 |
| 双入口 | `python -m bagua`（CLI）/ `python -m bagua.gui`（GUI） |

### v0.3.0

| 变更 | 说明 |
|------|------|
| 架构重构 | 拆分 service / divination / hexagram 等模块，CLI 瘦身 |
| perform_divination() | CLI 与后续 GUI 共用统一起卦入口 |
| 测试增至 20 项 | 含 test_service.py、test_divination.py |

### v0.2.1

| 问题 | 状态 | 说明 |
|------|------|------|
| Windows 启动崩溃 `ZoneInfoNotFoundError` | ✅ 已修复 | 添加 `tzdata` 依赖 + 固定偏移回退 |
| 铜钱法缺少自动模拟 | ✅ 已解决 | v0.2.0 |
| 正/反输入繁琐 | ✅ 已解决 | 改为 `1`/`2` |
| 时间无时区标注 | ✅ 已解决 | 地区选择 + 完整标注 |
| 用户信息每次重输 | ✅ 已解决 | `~/.bagua/config.json` |
| 缺少测试与 CI | ✅ 已解决 | pytest + GitHub Actions |

### 已知限制

- 农历起卦为数字简化版，未接入节气换月
- 八字排盘不含大运流年
- 固定偏移回退不支持夏令时（请安装 tzdata）

### 后续开发

v1.0 路线图已完成。维护与 v2.0 规划见 **[docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md)**、**[docs/DIVINATION_METHODS_PLAN.md](docs/DIVINATION_METHODS_PLAN.md)**。

| 阶段 | 内容 | 状态 |
|------|------|------|
| 0–5 | 架构 / GUI / CLI / 易学深化 / 打包 | ✅ 已完成 |
| P4 | 起卦方式扩展 Phase A–E | ✅ v1.0.0 |
| v1.x | Bug 修复、文档、体验小改 | 维护中 |
| v2.0+ | 六爻纳甲、物象起卦等 | 规划中 |

## License

MIT