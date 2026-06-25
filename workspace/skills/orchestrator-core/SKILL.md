---
name: orchestrator-core
description: "Multi-agent orchestration skill for wastewater monitoring system. Coordinates 4 specialized sub-agents: data-perception (acquisition and preprocessing), anomaly-detection (pattern recognition and violation detection), rule-reasoning (regulatory compliance analysis), and disposition-execution (alert classification and work order generation). Use when user queries involve wastewater monitoring data analysis, anomaly detection, compliance assessment, or处置方案 generation. The LLM dynamically decides which sub-agents to call and in what sequence based on task requirements."
---

# Orchestrator Core

Coordinate wastewater monitoring sub-agents to complete user tasks.

## Available Sub-Agents

### Data Perception Agent
- **Name**: `multi-dimensional-data-perception`
- **Location**: `../subagents/multi-dimensional-data-perception-agent`
- **Capability**: Acquire, clean, and standardize multi-dimensional time-series data
- **Trigger**: Query involves data acquisition, indicator queries, influent/effluent analysis
- **Input**: Time range, indicator list
- **Output**: Preprocessed data (influent and effluent indicators)

### Anomaly Detection Agent
- **Name**: `anomaly-detection`
- **Location**: `../subagents/anomaly-detection-agent`
- **Capability**: Detect time-series anomalies and violation patterns
- **Trigger**: Query involves anomaly detection, spike analysis, trend assessment
- **Dependency**: Requires data perception agent output
- **Output**: Anomaly point list, violation events

### Rule Reasoning Agent
- **Name**: `rule-reasoning`
- **Location**: `../subagents/rule-reasoning-agent`
- **Capability**: Regulatory compliance determination based on standards
- **Trigger**: Query involves compliance assessment, exceedance analysis, violation causation
- **Dependency**: Requires anomaly detection agent output
- **Output**: Compliance conclusion, violation basis

### Disposition Execution Agent
- **Name**: `disposition-execution`
- **Location**: `../subagents/disposition-execution-agent`
- **Capability**: Generate alert classification and work orders
- **Trigger**: Query involves work order generation, disposal recommendations, alert notification
- **Dependency**: Requires rule reasoning agent output
- **Output**: Work order details, disposal recommendations

## Orchestration Principles

1. **Dynamic Decision-Making**: Not all tasks require calling every sub-agent
2. **Respect Dependencies**: Invocation sequence must respect inter-agent dependencies
3. **Flexible Strategy**: Adjust invocation strategy based on task requirements
4. **Error Handling**: When sub-agents fail, determine whether to retry or use alternative approaches

## Available Tools

- `create_session()`: Create new session directory for state isolation
- `call_subagent(name, task, context)`: Invoke specified sub-agent
- `cleanup_sessions(days)`: Clean up session directories older than specified days

## Tool Usage Details

### create_session()

Creates a new session directory for state isolation.

**Creates:**
- Session directory: `workspace/state/session_YYYYMMDD_HHMMSS/`
- Metadata file: `_metadata.json` with creation timestamp

**Session directory contents (during execution):**
```
session_YYYYMMDD_HHMMSS/
├── _metadata.json          # Session metadata
├── task.json                # Current task (written by main agent)
├── data_result.json         # Data perception result
├── anomaly_result.json      # Anomaly detection result
├── rule_result.json         # Rule reasoning result
├── disposition_result.json  # Disposition execution result
└── final_response.json      # Aggregated final response
```

### call_subagent(subagent_name, task, context, session_dir, timeout)

Invokes a sub-agent to execute a task.

**Parameters:**
- `subagent_name` (str): Name of sub-agent
  - `"data-perception"` or `"multi-dimensional-data-perception"` - Multi-dimensional data perception
  - `"anomaly-detection"` or `"anomaly"` - Anomaly detection
  - `"rule-reasoning"` or `"rule"` - Rule reasoning
  - `"disposition-execution"` or `"disposition"` - Disposition execution
- `task` (str): Task description string
- `context` (dict, optional): Previous sub-agent results
- `session_dir` (str, optional): Session directory path (creates new if None)
- `timeout` (int, optional): Maximum wait time in seconds (default: 300)

**Returns:**
```python
{
    "task_id": "task_data-perception_1234567890",
    "status": "completed",  # or "failed", "error"
    "result": {...},        # Task result data
    "error": null,          # Error message if failed
    "metadata": {
        "duration_seconds": 2.3,
        "timestamp": "2025-06-23T14:30:25"
    }
}
```

**Error Handling:**
- `ValueError` - Invalid sub-agent name
- `TimeoutError` - Sub-agent execution exceeds timeout

**Result File Format:**
Each sub-agent writes a `{subagent_name}_result.json` file to the session directory.
```
"data-perception" → data_result.json
"anomaly-detection" → anomaly_result.json
"rule-reasoning" → rule_result.json
"disposition-execution" → disposition_result.json
```

### cleanup_sessions(days, dry_run)

Removes old session directories to manage disk space.

**Parameters:**
- `days` (int): Keep sessions from last N days (default: 7)
- `dry_run` (bool): If True, only report what would be deleted

**Returns:**
```python
{
    "count": 5,
    "size_bytes": 5242880,
    "size_mb": 5.0,
    "deleted": [...],
    "kept": [...],
    "dry_run": False
}
```

## Task Context Flow

When a task requires multiple sub-agents, pass previous results as context:

```
User Query → LLM Analysis → Sub-agent Selection
    ↓
Data Perception → (result) → Anomaly Detection → (result) → Rule Reasoning → (result) → Disposition
    ↓
Final Response
```

## Error Handling Strategy

- **Retryable errors**: Network timeout, API rate limit, database connection issues
- **Non-retryable errors**: Invalid parameters, permission denied, data not found
- **Decision**: Analyze error type and context before deciding retry or alternative approach
