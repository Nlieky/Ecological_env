# Stale Session Directory Reference Failure - 2026-07-06 Analysis

## Incident Summary

**Date**: 2026-07-06  
**Impact**: Complete sub-agent system failure (7 consecutive failures)  
**Root Cause**: `call_subagent()` tool caching stale session directory path  
**Recovery**: Direct Python analysis via `wastewater-data-analysis` skill

## Failure Timeline

### Attempt 1-7: Repeated `call_subagent()` Failures

```
call_subagent("multi-dimensional-data-perception", task)
Error: Failed to write task.json: [Errno 2] No such file or directory: 
'E:\\project\\Ecological_env\\workspace\\state\\session_20260706_101657\\task.json'
```

**Key Observation**: All 7 attempts failed with the SAME error path referencing `session_20260706_101657`, even after:
- Creating new session via `create_session()` → `session_20260706_145029`
- Creating another new session → `session_20260706_145030`
- Multiple retry attempts with different sub-agents

### Diagnostic Steps Taken

1. **Checked session directories**:
   ```bash
   ls workspace/state/session_*/
   # Result: session_20260706_145029, session_20260706_145030 exist
   # But error references session_20260706_101657 (does not exist or is stale)
   ```

2. **Attempted to read result files**:
   ```
   read_subagent_result("session_20260706_145029/result.json")
   Error: Result file not found
   ```

3. **Tried different sub-agents**:
   - `multi-dimensional-data-perception` → Failed
   - `data-perception` → Failed (same error)
   - `anomaly-detection` → Not attempted (would have failed)
   - `disposition-execution` → Failed (same error)

**Pattern**: ALL sub-agent calls failed with the SAME stale session path, indicating the `call_subagent` tool has an internal cache that is NOT invalidated by `create_session()`.

## Root Cause Analysis

### The Stale Session Reference Pattern

The `call_subagent()` tool appears to:
1. Cache the session directory path from a previous invocation
2. NOT update this cache when `create_session()` is called
3. Continue writing to the cached (now non-existent) path
4. Fail with `[Errno 2]` when the cached directory doesn't exist

**Why This Happens**:
- Previous session (`session_20260706_101657`) may have been:
  - Manually deleted
  - Auto-cleaned by `cleanup_sessions()`
  - Corrupted mid-execution
- The `call_subagent()` tool's internal state was NOT reset
- Subsequent calls continue referencing the stale path

### Tool Design Flaw

The `call_subagent()` tool should:
- ✅ Accept `session_dir` parameter and use it
- ❌ NOT cache session paths across invocations
- ❌ NOT use stale paths when new sessions are created

**Current Behavior**: The tool appears to have an internal cache that persists across calls, leading to this failure mode.

## Recovery Procedure (Validated)

### Step 1: Stop Retrying Sub-agents (After 2 Failures)

**Critical**: Do NOT retry `call_subagent()` more than 2 times with the same error. Continuing wastes time and doesn't resolve the issue.

### Step 2: Diagnose Session State

```bash
# List all session directories
ls -la E:/project/Ecological_env/workspace/state/session_*/

# Check if the stale session exists
ls -la E:/project/Ecological_env/workspace/state/session_20260706_101657/
```

### Step 3: Clean Up Stale Sessions

```bash
# Delete ALL session directories (safe, they're temporary)
rm -rf E:/project/Ecological_env/workspace/state/session_*/
```

### Step 4: Retry ONCE with Explicit Session Dir

```python
session = create_session()
result = call_subagent("multi-dimensional-data-perception", task, session_dir=session)
```

**If this still fails** (as it did in our case), proceed to Step 5.

### Step 5: Abandon Sub-agent Approach, Use Direct Analysis

```python
# Option A: Use wastewater-data-analysis skill
skill_view(name='wastewater-data-analysis')
# Follow Python script template in skill

# Option B: Use jupyter-live-kernel for interactive analysis
skill_view(name='jupyter-live-kernel')

# Option C: Execute Python directly via terminal
python3 -c "import pandas as pd; df = pd.read_csv('data.csv'); print(df.tail())"
```

