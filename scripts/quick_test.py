#!/usr/bin/env python
"""快速测试 Agent 查询功能"""

import requests
import json

print("=== Agent 查询功能测试 ===\n")

# 测试 1: 简单对话
print("测试 1: 简单对话（你好）")
try:
    response = requests.post(
        'http://localhost:8642/query',
        json={'query': '你好'}
    )
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 成功!")
        print(f"内容预览: {result.get('content', '')[:100]}...\n")
    else:
        print(f"❌ 失败: {response.text}\n")
except Exception as e:
    print(f"❌ 异常: {e}\n")

# 测试 2: 列出子智能体（测试工具调用）
print("测试 2: 列出子智能体（测试工具调用）")
try:
    response = requests.post(
        'http://localhost:8642/query',
        json={'query': '请使用 list_subagents 工具列出所有可用的子智能体'}
    )
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 成功!")
        content = result.get('content', '')
        print(f"内容预览: {content[:200]}...\n")
    else:
        print(f"❌ 失败: {response.text}\n")
except Exception as e:
    print(f"❌ 异常: {e}\n")

# 测试 3: 调用子智能体
print("测试 3: 调用异常检测子智能体")
try:
    response = requests.post(
        'http://localhost:8642/query',
        json={'query': '请使用 call_subagent 工具调用异常检测子智能体，询问它的职责'}
    )
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 成功!")
        content = result.get('content', '')
        print(f"内容预览: {content[:200]}...\n")
    else:
        print(f"❌ 失败: {response.text}\n")
except Exception as e:
    print(f"❌ 异常: {e}\n")

print("=== 测试完成 ===")
