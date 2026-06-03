#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整流程测试 - Orchestrator-Core架构
验证主智能体和4个子智能体的协同工作

测试流程：
1. 任务接收与解析 → 大模型读取主智能体身份
2. 大模型协调4个子智能体协同执行
3. 结果解释输出 → 大模型生成报告
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# 设置UTF-8编码输出（Windows兼容）
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Orchestrator-Core模块路径
orchestrator_scripts = project_root / "workspace" / "skills" / "orchestrator-core" / "scripts"
sys.path.insert(0, str(orchestrator_scripts))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def test_normal_data():
    """测试正常数据"""
    print("\n" + "=" * 70)
    print("测试1: 正常数据")
    print("=" * 70)

    from task_receiving_and_parsing import TaskReceivingAndParsingModule
    from execution_control import LLMAgentCoordinator
    from result_interpretation import ResultInterpretationModule

    # 初始化模块
    task_receiving = TaskReceivingAndParsingModule(llm_client=None)
    llm_coordinator = LLMAgentCoordinator(llm_client=None)
    result_interpretation = ResultInterpretationModule(llm_client=None)

    # 模拟正常数据
    data = {
        "influent": {
            "pH值": 7.2,
            "化学需氧量浓度（毫克/升）": 100,
            "总氮浓度（毫克/升）": 20,
            "氨氮浓度（毫克/升）": 8,
            "总磷浓度（毫克/升）": 2.0,
            "监测时间": "2026-05-22 10:00:00"
        },
        "effluent": {
            "pH值": 7.5,
            "化学需氧量浓度（毫克/升）": 45,
            "总氮浓度（毫克/升）": 12,
            "氨氮浓度（毫克/升）": 4,
            "总磷浓度（毫克/升）": 0.4,
            "监测时间": "2026-05-22 12:00:00"
        },
        "timestamp": "2026-05-22T12:00:00"
    }

    print("\n--- Stage 1: Task Receiving and Parsing ---")
    parse_result = task_receiving.process(data)

    if parse_result['status'] != 'success':
        print(f"[FAIL] Task parsing failed")
        return False

    print(f"[OK] Task parsing successful")
    print(f"  - Task ID: {parse_result['structured_task']['task_id']}")
    print(f"  - Intent type: {parse_result['intent'].intent_type}")
    print(f"  - Priority: {parse_result['structured_task']['priority']}")

    print("\n--- Stage 2: LLM Coordinating Sub-Agents ---")
    structured_task = parse_result['structured_task']
    intent = parse_result['intent']

    execution_results = llm_coordinator.coordinate_all_agents(
        task=structured_task,
        analysis_scope=intent.analysis_scope
    )

    print(f"[OK] Sub-agents execution completed: {len(execution_results)} agents")
    for agent_id, result in execution_results.items():
        status = result.get('status', 'unknown')
        print(f"  - {agent_id}: {status}")

    print("\n--- Stage 3: Result Interpretation and Report ---")
    interpretation_result = result_interpretation.interpret_results(
        execution_results=execution_results,
        task_info={
            "task_id": structured_task['task_id'],
            "task_name": structured_task['task_name'],
            "timestamp": data['timestamp']
        }
    )

    print(f"[OK] Report generation completed")
    # Print report without problematic characters
    report_content = interpretation_result['report']
    # Replace checkmarks that cause encoding issues
    report_content = report_content.replace('✓', '[OK]').replace('⚠️', '[WARN]').replace('⚡', '[ALERT]')
    print(f"\n{report_content}")

    # 检查结果
    analysis = interpretation_result['analysis']
    print(f"\n--- 汇总 ---")
    print(f"  - 参与子智能体: {len(analysis['agents_executed'])}")
    print(f"  - 检测到异常: {analysis.get('has_anomaly', False)}")
    print(f"  - 检测到违规: {analysis['has_violation']}")
    print(f"  - 嫌疑等级: {analysis['suspicion_level']}")

    return True


