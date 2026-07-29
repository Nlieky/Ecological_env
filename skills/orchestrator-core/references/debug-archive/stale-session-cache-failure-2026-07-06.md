# Stale Session Cache Failure Pattern (2026-07-06)

## Symptom

`call_subagent()` fails repeatedly with error:
```
Failed to write task.json: [Errno 2] No such file or directory: 'E:\\project\\Ecological_env\\workspace\\state\\session_20260706_101657\\task.json'
```

The session ID in the error path (`session_20260706_101657`) is from an OLD session, not the newly created one (`session_20260706_150524` or later).

## Root Cause

The `call_subagent` tool has an **internal session cache** that is NOT invalidated by `create_session()`. This is a systemic tool design flaw confirmed on 2026-07-06 after 12+ consecutive failures.

**Key findings:**
1. All 4 sub-agents are affected (`multi-dimensional-data-perception`, `anomaly-detection`, `rule-reasoning`, `disposition-execution`)
2. Passing `session_dir` parameter explicitly does NOT override the cached path
3. Creating new sessions does NOT clear the cache
4. The tool cannot self-recover once this state is entered

## Detection

- **Hermes warning**: `same_tool_failure_warning; count=N; [tool] has failed N times this turn`
- **Error pattern**: `[Errno 2]` referencing a session directory that doesn't exist or doesn't match the current session
- **Failure count**: 2+ consecutive failures with the same stale session path

## Recovery Procedure

### Step 1: Stop Sub-agent Calls Immediately
Do NOT retry `call_subagent()` more than twice with the same error. Continuing will not work.

### Step 2: Verify Session State
```bash
# List all session directories
ls -la E:/project/Ecological_env/workspace/state/session_*/

# Check if the stale session directory exists
ls -la E:/project/Ecological_env/workspace/state/session_20260706_101657/
```

### Step 3: Clean Up All Sessions
```bash
# Delete all session directories (required - tool cannot do this itself)
rm -rf E:/project/Ecological_env/workspace/state/session_*/
```

### Step 4: Switch to Direct Analysis
**Do NOT retry sub-agent approach.** Use one of these alternatives:

**Option A: Emergency Recovery Script**
```bash
python E:/project/Ecological_env/workspace/skills/data-analysis/wastewater-data-analysis/scripts/emergency-recovery.py --hours 24 --type effluent
```

**Option B: 24-Hour Anomaly Analysis Script**
```bash
python E:/project/Ecological_env/workspace/skills/data-analysis/wastewater-data-analysis/scripts/analyze-24h-anomalies.py
```

**Option C: Jupyter Live Kernel**
Use `data-science/jupyter-live-kernel` skill for interactive Python analysis.

**Option D: Direct Python via wastewater-data-analysis skill**
Follow the Python script templates in that skill.

## Prevention

1. **Pre-flight check**: Before starting complex multi-step tasks, run:
   ```bash
   ls workspace/state/session_*/
   df -h E:
   ```

2. **Regular cleanup**: Run `cleanup_sessions(days=3)` weekly or when disk space warnings appear.

3. **Early detection**: After 2 sub-agent failures with same error, immediately check for stale session pattern.

4. **Prefer direct analysis for simple queries**: For simple data queries like "最近 24 小时出水 COD 异常吗？", use `wastewater-data-analysis` skill directly instead of sub-agent orchestration.

## Decision Tree

```
call_subagent() fails
    ↓
Check error type
    ├─ [Errno 28] No space → cleanup_sessions(), retry ONCE, else direct analysis
    ├─ Error 401 Unauthorized → check .env, consider direct analysis for urgent tasks
    ├─ [Truncated: tool response...] → context overflow → direct analysis immediately
    └─ [Errno 2] stale session path → 
        ↓
        Compare session IDs (error path vs create_session() return)
        ↓
        IDs DON'T match → STALE CACHE DETECTED
        ↓
        1. Delete all sessions: rm -rf workspace/state/session_*/
        2. Retry ONCE with explicit session_dir
        3. If still failing → ABANDON sub-agent approach entirely
        4. Use direct Python analysis
```

## Session Log Reference

See `stale-session-cache-failure-2026-07-06-session-log.md` for complete timeline of 12 consecutive failures and recovery validation.

## Updated

2026-07-06 - Initial documentation based on session 145837 failure analysis
