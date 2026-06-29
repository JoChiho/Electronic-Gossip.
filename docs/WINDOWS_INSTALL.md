# Windows 安装与运行说明

> 适用于从 GitHub Releases 下载 `bagua-vX.Y.Z-win64.zip` 的用户。  
> 与 [PROJECT_STATUS.md](PROJECT_STATUS.md) 同步维护。

## 解压与运行

1. 下载 Release 中的 `bagua-vX.Y.Z-win64.zip`
2. 解压到任意目录（建议非系统盘路径不含中文空格亦可）
3. 双击运行：
   - **`bagua-gui.exe`** — 图形界面（推荐新手）
   - **`bagua.exe`** — 命令行版（需在「终端」中运行，或双击后快速使用）

用户数据保存在：

```
C:\Users\<你的用户名>\.bagua\
├── config.json    # 偏好与个人信息
└── records\       # 占卜历史
```

CLI 与 GUI **共用**同一配置文件。

## SmartScreen「已阻止未知发布者」

当前 Release 为**社区构建、未代码签名**的 exe，Windows Defender SmartScreen 可能提示：

> Windows 已保护你的电脑

**处理方式（任选）：**

1. 点击「更多信息」→「仍要运行」
2. 或在 exe 上右键 → **属性** → 勾选「解除锁定」→ 应用 → 再双击运行
3. 若企业环境禁止未签名程序，请改用源码安装：
   ```powershell
   git clone https://github.com/JoChiho/Electronic-Gossip..git
   cd Electronic-Gossip.
   .\scripts\setup.ps1
   python -m bagua.gui
   ```

这是未购买代码签名证书时的正常现象，**不代表文件被篡改**。建议只从项目官方 GitHub Releases 下载。

## 杀毒软件误报

PyInstaller 打包的单文件 exe 偶发被启发式扫描标记。若遇误报：

- 将解压目录加入白名单，或
- 使用 `pip install` 源码方式运行（见 README）

## 常见问题

| 现象 | 处理 |
|------|------|
| 双击 `bagua.exe` 闪退 | 在 PowerShell 中运行 `.\bagua.exe` 查看报错；或改用 `bagua-gui.exe` |
| 时区不准确 | 安装完整依赖后重装：`pip install tzdata`（exe 版已内置） |
| 农历/八字不可用 | 确认 Release 版本 ≥ v0.6.0 |
| 想恢复默认设置 | 删除 `%USERPROFILE%\.bagua\config.json` |

## 反馈

问题与建议请提交至项目 GitHub Issues，附上版本号与运行方式（exe / 源码）。