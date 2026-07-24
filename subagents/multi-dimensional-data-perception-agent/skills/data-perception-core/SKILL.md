---
name: data-perception-core
description: 获取监测数据。**触发条件**：用户提到"数据"、"进水"、"出水"、"指标"或时间范围时调用。
---

# 数据获取技能

## 核心规则

**只做一件事：调用脚本，传递结果。不要解析，不要生成报告。**

## 数据量警告
**当时间范围 >48 小时时，原始数据可能超过 127K 字符，导致工具响应被截断。**

**解决方案**：
- 如果用户只需要统计汇总（均值、最大、最小等），请求输出到 `summary_result.json` 并只包含统计信息
- 如果用户确实需要原始数据，将查询拆分为多个 ≤24h 的小窗口

```bash
# ✅ 正确：大范围请求汇总统计
python skills/data-perception-core/scripts/get_data.py --hours 168 --summary-only

# ✅ 正确：小范围请求原始数据
python skills/data-perception-core/scripts/get_data.py --hours 24

# ❌ 错误：大范围请求原始数据（会被截断）
python skills/data-perception-core/scripts/get_data.py --hours 168
```

## 执行流程

1. **先从用户查询识别时间范围，换算成 `--hours`（数据为小时级，1 条/小时）。这一步不能漏，也不能偷懒默认 24：**
   - "最近 N 小时" → `--hours N`
   - "最近 N 天 / N 日" → `--hours N×24`（如 3 天 → `--hours 72`）
   - "本周 / 一周 / 7 天" → `--hours 168`
   - "本月" → `--hours 720`
   - "昨天" → `--hours 24`
   - 明确日期 → `--start "YYYY-MM-DD HH:MM:SS" --end "..."`
   - **用户完全没提任何时间** → 才用 `--hours 24`

   ⚠️ 换算后必须把数值带进命令——一周就写 `--hours 168`，**不要照抄下面示例里的 24**。

   💡 兜底：即便你忘了传 `--hours`、或传错，`get_data.py` 会**自己从任务描述(task.json)里确定性解析**时间范围（一周→168、3天→72、本月→720…），以任务描述为准。所以**务必把用户的时间词原样写进任务描述**（如"获取最近一周…"），脚本会兜住。

2. **调用脚本**（用第 1 步算出的数值；下面以"一周"为例）
   ```bash
   python skills/data-perception-core/scripts/get_data.py --hours 168
   ```

3. **确认执行完成**
   响应："✅ 脚本执行完成"

## 脚本输出

脚本自动保存结果到 `data_result.json`，包含：
- influent: 进水数据数组
- effluent: 出水数据数组
- metadata: 元数据（时间范围、指标等）

**汇总模式输出**（当 `--summary-only` 指定时）：
- 保存到 `summary_result.json`
- 只包含各指标的均值/标准差/最大/最小/缺失数量
- 文件大小约 2KB（不会截断）

**输出路径**：
```
E:/project/Ecological_env/subagents/multi-dimensional-data-perception-agent/data_result.json
E:/project/Ecological_env/subagents/multi-dimensional-data-perception-agent/summary_result.json
```

## 记住

- ✅ 调用脚本
- ✅ 确认完成
- ❌ 不要解析JSON
- ❌ 不要生成报告
- ❌ 不要添加说明

---
