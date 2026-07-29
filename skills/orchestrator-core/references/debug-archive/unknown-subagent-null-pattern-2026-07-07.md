# Unknown Subagent: Null Pattern (2026-07-07)

## Error Signature

```json
{
  "task_id": "task_20260707XXXXXX_XXXXXXXX",
  "status": "failed",
  "result": null,
  "error": "Unknown subagent: None",
  "metadata": {
    "subagent_name": null,
    "timestamp": "2026-07-07TXX:XX:XX.XXXXXX"
  }
}
```

## Session Context

- **Date**: 2026-07-07
- **Query**: "最近24小时出水数据"
- **Subagent called**: `multi-dimensional-data-perception`
- **Call attempts**: 5 (violated 2-strike rule)
- **Expected behavior**: After 2 failures, should have switched to direct analysis
- **Actual behavior**: Kept retrying until Hermes loop warning fired at attempt 3, then continued anyway

## Root Cause Analysis

The `call_subagent` tool wrapper (Hermes-level) failed to forward the `subagent_name` parameter to the underlying Python script. The metadata shows `"subagent_name": null` even though the parameter was passed correctly in the tool call arguments.

This differs from:
- **Stale session [Errno 2]**: Session directory path caching issue → retry after cleanup may work
- **Task ID mismatch**: Sub-agent IS running, just ID format differs → wait and read result
- **Unknown subagent: None**: Sub-agent NEVER started → no retry possible

## Correct Response Protocol

```
call_subagent() → "Unknown subagent: None"
    ↓
[1] Recognize: tool parameter binding failure (not sub-agent issue)
[2] DO NOT retry call_subagent
[3] DO NOT wait + read result (no file will be created)
[4] Check available execution paths:
    ├─ Terminal available? → Run Python directly
    ├─ Jupyter available? → Use jupyter-live-kernel
    └─ Neither? → Provide user with manual command
```

## Manual Command Template

When no execution path is available, provide the user with:

```bash
python D:/Hermes/skills/data-analysis/wastewater-data-analysis/scripts/emergency-recovery.py --hours <N> --type <influent|effluent>
```

## Lessons Learned

1. **2-Strike Rule must be absolute** — The skill says "stop after 2 failures" but the agent violated this. This is a workflow enforcement issue that needs stronger language in the skill.
2. **Error pattern recognition** — "Unknown subagent: None" with null metadata is a distinct, non-recoverable failure mode. It should trigger immediate fallback, not retry.
3. **Tool Loop Warning is a stop sign** — When Hermes fires "same_tool_failure_warning", the agent must stop immediately and change approach, not just "diagnose while continuing".
