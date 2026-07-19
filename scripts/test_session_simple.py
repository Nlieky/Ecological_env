#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试会话连续性功能 - 简化版"""

import requests
import time
import json

AGENT_URL = "http://localhost:8642"

def test_session_continuity():
    """测试会话连续性"""
    print("=== 测试会话连续性 ===\n")

    session_id = None

    # 第一轮对话
    print("第一轮对话：设置名字")
    headers = {"Content-Type": "application/json"}
    data1 = {"query": "我叫测试用户，请记住我的名字"}

    resp1 = requests.post(f"{AGENT_URL}/query", json=data1, headers=headers, timeout=60)

    if resp1.status_code == 200:
        result1 = resp1.json()
        session_id = result1.get("session_id")
        print(f"✅ 第一轮成功")
        print(f"   Session ID: {session_id}")
        print(f"   回复预览: {result1.get('content', '')[:80]}...")
    else:
        print(f"❌ 第一轮失败: {resp1.status_code} - {resp1.text}")
        return False

    print()

    # 第二轮对话 - 使用相同session_id
    print("第二轮对话：询问名字（使用相同session_id）")
    time.sleep(1)

    data2 = {"query": "我叫什么名字？"}
    if session_id:
        resp2 = requests.post(
            f"{AGENT_URL}/query",
            json=data2,
            headers=headers,
            params={"session_id": session_id},  # 使用params传递session_id
            timeout=60
        )
    else:
        resp2 = requests.post(f"{AGENT_URL}/query", json=data2, headers=headers, timeout=60)

    if resp2.status_code == 200:
        result2 = resp2.json()
        print(f"✅ 第二轮成功")
        print(f"   Session ID: {result2.get('session_id')}")
        content = result2.get('content', '')
        print(f"   回复: {content[:150]}...")

        # 检查是否记得名字
        remembers = any(keyword in content for keyword in ['测试用户', '测试', '记得', '名字'])

        print()
        if remembers:
            print("✅ 会话连续性测试通过 - 主智能体记得之前的对话")
            return True
        else:
            print("❌ 会话连续性测试失败 - 主智能体不记得之前的对话")
            print(f"   关键词检查失败")
            return False
    else:
        print(f"❌ 第二轮失败: {resp2.status_code} - {resp2.text}")
        return False

if __name__ == "__main__":
    success = test_session_continuity()
    exit(0 if success else 1)
