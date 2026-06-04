#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的CLI查询工具

允许用户在终端直接输入自然语言查询，
通过Flask API发送请求并显示结果。
"""

import requests
import json
import sys

def send_query(query: str) -> dict:
    """发送查询到API"""
    try:
        response = requests.post(
            "http://localhost:5001/api/query",
            json={"query": query},
            timeout=300  # 增加到5分钟，因为LLM调用和子智能体执行需要时间
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        print("错误: 无法连接到查询接口")
        print("请先启动: python middleware/query_interface.py")
        return None
    except Exception as e:
        print(f"错误: {e}")
        return None


def format_result(result: dict):
    """格式化显示结果"""
    if not result:
        return

    print(f"\n查询: {result.get('query', 'N/A')}")

    intent = result.get('intent', {})
    if intent:
        print(f"\n[解析意图]")
        print(f"  时间范围: {intent.get('time_range', {})}")
        print(f"  指标: {intent.get('indicators', [])}")
        print(f"  分析类型: {intent.get('analysis_types', [])}")
        print(f"  数据源: {intent.get('data_source', 'both')}")

    data_info = result.get('data_info', {})
    if data_info:
        print(f"\n[数据信息]")
        print(f"  进水: {data_info.get('influent_count', 0)} 条")
        print(f"  出水: {data_info.get('effluent_count', 0)} 条")

    summary = result.get('summary')
    if summary:
        print(f"\n[分析报告]")
        print(f"  {summary}")

    analysis = result.get('analysis', {})
    if analysis.get('perception'):
        print(f"\n[数据感知] 已完成")
    if analysis.get('anomaly'):
        print(f"[异常检测] 已完成")


def main():
    """主循环"""
    print("=" * 60)
    print("  废水监测系统 - 自然语言查询")
    print("=" * 60)
    print("\n输入查询，或输入 'quit' 退出")
    print("示例: 过去24小时，ph和COD之间的相关性")
    print()

    while True:
        try:
            query = input("查询> ").strip()

            if not query:
                continue

            if query.lower() in ['quit', 'exit', 'q', '退出']:
                print("再见！")
                break

            result = send_query(query)
            format_result(result)
            print("-" * 60)

        except KeyboardInterrupt:
            print("\n\n程序已中断")
            break
        except Exception as e:
            print(f"错误: {e}")


if __name__ == '__main__':
    main()