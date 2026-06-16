# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Wastewater false discharge monitoring system based on a patent architecture using 6 layers: human-computer interaction, data collection, master agent, task orchestration, sub-agent, and data support layers. The system uses a Large Language Model (LLM) as a core coordinator that reads master/sub-agent identity files and calls pre-developed scripts from four sub-agents.

**最新功能**: Web智能查询界面，支持自然语言查询、图表可视化、异常点标注。

## Common Commands

### Web智能查询界面（推荐）

```bash
# Terminal 1: 启动查询接口
cd middleware
python query_interface.py
# 访问 http://localhost:8080

# Terminal 2: 启动监控服务（可选）
python app_orchestrator.py
```

### 示例自然语言查询
- "检测最近一周数据异常情况"
- "analyze pH COD anomalies in past 24 hours"
- "查看昨天总氮和总磷的趋势"

### 实时监测（Orchestrator-Core架构）

```bash
# Terminal 1: Start Flask middleware with full orchestrator-core pipeline
cd middleware
python app_orchestrator.py

# Terminal 2: Send simulated real-time data (reads from data/pollution_water_*.csv)
cd E:\project\Ecological_env
python stream/dual_data_stream.py

# Run independent test (no Flask required)
python tests/integration/test_orchestrator_simple.py
```

### Configuration

```bash
# Set up environment variables for LLM API
cd middleware
cp .env.example .env
# Edit .env to set ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN
```

### Testing

```bash
# Test LLM-driven single sub-agent coordination
python -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path('workspace/skills/orchestrator-core/scripts').resolve()))
from execution_control import LLMAgentCoordinator
from shared.configs.llm_client import get_llm_client

llm_client = get_llm_client(env_path='middleware/.env', config_path='shared/configs/llm_config.yaml')
coordinator = LLMAgentCoordinator(llm_client=llm_client)
result = coordinator.coordinate_agent_execution('multi-dimensional-data-perception-agent', {
    'task_id': 'test', 'data': {'influent': {'pH值': 7.2}, 'effluent': {'pH值': 7.5}}
})
print(result)
"

# Run orchestrator-core integration test
python tests/integration/test_orchestrator_simple.py

# Run master agent test
python tests/test_master_agent.py

# Run end-to-end pipeline test
python tests/integration/test_full_pipeline.py
```

### Monitoring

```bash
# Access Prometheus metrics
curl http://localhost:5000/metrics

# Health check
curl http://localhost:5000/health

# Grafana dashboard: import grafana/dashboards/stream_01.json
```

## Architecture Overview

### Patent 6-Layer Architecture

1. **Human-Computer Interaction Layer** (middleware/): Flask API, CLI, Grafana dashboards, **Web智能查询界面** ⭐
2. **Data Collection Layer** (stream/): Dual data stream simulator for influent/effluent data
3. **Master Agent Layer** (workspace/): Identity files (IDENTITY.md, AGENTS.md, MEMORY.md, SOUL.md, HEARTBEAT.md, TOOLS.md)
4. **Task Orchestration Layer** (workspace/skills/orchestrator-core/scripts/): Task structuring, flow generation, resource matching, execution control
5. **Sub-Agent Layer** (subagents/): Four specialized agents with their own identity files and scripts
6. **Data Support Layer** (shared/): Data, models, configs, knowledge base, operators

### Sub-Agents

1. **multi-dimensional-data-perception-agent** 📊: "多维数据感知子智能体" - Multi-Dimensional Data Processor, Vibe: 严谨、可靠、多源整合. Multi-source data acquisition, time alignment, data cleaning, standardization, data decomposition
2. **anomaly-detection-agent** 🔍: "异常检测子智能体" - Anomaly Detector, Vibe: 警惕、全面、谦逊. Operator adapter, anomaly scoring, pattern recognition (5 anomaly types), violation detection (4 violation types)
3. **rule-reasoning-agent** ⚖️: "规则推理子智能体" - Knowledge Reasoner, Vibe: 博学、精准、公正. Regulation matching, process validation, expert reasoning, violation generation
4. **disposition-execution-agent** 🚨: "研判预警与处置执行子智能体" - Action Executor, Vibe: 高效、规范、执行力强. Disposition analysis, warning generation, execution coordination

