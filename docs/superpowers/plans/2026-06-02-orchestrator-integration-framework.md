# DynamicOrchestrator 集成框架完善计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立最小可运行的4-agent集成框架，让DynamicOrchestrator能够协调智能体协作（从模拟执行开始，逐步过渡到真实执行）

**Architecture:** 动态编排器(DynamicOrchestrator)负责创建执行计划 → 执行引擎(ExecutionEngine)负责执行计划 → 各子智能体负责具体业务逻辑

**Tech Stack:** Python 3.10+, yaml, pathlib

---

## 文件结构概览

### 修改文件
- `run_comprehensive_tests.py` - 修复IntegrationTestLayer，跳过不存在的模块测试

### 新建文件
- `workspace/skills/orchestrator-core/scripts/execution_engine.py` - 执行引擎（模拟执行）
- `tests/integration/test_orchestrator_execution.py` - 集成测试
- `demo_orchestrator.py` - 端到端演示脚本

---

## 阶段1: 修复测试脚本（10分钟）

### Task 1: 修复IntegrationTestLayer

**Files:**
- Modify: `run_comprehensive_tests.py:247-295`

**目标:** 让IntegrationTestLayer只测试DynamicOrchestrator本身，跳过不存在的模块

- [ ] **Step 1: 修改IntegrationTestLayer.run()方法**

找到IntegrationTestLayer类的run()方法（约第247-295行），将其替换为以下实现：

```python
def run(self) -> List[TestResult]:
    """执行集成测试"""
    print(f"\n[3/5] {self.description()}...")

    # 测试1: DynamicOrchestrator
    start = time.time()
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "workspace/skills/orchestrator-core/scripts"))
        from dynamic_orchestrator import DynamicOrchestrator

        orchestrator = DynamicOrchestrator()
        agent_count = len(orchestrator.available_agents)
        task_mappings = len(orchestrator.task_type_mapping)

        if agent_count == 4 and task_mappings > 0:
            self._add_result("DynamicOrchestrator 验证", True, duration=time.time() - start)
        else:
            self._add_result(
                "DynamicOrchestrator 验证",
                False,
                f"智能体数: {agent_count} (期望4), 任务映射: {task_mappings}",
                time.time() - start
            )
    except Exception as e:
        self._add_result("DynamicOrchestrator 验证", False, f"{type(e).__name__}: {str(e)}", time.time() - start)

    # 测试2: 创建执行计划
    start = time.time()
    try:
        task = {
            "task_type": "violation_detection",
            "data": {"influent": {"pH": 7.5}, "effluent": {"pH": 7.8}}
        }
        plan = orchestrator.create_execution_plan(task)

        if len(plan.agents) == 4:
            self._add_result("创建执行计划", True, duration=time.time() - start)
        else:
            self._add_result(
                "创建执行计划",
                False,
                f"智能体数量错误: {len(plan.agents)} (期望4)",
                time.time() - start
            )
    except Exception as e:
        self._add_result("创建执行计划", False, f"{type(e).__name__}: {str(e)}", time.time() - start)

    # 测试3: 数据流模块导入（暂时跳过）
    self._add_result(
        "数据流模块导入",
        False,
        "跳过（模块尚未实现）",
        0.0
    )

    # 测试4: ExecutionControl（暂时跳过）
    self._add_result(
        "ExecutionControl 初始化",
        False,
        "跳过（模块尚未实现）",
        0.0
    )

    return self.results
```

- [ ] **Step 2: 运行测试验证**

```bash
cd E:\project\Ecological_env
python run_comprehensive_tests.py --skip-stream
```

Expected: IntegrationTestLayer显示"DynamicOrchestrator 验证"和"创建执行计划"通过

- [ ] **Step 3: 提交**

```bash
git add run_comprehensive_tests.py
git commit -m "test: fix IntegrationTestLayer to skip unimplemented modules"
```

---

## 阶段2: 创建执行引擎（20分钟）

### Task 2: 创建ExecutionEngine基础结构

**Files:**
- Create: `workspace/skills/orchestrator-core/scripts/execution_engine.py`

- [ ] **Step 1: 创建执行引擎文件**

