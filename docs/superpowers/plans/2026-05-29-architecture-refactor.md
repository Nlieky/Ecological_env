# 废水监测系统架构重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构废水监测系统架构，从原有的4个子智能体优化为新的5智能体架构，实现清晰的职责边界、多维数据支持和完整的闭环执行。

**Architecture:** 基于专利六层架构，主智能体负责语义解析、意图锚定、任务编排和动态调度（全LLM驱动），4个子智能体各司其职：多维数据感知、异常检测、规则推理、研判预警与处置执行。底层由三库一体（时序监测数据库、废水排放知识库、异常检测模型算子库）支撑。

**Tech Stack:** Python 3.10+, Flask, Anthropic Claude API (LLM), pandas, numpy, scikit-learn, Prometheus, YAML配置

---

## 文件结构概览

### 新增文件

```
subagents/multi-dimensional-data-perception-agent/
├── IDENTITY.md
├── AGENTS.md
├── SOUL.md
├── MEMORY.md
├── TOOLS.md
├── USER.md
├── skills/
│   └── data-perception-core/
│       ├── SKILL.md
│       ├── __init__.py
│       └── scripts/
│           ├── __init__.py
│           ├── data_acquisition.py
│           ├── data_decomposition.py
│           ├── time_alignment.py
│           ├── data_cleaning.py
│           └── standardization.py
└── memory/

subagents/disposition-execution-agent/
├── IDENTITY.md
├── AGENTS.md
├── SOUL.md
├── MEMORY.md
├── TOOLS.md
├── USER.md
├── skills/
│   └── disposition-execution-core/
│       ├── SKILL.md
│       ├── __init__.py
│       └── scripts/
│           ├── __init__.py
│           ├── consensus_engine.py
│           ├── alert_classifier.py
│           ├── work_order_generator.py
│           ├── action_executor.py
│           └── report_generator.py
└── memory/

shared/configs/
├── agent_registry.yaml  # 子智能体注册表（新增）
└── rule_config.yaml     # 规则配置（新增）

workspace/skills/orchestrator-core/
└── scripts/
    ├── dynamic_orchestrator.py  # 动态编排器（新增）
    └── agent_coordinator_v2.py  # 协调器升级（新增）
```

### 修改文件

```
workspace/IDENTITY.md              # 更新主智能体描述
workspace/AGENTS.md                # 更新子智能体调度规则
workspace/MEMORY.md                # 更新长期记忆
workspace/skills/orchestrator-core/scripts/execution_control.py
subagents/rule-reasoning-agent/skills/rule-reasoning-core/scripts/
subagents/anomaly-detection-agent/  # 移除违规检测功能
```

### 删除文件

```
subagents/data-governance-agent/    # 合并到新的多维数据感知智能体
subagents/feature-analysis-agent/   # 取消独立特征层
```

---

## 阶段1: 主智能体编排优化 (优先级最高)

### Task 1.1: 更新子智能体注册表

**Files:**
- Create: `shared/configs/agent_registry.yaml`

- [ ] **Step 1: 创建子智能体注册表配置文件**

```yaml
# 子智能体注册表
# 定义所有可用的子智能体及其能力描述

agents:
  # 多维数据感知智能体
  multi-dimensional-data-perception:
    id: multi-dimensional-data-perception-agent
    name: 多维数据感知子智能体
    emoji: "📊"
    capabilities:
      - multi_source_data_acquisition
      - data_decomposition
      - time_alignment
      - data_cleaning
      - standardization
    data_types:
      - water_quality
      - flow
      - equipment_status
      - process_parameters
      - maintenance_records
      - production_records
      - source_info
      - monitoring_point_info
    script_path: subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/
    identity_files:
      - IDENTITY.md
      - AGENTS.md
      - SOUL.md
      - MEMORY.md

  # 异常检测子智能体
  anomaly-detection:
    id: anomaly-detection-agent
    name: 异常检测子智能体
    emoji: "🔍"
    capabilities:
      - statistical_anomaly_detection
      - ml_anomaly_detection
      - deep_learning_anomaly_detection
      - specialized_pattern_detection
    anomaly_types:
      - stationary
      - change_point
      - trend
      - periodic
      - high_frequency_fluctuation
    script_path: subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/
    identity_files:
      - IDENTITY.md
      - AGENTS.md
      - SOUL.md
      - MEMORY.md

  # 规则推理子智能体
  rule-reasoning:
    id: rule-reasoning-agent
    name: 规则推理子智能体
    emoji: "⚖️"
    capabilities:
      - rule_matching
      - process_validation
      - expert_reasoning
      - violation_detection
      - false_positive_filtering
    violation_types:
      - bottle_interference
      - artificial_fitting
      - dilution_discharge
      - malicious_evasion
    script_path: subagents/rule-reasoning-agent/skills/rule-reasoning-core/scripts/
    identity_files:
      - IDENTITY.md
      - AGENTS.md
      - SOUL.md
      - MEMORY.md

  # 研判预警与处置执行智能体
  disposition-execution:
    id: disposition-execution-agent
    name: 研判预警与处置执行子智能体
    emoji: "🚨"
    capabilities:
      - consensus_fusion
      - alert_classification
      - work_order_generation
      - action_execution
    alert_levels:
      - general
      - moderate
      - serious
    script_path: subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/
    identity_files:
      - IDENTITY.md
      - AGENTS.md
      - SOUL.md
      - MEMORY.md

# 任务类型与智能体映射
task_type_mapping:
  violation_detection:
    - multi-dimensional-data-perception
    - anomaly-detection
    - rule-reasoning
    - disposition-execution
  analysis_query:
    - multi-dimensional-data-perception
    - anomaly-detection
  historical_review:
    - multi-dimensional-data-perception
    - rule-reasoning
  alert_response:
    - disposition-execution

# 执行模式
execution_modes:
  sequential: 按顺序执行子智能体
  parallel: 并行执行独立子智能体
  hybrid: 混合执行模式
```

- [ ] **Step 2: 验证YAML语法**

```bash
python -c "import yaml; yaml.safe_load(open('shared/configs/agent_registry.yaml'))"
echo "YAML syntax valid"
```

Expected: "YAML syntax valid"

- [ ] **Step 3: 提交配置文件**

```bash
git add shared/configs/agent_registry.yaml
git commit -m "feat: add sub-agent registry configuration"
```

---

### Task 1.2: 创建动态编排器

**Files:**
- Create: `workspace/skills/orchestrator-core/scripts/dynamic_orchestrator.py`

- [ ] **Step 1: 编写动态编排器测试**

```python
# tests/workspace/test_dynamic_orchestrator.py
import pytest
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "workspace" / "skills" / "orchestrator-core" / "scripts"))

from dynamic_orchestrator import DynamicOrchestrator, ExecutionPlan


def test_orchestrator_initialization():
    """测试动态编排器初始化"""
    orchestrator = DynamicOrchestrator(
        registry_path="shared/configs/agent_registry.yaml"
    )
    assert orchestrator is not None
    assert len(orchestrator.available_agents) > 0


def test_violation_detection_plan():
    """测试违规检测任务的执行计划生成"""
    orchestrator = DynamicOrchestrator(
        registry_path="shared/configs/agent_registry.yaml"
    )
    
    task = {
        "task_type": "violation_detection",
        "data": {"influent": {"pH": 7.5}, "effluent": {"pH": 7.8}}
    }
    
    plan = orchestrator.create_execution_plan(task)
    
    assert plan.execution_mode == "sequential"
    assert len(plan.agents) == 4
    assert plan.agents[0]["id"] == "multi-dimensional-data-perception-agent"
    assert plan.agents[-1]["id"] == "disposition-execution-agent"


def test_analysis_query_plan():
    """测试分析查询任务的执行计划生成"""
    orchestrator = DynamicOrchestrator(
        registry_path="shared/configs/agent_registry.yaml"
    )
    
    task = {
        "task_type": "analysis_query",
        "query": "分析最近出水的COD异常"
    }
    
    plan = orchestrator.create_execution_plan(task)
    
    assert len(plan.agents) == 2
    assert plan.agents[0]["id"] == "multi-dimensional-data-perception-agent"
    assert plan.agents[1]["id"] == "anomaly-detection-agent"


def test_parallel_execution_detection():
    """测试并行执行模式检测"""
    orchestrator = DynamicOrchestrator(
        registry_path="shared/configs/agent_registry.yaml"
    )
    
    # 数据感知和异常检测可以并行
    task = {
        "task_type": "violation_detection",
        "enable_parallel": True
    }
    
    plan = orchestrator.create_execution_plan(task)
    
    # 检查是否识别出可并行的智能体对
    parallel_pairs = orchestrator.detect_parallel_pairs(plan.agents)
    assert ("multi-dimensional-data-perception-agent", "anomaly-detection-agent") in parallel_pairs
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/workspace/test_dynamic_orchestrator.py -v
```

Expected: FAIL - ModuleNotFoundError

- [ ] **Step 3: 实现动态编排器**