### Orchestrator-Core Pipeline

Real-time data flows through three stages with **complete LLM driving**:

1. **Task Receiving and Parsing** (task_receiving_and_parsing.py):
   - Master agent reads identity files (IDENTITY.md, AGENTS.md, SOUL.md, MEMORY.md)
   - LLM parses task intent and creates structured task

2. **LLM Coordination** (execution_control.py) - **Complete LLM Driving**:
   - LLM reads sub-agent identities (SKILL.md, AGENTS.md, SOUL.md, MEMORY.md)
   - LLM gets list of available scripts for each sub-agent
   - LLM decides which script to call based on task requirements
   - LLM analyzes script execution results
   - Falls back to local mode if LLM fails

3. **Result Interpretation** (result_interpretation.py):
   - Master agent reads knowledge base (regulations, patterns, expert experience)
   - LLM generates natural language report

### Web智能查询架构（新增）

```
用户自然语言输入
    ↓
LLM意图解析（Haiku快速模型）
    ↓
HistoricalDataFetcher获取历史数据
    ↓
LLM协调子智能体分析：
  1. multi-dimensional-data-perception-agent（数据预处理）
  2. anomaly-detection-agent（异常检测）
    ↓
LLM生成自然语言报告（Sonnet主模型）
    ↓
返回完整数据（时序数据+异常详情）
    ↓
前端Chart.js可视化展示
```

## LLM Integration

### Client Configuration

- LLM client wrapper: `shared/configs/llm_client.py`
- Environment variables: `middleware/.env` (ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN)
- Non-sensitive config: `shared/configs/llm_config.yaml`

### LLM Role (Two-Layer LLM-Driven Coordination)

The system implements **two-layer LLM-driven coordination** where the LLM acts at both master and sub-agent levels:

#### First Layer LLM (Master Agent)
- **Plans execution**: Decides which sub-agents to call and in what order
- **Processes outputs**: Takes raw output from each sub-agent, structures it, and passes to next sub-agent
- **Accumulates context**: Builds up processed context instead of overwriting

#### Second Layer LLM (Within Each Sub-Agent)
- **Selects scripts**: Decides which script to call based on task and sub-agent identity
- **Analyzes results**: Interprets script execution results

Key implementation: `workspace/skills/orchestrator-core/scripts/execution_control.py`
- `_llm_plan_subagent_execution()`: First-layer LLM plans sub-agent execution
- `_llm_process_agent_output()`: First-layer LLM processes sub-agent outputs
- `_llm_coordinate_agent()`: Second-layer LLM coordinates within each sub-agent
- `_get_available_scripts()`: Lists available scripts for LLM to choose from
- `_execute_script_by_decision()`: Executes the script chosen by LLM
- `_llm_analyze_result()`: Second-layer LLM analyzes execution results

**LLM Call Pattern** (for 4 sub-agents):
- 1 First-layer call: Plan sub-agent execution
- 4 × 2 Second-layer calls: Script selection + result analysis per sub-agent
- 3 First-layer calls: Process outputs between sub-agents
- **Total: ~12 LLM API calls per complete workflow**
- Generates natural language reports

### Identity Files

**Master Agent** (workspace/):
- IDENTITY.md: Identity card (Name: 废水监测主智能体, Creature: Multi-Agent Orchestrator, Vibe: 专业、严谨、数据驱动, Emoji: 🌊)
- AGENTS.md: Workspace rules, conventions, red lines
- SOUL.md: Personality and tone (data-driven, global-first, timely response)
- MEMORY.md: Long-term memory (system architecture, monitoring indicators, sub-agent responsibilities, violation patterns)
- USER.md: User information (name, timezone, preferences)
- TOOLS.md: Environment-specific notes (Flask port, data paths, sub-agent endpoints)
- HEARTBEAT.md: Periodic tasks (empty, tasks handled in scripts)

**Sub-Agents** (subagents/{agent}/):
Each sub-agent has its own identity files:
- IDENTITY.md: Identity card with Name, Creature, Vibe, Emoji
- AGENTS.md: Sub-agent specific task instructions (most important)
- SOUL.md: Sub-agent's role and personality
- TOOLS.md: Sub-agent specific tool conventions
- USER.md: User information
- MEMORY.md: Professional long-term memory (kept from original structure)

