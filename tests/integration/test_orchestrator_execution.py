"""
动态编排器集成测试
测试DynamicOrchestrator和ExecutionEngine的完整工作流程
"""
import sys
from pathlib import Path

# 添加项目路径
# 当前文件在 tests/integration/，需要向上两级到项目根目录
project_root = Path(__file__).parent.parent.parent
orchestrator_scripts = project_root / "workspace" / "skills" / "orchestrator-core" / "scripts"
sys.path.insert(0, str(orchestrator_scripts))

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
