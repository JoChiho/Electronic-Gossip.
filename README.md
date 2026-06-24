# bagua

极简易经八卦占卜 CLI 工具。纯终端运行，起卦后生成可复制给大模型的结构化解读提示词。

> 仅供娱乐与文化学习参考，不构成任何决策依据。

## 功能

- **三种起卦方式**：铜钱法（手动/自动）、时间起卦、随机起卦
- **卦象展示**：卦名、上下卦符号、六爻图形与变爻标注
- **AI 提示词**：结构化输出，可直接复制到大模型
- **本地持久化**：时区、出生时间、八字、默认问题自动保存
- **跨平台时区**：Windows 自动安装 `tzdata`，缺失时回退固定 UTC 偏移

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
python -m bagua
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

### 项目结构

```
Electronic-Gossip/
├── bagua/                  # Python 包
│   ├── __init__.py
│   ├── __main__.py         # python -m bagua
│   ├── cli.py              # 主程序逻辑
│   └── timezone.py         # 时区解析（含 Windows 兼容）
├── tests/                  # 单元测试
├── scripts/setup.ps1       # Windows 环境脚本
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

## 打包为 exe

```bash
pip install pyinstaller
pyinstaller --onefile --name bagua --console bagua.py
```

## 问题记录与版本历史

### v0.2.1（当前）

| 问题 | 状态 | 说明 |
|------|------|------|
| Windows 启动崩溃 `ZoneInfoNotFoundError` | ✅ 已修复 | 添加 `tzdata` 依赖 + 固定偏移回退 |
| 铜钱法缺少自动模拟 | ✅ 已解决 | v0.2.0 |
| 正/反输入繁琐 | ✅ 已解决 | 改为 `1`/`2` |
| 时间无时区标注 | ✅ 已解决 | 地区选择 + 完整标注 |
| 用户信息每次重输 | ✅ 已解决 | `~/.bagua/config.json` |
| 缺少测试与 CI | ✅ 已解决 | pytest + GitHub Actions |

### 已知限制

- 时间起卦使用公历数字简化，未接入农历
- 八字需手动填写，未自动排盘
- 固定偏移回退不支持夏令时

### 后续方向

- [ ] 根据出生时间自动推算八字
- [ ] 农历日期支持
- [ ] 历史记录管理命令
- [ ] 非交互 CLI 参数模式

## License

MIT