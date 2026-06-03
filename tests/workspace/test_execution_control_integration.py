# tests/workspace/test_execution_control_integration.py
"""
集成测试：执行控制模块与动态编排器集成测试

测试目标：
1. 验证执行控制模块已集成动态编排器
2. 验证违规检测工作流的执行计划创建
3. 验证执行计划的模拟执行
"""
import pytest
from pathlib import Path
import sys

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "workspace" / "skills" / "orchestrator-core" / "scripts"))

from execution_control import ExecutionControlModule
from dynamic_orchestrator import DynamicOrchestrator, ExecutionPlan, ExecutionMode


def test_execution_control_with_dynamic_orchestrator():
    """测试执行控制模块集成动态编排器"""
    llm_client = None  # 使用本地模式测试

    execution_control = ExecutionControlModule(llm_client=llm_client)

    # 验证编排器已集成
    assert hasattr(execution_control, 'orchestrator'), "ExecutionControlModule should have orchestrator attribute"
    assert isinstance(execution_control.orchestrator, DynamicOrchestrator), "orchestrator should be DynamicOrchestrator instance"


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
    assert plan.task_type == "violation_detection", "Task type should be violation_detection"
    assert len(plan.agents) == 4, "Should have 4 agents for violation detection"
    assert plan.execution_mode == ExecutionMode.SEQUENTIAL, "Default mode should be sequential"

    # 执行（本地模式，不实际调用子智能体）
    result = execution_control.execute_plan(plan, dry_run=True)

    assert result["status"] == "dry_run", "Dry run should return dry_run status"
    assert result["agents_planned"] == 4, "Should plan 4 agents"
    assert result["execution_mode"] == "sequential", "Execution mode should be sequential"
    assert "agents" in result, "Result should contain agents list"
