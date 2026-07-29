---
name: data-perception-core
description: 获取监测数据——从 InfluxDB 取进出水数据，忠实保留原始值，标记缺失，标注 HRT，生成 chartData。当任务涉及"获取数据"、"进水"、"出水"、"指标"、"时间范围"时使用本技能。务必使用——数据获取是整个研判链路的第一步，没有数据后续子智能体无法工作。
---

# 数据获取技能

## 你做什么

你调用一个脚本（`get_data.py`），它从 InfluxDB 取进出水监测数据。脚本自动完成所有工作：
- 取进水 + 出水数据（忠实保留原始值，含缺失/异常——这些是监控对象，不清洗）
- 标记缺失时间点（`missing_points`）
- 标注 HRT=2h（供下游规则推理按需做进水出水对齐）
- 生成 chartData（供前端画曲线）

**你的工作就是：解析任务里的时间范围 → 调脚本 → 确认完成。**

## 怎么调

脚本路径：`$HERMES_HOME/skills/data-perception-core/scripts/get_data.py`

### 时间范围 → 参数

脚本支持两种方式（二选一）：

**方式 1：起止日期**（任务给了明确日期时优先用）
```bash
python "$HERMES_HOME/skills/data-perception-core/scripts/get_data.py" --start "2026-07-14" --end "2026-07-15"
```

**方式 2：最近 N 小时**（任务说"最近X天/小时"时用）
```bash
python "$HERMES_HOME/skills/data-perception-core/scripts/get_data.py" --hours 168
```

| 任务里说的 | 用哪个参数 |
|---|---|
| "7月14日到15日" | `--start "2026-07-14" --end "2026-07-15"` |
| "最近一周" / "7天" | `--hours 168` |
| "最近3天" | `--hours 72` |
| "最近24小时" / "昨天" | `--hours 24` |
| "本月" / "一个月" | `--hours 720` |
| 没提时间 | `--hours 24`（唯一允许默认的情况） |

**关键**：从任务描述里识别时间，选对参数，把数值/日期写进命令。任务说"一周"就写 `--hours 168`，不能写成 24。

### 好的调用 vs 差的调用

```
✅ 好：python "...get_data.py" --start "2026-07-14" --end "2026-07-15"
   → 时间精确，脚本取对应范围

✅ 好：python "...get_data.py" --hours 168
   → "一周"换算成 168 小时，正确

❌ 差：python "...get_data.py"
   → 没传时间，默认 24 小时——任务要一周却只取了一天

❌ 差：python "...get_data.py" --hours 24
   → 任务说"一周"却写了 24——没换算
```

## 执行流程

1. 从任务描述识别时间范围
2. 选对参数（明确日期用 `--start/--end`；相对时间用 `--hours`）
3. 调脚本
4. 响应："✅ 脚本执行完成"

就这些。不需要做别的。

## 为什么只调脚本、不做别的

**不解析 JSON / 不生成报告**：你的结果（`data_result.json`）由下游子智能体（异常检测）直接从文件读取，由主智能体整合成报告。你解析了也没人看，反而浪费你的迭代预算。

**不手写文件**：结果只能由 `get_data.py` 产出（它写了正确的格式 + metadata + chartData）。你手写会破坏格式，下游读不了。

**不探索目录**：你不需要知道项目结构，只需要调脚本。探索浪费时间和 token。

## 脚本输出

脚本自动保存到 `data_result.json`（在 `SESSION_DIR` 或子智能体默认目录），包含：
- `influent` / `effluent`：进出水数据（忠实原始，缺失值保留 None）
- `metadata`：时间范围、指标列表、`hrt_hours=2`、`missing_points`
- `chartData`：可视化数据（供前端画曲线）

下游异常检测链式消费此文件。