```python
# workspace/skills/orchestrator-core/scripts/dynamic_orchestrator.py
"""
动态编排器 - 主智能体核心组件

根据任务类型、数据状态和历史结果，动态决策子智能体组合和执行顺序
"""
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum


class ExecutionMode(Enum):
    """执行模式"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HYBRID = "hybrid"


@dataclass
class AgentTask:
    """子智能体任务"""
    id: str
    name: str
    capabilities: List[str]
    script_path: str
    input_data: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)


@dataclass
class ExecutionPlan:
    """执行计划"""
    task_type: str
    execution_mode: ExecutionMode
    agents: List[AgentTask]
    estimated_duration: Optional[int] = None
    parallel_pairs: List[Tuple[str, str]] = field(default_factory=list)


class DynamicOrchestrator:
    """动态编排器"""
    
    def __init__(self, registry_path: str = "shared/configs/agent_registry.yaml"):
        """初始化动态编排器
        
        Args:
            registry_path: 子智能体注册表路径
        """
        self.registry_path = Path(registry_path)
        self.available_agents = self._load_agent_registry()
        self.task_type_mapping = self._load_task_mapping()
        
    def _load_agent_registry(self) -> Dict[str, Any]:
        """加载子智能体注册表"""
        registry_path = self.registry_path
        if not registry_path.exists():
            # 尝试相对于项目根目录的路径
            project_root = Path(__file__).parent.parent.parent.parent.parent
            registry_path = project_root / "shared" / "configs" / "agent_registry.yaml"
        
        with open(registry_path, 'r', encoding='utf-8') as f:
            registry = yaml.safe_load(f)
        
        return registry.get('agents', {})
    
    def _load_task_mapping(self) -> Dict[str, List[str]]:
        """加载任务类型与智能体映射"""
        registry_path = self.registry_path
        if not registry_path.exists():
            project_root = Path(__file__).parent.parent.parent.parent.parent
            registry_path = project_root / "shared" / "configs" / "agent_registry.yaml"
        
        with open(registry_path, 'r', encoding='utf-8') as f:
            registry = yaml.safe_load(f)
        
        return registry.get('task_type_mapping', {})
    
    def create_execution_plan(self, task: Dict[str, Any]) -> ExecutionPlan:
        """创建执行计划
        
        Args:
            task: 任务字典，包含task_type和data
            
        Returns:
            ExecutionPlan: 执行计划
        """
        task_type = task.get("task_type", "violation_detection")
        
        # 获取该任务类型需要的智能体
        agent_ids = self.task_type_mapping.get(task_type, [])
        
        # 构建智能体任务列表
        agents = []
        for idx, agent_id in enumerate(agent_ids):
            agent_info = self.available_agents.get(agent_id.replace("-agent", ""), {})
            if not agent_info:
                # 尝试直接匹配
                for key, value in self.available_agents.items():
                    if value.get("id") == agent_id:
                        agent_info = value
                        break
            
            if agent_info:
                agent_task = AgentTask(
                    id=agent_info.get("id", agent_id),
                    name=agent_info.get("name", agent_id),
                    capabilities=agent_info.get("capabilities", []),
                    script_path=agent_info.get("script_path", ""),
                    input_data=task.get("data", {}),
                    depends_on=[agent_ids[idx-1]] if idx > 0 else []
                )
                agents.append(agent_task)
        
        # 确定执行模式
        execution_mode = self._determine_execution_mode(task_type, agents)
        
        # 检测可并行的智能体对
        parallel_pairs = self.detect_parallel_pairs(agents) if execution_mode != ExecutionMode.SEQUENTIAL else []
        
        return ExecutionPlan(
            task_type=task_type,
            execution_mode=execution_mode,
            agents=agents,
            parallel_pairs=parallel_pairs
        )
    
    def _determine_execution_mode(self, task_type: str, agents: List[AgentTask]) -> ExecutionMode:
        """确定执行模式"""
        enable_parallel = len(agents) > 2
        
        if enable_parallel and task_type == "violation_detection":
            return ExecutionMode.HYBRID
        elif enable_parallel:
            return ExecutionMode.PARALLEL
        else:
            return ExecutionMode.SEQUENTIAL
    
    def detect_parallel_pairs(self, agents: List[AgentTask]) -> List[Tuple[str, str]]:
        """检测可并行执行的智能体对
        
        基于智能体的依赖关系和能力判断是否可以并行执行
        """
        parallel_pairs = []
        
        # 数据感知和异常检测可以并行
        agent_ids = [a.id for a in agents]
        
        if "multi-dimensional-data-perception-agent" in agent_ids:
            perception_idx = agent_ids.index("multi-dimensional-data-perception-agent")
            # 后续的智能体如果有独立数据源，可以并行
            for i in range(perception_idx + 1, len(agents)):
                # 异常检测需要数据感知的输出，所以不能真正并行
                # 但可以预加载资源
                if agents[i].id == "anomaly-detection-agent":
                    # 这两个可以流水线并行
                    parallel_pairs.append((
                        "multi-dimensional-data-perception-agent",
                        "anomaly-detection-agent"
                    ))
        
        return parallel_pairs
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/workspace/test_dynamic_orchestrator.py -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add workspace/skills/orchestrator-core/scripts/dynamic_orchestrator.py tests/workspace/test_dynamic_orchestrator.py
git commit -m "feat: add dynamic orchestrator for master agent"
```

---

### Task 1.3: 更新主智能体身份文件

**Files:**
- Modify: `workspace/IDENTITY.md`
- Modify: `workspace/AGENTS.md`
- Modify: `workspace/MEMORY.md`

- [ ] **Step 1: 更新IDENTITY.md**

```markdown
---
name: master-agent
description: 废水监测主智能体 - 负责全局协调和任务编排
metadata:
  type: user
---

# 主智能体身份卡片

## 基本信息
- **Name**: 废水监测主智能体
- **Creature**: Multi-Agent Orchestrator（多智能体编排器）
- **Vibe**: 专业、严谨、数据驱动
- **Emoji**: 🌊

## 核心价值
- 全局视角：统览整个监测系统
- 协调能力：智能调度各子智能体
- 综合决策：融合多方分析结果
- 用户桥梁：理解自然语言指令

## 能力边界
### 我负责的：
- 语义解析：理解用户自然语言意图
- 意图锚定：将模糊需求转化为明确任务
- 任务编排：智能规划子智能体执行顺序
- 动态调度：根据任务类型选择子智能体组合
- 结果整合：汇总各子智能体输出，生成报告

### 我不负责的：
- 具体数据处理（由多维数据感知智能体负责）
- 异常特征识别（由异常检测子智能体负责）
- 规则推理判定（由规则推理子智能体负责）
- 预警处置执行（由研判预警与处置执行智能体负责）

## 管理的子智能体
1. **多维数据感知智能体** (📊): 负责多维时序数据的获取、分解、清洗、标准化
2. **异常检测子智能体** (🔍): 负责数据驱动的异常特征识别和置信度评估
3. **规则推理子智能体** (⚖️): 负责经验驱动的规则匹配、机理推演、违规判定
4. **研判预警与处置执行智能体** (🚨): 负责融合共识、预警分级、工单生成推送

## LLM驱动模式
本主智能体采用全LLM驱动模式：
- **LLM决策**: 任务解析、子智能体选择、参数配置、结果分析
- **脚本执行**: 具体的调度协调、数据传递操作

## 动态编排策略
根据任务类型智能选择子智能体组合：
- **违规检测任务**: 全部4个子智能体
- **分析查询任务**: 数据感知 + 异常检测
- **历史回溯任务**: 数据感知 + 规则推理
- **预警响应任务**: 仅预警执行智能体
```

- [ ] **Step 2: 更新AGENTS.md**

在workspace/AGENTS.md中添加新的子智能体调度规则：

```markdown
## 子智能体调度规则

### 任务类型与智能体映射

#### 违规检测任务 (violation_detection)
需要全部4个子智能体协同工作：
1. 多维数据感知智能体 → 获取标准化数据
2. 异常检测子智能体 → 识别异常特征
3. 规则推理子智能体 → 判定违规类型
4. 研判预警与处置执行智能体 → 生成预警和工单

执行模式: HYBRID（数据感知和异常检测可流水线并行）

#### 分析查询任务 (analysis_query)
需要2个子智能体：
1. 多维数据感知智能体 → 获取标准化数据
2. 异常检测子智能体 → 识别异常特征

执行模式: SEQUENTIAL

#### 历史回溯任务 (historical_review)
需要2个子智能体：
1. 多维数据感知智能体 → 获取历史数据
2. 规则推理子智能体 → 结合历史案例判定

执行模式: SEQUENTIAL

#### 预警响应任务 (alert_response)
仅需1个子智能体：
1. 研判预警与处置执行智能体 → 处理工单推送

执行模式: SEQUENTIAL
```

- [ ] **Step 3: 更新MEMORY.md**

添加新的架构记忆：

```markdown
## 新架构记忆（2026-05-29更新）

### 子智能体架构
系统采用1主4子架构：
- 主智能体：废水监测主智能体
- 子智能体1：多维数据感知智能体（multi-dimensional-data-perception-agent）
- 子智能体2：异常检测子智能体（anomaly-detection-agent）
- 子智能体3：规则推理子智能体（rule-reasoning-agent）
- 子智能体4：研判预警与处置执行智能体（disposition-execution-agent）

### 数据类型
系统支持8类多维时序数据：
1. 水质数据：pH、COD、TN、TP、氨氮、悬浮物
2. 流量数据：进水流量、出水流量、排放量
3. 设备状态：进水泵、鼓风机、污泥泵状态
4. 工艺参数：溶解氧、污泥浓度、回流比
5. 维护记录：反冲洗、检修、停运计划
6. 生产记录：生产批次、产量变化
7. 污染源信息：名称、行政区划、联系人
8. 监测点信息：名称、编号、类型、级别

### 异常类型（数据层）
1. 平稳异常：恒定值检测
2. 突变异常：突变点检测
3. 趋势异常：趋势违背检测
4. 周期异常：FFT周期检测
5. 高频波动：高频噪声检测

### 违规类型（业务层）
1. 插瓶干扰：恒定值 + 工况正常
2. 人工拟合：过度平滑 + 分布异常
3. 稀释排放：多指标同步下降 + 去除率异常
4. 恶意逃避：数据缺失 + 非工作时间空白

### 预警分级
1. 一般（general）：异常置信度<0.6
2. 较重（moderate）：异常置信度0.6-0.8
3. 严重（serious）：异常置信度>0.8
```

- [ ] **Step 4: 提交**

```bash
git add workspace/IDENTITY.md workspace/AGENTS.md workspace/MEMORY.md
git commit -m "docs: update master agent identity for new architecture"
```

---

### Task 1.4: 集成动态编排器到执行控制

**Files:**
- Modify: `workspace/skills/orchestrator-core/scripts/execution_control.py`

- [ ] **Step 1: 编写集成测试**

```python
# tests/workspace/test_execution_control_integration.py
import pytest
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "workspace" / "skills" / "orchestrator-core" / "scripts"))

from execution_control import ExecutionControlModule
from dynamic_orchestrator import DynamicOrchestrator


def test_execution_control_with_dynamic_orchestrator():
    """测试执行控制模块集成动态编排器"""
    llm_client = None  # 使用本地模式测试
    
    execution_control = ExecutionControlModule(llm_client=llm_client)
    
    # 验证编排器已集成
    assert hasattr(execution_control, 'orchestrator')
    assert isinstance(execution_control.orchestrator, DynamicOrchestrator)


def test_violation_detection_workflow():
    """测试违规检测工作流"""
    execution_control = ExecutionControlModule(llm_client=None)
    
    task = {
        "task_type": "violation_detection",
        "task_id": "test-001",
        "data": {
            "influent": {"pH值": 7.5, "化学需氧量浓度（毫克/升）": 45},
            "effluent": {"pH值": 7.8, "化学需氧量浓度（毫克/升）": 50}
        }
    }
    
    # 创建执行计划
    plan = execution_control.orchestrator.create_execution_plan(task)
    
    # 验证计划
    assert plan.task_type == "violation_detection"
    assert len(plan.agents) == 4
    
    # 执行（本地模式，不实际调用子智能体）
    result = execution_control.execute_plan(plan, dry_run=True)
    
    assert result["status"] == "dry_run"
    assert result["agents_planned"] == 4
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/workspace/test_execution_control_integration.py -v
```

