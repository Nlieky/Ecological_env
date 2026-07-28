---
name: data-perception-core
description: 获取监测数据。**触发条件**：用户提到"数据"、"进水"、"出水"、"指标"或时间范围时调用。
---

# 数据获取技能

## 工艺领域常量

**水力停留时间(HRT)= 2 小时**（当前工艺）。脚本会把 `hrt_hours=2` 标进 `data_result.json` 的 metadata，供下游(规则推理)按需做进水出水时间对齐。数据感知本身不做对齐。

## 核心规则

**只做一件事：把任务里的时间范围换算成正确的 `--hours`，调脚本，确认完成。不解析、不生成报告。**

## ⚠️ 执行纪律（严格白名单，违反必失败）

**算完 `--hours` 后，你只能执行那一条 `python` 命令，敲完就停。严禁任何其他终端操作：**
- ❌ 禁止 `cat >` / `>>` / `echo >` 写入、修改、删除任何文件（结果只能由脚本产出）
- ❌ 禁止 `python -c` / 内联代码 / 自己写脚本
- ❌ 禁止 `ls` / `find` / `head` / `tail` / `grep` / `cat` 读文件或探索目录
- ❌ 禁止 `cd` / `pwd` / `echo` 等闲逛
- ✅ **唯一允许**：直接 `python "$HERMES_HOME/skills/data-perception-core/scripts/get_data.py" --hours N`

## ⏰ 时间范围 → `--hours`（每次第一步，不许跳过、不许默认 24）

数据是小时级（1 条/小时）。**收到任务后，第一件事就是从任务描述里识别时间范围，换算成 `--hours`，把算出的数值带进命令：**

| 任务里提到 | `--hours` |
|-----------|-----------|
| 最近 N 小时 | N |
| 最近 N 天 / N 日 | N×24（如 3 天 → 72）|
| 一周 / 本周 / 7 天 | **168** |
| 两周 / 14 天 | 336 |
| 本月 / 一个月 | 720 |
| 昨天 | 24 |
| 明确起止日期 | `--start "YYYY-MM-DD HH:MM:SS" --end "..."` |
| **任务里完全没提时间** | 24（这是唯一允许默认的情况）|

- ⚠️ **换算后必须把数值写进命令**。任务说"一周"就写 `--hours 168`，绝不能写成 24。
- ✅ **运行前自检**：`--hours` 的数值是否 = 任务时间范围的换算结果？不符就改对再跑。

例：任务"获取最近一周的进出水数据" →
```bash
python "$HERMES_HOME/skills/data-perception-core/scripts/get_data.py" --hours 168
```

## 执行流程

1. 按上表把任务的**时间范围换算成 `--hours`**（不许默认 24）。
2. 用算出的数值调脚本。
3. 响应："✅ 脚本执行完成"

> 注：结果写到 `data_result.json` 文件（不 dump 到 stdout），范围再大也不会截断；下游异常检测从该文件读取，所以一周/一月直接取全量即可，无需拆窗或汇总。

## 脚本输出

脚本自动保存结果到 `data_result.json`，包含：
- influent: 进水数据数组
- effluent: 出水数据数组
- metadata: 元数据（时间范围、指标等）

**输出路径**：
```
SESSION_DIR/data_result.json                 # 若设置了 SESSION_DIR（子智能体调用时）
subagents/multi-dimensional-data-perception-agent/data_result.json   # 否则默认
```

## 记住

- ✅ 调用脚本
- ✅ 确认完成
- ❌ 不要解析JSON
- ❌ 不要生成报告
- ❌ 不要添加说明

---
