"""
子智能体上下文文件加载验证脚本

运行此脚本验证子智能体是否能正确加载自己的上下文文件。
"""

import os
import sys
import json
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置环境变量（如果需要）
os.environ.setdefault('MODEL', 'ctgu-vlm')
os.environ.setdefault('BASE_URL', 'http://172.16.12.41:30000/v1')

def main():
    print("=" * 60)
    print("子智能体上下文文件加载验证")
    print("=" * 60)

    # 导入 call_subagent
    try:
        from workspace.skills.orchestrator_core.scripts.call_subagent import call_subagent
        print("✓ call_subagent 导入成功")
    except ImportError as e:
        print(f"✗ 导入 call_subagent 失败: {e}")
        return

    # 测试调用异常检测子智能体
    print("\n[测试] 调用 anomaly-detection 子智能体...")
    print("-" * 60)

    result = call_subagent(
        "anomaly-detection",
        "简述你的身份和能力。不要超过50字。"
    )

    print("\n[结果]")
    print("-" * 60)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # 分析结果
    print("\n[分析]")
    print("-" * 60)

    if result.get('status') == 'completed':
        response = result.get('result', {}).get('response', '')
        print(f"✓ 子智能体执行成功")

        # 检查响应是否包含异常检测相关内容
        keywords = ['异常检测', 'anomaly', 'Anomaly Detection', '算子', 'operator']
        found_keywords = [kw for kw in keywords if kw.lower() in response.lower()]

        if found_keywords:
            print(f"✓ 响应包含专业关键词: {found_keywords}")
        else:
            print(f"⚠ 响应未包含预期的专业关键词")
            print(f"响应内容: {response[:200]}...")
    else:
        print(f"✗ 子智能体执行失败: {result.get('error')}")

    print("\n" + "=" * 60)
    print("验证完成")
    print("=" * 60)
    print("\n请检查上方的 [DEBUG] 输出，确认：")
    print("1. cwd 是否正确设置为子智能体目录")
    print("2. 上下文文件（AGENTS.md、SOUL.md 等）是否存在")
    print("3. 系统提示词是否包含子智能体的专业内容")

if __name__ == "__main__":
    main()