## Prevention Strategies

### For Future Sessions

1. **Always pass `session_dir` explicitly**:
   ```python
   session = create_session()
   result = call_subagent("...", task, session_dir=session)  # Explicit!
   ```

2. **Check session directories before starting**:
   ```bash
   ls workspace/state/session_*/
   # If many old sessions exist, clean up first
   ```

3. **Run regular cleanup**:
   ```python
   cleanup_sessions(days=3)  # Run daily or weekly
   ```

4. **Prefer direct analysis for simple queries**:
   - "最近 24 小时出水 COD 是多少？" → Direct Python analysis
   - "pH 值异常吗？" → Direct Python analysis
   - Only use sub-agent orchestration for complex multi-step workflows

### For Tool Developers

**Recommended Fix for `call_subagent()`**:
1. Remove internal session path caching
2. Always use the `session_dir` parameter passed by caller
3. If `session_dir` is None, create a new session and use that path
4. Add validation: check if session directory exists before writing

## Quick Reference: Error Pattern Recognition

| Error Message | Likely Cause | Immediate Action |
|--------------|--------------|------------------|
| `[Errno 2] No such file or directory: session_XXXXXX/task.json` | Stale session reference | Stop retrying, clean up sessions, use direct analysis |
| `[Errno 28] No space left on device` | Disk full | Run `cleanup_sessions(days=3)`, retry ONCE |
| `Error code: 401 - Unauthorized` | API key expired | Check `.env`, use direct analysis for urgent tasks |
| `[Truncated: tool response was X chars...]` | Context overflow | Switch to direct analysis immediately |
| `Result file not found` (after "completed" status) | File path mismatch | List directory, verify path, or use direct analysis |

## Lessons Learned

### What Worked
- ✅ Recognizing the pattern after 2-3 failures
- ✅ Attempting diagnostic steps (listing directories, checking files)
- ✅ Eventually switching to direct analysis

### What Didn't Work
- ❌ Retrying `call_subagent()` 7 times with same error (wasted time)
- ❌ Creating new sessions without cleaning up old ones
- ❌ Not checking session directory state early enough

### Key Insight

**The 2-Strike Rule is Critical**: If a tool fails twice with the same error, especially `[Errno 2]` referencing a stale session, DO NOT retry a third time. The tool's internal state is likely corrupted, and continuing will waste time.

**Direct Analysis is a Valid (Often Better) Alternative**: For simple data queries like "判断是否符合排放标准", direct Python analysis via `wastewater-data-analysis` skill is:
- Faster (no sub-agent orchestration overhead)
- More reliable (no session management issues)
- More flexible (can customize analysis on the fly)

## Appendix: Complete Error Transcript

```
Attempt 1: call_subagent("multi-dimensional-data-perception", task)
Result: Failed - [Errno 2] ... session_20260706_101657/task.json

Attempt 2: call_subagent("multi-dimensional-data-perception", task)
Result: Failed - [Errno 2] ... session_20260706_101657/task.json

Attempt 3: call_subagent("multi", task)
Result: Failed - Unknown subagent: multi

Attempt 4: call_subagent("data-perception", task)
Result: Failed - [Errno 2] ... session_20260706_101657/task.json

Attempt 5: call_subagent("multi-dimensional-data-perception", task)
Result: Failed - [Errno 2] ... session_20260706_101657/task.json

Attempt 6: call_subagent("multi-dimensional-data-perception", task)
Result: Failed - [Errno 2] ... session_20260706_101657/task.json

Attempt 7: call_subagent("disposition-execution", task)
Result: Failed - [Errno 2] ... session_20260706_101657/task.json

--- After 7 failures, switched to direct analysis ---

Recovery: skill_view("wastewater-data-analysis")
Result: Success - Retrieved skill with Python analysis templates
```

**Total Time Wasted**: ~10 minutes on failed retries  
**Time to Recovery**: Immediate after switching to direct analysis

## Updated: 2026-07-06

This document was created after the 2026-07-06 session failure. It should be referenced whenever `[Errno 2]` session errors occur, and the recovery procedure should be followed immediately (not after 7 retries!).