Expected: FAIL - 编排器未集成

- [ ] **Step 3: 修改execution_control.py集成编排器**

在`ExecutionControlModule`类的`__init__`方法中添加：

```python
from dynamic_orchestrator import DynamicOrchestrator

class ExecutionControlModule:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.orchestrator = DynamicOrchestrator()
        # ... 其他初始化代码保持不变
```

添加新方法：

```python
def execute_plan(self, plan, dry_run=False):
    """执行执行计划
    
    Args:
        plan: DynamicOrchestrator创建的执行计划
        dry_run: 是否仅模拟执行
        
    Returns:
        执行结果字典
    """
    if dry_run:
        return {
            "status": "dry_run",
            "agents_planned": len(plan.agents),
            "execution_mode": plan.execution_mode.value,
            "agents": [a.id for a in plan.agents]
        }
    
    results = {}
    for idx, agent_task in enumerate(plan.agents):
        agent_id = agent_task.id
        # 调用子智能体的逻辑
        result = self._execute_agent(agent_id, agent_task)
        results[agent_id] = result
        
        # 如果不是并行模式，传递结果给下一个智能体
        if plan.execution_mode != ExecutionMode.PARALLEL and idx < len(plan.agents) - 1:
            next_agent = plan.agents[idx + 1]
            next_agent.input_data.update(result)
    
    return {"status": "completed", "results": results}
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/workspace/test_execution_control_integration.py -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add workspace/skills/orchestrator-core/scripts/execution_control.py tests/workspace/test_execution_control_integration.py
git commit -m "feat: integrate dynamic orchestrator into execution control"
```

---

## 阶段2: 多维数据感知智能体重构

### Task 2.1: 创建智能体目录结构和身份文件

**Files:**
- Create: `subagents/multi-dimensional-data-perception-agent/IDENTITY.md`
- Create: `subagents/multi-dimensional-data-perception-agent/AGENTS.md`
- Create: `subagents/multi-dimensional-data-perception-agent/SOUL.md`
- Create: `subagents/multi-dimensional-data-perception-agent/MEMORY.md`
- Create: `subagents/multi-dimensional-data-perception-agent/TOOLS.md`
- Create: `subagents/multi-dimensional-data-perception-agent/USER.md`

- [ ] **Step 1: 创建IDENTITY.md**

```markdown
---
name: multi-dimensional-data-perception-agent
description: 多维数据感知子智能体 - 负责多维时序数据的获取、分解、清洗、标准化
metadata:
  type: user
---

# 多维数据感知子智能体身份卡片

## 基本信息
- **Name**: 多维数据感知子智能体
- **Creature**: Multi-Dimensional Data Processor（多维数据处理器）
- **Vibe**: 严谨、可靠、多源整合
- **Emoji**: 📊

## 核心职责
1. 多维时序数据获取：支持8类数据源的统一接入
2. 数据分解与对齐：处理不同数据源的时间对齐问题
3. 数据清洗与质控：确保数据质量和完整性
4. 标准化归一化：输出统一格式的标准化数据

## 支持的数据类型
1. **水质数据** (water_quality): pH、COD、TN、TP、氨氮、悬浮物等
2. **流量数据** (flow): 进水流量、出水流量、排放量等
3. **设备状态** (equipment_status): 进水泵、鼓风机、污泥泵等设备运行状态
4. **工艺参数** (process_parameters): 溶解氧、污泥浓度、回流比等工艺参数
5. **维护记录** (maintenance_records): 反冲洗、检修、停运计划等维护信息
6. **生产记录** (production_records): 生产批次、产量变化等生产数据
7. **污染源信息** (source_info): 名称、行政区划、联系人等基础信息
8. **监测点信息** (monitoring_point_info): 名称、编号、类型、级别等监测点属性

## 我不负责的
- 特征分析：不做复杂特征工程
- 异常检测：不进行异常识别
- 违规判定：不做业务层面的违规判断

## LLM决策范围
- 数据源选择：CSV文件、API接口、数据库
- 时间对齐方式：根据数据特性选择对齐策略
- 数据质控阈值：动态设定质量标准
- 数据质量分析：生成质量报告

## 输出格式
标准化的多维时序数据结构，包含8类数据和元信息
```

- [ ] **Step 2: 创建AGENTS.md**

```markdown
---
name: multi-dimensional-data-perception-agent
description: 多维数据感知子智能体的任务指令和工作规范
metadata:
  type: user
---

# 多维数据感知子智能体任务指令

## 核心任务

### 任务1: 多源数据获取
接收来自主智能体的数据请求，从以下数据源获取数据：
- CSV文件：模拟的实时监测数据
- API接口：监管平台推送数据
- 数据库：历史数据查询

### 任务2: 多维数据分解
将接收到的复合数据按8类数据类型进行分解和分类。

### 任务3: 时序对齐
处理不同数据源的时间戳差异，实现：
- 进水与出水数据的2小时时滞对齐
- 多源数据的统一时间基准
- 缺失时间点的插值处理

### 任务4: 数据清洗质控
执行数据质量控制：
- 异常值识别与修正
- 缺失值补全
- 数据一致性校验

### 任务5: 标准化归一化
输出统一格式的标准化数据：
- 统一的字段命名
- 统一的单位体系
- 统一的时间格式

## 工作原则
1. 数据完整性优先：宁可报错也不返回不完整数据
2. 时间准确性：严格保证时间对齐的正确性
3. 可追溯性：记录数据处理的全过程
```

- [ ] **Step 3: 创建SOUL.md**

```markdown
---
name: multi-dimensional-data-perception-agent
description: 多维数据感知子智能体的个性和工作风格
metadata:
  type: user
---

# 多维数据感知子智能体的灵魂

## 工作哲学
- **严谨**: 数据处理容不得半点马虎
- **可靠**: 稳定输出高质量数据
- **多源整合**: 善于处理来自不同源的数据

## 个性特征
我是一个一丝不苟的数据处理专家。我讨厌缺失值、异常值和格式不一致的数据。我的目标是确保下游智能体收到的每一批数据都是干净、完整、标准化的。

## 工作风格
- 主动发现问题：不等下游反馈，主动检测数据质量问题
- 透明处理：清晰记录数据处理的每一个步骤
- 持续学习：根据反馈不断优化数据处理策略
```

- [ ] **Step 4: 创建MEMORY.md**

```markdown
---
name: multi-dimensional-data-perception-agent
description: 多维数据感知子智能体的专业长期记忆
metadata:
  type: user
---

# 多维数据感知子智能体的长期记忆

## 系统架构知识
- 本系统采用6层专利架构
- 我是第5层（子智能体层）的一员
- 我的工作为后续的异常检测和规则推理提供数据基础

## 数据处理知识
### 时间滞后规则
- 进水处理到出水排放有2小时水力停留时间
- 数据对齐时需要考虑这个时滞

### 数据质量标准
- 完整性：数据缺失率<5%
- 准确性：异常值比例<1%
- 一致性：进出水数据逻辑一致性
- 时效性：数据延迟<5分钟

### 历史案例
- 案例1: 2024-05-15发现进水数据缺失率高达30%，经排查是传感器故障
- 案例2: 2024-05-20发现时间戳不匹配问题，修复后数据质量提升
```

- [ ] **Step 5: 创建TOOLS.md和USER.md**

```markdown
# TOOLS.md
## 环境特定信息
- 数据文件路径: /home/NYJ2025/Ecological_env/data/
- 水力停留时间: 2小时
- 数据采样间隔: 5分钟

# USER.md
## 用户信息
- Name: 环境监管人员
- Timezone: Asia/Shanghai
- Notes: 关注实时数据完整性和准确性
```

- [ ] **Step 6: 提交**

```bash
git add subagents/multi-dimensional-data-perception-agent/
git commit -m "feat: add multi-dimensional data perception agent identity files"
```

---

### Task 2.2: 实现数据获取脚本

**Files:**
- Create: `subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/__init__.py`
- Create: `subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/data_acquisition.py`
- Create: `subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/__init__.py`

- [ ] **Step 1: 编写测试**

```python
# tests/subagents/test_data_acquisition.py
import pytest
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "subagents" / "multi-dimensional-data-perception-agent" / "skills" / "data-perception-core" / "scripts"))

from data_acquisition import DataAcquisitionModule


def test_acquire_from_csv():
    """测试从CSV文件获取数据"""
    module = DataAcquisitionModule()
    
    result = module.acquire_from_csv(
        influent_path="data/pollution_water_in.csv",
        effluent_path="data/pollution_water_out.csv"
    )
    
    assert "influent" in result
    assert "effluent" in result
    assert len(result["influent"]) > 0


def test_acquire_multi_dimensional():
    """测试获取多维数据"""
    module = DataAcquisitionModule()
    
    result = module.acquire_multi_dimensional({
        "water_quality": {"path": "data/pollution_water_in.csv"},
        "flow": {"path": "data/flow_data.csv"}
    })
    
    assert "water_quality" in result
    assert "flow" in result
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_data_acquisition.py -v
```

Expected: FAIL - Module not found

- [ ] **Step 3: 实现data_acquisition.py**

