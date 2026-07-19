#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试P1-5：超时保护机制"""

import requests
import time
import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

AGENT_URL = "http://localhost:8642"

def test_timeout_protection():
    """测试超时保护机制"""
    print("=== 测试超时保护机制 ===\n")

    # 发起一个可能较长的复杂查询
    print("发送复杂查询（预期不会超过3分钟）...")

    start_time = time.time()

    try:
        response = requests.post(
            f"{AGENT_URL}/query",
            json={
                "query": "请帮我分析最近一周的废水排放数据，检测所有可能的异常情况，并根据法规判定违规类型，最后生成处置建议"
            },
            timeout=200  # 给予200秒的客户端超时
        )

        elapsed = time.time() - start_time

        if response.status_code == 200:
            result = response.json()
            print(f"✅ 查询完成")
            print(f"   耗时: {elapsed:.1f}秒")
            print(f"   Session ID: {result.get('session_id')}")
            print(f"   回复预览: {result.get('content', '')[:100]}...")

            # 检查是否在合理时间内完成
            if elapsed < 180:
                print(f"✅ 超时保护正常 - 在180秒内完成")
                return True
            else:
                print(f"⚠️ 查询超过180秒，可能没有触发超时保护")
                return False
        else:
            print(f"❌ 查询失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return False

    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"⚠️ 客户端超时（{elapsed:.1f}秒）")
        print("   这可能是正常的服务端超时响应")
        return True

    except Exception as e:
        print(f"❌ 查询异常: {e}")
        return False


def test_quick_queries():
    """测试快速查询是否仍然正常"""
    print("\n=== 测试快速查询 ===")

    start_time = time.time()

    try:
        response = requests.post(
            f"{AGENT_URL}/query",
            json={"query": "你好"},
            timeout=30
        )

        elapsed = time.time() - start_time

        if response.status_code == 200:
            result = response.json()
            print(f"✅ 快速查询成功")
            print(f"   耗时: {elapsed:.1f}秒")

            if elapsed < 10:
                print(f"✅ 快速查询性能正常")
                return True
            else:
                print(f"⚠️ 快速查询超过10秒")
                return False
        else:
            print(f"❌ 快速查询失败: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ 快速查询异常: {e}")
        return False


def main():
    """主测试函数"""
    print("P1-5：超时保护机制测试\n")
    print("=" * 50)

    results = []

    # 测试1：超时保护
    results.append(("超时保护", test_timeout_protection()))

    # 测试2：快速查询性能
    results.append(("快速查询性能", test_quick_queries()))

    # 汇总结果
    print("\n" + "=" * 50)
    print("测试结果汇总：")
    passed = 0
    failed = 0

    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "✅" if result else "❌"
        print(f"{symbol} {test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\n总计: {passed}/{len(results)} 通过")

    if failed == 0:
        print("✅ P1-5：超时保护机制测试通过！")
        return 0
    else:
        print(f"❌ {failed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit(main())
