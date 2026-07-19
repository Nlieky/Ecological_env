#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试会话连续性功能"""

import requests
import time
import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

AGENT_URL = "http://localhost:8642"

def test_session_continuity():
    """测试会话连续性"""
    print("=== 测试会话连续性 ===\n")

    session_id = None

    # 第一轮对话
    print("第一轮对话：设置名字")
    resp1 = requests.post(f"{AGENT_URL}/query",
        json={"query": "我叫测试用户，请记住我的名字"},
        timeout=60)

    if resp1.status_code == 200:
        data1 = resp1.json()
        session_id = data1.get("session_id")
        print(f"✅ 第一轮成功")
        print(f"   Session ID: {session_id}")
        print(f"   回复: {data1.get('content', '')[:100]}...")
    else:
        print(f"❌ 第一轮失败: {resp1.status_code}")
        return False

    print()

    # 第二轮对话 - 使用相同session_id
    print("第二轮对话：询问名字（使用相同session_id）")
    time.sleep(1)  # 短暂等待

    resp2 = requests.post(f"{AGENT_URL}/query", json={
        "query": "我叫什么名字？",
        "session_id": session_id
    }, timeout=60)

    if resp2.status_code == 200:
        data2 = resp2.json()
        print(f"✅ 第二轮成功")
        print(f"   Session ID: {data2.get('session_id')}")
        print(f"   回复: {data2.get('content', '')[:200]}...")

        # 检查是否记得名字
        content = data2.get('content', '')
        remembers = any(keyword in content for keyword in ['测试用户', '测试', '用户', '名字'])

        print()
        if remembers:
            print("✅ 会话连续性测试通过 - 主智能体记得之前的对话")
            return True
        else:
            print("❌ 会话连续性测试失败 - 主智能体不记得之前的对话")
            return False
    else:
        print(f"❌ 第二轮失败: {resp2.status_code}")
        return False

def test_session_independence():
    """测试不同session_id的独立性"""
    print("\n=== 测试会话独立性 ===\n")

    # Session A: 设置英文名字
    print("Session A: 设置英文名字")
    resp_a = requests.post(f"{AGENT_URL}/query", json={
        "query": "我的名字是Alice"
    }, timeout=60)

    session_a = resp_a.json().get("session_id") if resp_a.status_code == 200 else None
    print(f"   Session A ID: {session_a}")

    # Session B: 设置中文名字
    print("Session B: 设置中文名字")
    resp_b = requests.post(f"{AGENT_URL}/query", json={
        "query": "我的名字是张三"
    }, timeout=60)

    session_b = resp_b.json().get("session_id") if resp_b.status_code == 200 else None
    print(f"   Session B ID: {session_b}")

    print()

    # 询问Session A的名字
    print("询问Session A的名字")
    resp_a_check = requests.post(f"{AGENT_URL}/query", json={
        "query": "我叫什么名字？",
        "session_id": session_a
    }, timeout=60)

    content_a = resp_a_check.json().get('content', '') if resp_a_check.status_code == 200 else ""
    remembers_a = 'Alice' in content_a
    print(f"   Session A记得: {remembers_a} (记得Alice)")

    # 询问Session B的名字
    print("询问Session B的名字")
    resp_b_check = requests.post(f"{AGENT_URL}/query", json={
        "query": "我叫什么名字？",
        "session_id": session_b
    }, timeout=60)

    content_b = resp_b_check.json().get('content', '') if resp_b_check.status_code == 200 else ""
    remembers_b = '张三' in content_b or '三' in content_b
    print(f"   Session B记得: {remembers_b} (记得张三)")

    print()
    if remembers_a and remembers_b:
        print("✅ 会话独立性测试通过 - 不同session_id保持独立记忆")
        return True
    else:
        print("❌ 会话独立性测试失败")
        return False

if __name__ == "__main__":
    print("会话连续性和独立性测试\n")

    # 测试连续性
    continuity_ok = test_session_continuity()

    # 测试独立性
    independence_ok = test_session_independence()

    print("\n" + "=" * 50)
    if continuity_ok and independence_ok:
        print("✅ 所有测试通过")
        sys.exit(0)
    else:
        print("❌ 部分测试失败")
        sys.exit(1)