**Sub-Agent Identities**:
- multi-dimensional-data-perception-agent 📊: "多维数据感知子智能体" - Multi-Dimensional Data Processor, Vibe: 严谨、可靠、多源整合
- anomaly-detection-agent 🔍: "异常检测子智能体" - Anomaly Detector, Vibe: 警惕、全面、谦逊
- rule-reasoning-agent ⚖️: "规则推理子智能体" - Knowledge Reasoner, Vibe: 博学、精准、公正
- disposition-execution-agent 🚨: "研判预警与处置执行子智能体" - Action Executor, Vibe: 高效、规范、执行力强

## Data Flow

### 实时监测流程
```
stream/dual_data_stream.py → Flask /api/dual-stream
    ↓
Task Receiving & Parsing (master agent identity loaded)
    ↓
LLM coordinates 4 sub-agents (each loads its own identity):
    1. multi-dimensional-data-perception-agent → scripts in data-perception-core/scripts/
    2. anomaly-detection-agent → scripts in anomaly-detection-core/scripts/
    3. rule-reasoning-agent → scripts in rule-reasoning-core/scripts/
    4. disposition-execution-agent → scripts in disposition-execution-core/scripts/
    ↓
Result Interpretation (knowledge base loaded)
    ↓
Natural language report + alerts
```

### Web智能查询流程（新增）
```
Web界面 → middleware/query_interface.py
    ↓
LLM解析查询意图（Haiku）
    ↓
获取历史数据（HistoricalDataFetcher）
    ↓
LLM协调子智能体：
  - multi-dimensional-data-perception-agent
  - anomaly-detection-agent
    ↓
LLM生成报告（Sonnet）
    ↓
返回时序数据 + 异常详情
    ↓
前端Chart.js可视化
```

## Key Files

### Web智能查询（新增）
- `middleware/query_interface.py`: Flask查询接口，LLM驱动的自然语言查询
- `middleware/historical_data_fetcher.py`: 历史数据获取器
- `middleware/static/index.html`: Web前端界面
- `middleware/static/js/charts.js`: Chart.js图表模块
- `middleware/static/js/app.js`: 前端应用逻辑

### 核心模块
- `middleware/app_orchestrator.py`: Flask middleware implementing full orchestrator-core pipeline
- `stream/dual_data_stream.py`: Dual data stream simulator (reads from data/pollution_water_*.csv)
- `workspace/skills/orchestrator-core/scripts/`: Core orchestration modules
- `shared/configs/llm_client.py`: LLM client wrapper with configuration loading
- `shared/knowledge/`: Knowledge base (regulations/, process_knowledge/, violation_patterns/, expert_experience/)
- `shared/operators/`: Anomaly detection operators (statistical/, ml/, deep_learning/)

## Web界面功能

### 查询面板
- 自然语言输入框
- 实时状态显示
- 结果摘要展示
- 时序图表可视化

### 监控面板
- Grafana仪表板嵌入
- 实时数据展示
- 指标对比图表

### 分析报告面板
- Chart.js时序图表
- 多指标显示（pH、COD、TN、NH3-N、TP）
- 异常点红色标注
- 交互式tooltip

## Violation Detection

The system detects 4 types of violations:
1. **插瓶干扰** (bottle interference): Constant or near-constant values
2. **人工拟合** (artificial fitting): Too-smooth curves, low variance
3. **稀释排放** (dilution discharge): Sudden flow increase with proportional pollutant decrease
4. **恶意逃避** (malicious evasion): Patterns designed to avoid detection

## Notes

- All modules are initialized with `llm_client=None` by default; LLM integration happens through the coordinator
- Path resolution uses multiple strategies to find workspace/ and subagents/ directories dynamically
- IntentResult is a dataclass - access attributes via dot notation, not `.get()` method
- Prometheus metrics expose influent/effluent pH, COD, TN, AN, TP, flow rate, and counters for data processed, anomalies detected, and alerts
- **Web查询支持中英文自然语言输入**
- **图表自动标注异常点，支持图例点击切换**
