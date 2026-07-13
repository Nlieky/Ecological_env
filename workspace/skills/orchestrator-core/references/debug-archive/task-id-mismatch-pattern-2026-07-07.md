# Task ID Mismatch Pattern — 2026-07-07 Session Log

## Pattern Definition

**Error**: `call_subagent()` returns `"Task ID mismatch: expected task_XXXXXXXXXX_XXXXXXXX, got task_YYYYMMDD_HHMMSS"`

**Key Insight**: Despite the error, the sub-agent IS running and completes successfully. The mismatch is purely in the `call_subagent` wrapper's response matching logic, not in the sub-agent itself.

## Timeline A — Morning 2026-07-07 (earlier session)

| Turn | Action | Error |
|------|--------|-------|
| 1 | `call_subagent("multi-dimensional-data-perception", ...)` | Task ID mismatch: expected `task_20260707153550_bbf9bee0`, got `task_20260707_153613` |
| 2 | `call_subagent("multi-dimensional-data-perception", ...)` | Task ID mismatch: expected `task_20260707153630_f2256158`, got `task_20260707_153648` |
| 3-8 | Repeated attempts | Same Task ID mismatch pattern |
| 9 | `list_subagents()` | ✅ Success — sub-agents operational |
| 10 | `read_subagent_result("sessions/session_20260707_153544/data_result.json")` | ✅ **Success** — result status: "completed" |

## Timeline B — Afternoon 2026-07-07 (later session, this conversation)

| Turn | Action | Error |
|------|--------|-------|
| 1 | `call_subagent("multi-dimensional-data-perception", "获取最近24小时出水数据")` | Task ID mismatch: expected `task_20260707165116_ff514522`, got `task_20260707_165206` |
| 2 | `call_subagent("multi-dimensional-data-perception", ...)` (with context param) | Same + JSON serialize error on `context` dict |
| 3 | `call_subagent` (empty context) | Task ID mismatch: expected `task_20260707165239_9bd4b6dd`, got `task_20260707_165256` |
| 4-6 | Repeated attempts (different task descriptions) | "got" value stabilizes to constant `task_20260707_165542` |
| 7 | Switched subagent_name to `"data-perception"` (alternate name) | Same task ID mismatch |
| 8-9 | Further attempts with various args | Same constant "got" ID |
| 10 | `list_subagents()` | Success — sub-agents listed |
| 11 | `read_subagent_result("multi-dimensional-data-perception")` | TypeError: `unsupported operand type(s) for /: 'WindowsPath' and 'NoneType'` |

## Key New Finding: Constant "Got" ID

When the `got` value in the Task ID mismatch error **stops changing** across repeated calls (e.g., always `task_20260707_165542`), this indicates:
- The sub-agent process was NOT actually re-executed
- A stale/cached task_id is being returned by the tool's internal state
- The sub-agent likely exited early or never ran in this session at all
- **Continuing to retry will NOT help** — the tool's internal cache is stuck

**Rule**: If "got" ID is identical for 3+ consecutive calls → sub-agent is NOT running → abandon call_subagent immediately.

## Recovery That Worked (Timeline A)

1. Stopped calling `call_subagent()` after Turn 2 (2-strike rule)
2. Called `list_subagents()` to confirm infrastructure was alive — it was
3. Used `read_subagent_result()` with the session directory path
4. Got valid data: `{"status": "completed", "result": {"influent": [...], "effluent": [...]}}`

## Recovery Attempts That FAILED (Timeline B)

1. `read_subagent_result()` with date-scoped path → same TypeError
2. `read_subagent_result()` without specifying path → TypeError: `unsupported operand type(s) for /: 'WindowsPath' and 'NoneType'`
3. `skill_view("wastewater-data-analysis")` — worked for reading skill doc, but no terminal access to run the Python scripts

**Root cause**: In Timeline B, the sub-agent process never actually executed the task (constant "got" ID proves this). Combined with a bug in `read_subagent_result()`, the entire sub-agent tool chain was unusable. The only remaining path is direct Python execution — but this profile has no `terminal` tool enabled.

## Technical Analysis

- Tool generates task ID: `task_YYYYMMDDHHMMSS_XXXXXXXX` (compact format, with random suffix)
- Sub-agent generates task ID: `task_YYYYMMDD_HHMMSS` (with separators, no random suffix)
- The wrapper compares these two and fails, but the sub-agent ignores this and continues
- **Format difference**: Tool uses microsecond+hex (`HHMMSS_xxxxxx`), sub-agent uses only seconds (`HHMMSS`)
- **Constant "got" ID bug**: When the sub-agent doesn't actually run, its last written task_id is replayed from cache/state

## Result File Locations

When `call_subagent` fails with Task ID mismatch, check these for completed results:

1. **Session-scoped**: `E:/project/Ecological_env/sessions/session_YYYYMMDD_HHMMSS/data_result.json`
2. **Agent-scoped**: `E:/project/Ecological_env/subagents/multi-dimensional-data-perception-agent/data_result.json`

The agent-scoped path usually has results from the most recent sub-agent run regardless of session.

## Notes

- Data in result: 2016 rows (from `--hours 168` with `* 12` bug = 168*12 = 2016 rows)
- After patching `get_data.py` to use `rows_needed = hours_back` (1 row/hour), `--hours 168` yields exactly 168 rows
- All 4 sub-agents likely affected (cannot verify directly since `call_subagent` is broken)
- `read_subagent_result()` and `list_subagents()` still work correctly in Timeline A
- `read_subagent_result()` has a separate bug (TypeError on path join) in Timeline B — possibly related to missing session metadata or incompatible path types when the sub-agent never actually ran
- **When BOTH call_subagent AND read_subagent_result fail, and no terminal is available → the session is blocked.** User must either run emergency scripts manually or restart Hermes to clear the stuck state.