创建新文件 `workspace/skills/orchestrator-core/scripts/execution_engine.py`，内容如下：

```python
"""
执行引擎 - 执行DynamicOrchestrator创建的执行计划
"""
import logging
import time
from typing import Dict, Any, List
from dataclasses import dataclass, field

# 导入DynamicOrchestrator的类型
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from dynamic_orchestrator import ExecutionPlan, AgentTask


logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """单个智能体的执行结果"""
    agent_id: str
    status: str  # success, failed, skipped
    output: Dict[str, Any] = field(default_factory=dict)
    error: str = None
    duration: float = 0.0


@dataclass
class ExecutionResult:
    """完整执行结果"""
    plan: ExecutionPlan
    agent_results: List[AgentResult]
    total_duration: float
    success: bool


class ExecutionEngine:
    """执行引擎 - 负责执行DynamicOrchestrator创建的执行计划"""

    def __init__(self):
        """初始化执行引擎"""
        self.logger = logger

    def execute_plan(self, plan: ExecutionPlan) -> ExecutionResult:
        """执行一个执行计划

        Args:
            plan: DynamicOrchestrator创建的执行计划

        Returns:
            ExecutionResult: 执行结果
        """
        start_time = time.time()
        agent_results: List[AgentResult] = []

        self.logger.info(f"开始执行计划: {plan.task_type}")
        self.logger.info(f"执行模式: {plan.execution_mode}")
        self.logger.info(f"智能体数量: {len(plan.agents)}")

        for idx, agent_task in enumerate(plan.agents):
            self.logger.info(f"执行智能体 {idx + 1}/{len(plan.agents)}: {agent_task.id}")

            # 检查依赖是否满足
            if agent_task.depends_on:
                self.logger.info(f"  依赖: {agent_task.depends_on}")
                # TODO: 检查依赖的agent是否成功执行

            # 执行智能体
            result = self._execute_agent(agent_task)
            agent_results.append(result)

            self.logger.info(f"  结果: {result.status} ({result.duration:.2f}s)")

            # 如果执行失败，考虑是否继续
            if result.status == "failed":
                self.logger.warning(f"智能体 {agent_task.id} 执行失败")

        total_duration = time.time() - start_time
        success_count = sum(1 for r in agent_results if r.status == "success")

        return ExecutionResult(
            plan=plan,
            agent_results=agent_results,
            total_duration=total_duration,
            success=(success_count == len(agent_results))
        )

    def _execute_agent(self, agent_task: AgentTask) -> AgentResult:
        """执行单个智能体

        Args:
            agent_task: 智能体任务

        Returns:
            AgentResult: 执行结果
        """
        start_time = time.time()

        # TODO: 实际执行逻辑 - 后续实现
        # 目前返回模拟结果
        result = AgentResult(
            agent_id=agent_task.id,
            status="success",
            output={
                "message": f"模拟执行 {agent_task.id}",
                "input_data": agent_task.input_data
            },
            duration=time.time() - start_time
        )

        return result
```

- [ ] **Step 2: 验证语法**

```bash
cd E:\project\Ecological_env
python -c "import sys; sys.path.insert(0, 'workspace/skills/orchestrator-core/scripts'); from execution_engine import ExecutionEngine; print('[OK] ExecutionEngine imported')"
```

Expected: [OK] ExecutionEngine imported

- [ ] **Step 3: 提交**

```bash
git add workspace/skills/orchestrator-core/scripts/execution_engine.py
git commit -m "feat: add ExecutionEngine for orchestrating agent execution"
```

---

## 阶段3: 集成测试（15分钟）

### Task 3: 创建集成测试

**Files:**
- Create: `tests/integration/test_orchestrator_execution.py`

- [ ] **Step 1: 创建集成测试文件**

创建新文件 `tests/integration/test_orchestrator_execution.py`，内容如下：

