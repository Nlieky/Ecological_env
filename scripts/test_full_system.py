#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""完整系统测试 - 验证重构后的架构功能"""

import requests
import json
import time
import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 服务配置
BACKEND_URL = "http://localhost:8000"
AGENT_URL = "http://localhost:8642"

def print_section(title):
    """打印测试区块标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_test(name, result, details=""):
    """打印测试结果"""
    status = "[PASS]" if result else "[FAIL]"
    print(f"{status} {name}")
    if details:
        print(f"     {details}")

def test_service_health():
    """测试服务健康状态"""
    print_section("1. 服务健康检查")

    results = []

    # Agent服务
    try:
        resp = requests.get(f"{AGENT_URL}/health", timeout=5)
        data = resp.json()
        is_healthy = data.get("status") == "healthy" and data.get("agent_initialized") == True
        print_test("Agent服务健康", is_healthy, f"status={data.get('status')}, agent_init={data.get('agent_initialized')}")
        results.append(is_healthy)
    except Exception as e:
        print_test("Agent服务健康", False, str(e))
        results.append(False)

    # 后端API
    try:
        resp = requests.get(f"{BACKEND_URL}/api/health", timeout=5)
        data = resp.json()
        is_healthy = data.get("status") == "healthy"
        print_test("后端API健康", is_healthy, f"status={data.get('status')}, version={data.get('version')}")
        results.append(is_healthy)
    except Exception as e:
        print_test("后端API健康", False, str(e))
        results.append(False)

    return all(results)

def test_simple_query():
    """测试简单查询"""
    print_section("2. 简单查询测试")

    test_cases = [
        {"query": "你好", "expect_content": True},
        {"query": "你是谁", "expect_content": True},
        {"query": "介绍一下你的能力", "expect_content": True}
    ]

    results = []

    for i, case in enumerate(test_cases, 1):
        try:
            print(f"\n测试 {i}: {case['query'][:30]}...")

            start = time.time()
            resp = requests.post(
                f"{BACKEND_URL}/api/query",
                json={"query": case["query"]},
                timeout=120
            )
            elapsed = time.time() - start

            if resp.status_code == 200:
                data = resp.json()
                has_content = bool(data.get("content") and len(data.get("content", "")) > 10)

                print_test(f"查询 {i}", has_content,
                          f"状态码={resp.status_code}, 耗时={elapsed:.2f}s, 内容长度={len(data.get('content', ''))}")

                if has_content:
                    print(f"     回复预览: {data.get('content', '')[:80]}...")

                results.append(has_content)
            else:
                print_test(f"查询 {i}", False, f"状态码={resp.status_code}")
                results.append(False)

        except Exception as e:
            print_test(f"查询 {i}", False, str(e))
            results.append(False)

    return all(results)

def test_complex_query():
    """测试复杂查询（可能涉及子智能体调用）"""
    print_section("3. 复杂查询测试（子智能体调用）")

    # 这些查询需要主智能体调用子智能体
    complex_queries = [
        "帮我查看最近的监测数据",
        "检查是否有异常情况",
        "今天有什么违规情况"
    ]

    results = []

    for i, query in enumerate(complex_queries, 1):
        try:
            print(f"\n复杂查询 {i}: {query[:40]}...")

            start = time.time()
            resp = requests.post(
                f"{BACKEND_URL}/api/query",
                json={"query": query},
                timeout=180  # 复杂查询需要更长时间
            )
            elapsed = time.time() - start

            if resp.status_code == 200:
                data = resp.json()
                has_response = bool(data.get("content") and len(data.get("content", "")) > 20)

                print_test(f"复杂查询 {i}", has_response,
                          f"状态码={resp.status_code}, 耗时={elapsed:.2f}s")

                if has_response:
                    content = data.get("content", "")
                    print(f"     回复长度: {len(content)} 字符")
                    print(f"     回复预览: {content[:100]}...")

                results.append(has_response)
            else:
                print_test(f"复杂查询 {i}", False, f"状态码={resp.status_code}")
                results.append(False)

        except requests.Timeout:
            print_test(f"复杂查询 {i}", False, "请求超时（可能需要更长时间）")
            results.append(False)
        except Exception as e:
            print_test(f"复杂查询 {i}", False, str(e))
            results.append(False)

    return all(results)

def test_session_continuity():
    """测试会话连续性"""
    print_section("4. 会话连续性测试")

    try:
        # 第一次查询，获取session_id
        print("\n第一次查询...")
        resp1 = requests.post(
            f"{BACKEND_URL}/api/query",
            json={"query": "我叫测试用户"},
            timeout=60
        )

        if resp1.status_code != 200:
            print_test("会话连续性", False, "第一次查询失败")
            return False

        session_id = resp1.json().get("session_id")
        print(f"     获得Session ID: {session_id}")

        # 第二次查询，使用相同session
        print("第二次查询（使用相同session）...")
        resp2 = requests.post(
            f"{BACKEND_URL}/api/query",
            json={"query": "我叫什么名字？", "session_id": session_id},
            timeout=60
        )

        if resp2.status_code != 200:
            print_test("会话连续性", False, "第二次查询失败")
            return False

        content = resp2.json().get("content", "")
        # 检查是否记得之前的对话内容
        remembers = "测试用户" in content or "叫" in content

        print_test("会话连续性", remembers, f"是否记得上下文: {remembers}")
        print(f"     回复: {content[:100]}...")

        return remembers

    except Exception as e:
        print_test("会话连续性", False, str(e))
        return False

def test_agent_capabilities():
    """测试Agent能力说明接口"""
    print_section("5. Agent能力说明接口")

    try:
        resp = requests.get(f"{BACKEND_URL}/api/query/capabilities", timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            has_master = "master_agent" in data
            has_sub_agents = "sub_agents" in data
            has_decision_tree = "decision_tree" in data

            print_test("能力接口 - 主智能体", has_master)
            print_test("能力接口 - 子智能体列表", has_sub_agents)
            print_test("能力接口 - 决策树", has_decision_tree)

            if has_sub_agents:
                agents = data.get("sub_agents", [])
                print(f"     子智能体数量: {len(agents)}")
                for agent in agents:
                    print(f"     - {agent.get('name')}: {agent.get('role')}")

            return has_master and has_sub_agents
        else:
            print_test("能力接口", False, f"状态码={resp.status_code}")
            return False

    except Exception as e:
        print_test("能力接口", False, str(e))
        return False

def main():
    """主测试流程"""
    print("\n" + "=" * 60)
    print("  废水监测系统 - 完整功能测试")
    print("=" * 60)

    test_results = []

    # 执行各项测试
    test_results.append(("服务健康", test_service_health()))
    test_results.append(("简单查询", test_simple_query()))
    test_results.append(("复杂查询", test_complex_query()))
    test_results.append(("会话连续性", test_session_continuity()))
    test_results.append(("能力接口", test_agent_capabilities()))

    # 汇总结果
    print_section("测试结果汇总")

    for name, result in test_results:
        print_test(name, result)

    passed = sum(1 for _, r in test_results if r)
    total = len(test_results)

    print("\n" + "=" * 60)
    print(f"  总计: {passed}/{total} 测试组通过")
    print("=" * 60)

    if passed == total:
        print("\n[OK] 所有测试通过！系统运行正常。")
        return 0
    else:
        print(f"\n[WARN] {total - passed} 个测试组失败，请检查。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
