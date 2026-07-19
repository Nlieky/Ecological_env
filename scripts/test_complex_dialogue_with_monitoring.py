#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""复杂对话测试 - 完整流程监控"""

import requests
import time
import json
import sys
import io
from datetime import datetime

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

AGENT_URL = "http://localhost:8642"
BACKEND_URL = "http://localhost:8000"

def print_section(title):
    """打印分节标题"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)

def monitor_request(url, method, endpoint, data=None, params=None):
    """监控HTTP请求"""
    start_time = time.time()
    try:
        if method == "POST":
            response = requests.post(f"{url}{endpoint}", json=data, params=params, timeout=180)
        else:
            response = requests.get(f"{url}{endpoint}", params=params, timeout=180)

        elapsed = time.time() - start_time

        return {
            "success": response.status_code == 200,
            "status_code": response.status_code,
            "elapsed": elapsed,
            "response": response.json() if response.status_code == 200 else None,
            "error": None if response.status_code == 200 else response.text
        }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "success": False,
            "status_code": None,
            "elapsed": elapsed,
            "response": None,
            "error": str(e)
        }

def check_system_logs(session_id):
    """检查系统日志"""
    try:
        # 查询API调用日志
        response = requests.get(
            f"{BACKEND_URL}/api/logs",
            params={"log_type": "api", "limit": 5},
            timeout=10
        )

        if response.status_code == 200:
            logs = response.json().get("data", [])
            return logs
        return []
    except Exception as e:
        print(f"⚠️ 获取日志失败: {e}")
        return []

def test_complex_dialogue():
    """测试复杂对话流程"""

    print_section("复杂对话测试 - 完整流程监控")

    session_id = None
    conversation_flow = []

    # ===== 第一轮：身份设定 =====
    print_section("第一轮：身份设定")

    turn1_start = time.time()
    result1 = monitor_request(
        AGENT_URL, "POST", "/query",
        data={"query": "我是环保局监察人员，正在检查某企业的废水排放情况"}
    )
    turn1_elapsed = time.time() - turn1_start

    if result1["success"]:
        session_id = result1["response"].get("session_id")
        conversation_flow.append({
            "turn": 1,
            "query": "身份设定",
            "elapsed": turn1_elapsed,
            "session_id": session_id,
            "response_length": len(result1["response"].get("content", ""))
        })

        print(f"✅ 第一轮完成 ({turn1_elapsed:.2f}秒)")
        print(f"   Session ID: {session_id}")
        print(f"   回复长度: {len(result1['response'].get('content', ''))} 字符")
    else:
        print(f"❌ 第一轮失败: {result1.get('error')}")
        return

    time.sleep(1)

    # ===== 第二轮：复杂查询 =====
    print_section("第二轮：复杂查询（涉及多个子智能体）")

    turn2_start = time.time()
    result2 = monitor_request(
        AGENT_URL, "POST", "/query",
        data={
            "query": "请帮我分析最近一周的进出水监测数据，检测异常情况，并根据相关法规判定是否有违规行为，最后给出处置建议",
            "session_id": session_id
        }
    )
    turn2_elapsed = time.time() - turn2_start

    if result2["success"]:
        conversation_flow.append({
            "turn": 2,
            "query": "复杂查询（多子智能体）",
            "elapsed": turn2_elapsed,
            "session_id": result2["response"].get("session_id"),
            "response_length": len(result2["response"].get("content", ""))
        })

        print(f"✅ 第二轮完成 ({turn2_elapsed:.2f}秒)")
        print(f"   回复长度: {len(result2['response'].get('content', ''))} 字符")
        print(f"   回复预览: {result2['response'].get('content', '')[:100]}...")
    else:
        print(f"❌ 第二轮失败: {result2.get('error')}")
        return

    time.sleep(1)

    # ===== 第三轮：上下文测试 =====
    print_section("第三轮：上下文记忆测试")

    turn3_start = time.time()
    result3 = monitor_request(
        AGENT_URL, "POST", "/query",
        data={
            "query": "根据刚才的分析，你认为最紧迫的问题是什么？",
            "session_id": session_id
        }
    )
    turn3_elapsed = time.time() - turn3_start

    if result3["success"]:
        conversation_flow.append({
            "turn": 3,
            "query": "上下文记忆测试",
            "elapsed": turn3_elapsed,
            "session_id": result3["response"].get("session_id"),
            "response_length": len(result3["response"].get("content", ""))
        })

        content = result3["response"].get("content", "")
        has_memory = any(keyword in content for keyword in ["刚才", "之前", "分析", "数据"])

        print(f"✅ 第三轮完成 ({turn3_elapsed:.2f}秒)")
        print(f"   记忆保持: {'✅ 是' if has_memory else '❌ 否'}")
        print(f"   回复预览: {content[:100]}...")
    else:
        print(f"❌ 第三轮失败: {result3.get('error')}")
        return

    # ===== 流程分析 =====
    print_section("流程分析")

    total_elapsed = sum(turn["elapsed"] for turn in conversation_flow)

    print(f"总对话轮数: {len(conversation_flow)}")
    print(f"总耗时: {total_elapsed:.2f}秒")
    print(f"平均耗时: {total_elapsed/len(conversation_flow):.2f}秒/轮")

    print("\n各轮详情:")
    for turn in conversation_flow:
        print(f"  第{turn['turn']}轮: {turn['query']} - {turn['elapsed']:.2f}秒, {turn['response_length']}字符")

    # ===== 检查系统日志 =====
    print_section("系统日志检查")

    logs = check_system_logs(session_id)
    if logs:
        print(f"最近的API调用记录:")
        for i, log in enumerate(logs[:3], 1):
            latency = log.get('latency_ms')
            latency_str = f"{latency/1000:.2f}秒" if latency else "N/A"
            print(f"  {i}. 时间: {log.get('timestamp')}, 延迟: {latency_str}")
    else:
        print("⚠️ 未找到相关日志")

    # ===== 性能评估 =====
    print_section("性能评估")

    performance_checks = [
        ("会话连续性", session_id is not None),
        ("响应速度", total_elapsed/len(conversation_flow) < 30),
        ("复杂查询处理", turn2_elapsed < 60),
        ("上下文记忆", has_memory)
    ]

    all_passed = True
    for check_name, passed in performance_checks:
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}")
        if not passed:
            all_passed = False

    print(f"\n{'='*60}")
    if all_passed:
        print("✅ 所有检查通过 - 智能体系统运行正常")
    else:
        print("⚠️ 部分检查未通过 - 需要进一步优化")
    print('='*60)

    return {
        "conversation_flow": conversation_flow,
        "performance_checks": performance_checks,
        "all_passed": all_passed
    }

if __name__ == "__main__":
    result = test_complex_dialogue()
    exit(0 if result.get("all_passed") else 1)