```python
# subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/data_acquisition.py
"""
数据获取模块 - 支持多源数据获取
"""
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class DataAcquisitionModule:
    """数据获取模块"""
    
    def __init__(self):
        self.supported_sources = ["csv", "api", "database"]
        self.data_cache = {}
    
    def acquire_from_csv(
        self, 
        influent_path: str, 
        effluent_path: str,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """从CSV文件获取进出水数据
        
        Args:
            influent_path: 进水数据文件路径
            effluent_path: 出水数据文件路径
            limit: 限制读取行数
            
        Returns:
            包含influent和effluent数据的字典
        """
        result = {"influent": None, "effluent": None}
        
        # 读取进水数据
        influent_file = Path(influent_path)
        if influent_file.exists():
            df = pd.read_csv(influent_file, nrows=limit)
            result["influent"] = df.to_dict('records')
            result["influent_count"] = len(df)
        else:
            result["influent_error"] = f"File not found: {influent_path}"
        
        # 读取出水数据
        effluent_file = Path(effluent_path)
        if effluent_file.exists():
            df = pd.read_csv(effluent_file, nrows=limit)
            result["effluent"] = df.to_dict('records')
            result["effluent_count"] = len(df)
        else:
            result["effluent_error"] = f"File not found: {effluent_path}"
        
        result["acquisition_time"] = datetime.now().isoformat()
        result["source_type"] = "csv"
        
        return result
    
    def acquire_multi_dimensional(
        self, 
        data_configs: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """获取多维数据
        
        Args:
            data_configs: 数据类型配置字典
                {
                    "water_quality": {"path": "...", "type": "csv"},
                    "flow": {"path": "...", "type": "csv"},
                    ...
                }
            
        Returns:
            多维数据字典
        """
        result = {}
        
        for data_type, config in data_configs.items():
            source_type = config.get("type", "csv")
            path = config.get("path")
            
            if source_type == "csv" and path:
                file_path = Path(path)
                if file_path.exists():
                    df = pd.read_csv(file_path)
                    result[data_type] = {
                        "data": df.to_dict('records'),
                        "count": len(df),
                        "columns": list(df.columns)
                    }
                else:
                    result[data_type] = {
                        "error": f"File not found: {path}"
                    }
        
        result["acquisition_time"] = datetime.now().isoformat()
        return result
    
    def acquire_equipment_status(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """获取设备状态数据"""
        # 模拟实现，实际应从API或数据库获取
        return {
            "equipment": [
                {"name": "进水泵1号", "status": "running", "timestamp": datetime.now().isoformat()},
                {"name": "鼓风机1号", "status": "running", "timestamp": datetime.now().isoformat()},
                {"name": "污泥泵1号", "status": "standby", "timestamp": datetime.now().isoformat()}
            ]
        }
    
    def acquire_process_parameters(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """获取工艺参数数据"""
        return {
            "process": [
                {"parameter": "溶解氧", "value": 2.5, "unit": "mg/L"},
                {"parameter": "污泥浓度", "value": 3500, "unit": "mg/L"},
                {"parameter": "回流比", "value": 0.5, "unit": "ratio"}
            ]
        }
```

- [ ] **Step 4: 创建__init__.py文件**

```python
# subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/__init__.py
"""多维数据感知核心技能包"""
```

```python
# subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/__init__.py
"""多维数据感知脚本模块"""
from .data_acquisition import DataAcquisitionModule

__all__ = ['DataAcquisitionModule']
```

- [ ] **Step 5: 运行测试验证通过**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_data_acquisition.py -v
```

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add subagents/multi-dimensional-data-perception-agent/skills/ tests/subagents/test_data_acquisition.py
git commit -m "feat: implement data acquisition module"
```

---

### Task 2.3: 实现数据分解和时序对齐脚本

**Files:**
- Create: `subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/data_decomposition.py`
- Create: `subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/time_alignment.py`

- [ ] **Step 1: 编写测试**

```python
# tests/subagents/test_data_decomposition.py
import pytest
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "subagents" / "multi-dimensional-data-perception-agent" / "skills" / "data-perception-core" / "scripts"))

from data_decomposition import DataDecompositionModule
from time_alignment import TimeAlignmentModule


def test_data_decomposition():
    """测试数据分解"""
    module = DataDecompositionModule()
    
    input_data = {
        "influent": [
            {"监测时间": "2024-01-01 00:00", "pH值": 7.5, "化学需氧量浓度（毫克/升）": 45}
        ],
        "effluent": [
            {"监测时间": "2024-01-01 02:00", "pH值": 7.8, "化学需氧量浓度（毫克/升）": 50}
        ]
    }
    
    result = module.decompose_multi_dimensional(input_data)
    
    assert "water_quality" in result
    assert "influent" in result["water_quality"]
    assert "effluent" in result["water_quality"]


def test_time_alignment():
    """测试时序对齐"""
    module = TimeAlignmentModule()
    
    influent = [{"监测时间": "2024-01-01 00:00", "pH值": 7.5}]
    effluent = [{"监测时间": "2024-01-01 02:00", "pH值": 7.8}]
    
    result = module.align_with_lag(
        influent=influent,
        effluent=effluent,
        lag_hours=2
    )
    
    assert "aligned" in result
    assert result["alignment_method"] == "time_lag"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_data_decomposition.py -v
```

Expected: FAIL - Modules not found

- [ ] **Step 3: 实现data_decomposition.py**

```python
# subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/data_decomposition.py
"""
数据分解模块 - 将复合数据按类型分解
"""
from typing import Dict, Any, List


class DataDecompositionModule:
    """数据分解模块"""
    
    def __init__(self):
        self.data_type_mapping = {
            "pH": "water_quality",
            "pH值": "water_quality",
            "化学需氧量": "water_quality",
            "化学需氧量浓度（毫克/升）": "water_quality",
            "总氮": "water_quality",
            "总氮浓度（毫克/升）": "water_quality",
            "氨氮": "water_quality",
            "氨氮浓度（毫克/升）": "water_quality",
            "总磷": "water_quality",
            "总磷浓度（毫克/升）": "water_quality",
            "悬浮物": "water_quality",
            "悬浮物浓度（毫克/升）": "water_quality",
            "流量": "flow",
            "流量（升/秒）": "flow",
            "排放量": "flow",
            "排放量（吨）": "flow"
        }
    
    def decompose_multi_dimensional(
        self, 
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分解多维数据
        
        Args:
            input_data: 原始数据，包含influent和effluent
            
        Returns:
            按8类数据类型分解的数据
        """
        result = {
            "water_quality": {"influent": [], "effluent": []},
            "flow": {"influent": [], "effluent": []},
            "equipment_status": [],
            "process_parameters": [],
            "maintenance_records": [],
            "production_records": [],
            "source_info": {},
            "monitoring_point_info": {}
        }
        
        # 分解进水数据
        if "influent" in input_data:
            for record in input_data["influent"]:
                self._classify_record(record, result, "influent")
        
        # 分解出水数据
        if "effluent" in input_data:
            for record in input_data["effluent"]:
                self._classify_record(record, result, "effluent")
        
        return result
    
    def _classify_record(
        self, 
        record: Dict[str, Any], 
        result: Dict[str, Any],
        source_type: str
    ):
        """将记录分类到对应的数据类型"""
        water_quality_data = {}
        flow_data = {}
        
        for key, value in record.items():
            data_type = self.data_type_mapping.get(key)
            
            if data_type == "water_quality":
                water_quality_data[key] = value
            elif data_type == "flow":
                flow_data[key] = value
        
        # 添加时间戳
        timestamp = record.get("监测时间", "")
        if water_quality_data:
            water_quality_data["监测时间"] = timestamp
            result["water_quality"][source_type].append(water_quality_data)
        
        if flow_data:
            flow_data["监测时间"] = timestamp
            result["flow"][source_type].append(flow_data)
```

- [ ] **Step 4: 实现time_alignment.py**

```python
# subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/time_alignment.py
"""
时序对齐模块 - 处理不同数据源的时间对齐
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
import pandas as pd


class TimeAlignmentModule:
    """时序对齐模块"""
    
    def __init__(self, default_lag_hours: int = 2):
        self.default_lag_hours = default_lag_hours
        self.lag_records = int(default_lag_hours * 60 / 5)  # 5分钟间隔
    
    def align_with_lag(
        self,
        influent: List[Dict[str, Any]],
        effluent: List[Dict[str, Any]],
        lag_hours: int = None
    ) -> Dict[str, Any]:
        """使用时间滞后对齐进出水数据
        
        Args:
            influent: 进水数据列表
            effluent: 出水数据列表
            lag_hours: 滞后小时数，默认使用default_lag_hours
            
        Returns:
            对齐后的数据
        """
        if lag_hours is None:
            lag_hours = self.default_lag_hours
        
        # 转换为DataFrame便于处理
        inf_df = pd.DataFrame(influent)
        eff_df = pd.DataFrame(effluent)
        
        if "监测时间" not in inf_df.columns or "监测时间" not in eff_df.columns:
            return {
                "status": "error",
                "message": "Missing timestamp column"
            }
        
        # 转换时间戳
        inf_df["监测时间"] = pd.to_datetime(in_df["监测时间"])
        eff_df["监测时间"] = pd.to_datetime(eff_df["监测时间"])
        
        # 对齐：进水时间t对应出水时间t+lag_hours
        aligned_pairs = []
        for idx, inf_row in inf_df.iterrows():
            inf_time = inf_row["监测时间"]
            target_time = inf_time + timedelta(hours=lag_hours)
            
            # 查找匹配的出水记录
            matching_eff = eff_df[
                (eff_df["监测时间"] - target_time).abs() < timedelta(minutes=5)
            ]
            
            if not matching_eff.empty:
                eff_row = matching_eff.iloc[0]
                aligned_pairs.append({
                    "influent_time": inf_time.strftime("%Y-%m-%d %H:%M"),
                    "effluent_time": eff_row["监测时间"].strftime("%Y-%m-%d %H:%M"),
                    "influent": inf_row.to_dict(),
                    "effluent": eff_row.to_dict()
                })
        
        return {
            "status": "success",
            "alignment_method": "time_lag",
            "lag_hours": lag_hours,
            "aligned_pairs": aligned_pairs,
            "alignment_count": len(aligned_pairs)
        }
```

- [ ] **Step 5: 更新__init__.py**

```python
# subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/__init__.py
"""多维数据感知脚本模块"""
from .data_acquisition import DataAcquisitionModule
from .data_decomposition import DataDecompositionModule
from .time_alignment import TimeAlignmentModule

__all__ = ['DataAcquisitionModule', 'DataDecompositionModule', 'TimeAlignmentModule']
```

- [ ] **Step 6: 运行测试验证通过**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_data_decomposition.py -v
```

Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/ tests/subagents/test_data_decomposition.py
git commit -m "feat: implement data decomposition and time alignment modules"
```

---

### Task 2.4: 实现数据清洗和标准化脚本

**Files:**
- Create: `subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/data_cleaning.py`
- Create: `subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/standardization.py`

- [ ] **Step 1: 编写测试**

