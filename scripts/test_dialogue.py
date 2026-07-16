#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试主智能体对话功能
"""

import sys
import os
from pathlib import Path

# 确保项目根目录在 Python 路径
PROJECT_ROOT = Path("E:/project/Ecological_env").resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 加载 .env 文件
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    with open(env_file, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

# 设置环境变量
os.environ['PROJECT_ROOT'] = str(PROJECT_ROOT)

print("=" * 60)
print("测试主智能体对话功能")
print("=" * 60)
print(f"项目根目录: {PROJECT_ROOT}")
print()

# 检查身份文件
soul_md = PROJECT_ROOT / "workspace" / "SOUL.md"
print(f"[1] 检查身份文件: {soul_md}")
print(f"    存在: {soul_md.exists()}")
if soul_md.exists():
    print(f"    大小: {soul_md.stat().st_size} 字节")

# 检查环境变量
print()
print("[2] 检查环境变量:")
print(f"    LLM_BASE_URL: {os.environ.get('LLM_BASE_URL', '未设置')}")
print(f"    LLM_MODEL: {os.environ.get('LLM_MODEL', '未设置')}")
print(f"    LLM_API_KEY: {'已设置' if os.environ.get('LLM_API_KEY') else '未设置'}")

# 尝试导入 AIAgent
print()
print("[3] 尝试导入 Hermes AIAgent...")
try:
    from run_agent import AIAgent
    print("    ✅ AIAgent 导入成功")
except ImportError as e:
    print(f"    ❌ AIAgent 导入失败: {e}")
    sys.exit(1)

# 测试简单对话
print()
print("[4] 测试简单对话...")
print("    提示: 这将直接调用 LLM API，可能需要一些时间")
print()

try:
    agent = AIAgent(
        base_url=os.environ.get("LLM_BASE_URL", "https://api.longcat.chat/openai/v1"),
        api_key=os.environ.get("LLM_API_KEY", ""),
        model=os.environ.get("LLM_MODEL", "LongCat-2.0"),
        provider="custom",
        load_soul_identity=True,
        skip_context_files=False,
        max_iterations=5,
        quiet_mode=False,
    )

    test_query = "你好，请介绍一下你自己。"
    print(f"    发送查询: {test_query}")
    print()

    response = agent.run_conversation(
        user_message=test_query,
        conversation_history=None,
    )

    print()
    print("=" * 60)
    print("响应:")
    print("=" * 60)
    if isinstance(response, dict):
        print(response.get('final_response', str(response)))
    else:
        print(response)
    print("=" * 60)

except Exception as e:
    print(f"    ❌ 对话失败: {e}")
    import traceback
    traceback.print_exc()

print()
print("测试完成")
