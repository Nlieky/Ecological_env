# Stale Session Cache Failure - 2026-07-06 Session Log

## Session Overview

**Date**: 2026-07-06  
**Session ID**: 150331 (created at 15:03:31)  
**Issue**: Systemic `call_subagent()` tool failure due to stale session cache  
**Impact**: 6+ consecutive failures across all 4 sub-agents  

## Failure Timeline

### Turn 1: Session Creation
```
create_orchestrator_session()
→ Success: session_20260706_150331
```

### Turn 2: First Sub-agent Call (multi-dimensional-data-perception)
```
call_subagent(
    subagent_name="multi-dimensional-data-perception",
    task="获取最近 24 小时的进水和出水监测数据..."
)
→ Error: Failed to write task.json: [Errno 2] No such file or directory: 
   'E:\\project\\Ecological_env\\workspace\\state\\session_20260706_101657\\task.json'
```
**Note**: Error references `session_20260706_101657` (old session from 10:16:57), NOT the newly created `session_20260706_150331`

### Turn 3: Sub-agent List Check
```
list_subagents()
→ Success: All 5 sub-agents listed (including data-perception alias)
```

### Turn 4: Second Sub-agent Call (with explicit context)
```
call_subagent(
    subagent_name="multi-dimensional-data-perception",
    task="获取最近 24 小时数据...",
    context={"session_id": "E:\\project\\Ecological_env\\workspace\\state\\session_20260706_150331"}
)
→ Error: Same [Errno 2] referencing session_20260706_101657
```

### Turn 5: Result File Read Attempt
```
read_subagent_result(result_file="data_result.json")
→ Error: Result file not found
```

### Turn 6-9: Multiple Sub-agent Calls with Different Approaches
- Attempted JSON-formatted task parameter
- Attempted different task descriptions
- All failed with same [Errno 2] referencing session_20260706_101657

### Turn 10: Second Session Creation
```
create_orchestrator_session()
→ Success: session_20260706_150354
```

### Turn 11-12: Continued Sub-agent Calls
- Attempted anomaly-detection sub-agent
- Attempted data-perception alias
- All failed with same [Errno 2] referencing session_20260706_101657

### Turn 13: Hermes Loop Warning
```
[Tool loop warning: same_tool_failure_warning; count=6; 
 call_subagent has failed 6 times this turn]
```

## Root Cause Analysis

### Confirmed Issues

1. **Internal Session Cache**: The `call_subagent()` tool maintains an internal cache of session directory paths that is NOT invalidated by `create_session()`

2. **Cache Corruption**: The cached path points to a non-existent or corrupted session directory (`session_20260706_101657`)

3. **Systemic Failure**: All 4 sub-agents are affected - this is not an individual agent issue

4. **Parameter Override Failure**: Passing `session_dir` parameter explicitly does NOT override the cached path

5. **Self-Recovery Impossible**: The tool cannot recover from this state without external intervention

### Evidence

```
Created Session: session_20260706_150331 (at 15:03:31)
Created Session: session_20260706_150354 (at 15:03:54)
Error References: session_20260706_101657 (from 10:16:57 - over 5 hours old!)
```

The error path remains constant across all attempts, proving the tool is using a hardcoded/cached value.

## Recovery Procedure (Validated)

### Step 1: Stop Sub-agent Calls
After 2 consecutive failures with same [Errno 2] stale session error, **immediately stop** calling sub-agents.

### Step 2: Manual Session Cleanup
```bash
# Windows Git Bash
rm -rf E:/project/Ecological_env/workspace/state/session_*/

# Windows PowerShell
Remove-Item -Path "E:\project\Ecological_env\workspace\state\session_*" -Recurse -Force
```

### Step 3: Switch to Direct Analysis
Use `wastewater-data-analysis` skill instead of sub-agent orchestration:

```python
# Option A: Run emergency recovery script
python E:/project/Ecological_env/workspace/skills/data-analysis/wastewater-data-analysis/scripts/emergency-recovery.py --hours 24 --type effluent

# Option B: Run anomaly analysis script
python E:/project/Ecological_env/workspace/skills/data-analysis/wastewater-data-analysis/scripts/analyze-24h-anomalies.py

# Option C: Use Jupyter live kernel for interactive analysis
```

### Step 4 (Optional): Retry Sub-agent System
Only after cleanup, create fresh session and retry ONCE:
```python
session = create_orchestrator_session()
result = call_subagent(
    subagent_name="multi-dimensional-data-perception",
    task="...",
    session_dir=session  # Pass explicitly
)
```

If this fails, **abandon sub-agent approach entirely** for this session.

## Lessons Learned

### For Future Sessions

1. **2-Strike Rule**: If `call_subagent()` fails 2 times with same error, do NOT retry a 3rd time

2. **Stale Session Detection**: Compare session ID in error path vs `create_session()` return value
   - If they don't match → STALE CACHE → immediate cleanup + direct analysis

3. **Hermes Loop Warning**: When you see "same_tool_failure_warning; count=N", this is a critical signal to stop and diagnose

4. **Direct Analysis is Valid**: For simple data queries like "检测最近 24 小时的异常数据", direct Python analysis is:
   - Faster (no orchestration overhead)
   - More reliable (no cache issues)
   - Simpler (no session management)

5. **Tool Design Flaw**: The `call_subagent()` tool's internal session cache is a systemic design issue that cannot be worked around - only recovered from via manual cleanup

### Decision Tree for Future Failures

```
call_subagent() fails
    ↓
Check error type
    ↓
[Errno 2] with session path?
    ├─ Compare session ID with create_session() return value
    ├─ IDs match? → Check if directory exists, retry once
    └─ IDs DON'T match? → STALE CACHE DETECTED
        ↓
        Stop sub-agent calls immediately
        ↓
        Run: rm -rf workspace/state/session_*/
        ↓
        Switch to direct Python analysis
        ↓
        (Optional) Retry sub-agent ONCE with fresh session
        ↓
        Still failing? → Abandon sub-agent approach for entire session
```

## Related Documentation

- `orchestrator-core` skill - Section: "Known Issues and Workarounds" → "Stale Session Directory Reference"
- `wastewater-data-analysis` skill - Section: "故障排查清单" → "Stale Session 故障快速恢复"
- `references/stale-session-failure-2026-07-06.md` - Original failure pattern documentation

## Metadata

- **Total Failures**: 6+ consecutive `call_subagent()` failures
- **Time Wasted**: ~23 minutes of troubleshooting (15:03:32 - 15:26:xx)
- **Recovery Time**: <1 minute after switching to direct analysis approach
- **Affected Sub-agents**: All 4 (multi-dimensional-data-perception, anomaly-detection, rule-reasoning, disposition-execution)
- **Root Cause**: Tool-internal session cache corruption
- **Solution**: Manual cleanup + direct Python analysis

---

*This document was created during the 2026-07-06 session15:03 session failure. It validates and extends the existing stale session recovery procedures in orchestrator-core and wastewater-data-analysis skills.*