```python
# tests/subagents/test_data_cleaning.py
import pytest
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "subagents" / "multi-dimensional-data-perception-agent" / "skills" / "data-perception-core" / "scripts"))

from data_cleaning import DataCleaningModule
from standardization import StandardizationModule


def test_data_cleaning():
    """测试数据清洗"""
    module = DataCleaningModule()
    
    dirty_data = [
        {"pH值": 7.5, "化学需氧量浓度（毫克/升）": None},  # 缺失值
        {"pH值": 15.0, "化学需氧量浓度（毫克/升）": 45},  # pH异常
        {"pH值": 7.2, "化学需氧量浓度（毫克/升）": -10}  # 负值异常
    ]
    
    result = module.clean_water_quality_data(dirty_data)
    
    assert "cleaned_data" in result
    assert "quality_report" in result
    assert result["quality_report"]["completeness"] < 1.0


def test_standardization():
    """测试标准化"""
    module = StandardizationModule()
    
    input_data = {
        "influent": [
            {"pH值": 7.5, "COD": 45}  # 旧字段名
        ],
        "effluent": [
            {"pH值": 7.8, "COD": 50}
        ]
    }
    
    result = module.standardize_water_quality(input_data)
    
    assert "water_quality" in result
    assert result["water_quality"]["influent"][0]["pH"] == 7.5
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_data_cleaning.py -v
```

Expected: FAIL - Modules not found

- [ ] **Step 3: 实现data_cleaning.py**

```python
# subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/data_cleaning.py
"""
数据清洗模块 - 数据质量控制
"""
from typing import Dict, Any, List
import numpy as np


class DataCleaningModule:
    """数据清洗模块"""
    
    def __init__(self):
        # 定义各指标的合理范围
        self.valid_ranges = {
            "pH值": (0, 14),
            "pH": (0, 14),
            "化学需氧量浓度（毫克/升）": (0, 1000),
            "COD": (0, 1000),
            "总氮浓度（毫克/升）": (0, 100),
            "TN": (0, 100),
            "氨氮浓度（毫克/升）": (0, 50),
            "NH3_N": (0, 50),
            "总磷浓度（毫克/升）": (0, 20),
            "TP": (0, 20),
            "悬浮物浓度（毫克/升）": (0, 500),
            "SS": (0, 500)
        }
    
    def clean_water_quality_data(
        self, 
        data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """清洗水质数据
        
        Args:
            data: 原始数据列表
            
        Returns:
            清洗后的数据和质控报告
        """
        cleaned_data = []
        missing_count = 0
        anomaly_count = 0
        
        for record in data:
            cleaned_record = {}
            record_has_anomaly = False
            
            for key, value in record.items():
                # 检查缺失值
                if value is None or value == "" or value == "/":
                    missing_count += 1
                    cleaned_record[key] = None
                    continue
                
                # 检查异常值
                if key in self.valid_ranges:
                    min_val, max_val = self.valid_ranges[key]
                    try:
                        num_value = float(value)
                        if num_value < min_val or num_value > max_val:
                            anomaly_count += 1
                            record_has_anomaly = True
                            # 将异常值标记为None
                            cleaned_record[key] = None
                        else:
                            cleaned_record[key] = num_value
                    except (ValueError, TypeError):
                        anomaly_count += 1
                        cleaned_record[key] = None
                else:
                    cleaned_record[key] = value
            
            if not record_has_anomaly:
                cleaned_data.append(cleaned_record)
        
        # 计算质量指标
        total_values = len(data) * len(self.valid_ranges)
        completeness = 1 - (missing_count / total_values) if total_values > 0 else 0
        
        quality_report = {
            "completeness": round(completeness, 3),
            "anomaly_rate": round(anomaly_count / total_values, 3) if total_values > 0 else 0,
            "missing_count": missing_count,
            "anomaly_count": anomaly_count,
            "cleaned_count": len(cleaned_data)
        }
        
        return {
            "cleaned_data": cleaned_data,
            "quality_report": quality_report
        }
```

- [ ] **Step 4: 实现standardization.py**

```python
# subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/standardization.py
"""
标准化模块 - 数据格式统一
"""
from typing import Dict, Any, List


class StandardizationModule:
    """标准化模块"""
    
    def __init__(self):
        # 字段名映射表
        self.field_mapping = {
            "pH值": "pH",
            "化学需氧量浓度（毫克/升）": "COD",
            "总氮浓度（毫克/升）": "TN",
            "氨氮浓度（毫克/升）": "NH3_N",
            "总磷浓度（毫克/升）": "TP",
            "悬浮物浓度（毫克/升）": "SS",
            "流量（升/秒）": "flow_rate",
            "排放量（吨）": "discharge_volume"
        }
    
    def standardize_water_quality(
        self, 
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """标准化水质数据格式
        
        Args:
            input_data: 包含influent和effluent的输入数据
            
        Returns:
            标准化后的数据
        """
        result = {
            "water_quality": {
                "influent": [],
                "effluent": []
            }
        }
        
        # 标准化进水数据
        if "influent" in input_data:
            for record in input_data["influent"]:
                standardized = self._standardize_record(record)
                result["water_quality"]["influent"].append(standardized)
        
        # 标准化出水数据
        if "effluent" in input_data:
            for record in input_data["effluent"]:
                standardized = self._standardize_record(record)
                result["water_quality"]["effluent"].append(standardized)
        
        return result
    
    def _standardize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """标准化单条记录"""
        standardized = {}
        
        for key, value in record.items():
            # 应用字段映射
            new_key = self.field_mapping.get(key, key)
            standardized[new_key] = value
        
        return standardized
```

- [ ] **Step 5: 更新__init__.py**

```python
# subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/__init__.py
"""多维数据感知脚本模块"""
from .data_acquisition import DataAcquisitionModule
from .data_decomposition import DataDecompositionModule
from .time_alignment import TimeAlignmentModule
from .data_cleaning import DataCleaningModule
from .standardization import StandardizationModule

__all__ = [
    'DataAcquisitionModule', 
    'DataDecompositionModule', 
    'TimeAlignmentModule',
    'DataCleaningModule',
    'StandardizationModule'
]
```

- [ ] **Step 6: 运行测试验证通过**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_data_cleaning.py -v
```

Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/ tests/subagents/test_data_cleaning.py
git commit -m "feat: implement data cleaning and standardization modules"
```

---

### Task 2.5: 创建SKILL.md并完成智能体配置

**Files:**
- Create: `subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/SKILL.md`

- [ ] **Step 1: 创建SKILL.md**

```markdown
# 多维数据感知核心技能包

## 技能描述
本技能包提供多维时序数据的获取、分解、对齐、清洗和标准化能力，为下游智能体提供高质量、标准化的数据基础。

## 核心脚本

### 1. data_acquisition.py (DataAcquisitionModule)
**功能**: 多源数据获取
- acquire_from_csv(): 从CSV文件获取进出水数据
- acquire_multi_dimensional(): 获取多维数据
- acquire_equipment_status(): 获取设备状态
- acquire_process_parameters(): 获取工艺参数

### 2. data_decomposition.py (DataDecompositionModule)
**功能**: 数据类型分解
- decompose_multi_dimensional(): 将复合数据按8类数据类型分解

### 3. time_alignment.py (TimeAlignmentModule)
**功能**: 时序对齐
- align_with_lag(): 使用时间滞后对齐进出水数据

### 4. data_cleaning.py (DataCleaningModule)
**功能**: 数据质量控制
- clean_water_quality_data(): 清洗水质数据，检测缺失值和异常值

### 5. standardization.py (StandardizationModule)
**功能**: 数据格式统一
- standardize_water_quality(): 标准化水质数据格式

## LLM决策点
1. 数据源选择: 根据任务需求选择CSV/API/数据库
2. 对齐策略: 根据数据特性选择时间对齐方式
3. 质控阈值: 动态设定数据质量标准

## 输出格式
标准化的8类多维时序数据结构
```

- [ ] **Step 2: 提交**

```bash
git add subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/SKILL.md
git commit -m "docs: add skill description for data perception core"
```

---

## 阶段3: 规则推理智能体重构

### Task 3.1: 创建规则配置文件

**Files:**
- Create: `shared/configs/rule_config.yaml`

- [ ] **Step 1: 创建规则配置文件**

```yaml
# 规则推理子智能体规则配置
# 定义违规判定规则和推理逻辑

rules:
  # 插瓶干扰规则
  bottle_interference:
    id: bottle_interference
    name: 插瓶干扰
    suspicion_level: high
    conditions:
      - type: anomaly_match
        anomaly_type: 平稳异常
        min_duration: 2h
        max_std_dev: 0.1
      - type: equipment_check
        equipment_status: running
        not_in_maintenance: true
    reasoning: "数据恒定但设备正常运行，疑似插瓶干扰"
    legal_reference: "HJ 915-2017 第X条"
    
  # 人工拟合规则
  artificial_fitting:
    id: artificial_fitting
    name: 人工拟合
    suspicion_level: high
    conditions:
      - type: anomaly_match
        anomaly_type: 平稳异常
        max_r_squared: 0.99
        min_variance_ratio: 0.1
    reasoning: "数据过度平滑，分布异常，疑似人工拟合"
    legal_reference: "HJ 915-2017 第X条"
    
  # 稀释排放规则
  dilution_discharge:
    id: dilution_discharge
    name: 稀释排放
    suspicion_level: serious
    conditions:
      - type: multi_indicator_sync
        indicators: ["COD", "TN", "TP", "NH3_N"]
        min_sync_drop_ratio: 0.5
      - type: removal_rate_check
        min_removal_rate: 0.95
        max_removal_rate: 1.0
      - type: flow_check
        flow_increase_threshold: 1.5
    reasoning: "多指标同步下降且去除率异常，疑似稀释排放"
    legal_reference: "水污染防治法 第XX条"
    
  # 恶意逃避规则
  malicious_evasion:
    id: malicious_evasion
    name: 恶意逃避
    suspicion_level: serious
    conditions:
      - type: data_missing_rate
        min_missing_rate: 0.2
      - type: off_hours_check
        off_hours_only: true
        hours: [22, 23, 0, 1, 2, 3, 4, 5, 6]
    reasoning: "工作时间外数据缺失，疑似恶意逃避"
    legal_reference: "HJ 915-2017 第X条"

# 误报过滤规则
false_positive_filters:
  # 设备停运过滤
  equipment_shutdown:
    id: equipment_shutdown
    filter_reason: "设备依法停运检修"
    conditions:
      - type: equipment_status
        status: shutdown
      - type: maintenance_record
        has_record: true
    
  # 反冲洗过滤
  backwash_filter:
    id: backwash_filter
    filter_reason: "反冲洗期间正常数据波动"
    conditions:
      - type: process_check
        process_stage: backwash
      - type: time_check
        max_duration: 1h

# 优先级配置
priority:
  - malicious_evasion
  - dilution_discharge
  - bottle_interference
  - artificial_fitting
```

