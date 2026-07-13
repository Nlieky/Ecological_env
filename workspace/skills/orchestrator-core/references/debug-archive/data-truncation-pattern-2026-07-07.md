# Data Truncation from Large Result Sets (2026-07-07)

## Summary

When requesting raw time-series data for >24 hours via the data-perception sub-agent, the result can exceed 127,880 characters and get truncated by the Hermes tool system. The solution is to request summary statistics instead of raw data.

## Session Context

**Date**: 2026-07-07
**Task**: User requested "最近一周进出水口的监测数据" (recent one week of influent/effluent monitoring data)
**Time range**: 168 hours (7 days × 24 hours)

## What Happened

### Attempt 1: Direct sub-agent call with empty name
```
call_subagent(subagent_name="", task="...")
→ Error: "Unknown subagent: "
```
Repeated 3 times with identical error. **Lesson**: Always provide valid `subagent_name`.

### Attempt 2: Dict as context parameter
```
call_subagent(subagent_name="multi-dimensional-data-perception", task="...", context={"data_type": "both"})
→ Error: "TypeError: the JSON object must be str, bytes or bytearray, not dict"
```
**Lesson**: The `context` parameter expects a JSON string, not a dict. Or simply omit it for first calls.

### Attempt 3: Valid call but Task ID mismatch
```
call_subagent(subagent_name="multi-dimensional-data-perception", task="获取最近一周...")
→ Error: "Task ID mismatch: expected task_20260707162034_a2e17ee1, got task_20260707_162213"
```
The sub-agent IS running despite the error. Waited and read result file directly.

### Attempt 4: Read result — SUCCESS but truncated
```
read_subagent_result("E:/project/Ecological_env/subagents/multi-dimensional-data-perception-agent/data_result.json")
→ Status: completed
→ Result: 127,888 chars → TRUNCATED
```
The full dataset (168 rows × 8 indicators × 2 files) exceeded the tool response limit.

### Attempt 5: Request summary statistics — SUCCESS
```
call_subagent("multi-dimensional-data-perception",
    "执行Python脚本读取CSV，取最后168行，计算各指标的均值/标准差/最大/最小/缺失数量，
     写入 summary_result.json，只输出汇总统计，不要原始数据。")

read_subagent_result("E:/project/Ecological_env/subagents/multi-dimensional-data-perception-agent/summary_result.json")
→ Status: completed
→ Result: ~2KB JSON with full statistics ✓
```

## Result File Path Patterns

### Agent-scoped (default)
```
E:/project/Ecological_env/subagents/multi-dimensional-data-perception-agent/data_result.json
```

### Agent-scoped (custom filename)
```
E:/project/Ecological_env/subagents/multi-dimensional-data-perception-agent/summary_result.json
```

### Session-scoped
```
E:/project/Ecological_env/sessions/session_YYYYMMDD_HHMMSS/data_result.json
```

## Decision Rules

| Time range | User needs | Approach |
|------------|------------|----------|
| ≤24h | Raw data | Direct sub-agent call, read `data_result.json` |
| ≤24h | Statistics | Direct sub-agent call or `wastewater-data-analysis` |
| >24h | Raw data | Multiple calls with smaller windows, then merge |
| >24h | Statistics | Sub-agent with summary task → `summary_result.json` |
| Any | Quick stats | `wastewater-data-analysis` skill (direct Python) |

## Key Insight

The sub-agent reuses the same output path (`data_result.json`) across multiple calls within the same session. When you need different output (e.g., summary vs raw), specify a custom filename in the task and read from that path.