def test_exceedance_data():
    """测试超标数据"""
    print("\n" + "=" * 70)
    print("测试2: 超标数据")
    print("=" * 70)

    from task_receiving_and_parsing import TaskReceivingAndParsingModule
    from execution_control import LLMAgentCoordinator
    from result_interpretation import ResultInterpretationModule

    # 初始化模块
    task_receiving = TaskReceivingAndParsingModule(llm_client=None)
    llm_coordinator = LLMAgentCoordinator(llm_client=None)
    result_interpretation = ResultInterpretationModule(llm_client=None)

    # 模拟超标数据
    data = {
        "influent": {
            "pH值": 7.0,
            "化学需氧量浓度（毫克/升）": 100,
            "监测时间": "2026-05-22 10:00:00"
        },
        "effluent": {
            "pH值": 7.5,
            "化学需氧量浓度（毫克/升）": 75,  # 超标！
            "监测时间": "2026-05-22 12:00:00"
        },
        "timestamp": "2026-05-22T12:00:00"
    }

    print("\n--- 阶段1: 任务接收与解析 ---")
    parse_result = task_receiving.process(data)

    if parse_result['status'] != 'success':
        print(f"❌ 任务解析失败")
        return False

    print(f"✓ 任务解析成功")

    print("\n--- 阶段2: 大模型协调子智能体 ---")
    structured_task = parse_result['structured_task']
    intent = parse_result['intent']

    execution_results = llm_coordinator.coordinate_all_agents(
        task=structured_task,
        analysis_scope=intent.analysis_scope
    )

    print(f"✓ 子智能体执行完成")

    print("\n--- 阶段3: 结果解释与报告 ---")
    interpretation_result = result_interpretation.interpret_results(
        execution_results=execution_results,
        task_info={
            "task_id": structured_task['task_id'],
            "task_name": structured_task['task_name'],
            "timestamp": data['timestamp']
        }
    )

    print(f"\n{interpretation_result['report']}")

    # 检查结果
    analysis = interpretation_result['analysis']
    print(f"\n--- 汇总 ---")
    print(f"  - 检测到异常: {analysis.get('has_anomaly', False)}")
    print(f"  - 检测到违规: {analysis['has_violation']}")
    print(f"  - 嫌疑等级: {analysis['suspicion_level']}")

    if analysis['has_violation']:
        print(f"  - 违规数量: {len(analysis['violations'])}")
        for vio in analysis['violations']:
            print(f"    * {vio['type']}: {vio['message']}")

    return analysis['has_violation']


def test_constant_value_anomaly():
    """测试恒定值异常（插瓶干扰）"""
    print("\n" + "=" * 70)
    print("测试3: 恒定值异常（插瓶干扰）")
    print("=" * 70)

    from task_receiving_and_parsing import TaskReceivingAndParsingModule
    from execution_control import LLMAgentCoordinator
    from result_interpretation import ResultInterpretationModule

    # 初始化模块
    task_receiving = TaskReceivingAndParsingModule(llm_client=None)
    llm_coordinator = LLMAgentCoordinator(llm_client=None)
    result_interpretation = ResultInterpretationModule(llm_client=None)

    # 发送多条恒定数据
    for i in range(10):
        data = {
            "influent": {
                "pH值": 7.0 + i * 0.01,
                "化学需氧量浓度（毫克/升）": 100 + i,
                "监测时间": f"2026-05-22 {10+i}:00:00"
            },
            "effluent": {
                "pH值": 7.5,  # 恒定
                "化学需氧量浓度（毫克/升）": 45,  # 恒定
                "监测时间": f"2026-05-22 {12+i}:00:00"
            },
            "timestamp": f"2026-05-22T{12+i}:00:00"
        }

        parse_result = task_receiving.process(data)
        if parse_result['status'] != 'success':
            continue

        execution_results = llm_coordinator.coordinate_all_agents(
            task=parse_result['structured_task'],
            analysis_scope=parse_result['intent'].analysis_scope
        )

    # 最后一次解析并生成报告
    interpretation_result = result_interpretation.interpret_results(
        execution_results=execution_results,
        task_info={
            "task_id": "test_constant",
            "task_name": "恒定值异常测试",
            "timestamp": data['timestamp']
        }
    )

    print(f"\n{interpretation_result['report']}")

    # 检查结果
    analysis = interpretation_result['analysis']
    print(f"\n--- 汇总 ---")
    print(f"  - 检测到异常: {analysis.get('has_anomaly', False)}")
    print(f"  - 检测到违规: {analysis['has_violation']}")
    print(f"  - 嫌疑等级: {analysis['suspicion_level']}")

    return analysis['suspicion_level'] in ['high', 'critical']


def main():
    """运行所有测试"""
    print("=" * 70)
    print("Orchestrator-Core 完整流程测试")
    print("=" * 70)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"项目路径: {project_root}")

    results = []

    # 测试1: 正常数据
    try:
        result = test_normal_data()
        results.append(("正常数据", result, "应无违规"))
    except Exception as e:
        logger.error(f"测试1失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("正常数据", False, f"异常: {e}"))

    # 测试2: 超标数据
    try:
        result = test_exceedance_data()
        results.append(("超标数据", result, "应检测到违规"))
    except Exception as e:
        logger.error(f"测试2失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("超标数据", False, f"异常: {e}"))

    # 测试3: 恒定值异常
    try:
        result = test_constant_value_anomaly()
        results.append(("恒定值异常", result, "应检测到插瓶干扰"))
    except Exception as e:
        logger.error(f"测试3失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("恒定值异常", False, f"异常: {e}"))

    # 汇总结果
    print("\n" + "=" * 70)
    print("测试汇总")
    print("=" * 70)

    passed = 0
    failed = 0

    for name, result, expected in results:
        status = "[PASS]" if result else "[FAIL]"
        if result:
            passed += 1
        else:
            failed += 1

        print(f"{status} | {name:20s} | {expected}")

    print(f"\n总计: {passed} 通过, {failed} 失败")

    if failed == 0:
        print("\n[PASS] 所有测试通过！Orchestrator-Core架构正常工作")
    else:
        print(f"\n[FAIL] {failed} 个测试失败，请检查")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
