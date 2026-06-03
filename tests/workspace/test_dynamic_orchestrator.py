# tests/workspace/test_dynamic_orchestrator.py
import pytest
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "workspace" / "skills" / "orchestrator-core" / "scripts"))

from dynamic_orchestrator import DynamicOrchestrator, ExecutionPlan, ExecutionMode


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

    assert plan.execution_mode == ExecutionMode.SEQUENTIAL
    assert len(plan.agents) == 4
    assert plan.agents[0].id == "multi-dimensional-data-perception-agent"
    assert plan.agents[-1].id == "disposition-execution-agent"


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
    assert plan.agents[0].id == "multi-dimensional-data-perception-agent"
    assert plan.agents[1].id == "anomaly-detection-agent"


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


if __name__ == "__main__":
    print("Running dynamic orchestrator tests...")
    print()

    try:
        test_orchestrator_initialization()
        print("✓ test_orchestrator_initialization passed")

        test_violation_detection_plan()
        print("✓ test_violation_detection_plan passed")

        test_analysis_query_plan()
        print("✓ test_analysis_query_plan passed")

        test_parallel_execution_detection()
        print("✓ test_parallel_execution_detection passed")

        print()
        print("=" * 50)
        print("All tests passed!")
    except Exception as e:
        print()
        print("=" * 50)
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