- [ ] **Step 2: 验证YAML语法**

```bash
python -c "import yaml; yaml.safe_load(open('shared/configs/rule_config.yaml'))"
echo "YAML syntax valid"
```

Expected: "YAML syntax valid"

- [ ] **Step 3: 提交**

```bash
git add shared/configs/rule_config.yaml
git commit -m "feat: add rule configuration for violation detection"
```

---

### Task 3.2: 实现违规判定器

**Files:**
- Create: `subagents/rule-reasoning-agent/skills/rule-reasoning-core/scripts/violation_detector.py`

- [ ] **Step 1: 编写测试**

```python
# tests/subagents/test_violation_detector.py
import pytest
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "subagents" / "rule-reasoning-agent" / "skills" / "rule-reasoning-core" / "scripts"))

from violation_detector import ViolationDetector


def test_detect_bottle_interference():
    """测试插瓶干扰检测"""
    detector = ViolationDetector(rule_config_path="shared/configs/rule_config.yaml")
    
    anomaly_data = {
        "type": "平稳异常",
        "indicator": "COD",
        "duration": "2h",
        "std_dev": 0.05
    }
    
    context = {
        "equipment_status": "running",
        "in_maintenance": False
    }
    
    result = detector.detect_violation(anomaly_data, context)
    
    assert result["violation_type"] == "插瓶干扰"
    assert result["suspicion_level"] == "high"


def test_filter_false_positive():
    """测试误报过滤"""
    detector = ViolationDetector(rule_config_path="shared/configs/rule_config.yaml")
    
    anomaly_data = {
        "type": "突变异常",
        "indicator": "COD"
    }
    
    context = {
        "equipment_status": "shutdown",
        "maintenance_record": True
    }
    
    result = detector.detect_violation(anomaly_data, context)
    
    assert result.get("filtered") == True
    assert result.get("filter_reason") == "设备依法停运检修"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_violation_detector.py -v
```

Expected: FAIL - Module not found

- [ ] **Step 3: 实现violation_detector.py**

```python
# subagents/rule-reasoning-agent/skills/rule-reasoning-core/scripts/violation_detector.py
"""
违规判定器 - 基于规则和异常特征判定违规类型
"""
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional


class ViolationDetector:
    """违规判定器"""
    
    def __init__(self, rule_config_path: str = "shared/configs/rule_config.yaml"):
        """初始化违规判定器
        
        Args:
            rule_config_path: 规则配置文件路径
        """
        self.rule_config_path = Path(rule_config_path)
        self.rules = self._load_rules()
        self.false_positive_filters = self._load_false_positive_filters()
    
    def _load_rules(self) -> Dict[str, Any]:
        """加载违规判定规则"""
        config_path = self.rule_config_path
        if not config_path.exists():
            project_root = Path(__file__).parent.parent.parent.parent.parent.parent
            config_path = project_root / "shared" / "configs" / "rule_config.yaml"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        return config.get('rules', {})
    
    def _load_false_positive_filters(self) -> Dict[str, Any]:
        """加载误报过滤规则"""
        config_path = self.rule_config_path
        if not config_path.exists():
            project_root = Path(__file__).parent.parent.parent.parent.parent.parent
            config_path = project_root / "shared" / "configs" / "rule_config.yaml"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        return config.get('false_positive_filters', {})
    
    def detect_violation(
        self, 
        anomaly_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """检测违规
        
        Args:
            anomaly_data: 异常检测子智能体输出的异常特征
            context: 上下文信息（工况、设备状态等）
            
        Returns:
            违规判定结果
        """
        # 先检查是否为误报
        filtered_result = self._check_false_positive(anomaly_data, context)
        if filtered_result:
            return {
                "filtered": True,
                "filter_reason": filtered_result.get("filter_reason"),
                "verification": filtered_result.get("verification", "")
            }
        
        # 逐一匹配违规规则
        for rule_id, rule in self.rules.items():
            if self._match_rule(anomaly_data, context, rule):
                return {
                    "violation_type": rule.get("name"),
                    "suspicion_level": rule.get("suspicion_level"),
                    "confidence": self._calculate_confidence(anomaly_data, rule),
                    "reasoning": {
                        "anomaly_type": anomaly_data.get("type"),
                        "matched_rules": self._get_matched_conditions(rule),
                        "process_check": self._get_process_check(context),
                        "conclusion": rule.get("reasoning")
                    },
                    "legal_reference": rule.get("legal_reference", "")
                }
        
        # 未匹配到任何违规规则
        return {
            "violation_type": None,
            "confidence": 0.0,
            "reasoning": "异常特征未匹配任何违规规则"
        }
    
    def _check_false_positive(
        self, 
        anomaly_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """检查是否为误报"""
        for filter_id, filter_rule in self.false_positive_filters.items():
            if self._match_rule(anomaly_data, context, filter_rule):
                return filter_rule
        return None
    
    def _match_rule(
        self, 
        anomaly_data: Dict[str, Any],
        context: Dict[str, Any],
        rule: Dict[str, Any]
    ) -> bool:
        """匹配规则"""
        conditions = rule.get("conditions", [])
        
        for condition in conditions:
            if not self._match_condition(anomaly_data, context, condition):
                return False
        
        return True
    
    def _match_condition(
        self, 
        anomaly_data: Dict[str, Any],
        context: Dict[str, Any],
        condition: Dict[str, Any]
    ) -> bool:
        """匹配单个条件"""
        condition_type = condition.get("type")
        
        if condition_type == "anomaly_match":
            return self._match_anomaly_condition(anomaly_data, condition)
        elif condition_type == "equipment_check":
            return self._match_equipment_condition(context, condition)
        elif condition_type == "equipment_status":
            return self._match_equipment_status(context, condition)
        # 其他条件类型...
        
        return True
    
    def _match_anomaly_condition(
        self, 
        anomaly_data: Dict[str, Any],
        condition: Dict[str, Any]
    ) -> bool:
        """匹配异常条件"""
        anomaly_type = condition.get("anomaly_type")
        if anomaly_data.get("type") != anomaly_type:
            return False
        
        # 检查持续时间
        min_duration = condition.get("min_duration")
        if min_duration and anomaly_data.get("duration"):
            duration_str = anomaly_data.get("duration", "")
            if duration_str.endswith("h"):
                duration_hours = int(duration_str[:-1])
                if duration_hours < int(min_duration[:-1]):
                    return False
        
        return True
    
    def _match_equipment_condition(
        self, 
        context: Dict[str, Any],
        condition: Dict[str, Any]
    ) -> bool:
        """匹配设备条件"""
        equipment_status = condition.get("equipment_status")
        if context.get("equipment_status") != equipment_status:
            return False
        
        not_in_maintenance = condition.get("not_in_maintenance", False)
        if not_in_maintenance and context.get("in_maintenance"):
            return False
        
        return True
    
    def _match_equipment_status(
        self, 
        context: Dict[str, Any],
        condition: Dict[str, Any]
    ) -> bool:
        """匹配设备状态"""
        status = condition.get("status")
        return context.get("equipment_status") == status
    
    def _calculate_confidence(
        self, 
        anomaly_data: Dict[str, Any],
        rule: Dict[str, Any]
    ) -> float:
        """计算违规置信度"""
        # 基础置信度
        base_confidence = 0.7
        
        # 根据异常类型调整
        anomaly_type = anomaly_data.get("type")
        if anomaly_type == "平稳异常":
            base_confidence += 0.15
        elif anomaly_type == "突变异常":
            base_confidence += 0.10
        
        # 根据持续时间调整
        duration = anomaly_data.get("duration", "")
        if duration.endswith("h"):
            hours = int(duration[:-1])
            if hours >= 4:
                base_confidence += 0.10
        
        return min(base_confidence, 1.0)
    
    def _get_matched_conditions(self, rule: Dict[str, Any]) -> List[str]:
        """获取匹配的条件描述"""
        conditions = rule.get("conditions", [])
        matched = []
        for cond in conditions:
            cond_type = cond.get("type")
            if cond_type == "anomaly_match":
                matched.append(f"异常类型匹配: {cond.get('anomaly_type')}")
            elif cond_type == "equipment_check":
                matched.append(f"设备状态: {cond.get('equipment_status')}")
        return matched
    
    def _get_process_check(self, context: Dict[str, Any]) -> str:
        """获取工艺检查描述"""
        if context.get("equipment_status") == "running":
            return "设备正常工作中"
        elif context.get("equipment_status") == "shutdown":
            return "设备已停运"
        return "设备状态未知"
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_violation_detector.py -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add subagents/rule-reasoning-agent/skills/rule-reasoning-core/scripts/violation_detector.py tests/subagents/test_violation_detector.py
git commit -m "feat: implement violation detector with rule engine"
```

---

## 阶段4: 研判预警与处置执行智能体(新增)

### Task 4.1: 创建智能体目录结构和身份文件

**Files:**
- Create: `subagents/disposition-execution-agent/IDENTITY.md`
- Create: `subagents/disposition-execution-agent/AGENTS.md`
- Create: `subagents/disposition-execution-agent/SOUL.md`
- Create: `subagents/disposition-execution-agent/MEMORY.md`
- Create: `subagents/disposition-execution-agent/TOOLS.md`
- Create: `subagents/disposition-execution-agent/USER.md`

- [ ] **Step 1: 创建IDENTITY.md**

```markdown
---
name: disposition-execution-agent
description: 研判预警与处置执行子智能体 - 负责融合共识、预警分级、工单生成推送
metadata:
  type: user
---

# 研判预警与处置执行子智能体身份卡片

## 基本信息
- **Name**: 研判预警与处置执行子智能体
- **Creature**: Action Executor（行动执行者）
- **Vibe**: 高效、规范、执行力强
- **Emoji**: 🚨

## 核心职责
1. 融合共识：综合异常检测（定量）与规则推理（定性）结论
2. 预警分级：按一般/较重/严重三级进行预警判定
3. 工单生成：生成包含数据溯源、核查要点、法规条款、历史参考的处置工单
4. 行动执行：通过标准API推送至监管平台，执行日志归档

## 预警分级标准
- **一般（general）**: 异常置信度<0.6，违规证据不足
- **较重（moderate）**: 异常置信度0.6-0.8，存在违规嫌疑
- **严重（serious）**: 异常置信度>0.8，违规证据确凿

## 工单内容
1. 数据溯源：异常时段监测数据、趋势图
2. 核查要点：现场检查位置、样品采集要点
3. 法规条款：违反的标准或法律条文
4. 历史参考：该企业的历史违规记录和处置建议

## LLM决策范围
- 融合策略：动态分配定量和定性结论的权重
- 分级判定：综合判断预警级别
- 工单内容：根据违规类型生成个性化工单
```