```python
"""
动态编排器集成测试
测试DynamicOrchestrator和ExecutionEngine的完整工作流程
"""
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "workspace" / "skills" / "orchestrator-core" / "scripts"))

from dynamic_orchestrator import DynamicOrchestrator
from execution_engine import ExecutionEngine, ExecutionResult


def test_orchestrator_and_engine_integration():
    """测试编排器和执行引擎的集成"""
    # 1. 创建编排器
    orchestrator = DynamicOrchestrator(
        registry_path="shared/configs/agent_registry.yaml"
    )

    # 2. 创建任务
    task = {
        "task_type": "violation_detection",
        "data": {
            "influent": {"pH": 7.5, "COD": 450},
            "effluent": {"pH": 7.8, "COD": 50}
        }
    }

    # 3. 创建执行计划
    plan = orchestrator.create_execution_plan(task)

    print(f"执行计划创建成功:")
    print(f"  任务类型: {plan.task_type}")
    print(f"  执行模式: {plan.execution_mode}")
    print(f"  智能体数量: {len(plan.agents)}")

    assert len(plan.agents) == 4, "应该有4个智能体"

    # 4. 创建执行引擎
    engine = ExecutionEngine()

    # 5. 执行计划
    result = engine.execute_plan(plan)

    print(f"\n执行结果:")
    print(f"  总耗时: {result.total_duration:.2f}s")
    print(f"  成功: {result.success}")

    for agent_result in result.agent_results:
        print(f"  {agent_result.agent_id}: {agent_result.status}")

    # 6. 验证结果
    assert result is not None, "应该有执行结果"
    assert len(result.agent_results) == 4, "应该有4个智能体结果"
    assert result.success is True, "执行应该成功（模拟模式下）"

    print("\n[OK] 集成测试通过!")


def test_analysis_query_plan():
    """测试分析查询任务的执行"""
    orchestrator = DynamicOrchestrator()

    task = {
        "task_type": "analysis_query",
        "query": "分析最近出水的COD异常"
    }

    plan = orchestrator.create_execution_plan(task)
    engine = ExecutionEngine()
    result = engine.execute_plan(plan)

    assert len(plan.agents) == 2, "分析查询只需要2个智能体"
    assert len(result.agent_results) == 2, "应该有2个智能体结果"

    print("[OK] 分析查询测试通过!")


if __name__ == "__main__":
    print("=" * 60)
    print("动态编排器集成测试")
    print("=" * 60)
    print()

    try:
        test_orchestrator_and_engine_integration()
        print()
        test_analysis_query_plan()
        print()
        print("=" * 60)
        print("所有测试通过!")
        print("=" * 60)
    except Exception as e:
        print()
        print("=" * 60)
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

- [ ] **Step 2: 运行测试**

```bash
cd E:\project\Ecological_env
python tests/integration/test_orchestrator_execution.py
```

Expected: 显示执行计划和执行结果，最后输出"所有测试通过!"

- [ ] **Step 3: 提交**

```bash
git add tests/integration/test_orchestrator_execution.py
git commit -m "test: add orchestrator and execution engine integration test"
```

---

## 阶段4: 端到端演示（20分钟）

### Task 4: 创建演示脚本

**Files:**
- Create: `demo_orchestrator.py`

- [ ] **Step 1: 创建演示脚本**

在项目根目录创建 `demo_orchestrator.py`，内容如下：

```python
"""
动态编排器演示脚本
展示4-agent架构的协作流程
"""
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "workspace" / "skills" / "orchestrator-core" / "scripts"))

from dynamic_orchestrator import DynamicOrchestrator
from execution_engine import ExecutionEngine


def print_header(title: str):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_section(title: str):
    """打印小节标题"""
    print(f"\n{title}")
    print("-" * 60)


