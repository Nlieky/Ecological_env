#!/usr/bin/env python
"""测试 Agent API 服务的简单脚本"""

import requests
import json

def test_query():
    """测试查询接口"""
    try:
        response = requests.post(
            'http://localhost:8642/query',
            json={'query': '你是谁？请简单介绍自己。'}
        )

        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"成功!")
            print(f"会话ID: {result.get('session_id')}")
            print(f"时间戳: {result.get('timestamp')}")
            print(f"内容: {result.get('content')[:200]}...")
            return True
        else:
            print(f"失败: {response.text}")
            return False

    except Exception as e:
        print(f"请求异常: {e}")
        return False

def test_health():
    """测试健康检查接口"""
    try:
        response = requests.get('http://localhost:8642/health')
        print(f"健康检查: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"健康检查失败: {e}")
        return False

if __name__ == "__main__":
    print("=== Agent API 测试 ===\n")

    print("1. 健康检查...")
    test_health()

    print("\n2. 查询测试...")
    test_query()