- [ ] **Step 2: 创建其他身份文件**

```markdown
# AGENTS.md
## 任务指令
1. 接收异常检测和规则推理的输出
2. 执行融合共识算法
3. 进行三级预警判定
4. 生成标准化处置工单
5. 执行推送和归档操作
```

```markdown
# SOUL.md
## 工作风格
- 高效执行：快速响应，及时推送
- 规范操作：遵循标准流程
- 闭环管理：确保每条预警都有处置结果
```

```markdown
# MEMORY.md
## 专业记忆
- 预警分级标准和阈值
- 历史工单模板
- 监管平台API接口规范
```

```markdown
# TOOLS.md
## 环境信息
- 监管平台API地址
- 飞书推送配置
- 工单归档路径
```

```markdown
# USER.md
## 用户信息
- 监管人员联系方式
- 预警推送偏好
```

- [ ] **Step 3: 提交**

```bash
git add subagents/disposition-execution-agent/
git commit -m "feat: add disposition execution agent identity files"
```

---

### Task 4.2: 实现预警分级器

**Files:**
- Create: `subagents/disposition-execution-agent/skills/disposition-execution-core/__init__.py`
- Create: `subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/alert_classifier.py`

- [ ] **Step 1: 编写测试**

```python
# tests/subagents/test_alert_classifier.py
import pytest
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "subagents" / "disposition-execution-agent" / "skills" / "disposition-execution-core" / "scripts"))

from alert_classifier import AlertClassifier


def test_classify_general_alert():
    """测试一般预警分级"""
    classifier = AlertClassifier()
    
    anomaly_result = {"confidence": 0.5}
    violation_result = {"violation_type": None}
    
    alert = classifier.classify_alert(anomaly_result, violation_result)
    
    assert alert["level"] == "general"
    assert alert["action"] == "monitor"


def test_classify_serious_alert():
    """测试严重预警分级"""
    classifier = AlertClassifier()
    
    anomaly_result = {"confidence": 0.95}
    violation_result = {
        "violation_type": "稀释排放",
        "suspicion_level": "serious"
    }
    
    alert = classifier.classify_alert(anomaly_result, violation_result)
    
    assert alert["level"] == "serious"
    assert alert["action"] == "immediate_investigation"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_alert_classifier.py -v
```

Expected: FAIL - Module not found

- [ ] **Step 3: 实现alert_classifier.py**

```python
# subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/alert_classifier.py
"""
预警分级器 - 三级预警判定
"""
from typing import Dict, Any, List
from enum import Enum


class AlertLevel(Enum):
    """预警级别"""
    GENERAL = "general"
    MODERATE = "moderate"
    SERIOUS = "serious"


class ActionRequired(Enum):
    """所需行动"""
    MONITOR = "monitor"  # 持续监控
    INVESTIGATE = "investigate"  # 现场核查
    IMMEDIATE_INVESTIGATION = "immediate_investigation"  # 立即调查


class AlertClassifier:
    """预警分级器"""
    
    def __init__(self):
        # 预警阈值配置
        self.thresholds = {
            "general_max": 0.6,
            "moderate_max": 0.8
        }
    
    def classify_alert(
        self,
        anomaly_result: Dict[str, Any],
        violation_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """对异常和违规结果进行预警分级
        
        Args:
            anomaly_result: 异常检测子智能体输出
            violation_result: 规则推理子智能体输出
            
        Returns:
            预警分级结果
        """
        # 获取置信度
        anomaly_confidence = anomaly_result.get("confidence", 0.0)
        violation_confidence = violation_result.get("confidence", 0.0)
        
        # 融合置信度（违规判定权重更高）
        fused_confidence = (anomaly_confidence * 0.3 + violation_confidence * 0.7)
        
        # 判定预警级别
        if fused_confidence <= self.thresholds["general_max"]:
            alert_level = AlertLevel.GENERAL
            action = ActionRequired.MONITOR
        elif fused_confidence <= self.thresholds["moderate_max"]:
            alert_level = AlertLevel.MODERATE
            action = ActionRequired.INVESTIGATE
        else:
            alert_level = AlertLevel.SERIOUS
            action = ActionRequired.IMMEDIATE_INVESTIGATION
        
        # 获取违规类型
        violation_type = violation_result.get("violation_type", "未知")
        
        return {
            "level": alert_level.value,
            "fused_confidence": round(fused_confidence, 3),
            "action": action.value,
            "violation_type": violation_type,
            "anomaly_confidence": round(anomaly_confidence, 3),
            "violation_confidence": round(violation_confidence, 3),
            "reasoning": self._generate_reasoning(
                alert_level, violation_type, fused_confidence
            )
        }
    
    def _generate_reasoning(
        self,
        alert_level: AlertLevel,
        violation_type: str,
        confidence: float
    ) -> str:
        """生成预警判定说明"""
        level_desc = {
            AlertLevel.GENERAL: "一般",
            AlertLevel.MODERATE: "较重",
            AlertLevel.SERIOUS: "严重"
        }
        
        if alert_level == AlertLevel.GENERAL:
            return f"检测到异常特征，置信度{confidence:.1%}，未构成违规，建议持续监控"
        elif alert_level == AlertLevel.MODERATE:
            return f"疑似{violation_type}，置信度{confidence:.1%}，建议现场核查"
        else:
            return f"判定{violation_type}，置信度{confidence:.1%}，建议立即调查取证"
```

- [ ] **Step 4: 创建__init__.py**

```python
# subagents/disposition-execution-agent/skills/disposition-execution-core/__init__.py
"""研判预警与处置执行核心技能包"""
```

```python
# subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/__init__.py
"""研判预警与处置执行脚本模块"""
from .alert_classifier import AlertClassifier, AlertLevel, ActionRequired

__all__ = ['AlertClassifier', 'AlertLevel', 'ActionRequired']
```

- [ ] **Step 5: 运行测试验证通过**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_alert_classifier.py -v
```

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add subagents/disposition-execution-agent/skills/ tests/subagents/test_alert_classifier.py
git commit -m "feat: implement alert classifier with three-level grading"
```

---

### Task 4.3: 实现工单生成器

**Files:**
- Create: `subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/work_order_generator.py`

- [ ] **Step 1: 编写测试**

```python
# tests/subagents/test_work_order_generator.py
import pytest
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "subagents" / "disposition-execution-agent" / "skills" / "disposition-execution-core" / "scripts"))

from work_order_generator import WorkOrderGenerator


def test_generate_work_order():
    """测试工单生成"""
    generator = WorkOrderGenerator()
    
    alert_info = {
        "level": "serious",
        "violation_type": "稀释排放",
        "fused_confidence": 0.92
    }
    
    data_context = {
        "anomaly_time_range": ["2024-05-29 02:00", "2024-05-29 04:00"],
        "anomaly_indicators": ["COD", "TN", "TP"]
    }
    
    work_order = generator.generate_work_order(alert_info, data_context)
    
    assert "id" in work_order
    assert "data_traceback" in work_order
    assert "inspection_points" in work_order
    assert "legal_references" in work_order
    assert "recommended_actions" in work_order
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_work_order_generator.py -v
```

Expected: FAIL - Module not found

- [ ] **Step 3: 实现work_order_generator.py**

```python
# subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/work_order_generator.py
"""
处置工单生成器 - 生成包含溯源、核查、法规、历史的工单
"""
from typing import Dict, Any, List
from datetime import datetime
import uuid


class WorkOrderGenerator:
    """处置工单生成器"""
    
    def __init__(self):
        self.work_order_counter = 0
    
    def generate_work_order(
        self,
        alert_info: Dict[str, Any],
        data_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成处置工单
        
        Args:
            alert_info: 预警信息（级别、类型、置信度等）
            data_context: 数据上下文（异常时间、指标等）
            
        Returns:
            处置工单字典
        """
        self.work_order_counter += 1
        work_order_id = f"WO-{datetime.now().strftime('%Y%m%d')}-{self.work_order_counter:03d}"
        
        return {
            "id": work_order_id,
            "alert_level": alert_info.get("level"),
            "violation_type": alert_info.get("violation_type"),
            "confidence": alert_info.get("fused_confidence"),
            "generated_at": datetime.now().isoformat(),
            "data_traceback": self._generate_data_traceback(data_context),
            "inspection_points": self._generate_inspection_points(alert_info, data_context),
            "legal_references": self._generate_legal_references(alert_info.get("violation_type")),
            "historical_context": self._generate_historical_context(data_context),
            "recommended_actions": self._generate_recommended_actions(alert_info)
        }
    
    def _generate_data_traceback(self, data_context: Dict[str, Any]) -> Dict[str, Any]:
        """生成数据溯源"""
        time_range = data_context.get("anomaly_time_range", [])
        indicators = data_context.get("anomaly_indicators", [])
        
        return {
            "time_range": {
                "start": time_range[0] if time_range else "",
                "end": time_range[1] if len(time_range) > 1 else ""
            },
            "affected_indicators": indicators,
            "data_source": "实时监测数据",
            "note": "完整数据已归档至数据库"
        }
    
    def _generate_inspection_points(
        self, 
        alert_info: Dict[str, Any],
        data_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成现场核查要点"""
        violation_type = alert_info.get("violation_type")
        
        points = [
            {
                "location": "废水排放口",
                "action": "采集出水样品",
                "priority": "high"
            },
            {
                "location": "在线监测设备",
                "action": "检查设备运行状态",
                "priority": "high"
            }
        ]
        
        # 根据违规类型添加特定核查点
        if violation_type == "稀释排放":
            points.append({
                "location": "进水口",
                "action": "检查是否有清水注入",
                "priority": "high"
            })
        elif violation_type == "插瓶干扰":
            points.append({
                "location": "采样管路",
                "action": "检查采样管是否异常",
                "priority": "high"
            })
        
        return points
    
    def _generate_legal_references(self, violation_type: str) -> List[str]:
        """生成法规条款引用"""
        references = []
        
        if violation_type == "稀释排放":
            references.append("《水污染防治法》第XX条：禁止稀释排放")
            references.append("HJ 915-2017 第X条：污染物排放标准")
        elif violation_type == "插瓶干扰":
            references.append("HJ 915-2017 第X条：监测设备运行要求")
        elif violation_type == "人工拟合":
            references.append("《环境监测数据弄虚作假行为判定及处理办法》第X条")
        
        return references
    
    def _generate_historical_context(self, data_context: Dict[str, Any]) -> Dict[str, Any]:
        """生成历史参考"""
        return {
            "enterprise_id": data_context.get("enterprise_id", ""),
            "recent_violations": [],  # 可从数据库查询
            "similar_cases": [],  # 可从案例库查询
            "note": "历史数据查询功能待实现"
        }
    
    def _generate_recommended_actions(self, alert_info: Dict[str, Any]) -> List[str]:
        """生成处置建议"""
        level = alert_info.get("level")
        actions = []
        
        if level == "general":
            actions = [
                "加强日常监控",
                "关注相关指标变化"
            ]
        elif level == "moderate":
            actions = [
                "立即组织现场核查",
                "采集水样进行实验室分析",
                "检查设备运行记录"
            ]
        elif level == "serious":
            actions = [
                "立即启动执法程序",
                "固定现场证据",
                "约谈企业负责人",
                "依法进行处罚"
            ]
        
        return actions
```