def demo_violation_detection():
    """演示违规检测任务"""
    print_header("违规检测任务演示")

    # 1. 创建编排器
    print_section("1. 初始化动态编排器")
    orchestrator = DynamicOrchestrator(
        registry_path="shared/configs/agent_registry.yaml"
    )

    print(f"已加载智能体数量: {len(orchestrator.available_agents)}")
    for agent_id, agent_info in orchestrator.available_agents.items():
        print(f"  - {agent_info.get('name', agent_id)}")

    print(f"\n支持的任务类型: {list(orchestrator.task_type_mapping.keys())}")

    # 2. 创建任务
    print_section("2. 创建违规检测任务")
    task = {
        "task_type": "violation_detection",
        "data": {
            "influent": {"pH": 7.5, "COD": 450, "TN": 45, "TP": 5},
            "effluent": {"pH": 7.8, "COD": 50, "TN": 15, "TP": 0.5}
        }
    }

    print(f"任务类型: {task['task_type']}")
    print(f"输入数据: 进水pH={task['data']['influent']['pH']}, 出水COD={task['data']['effluent']['COD']}")

    # 3. 创建执行计划
    print_section("3. 生成执行计划")
    plan = orchestrator.create_execution_plan(task)

    print(f"执行模式: {plan.execution_mode}")
    print(f"智能体执行顺序:")
    for idx, agent in enumerate(plan.agents, 1):
        deps = f" (依赖: {agent.depends_on[0]})" if agent.depends_on else ""
        print(f"  {idx}. {agent.name}{deps}")

    # 4. 执行计划
    print_section("4. 执行计划")
    engine = ExecutionEngine()
    result = engine.execute_plan(plan)

    print(f"\n执行摘要:")
    print(f"  总耗时: {result.total_duration:.2f}s")
    print(f"  执行状态: {'成功' if result.success else '失败'}")

    print(f"\n各智能体执行结果:")
    for agent_result in result.agent_results:
        status_icon = "[OK]" if agent_result.status == "success" else "[FAIL]"
        print(f"  {status_icon} {agent_result.agent_id}")
        print(f"      耗时: {agent_result.duration:.3f}s")
        if agent_result.output:
            print(f"      输出: {agent_result.output.get('message', '')}")

    return result


def demo_analysis_query():
    """演示分析查询任务"""
    print_header("分析查询任务演示")

    orchestrator = DynamicOrchestrator()
    engine = ExecutionEngine()

    task = {
        "task_type": "analysis_query",
        "query": "分析最近出水的COD异常"
    }

    print(f"任务类型: {task['task_type']}")
    print(f"查询内容: {task['query']}")

    plan = orchestrator.create_execution_plan(task)
    result = engine.execute_plan(plan)

    print(f"\n执行结果:")
    print(f"  智能体数量: {len(plan.agents)}")
    print(f"  执行成功: {result.success}")

    return result


def main():
    """主函数"""
    print_header("废水虚假排放监测系统 - 4-Agent架构演示")

    print("\n本演示展示动态编排器如何协调4个子智能体协作完成违规检测任务。")
    print("各子智能体职责:")
    print("  1. 多维数据感知智能体 - 获取多源数据，进行数据清洗和对齐")
    print("  2. 异常检测智能体 - 检测数据中的异常模式")
    print("  3. 规则推理智能体 - 基于规则判定违规行为")
    print("  4. 研判预警与处置执行智能体 - 融合结果，生成预警和工单")

    try:
        # 演示1: 违规检测
        demo_violation_detection()

        # 演示2: 分析查询
        demo_analysis_query()

        print_header("演示完成")

        print("\n下一步:")
        print("  1. 实现各个子智能体的具体业务逻辑")
        print("  2. 实现智能体之间的数据传递")
        print("  3. 实现真实的违规检测算法")

    except Exception as e:
        print(f"\n演示执行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行演示**

```bash
cd E:\project\Ecological_env
python demo_orchestrator.py
```

Expected: 完整的演示输出，展示4-agent架构的协作流程

- [ ] **Step 3: 提交**

```bash
git add demo_orchestrator.py
git commit -m "demo: add orchestrator demonstration script"
```

---

## 验收标准

完成所有任务后，系统应该具备以下能力：

1. ✅ IntegrationTestLayer能够通过DynamicOrchestrator相关测试
2. ✅ ExecutionEngine能够执行DynamicOrchestrator创建的计划
3. ✅ 集成测试验证完整的编排→执行流程
4. ✅ 演示脚本清晰展示4-agent架构的协作方式
5. ✅ 为后续实现各个子智能体打下坚实基础

---

## 总计任务数

- 阶段1（修复测试）: 1个任务
- 阶段2（执行引擎）: 1个任务
- 阶段3（集成测试）: 1个任务
- 阶段4（演示脚本）: 1个任务

**总计: 4个任务，预计耗时: 65分钟（约1小时）**