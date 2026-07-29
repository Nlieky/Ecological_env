"""
动态编排器 - 主智能体调用子智能体的核心逻辑

此脚本实现主智能体与 4 个子智能体之间的协调。
"""
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def call_subagent(subagent_name, task_description, input_data=None):
    """
    调用子智能体执行任务

    Args:
        subagent_name: 子智能体名称
        task_description: 任务描述
        input_data: 输入数据（可选）

    Returns:
        子智能体的执行结果
    """
    # 子智能体路径映射
    subagent_paths = {
        "multi-dimensional-data-perception": project_root / "subagents" / "multi-dimensional-data-perception-agent",
        "anomaly-detection": project_root / "subagents" / "anomaly-detection-agent",
        "rule-reasoning": project_root / "subagents" / "rule-reasoning-agent",
        "disposition-execution": project_root / "subagents" / "disposition-execution-agent"
    }

    subagent_path = subagent_paths.get(subagent_name)
    if not subagent_path:
        return {
            "status": "error",
            "message": f"未知的子智能体: {subagent_name}",
            "result": None
        }

    try:
        # 这里应该调用子智能体的 AIAgent
        # 目前返回模拟数据用于测试
        return _call_subagent_impl(subagent_name, subagent_path, task_description, input_data)
    except Exception as e:
        return {
            "status": "error",
            "message": f"调用子智能体失败: {e}",
            "result": None
        }


def _call_subagent_impl(subagent_name, subagent_path, task_description, input_data):
    """
    实际调用子智能体的实现

    TODO: 这里需要集成 Hermes 的 delegate_task 机制
    目前返回模拟数据
    """
    # 模拟每个子智能体的响应
    mock_responses = {
        "multi-dimensional-data-perception": {
            "status": "success",
            "processed_data": {
                "influent": {"COD": 120, "TN": 25, "TP": 3, "pH": 7.2},
                "effluent": {"COD": 45, "TN": 12, "TP": 0.4, "pH": 7.0}
            },
            "quality_metrics": {"completeness": "95%"}
        },
        "anomaly-detection": {
            "status": "success",
            "anomalies": [
                {"type": "spike", "metric": "COD", "severity": "high"}
            ],
            "violations": [
                {"rule": "COD_MAX", "actual": 85, "threshold": 50}
            ]
        },
        "rule-reasoning": {
            "status": "success",
            "compliance_status": "non_compliant",
            "reasoning": "COD浓度超过一级A标准限值"
        },
        "disposition-execution": {
            "status": "success",
            "alert_classification": "urgent",
            "work_order": {
                "id": "WO-2024-001",
                "title": "COD超标紧急处置",
                "actions": ["调整曝气量", "加强污泥回流"]
            }
        }
    }

    return mock_responses.get(subagent_name, {"status": "unknown"})


def orchestrate(query, context=None):
    """
    编排子智能体完成用户查询

    Args:
        query: 用户查询
        context: 上下文信息（可选）

    Returns:
        编排结果，包含所有子智能体的调用结果
    """
    # 简单的查询分析，决定需要调用哪些子智能体
    query_lower = query.lower()

    # 默认调用所有 4 个子智能体
    required_agents = []

    # 数据相关查询
    if any(keyword in query_lower for keyword in ["数据", "查询", "获取", "进水", "出水"]):
        required_agents.append("multi-dimensional-data-perception")

    # 异常检测查询
    if any(keyword in query_lower for keyword in ["异常", "检测", "超标", "违规"]):
        required_agents.append("anomaly-detection")

    # 规则推理查询
    if any(keyword in query_lower for keyword in ["合规", "标准", "法规", "判断"]):
        required_agents.append("rule-reasoning")

    # 处置查询
    if any(keyword in query_lower for keyword in ["处置", "工单", "告警", "响应"]):
        required_agents.append("disposition-execution")

    # 如果没有明确指向，调用全部
    if not required_agents:
        required_agents = [
            "multi-dimensional-data-perception",
            "anomaly-detection",
            "rule-reasoning",
            "disposition-execution"
        ]

    # 依次调用子智能体
    results = []
    for agent_name in required_agents:
        agent_result = call_subagent(agent_name, query)
        results.append({
            "agent": agent_name,
            "result": agent_result
        })

    # 整合结果
    return {
        "orchestration_result": {
            "sub_agent_calls": results,
            "query": query,
            "agents_called": [r["agent"] for r in results],
            "summary": f"已调用 {len(results)} 个子智能体完成任务"
        }
    }


def skill_function(query, context=None):
    """
    Hermes Skill 的入口函数

    Args:
        query: 用户查询
        context: 上下文

    Returns:
        编排结果
    """
    return orchestrate(query, context)


def main():
    """测试入口"""
    test_query = "分析当前废水监测数据，检测异常并给出处置建议"
    result = orchestrate(test_query)
    print("=" * 60)
    print("编排器测试结果")
    print("=" * 60)
    print(f"查询: {test_query}")
    print()
    for call in result["orchestration_result"]["sub_agent_calls"]:
        print(f"子智能体: {call['agent']}")
        print(f"状态: {call['result'].get('status')}")
        print()
    print("=" * 60)


if __name__ == "__main__":
    main()