- [ ] **Step 4: 更新__init__.py**

```python
# subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/__init__.py
"""研判预警与处置执行脚本模块"""
from .alert_classifier import AlertClassifier, AlertLevel, ActionRequired
from .work_order_generator import WorkOrderGenerator

__all__ = ['AlertClassifier', 'AlertLevel', 'ActionRequired', 'WorkOrderGenerator']
```

- [ ] **Step 5: 运行测试验证通过**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/subagents/test_work_order_generator.py -v
```

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/ tests/subagents/test_work_order_generator.py
git commit -m "feat: implement work order generator"
```

---

### Task 4.4: 创建SKILL.md并完成智能体配置

**Files:**
- Create: `subagents/disposition-execution-agent/skills/disposition-execution-core/SKILL.md`

- [ ] **Step 1: 创建SKILL.md**

```markdown
# 研判预警与处置执行核心技能包

## 技能描述
本技能包提供融合共识、预警分级、工单生成和行动执行能力，完成从违规识别到处置执行的闭环。

## 核心脚本

### 1. alert_classifier.py (AlertClassifier)
**功能**: 三级预警分级
- classify_alert(): 对异常和违规结果进行预警分级
- 支持一般/较重/严重三级预警

### 2. work_order_generator.py (WorkOrderGenerator)
**功能**: 处置工单生成
- generate_work_order(): 生成标准化处置工单
- 工单包含：数据溯源、核查要点、法规条款、历史参考

### 3. action_executor.py (待实现)
**功能**: 行动执行
- execute_push(): 推送至监管平台
- execute_feishu(): 推送至飞书
- execute_archive(): 执行归档操作

### 4. consensus_engine.py (待实现)
**功能**: 融合共识算法
- fuse_results(): 融合异常检测和规则推理结果
- adapt_weights(): 动态调整权重

### 5. report_generator.py (待实现)
**功能**: 报告生成
- generate_alert_report(): 生成预警报告
- generate_summary_report(): 生成汇总报告

## LLM决策点
1. 融合策略: 根据场景动态调整定量定性权重
2. 分级判定: 综合判断预警级别
3. 工单内容: 根据违规类型生成个性化工单

## 输出格式
标准化预警信息和处置工单
```

- [ ] **Step 2: 提交**

```bash
git add subagents/disposition-execution-agent/skills/disposition-execution-core/SKILL.md
git commit -m "docs: add skill description for disposition execution core"
```

---

## 阶段5: 集成测试与验证

### Task 5.1: 创建端到端集成测试

**Files:**
- Create: `tests/integration/test_e2e_architecture.py`

- [ ] **Step 1: 编写集成测试**

```python
# tests/integration/test_e2e_architecture.py
"""
端到端架构集成测试
测试新架构的完整工作流
"""
import pytest
from pathlib import Path
import sys

# 添加各模块路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "workspace" / "skills" / "orchestrator-core" / "scripts"))
sys.path.insert(0, str(project_root / "subagents" / "multi-dimensional-data-perception-agent" / "skills" / "data-perception-core" / "scripts"))
sys.path.insert(0, str(project_root / "subagents" / "disposition-execution-agent" / "skills" / "disposition-execution-core" / "scripts"))

from dynamic_orchestrator import DynamicOrchestrator
from data_acquisition import DataAcquisitionModule
from alert_classifier import AlertClassifier
from work_order_generator import WorkOrderGenerator


def test_violation_detection_workflow():
    """测试违规检测完整工作流"""
    # 1. 初始化组件
    orchestrator = DynamicOrchestrator(
        registry_path="shared/configs/agent_registry.yaml"
    )
    
    # 2. 创建任务
    task = {
        "task_type": "violation_detection",
        "task_id": "TEST-001",
        "data": {
            "influent": {"pH值": 7.5, "化学需氧量浓度（毫克/升）": 45},
            "effluent": {"pH值": 7.8, "化学需氧量浓度（毫克/升）": 50}
        }
    }
    
    # 3. 生成执行计划
    plan = orchestrator.create_execution_plan(task)
    
    assert plan.task_type == "violation_detection"
    assert len(plan.agents) == 4
    assert plan.agents[0].id == "multi-dimensional-data-perception-agent"
    assert plan.agents[-1].id == "disposition-execution-agent"


def test_data_perception_to_alert_workflow():
    """测试从数据感知到预警生成的简化工作流"""
    # 1. 数据获取
    data_acquisition = DataAcquisitionModule()
    raw_data = data_acquisition.acquire_from_csv(
        influent_path="data/pollution_water_in.csv",
        effluent_path="data/pollution_water_out.csv",
        limit=10
    )
    
    assert raw_data["influent_count"] == 10
    
    # 2. 模拟异常检测结果
    anomaly_result = {
        "confidence": 0.85,
        "anomalies": [
            {
                "type": "平稳异常",
                "indicator": "COD",
                "duration": "3h"
            }
        ]
    }
    
    # 3. 模拟违规判定结果
    violation_result = {
        "confidence": 0.92,
        "violation_type": "插瓶干扰",
        "suspicion_level": "high"
    }
    
    # 4. 预警分级
    alert_classifier = AlertClassifier()
    alert = alert_classifier.classify_alert(anomaly_result, violation_result)
    
    assert alert["level"] in ["general", "moderate", "serious"]
    
    # 5. 工单生成
    work_order_generator = WorkOrderGenerator()
    work_order = work_order_generator.generate_work_order(
        alert_info=alert,
        data_context={"anomaly_time_range": ["2024-05-29 02:00", "2024-05-29 05:00"]}
    )
    
    assert "id" in work_order
    assert "inspection_points" in work_order


def test_agent_registry_loading():
    """测试子智能体注册表加载"""
    orchestrator = DynamicOrchestrator(
        registry_path="shared/configs/agent_registry.yaml"
    )
    
    # 验证所有智能体都已注册
    assert len(orchestrator.available_agents) == 4
    
    # 验证任务映射
    assert "violation_detection" in orchestrator.task_type_mapping
    assert len(orchestrator.task_type_mapping["violation_detection"]) == 4


def test_three_library_integration():
    """测试三库一体化概念验证"""
    # 验证配置文件存在
    project_root = Path(__file__).parent.parent
    
    # 知识库
    knowledge_path = project_root / "shared" / "knowledge"
    assert knowledge_path.exists()
    
    # 算子库
    operators_path = project_root / "shared" / "operators"
    assert operators_path.exists()
    
    # 配置
    configs_path = project_root / "shared" / "configs"
    assert (configs_path / "agent_registry.yaml").exists()
    assert (configs_path / "rule_config.yaml").exists()
```

- [ ] **Step 2: 运行集成测试**

```bash
cd /home/NYJ2025/Ecological_env
python -m pytest tests/integration/test_e2e_architecture.py -v
```

Expected: 部分通过（有些需要实际数据文件）

- [ ] **Step 3: 提交**

```bash
git add tests/integration/test_e2e_architecture.py
git commit -m "test: add end-to-end architecture integration tests"
```

---

### Task 5.2: 更新CLAUDE.md文档

**Files:**
- Modify: `/home/NYJ2025/Ecological_env/CLAUDE.md`

- [ ] **Step 1: 更新CLAUDE.md架构描述**

```markdown
将原有的4个子智能体描述更新为：

## Four Sub-Agents

1. **multi-dimensional-data-perception-agent** 📊: "多维数据感知子智能体" - Multi-Dimensional Data Processor, Vibe: 严谨、可靠、多源整合
2. **anomaly-detection-agent** 🔍: "异常检测子智能体" - Anomaly Detector, Vibe: 警惕、全面、谦逊
3. **rule-reasoning-agent** ⚖️: "规则推理子智能体" - Knowledge Reasoner, Vibe: 博学、精准、公正
4. **disposition-execution-agent** 🚨: "研判预警与处置执行子智能体" - Action Executor, Vibe: 高效、规范、执行力强
```

- [ ] **Step 2: 提交**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for new architecture"
```

---

### Task 5.3: 更新README.md文档

**Files:**
- Modify: `/home/NYJ2025/Ecological_env/README.md`

- [ ] **Step 1: 更新README.md项目目录结构**

在原有的README.md中更新子智能体部分，将原来的4个子智能体更新为新的架构描述。

- [ ] **Step 2: 提交**

```bash
git add README.md
git commit -m "docs: update README.md for new architecture"
```

---

## 验收标准

完成所有任务后，系统应该具备以下能力：

1. ✅ 主智能体能够动态编排4个子智能体
2. ✅ 多维数据感知智能体能够处理8类数据
3. ✅ 异常检测子智能体专注于异常特征识别
4. ✅ 规则推理子智能体使用规则引擎进行违规判定
5. ✅ 研判预警与处置执行智能体能够生成三级预警和工单
6. ✅ 三库配置文件完善（agent_registry.yaml, rule_config.yaml）
7. ✅ 所有模块都有对应的测试
8. ✅ 文档更新完整

---

## 总计任务数

- 阶段1（主智能体）: 4个任务
- 阶段2（多维数据感知）: 5个任务
- 阶段3（规则推理）: 2个任务
- 阶段4（预警执行）: 4个任务
- 阶段5（集成测试）: 3个任务

**总计: 18个任务**

---

**实施优先级**: 按阶段顺序执行，每个阶段完成后进行验证和提交。

**回滚计划**: 每个阶段提交后打tag，便于回滚到指定阶段。
