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
