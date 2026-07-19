#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试重构后的API架构 - 后端转发到Agent服务"""

import requests
import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_backend_query():
    """测试后端查询接口（转发到Agent服务）"""

    print("测试重构后的后端查询接口...")
    print("=" * 60)

    # 测试简单查询
    try:
        response = requests.post(
            'http://localhost:8000/api/query',
            json={'query': '你好'},
            timeout=60
        )

        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("[OK] 查询成功")
            print(f"Session ID: {data.get('session_id')}")
            print(f"内容预览: {data.get('content', '')[:100]}...")
            print(f"Timestamp: {data.get('timestamp')}")
            return True
        else:
            print(f"[FAIL] 查询失败: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"[ERROR] 异常: {type(e).__name__}: {str(e)[:200]}")
        return False


def test_agent_service_direct():
    """直接测试Agent服务"""

    print("")
    print("直接测试Agent服务...")
    print("=" * 60)

    try:
        response = requests.post(
            'http://localhost:8642/query',
            json={'query': '你好'},
            timeout=60
        )

        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("[OK] Agent服务正常")
            print(f"内容预览: {data.get('content', '')[:100]}...")
            return True
        else:
            print(f"[FAIL] Agent服务失败: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"[ERROR] 异常: {type(e).__name__}: {str(e)[:200]}")
        return False


if __name__ == "__main__":
    print("重构架构测试")
    print("=" * 60)

    # 先测试Agent服务
    agent_ok = test_agent_service_direct()

    # 再测试后端转发
    backend_ok = test_backend_query()

    print("")
    print("=" * 60)
    if agent_ok and backend_ok:
        print("[OK] 所有测试通过！重构架构正常工作")
        sys.exit(0)
    else:
        print("[FAIL] 测试失败，需要检查配置")
        sys.exit(1)
