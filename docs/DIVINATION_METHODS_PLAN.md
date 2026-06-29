# 起卦方式扩展计划

> 维护说明：每完成一步将 `[ ]` 改为 `[x]`，并在「进度日志」追加一行。  
> 创建日期：2026-06-29 · 当前基线版本：**v1.0.0**（起卦方式已冻结）

---

## 一、现状（v0.9.3）

| 方式 | 代码键 | 实现 | 专业定位 |
|------|--------|------|----------|
| 铜钱法 | `coin` | ✅ | 三钱法，近世最常用 |
| 时间起卦 | `time` | ✅ | 梅花易数「年月日时」体例 |
| 随机起卦 | `random` | ✅ | 工具向，非传统术数 |
| 数字起卦 | `number` | ✅ | 梅花报数，2～3 数 |
| 手动选卦 | `manual` | ✅ | 指定上下卦 + 可选动爻 |
| 蓍草法 | `yarrow` | ✅ | 大衍筮法模拟 |
| 汉字起卦 | `character` | ✅ | 梅花字课，笔画/码点 |

**统一数据流：**

```
divination.py（各方法纯逻辑）
  → build_hexagram()（六爻 → 卦象）
  → service.perform_divination()
  → prompt.generate_ai_prompt()
```

新增方式只需：**纯逻辑算六爻 + method_desc + GUI/CLI 入参 + AI 方法论说明**。

---

## 二、待扩展的常见起卦方式

### 第一梯队（v0.10.x）

| 方式 | 版本 | 要点 |
|------|------|------|
| **数字起卦**（梅花报数） | v0.10.0 | 2～3 个数字；复用梅花 mod 8 / mod 6 |
| **手动选卦** | v0.10.1 | 用户选上下卦 + 动爻（可无动爻） |
| **蓍草法**（大衍模拟） | v0.10.2 | 50 蓍草算法模拟；输出 6/7/8/9 |

### 第二梯队（v0.11.x）

| 方式 | 版本 | 要点 |
|------|------|------|
| **汉字起卦**（测字/字课） | v0.11.0 | 笔画数或码点取数；需字库与口径说明 |
| **物象起卦**（表单化） | v0.11.x? | 两物/两数映射八卦；可选 |

### 第三梯队（v1.0 后 / 暂不纳入）

| 方式 | 说明 |
|------|------|
| 六爻纳甲 | 配六亲、世应，体系过大 |
| 奇门遁甲 | 另一套盘式，不宜与易经卦混用 |
| 先天数/河图数 | 流派多，需用户选口径 |
| 声音/方位自动采集 | 软件难稳定采集 |

---

## 三、目标架构

```
bagua/
  divination/
    __init__.py          # DIVINATION_METHODS 注册表
    coin.py              # 铜钱（自 divination.py 迁出）
    time.py              # 梅花时间
    number.py            # 数字起卦
    yarrow.py            # 蓍草法
    manual.py            # 手动选卦
    character.py         # 汉字起卦（后期）
  models.py              # DivinationMethod 联合类型扩展
  prompt.py              # _method_guidance() 按方法分支
  gui_forms.py           # 各方法动态表单（coin_frame / time_frame 模式）
```

**统一接口：**

```python
def divinate_*(...) -> tuple[list[int], str]:  # 六爻值, method_desc
```

**配置扩展（UserConfig）：**

- `number_inputs` — 数字起卦
- `manual_upper` / `manual_lower` / `manual_changing` — 手动选卦
- `yarrow_show_process` — 蓍草过程展示（可选）

---

## 四、分阶段任务清单

### Phase A — v0.10.0 数字起卦（梅花报数）

- [x] **A1** `divinate_by_numbers(n1, n2, n3=None)` 纯逻辑  
  - 两数：上卦 n1%8，下卦 n2%8，动爻 (n1+n2)%6  
  - 三数：上卦 n1%8，下卦 n2%8，动爻 n3%6  
  - 单元测试：固定输入可复现
- [x] **A2** `DivinationMethod` 增加 `"number"`；`METHOD_LABELS`、CLI  
  - `--method number --nums "3 8 5"`（或等价参数）
- [x] **A3** GUI：起卦方式「数字起卦」+ 2～3 个数字输入框 + 说明文案
- [x] **A4** `prompt.py`【方法论·数字卦】+ `method_desc` 展示公式
- [x] **A5** 集成测试 `perform_divination("number", ...)`；历史/Markdown 无需改 schema
- [x] **A6** bump 版本、CHANGELOG、`PROJECT_STATUS.md`

