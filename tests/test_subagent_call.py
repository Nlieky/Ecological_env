"""
测试子智能体调用机制

验证主智能体通过 subprocess 调用子智能体的完整流程
"""
import os
import sys
import json
import tempfile
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import importlib.util

# 动态导入 call_subagent 模块（因为目录名包含连字符）
spec = importlib.util.spec_from_file_location(
    "call_subagent",
    project_root / "workspace" / "skills" / "orchestrator-core" / "scripts" / "call_subagent.py"
)
call_subagent_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(call_subagent_module)

call_subagent = call_subagent_module.call_subagent
get_session_dir = call_subagent_module.get_session_dir

# 动态导入 create_session 模块
spec2 = importlib.util.spec_from_file_location(
    "create_session",
    project_root / "workspace" / "skills" / "orchestrator-core" / "scripts" / "create_session.py"
)
create_session_module = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(create_session_module)

create_session = create_session_module.create_session


def test_create_session():
    """测试会话创建"""
    print("\n" + "=" * 60)
    print("测试 1: 创建会话")
    print("=" * 60)

    session_id = create_session()
    print(f"[PASS] 会话ID: {session_id}")

    # 验证会话目录存在
    session_dir = Path("sessions") / session_id
    if session_dir.exists():
        print(f"[PASS] 会话目录存在: {session_dir}")
    else:
        print(f"[FAIL] 会话目录不存在: {session_dir}")

    return session_id


def test_call_anomaly_detection_agent():
    """测试调用异常检测子智能体"""
    print("\n" + "=" * 60)
    print("测试 2: 调用异常检测子智能体")
    print("=" * 60)

    # 创建新会话
    session_id = create_session()

    # 调用子智能体
    print(f"会话ID: {session_id}")
    print("正在调用异常检测子智能体...")

    result = call_subagent(
        subagent_name="anomaly-detection",
        task="检测最近24小时的COD异常",
        context={"time_range": "24h"}
    )

    print(f"状态: {result.get('status')}")
    print(f"任务ID: {result.get('task_id')}")

    if result.get('status') == 'completed':
        print("[PASS] 子智能体调用成功")

        # 检查结果文件
        result_file = Path("sessions") / session_id / "anomaly_result.json"
        if result_file.exists():
            print(f"[PASS] 结果文件存在: {result_file}")
            with open(result_file, 'r', encoding='utf-8') as f:
                result_data = json.load(f)
            print(f"结果内容: {json.dumps(result_data, indent=2, ensure_ascii=False)[:200]}...")
        else:
            print(f"[FAIL] 结果文件不存在: {result_file}")
    else:
        print(f"[FAIL] 子智能体调用失败: {result.get('error')}")

    return result


def test_call_data_perception_agent():
    """测试调用数据感知子智能体"""
    print("\n" + "=" * 60)
    print("测试 3: 调用数据感知子智能体")
    print("=" * 60)

    session_id = create_session()

    print(f"会话ID: {session_id}")
    print("正在调用数据感知子智能体...")

    result = call_subagent(
        subagent_name="multi-dimensional-data-perception",
        task="获取最近24小时的进水和出水数据",
        context={"time_range": "24h"}
    )

    print(f"状态: {result.get('status')}")
    print(f"任务ID: {result.get('task_id')}")

    if result.get('status') == 'completed':
        print("[PASS] 子智能体调用成功")

        result_file = Path("sessions") / session_id / "data_result.json"
        if result_file.exists():
            print(f"[PASS] 结果文件存在: {result_file}")
        else:
            print(f"[FAIL] 结果文件不存在: {result_file}")
    else:
        print(f"[FAIL] 子智能体调用失败: {result.get('error')}")

    return result


def test_call_rule_reasoning_agent():
    """测试调用规则推理子智能体"""
    print("\n" + "=" * 60)
    print("测试 4: 调用规则推理子智能体")
    print("=" * 60)

    session_id = create_session()

    print(f"会话ID: {session_id}")
    print("正在调用规则推理子智能体...")

    result = call_subagent(
        subagent_name="rule-reasoning",
        task="判断当前COD是否超标",
        context={"indicator": "COD", "value": 85}
    )

    print(f"状态: {result.get('status')}")
    print(f"任务ID: {result.get('task_id')}")

    if result.get('status') == 'completed':
        print("[PASS] 子智能体调用成功")

        result_file = Path("sessions") / session_id / "rule_result.json"
        if result_file.exists():
            print(f"[PASS] 结果文件存在: {result_file}")
        else:
            print(f"[FAIL] 结果文件不存在: {result_file}")
    else:
        print(f"[FAIL] 子智能体调用失败: {result.get('error')}")

    return result


def test_call_disposition_execution_agent():
    """测试调用处置执行子智能体"""
    print("\n" + "=" * 60)
    print("测试 5: 调用处置执行子智能体")
    print("=" * 60)

    session_id = create_session()

    print(f"会话ID: {session_id}")
    print("正在调用处置执行子智能体...")

    result = call_subagent(
        subagent_name="disposition-execution",
        task="生成COD超标预警工单",
        context={"severity": "urgent"}
    )

    print(f"状态: {result.get('status')}")
    print(f"任务ID: {result.get('task_id')}")

    if result.get('status') == 'completed':
        print("[PASS] 子智能体调用成功")

        result_file = Path("sessions") / session_id / "disposition_result.json"
        if result_file.exists():
            print(f"[PASS] 结果文件存在: {result_file}")
        else:
            print(f"[FAIL] 结果文件不存在: {result_file}")
    else:
        print(f"[FAIL] 子智能体调用失败: {result.get('error')}")

    return result


def main():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("子智能体调用机制测试")
    print("=" * 80)

    # 切换到项目目录
    os.chdir(project_root)

    results = {
        "create_session": test_create_session(),
        "anomaly_detection": test_call_anomaly_detection_agent(),
        "data_perception": test_call_data_perception_agent(),
        "rule_reasoning": test_call_rule_reasoning_agent(),
        "disposition_execution": test_call_disposition_execution_agent()
    }

    # 汇总结果
    print("\n" + "=" * 80)
    print("测试结果汇总")
    print("=" * 80)

    for test_name, result in results.items():
        status = "[PASS] PASS" if isinstance(result, dict) and result.get('status') == 'completed' else "[FAIL] FAIL"
        print(f"{test_name:20} : {status}")

    passed_count = sum(1 for r in results.values() if isinstance(r, dict) and r.get('status') == 'completed')
    total_count = len(results)

    print(f"\n总计: {passed_count}/{total_count} 通过")

    if passed_count == total_count:
        print("[PASS] 所有测试通过！")
        return 0
    else:
        print("[FAIL] 部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