**验收：** 输入 `3, 8, 5` 卦象可复现；提示词含公式与体用说明。

---

### Phase B — v0.10.1 手动选卦

- [x] **B1** `divinate_manual(upper_idx, lower_idx, changing_line|None)`
- [x] **B2** 动爻可选「无」→ 全静爻（7/8）
- [x] **B3** GUI：上卦/下卦 Combobox（乾1…坤8）+ 动爻 Combobox
- [x] **B4** CLI 非交互参数；`last_method` 持久化
- [x] **B5** 测试：乾上坤下第3爻动、纯阳静卦等
- [x] **B6** 版本与文档更新

**验收：** 手动选择与预期本卦/之卦一致。

---

### Phase C — v0.10.2 蓍草法（大衍模拟）

- [x] **C1** 大衍算法纯函数（分二、挂一、揲四、归奇；三变得一爻）
- [x] **C2** `divinate_yarrow(rng, *, record_steps=False)` → 六爻 + 可选步骤日志
- [x] **C3** GUI：「模拟蓍草」+ 可选「演卦过程」展开区
- [x] **C4** 提示词注明「大衍筮法模拟，非实体蓍草」
- [x] **C5** 统计测试：固定 seed 可复现；长期分布符合大衍理论概率（1/16…3/16）
- [x] **C6** 版本与文档更新

**验收：** 算法正确；分布合理。

---

### Phase D — v0.11.0 汉字起卦

- [x] **D1** 选定笔画口径（康熙 / 简体）并文档化  
  - 默认 `kangxi`（康熙字典）；可选 `simplified`（简体）；未收录字码点回退
- [x] **D2** `character_to_numbers(text)` → 上卦/下卦/动爻
- [x] **D3** GUI：一字/词输入 + 笔画预览
- [x] **D4** 多字策略可配置（auto / first_two / first_three / total）
- [x] **D5** 常用字单测与手工核算对照（乾、水火、问事人等）
- [x] **D6** 版本与文档更新

---

### Phase E — 横切任务（贯穿各版本）

- [x] **E1** 重构 `divination.py` 为子模块 + 注册表
- [x] **E2** CLI 交互引导按 `last_method` 分支（对齐 GUI）
- [x] **E3** README / `PROJECT_STATUS` 起卦方式对照表
- [x] **E4** 每种新方法 ≥3 单测 + 1 个 service 集成测
- [x] **E5** GUI 内「起卦方式说明」帮助（Tab 或链接文档）

---

## 五、版本路线图

```
v0.10.0  数字起卦（梅花报数）     ← 已完成
v0.10.1  手动选卦                 ← 已完成
v0.10.2  蓍草法（大衍模拟）     ← 已完成
v0.11.0  汉字起卦                 ← 已完成
v1.0.0   起卦方式冻结 + 文档 + Release 验证   ← 已完成
```

---

## 六、明确不做（v1.0 前）

- [ ] ~~六爻纳甲全自动排盘~~（超出「起卦 → AI 提示词」边界）
- [ ] ~~奇门遁甲起卦~~（另一体系）
- [ ] ~~将随机起卦包装为传统术数~~（保留调试用途，提示词标明非传统）

---

## 七、进度日志

| 日期 | 版本 | 摘要 |
|------|------|------|
| 2026-06-29 | — | 计划文档创建；用户确认实施顺序 |
| 2026-06-29 | v0.10.0 | Phase A 完成：数字起卦（梅花报数）全链路 |
| 2026-06-29 | v0.10.1 | Phase B 完成：手动选卦（上下卦 + 可选动爻） |
| 2026-06-29 | v0.10.2 | Phase C 完成：蓍草法（大衍筮法模拟） |
| 2026-06-29 | v0.11.0 | Phase D 完成：汉字起卦（梅花字课） |
| 2026-06-29 | v0.12.0 | Phase E 完成：divination 子模块、CLI last_method、GUI 帮助、文档对照表 |
| 2026-06-29 | v1.0.0 | 稳定版发布：七种起卦方式冻结；文档与发版验证完成 |
| | | |

---

## 八、相关文件

| 文件 | 说明 |
|------|------|
| `bagua/divination/` | 起卦逻辑子模块 + `registry.py` 注册表 |
| `bagua/data.py` | `METHOD_LABELS` |
| `bagua/prompt.py` | `_method_guidance()` |
| `bagua/gui_forms.py` | 动态表单区 |
| `docs/PROJECT_STATUS.md` | 项目总览 |