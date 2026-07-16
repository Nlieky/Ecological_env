#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试LLM API响应速度"""

import time
import os
from pathlib import Path
from openai import OpenAI

# 读取.env文件
env_file = Path(__file__).parent.parent / '.env'
if env_file.exists():
    with open(env_file, encoding='utf-8') as f:
        for line in f:
            if line.startswith('LLM_') and '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

client = OpenAI(
    base_url=os.environ.get('LLM_BASE_URL'),
    api_key=os.environ.get('LLM_API_KEY')
)

print("=" * 60)
print("本地Qwen模型 API响应速度测试")
print("=" * 60)
print(f"Base URL: {os.environ.get('LLM_BASE_URL')}")
print(f"Model: {os.environ.get('LLM_MODEL')}")
print(f"API Key: {os.environ.get('LLM_API_KEY')[:10]}...")
print()

# 测试1: 简单查询
print("测试1: 简单查询（max_tokens=50）")
start = time.time()
response = client.chat.completions.create(
    model=os.environ.get('LLM_MODEL'),
    messages=[{'role': 'user', 'content': '你好，请简短回答'}],
    max_tokens=50
)
elapsed = time.time() - start
print(f"耗时: {elapsed:.2f}秒")
print(f"响应对象类型: {type(response)}")
print(f"响应属性: {dir(response)}")
if hasattr(response, 'choices') and response.choices:
    choice = response.choices[0]
    print(f"Finish reason: {choice.finish_reason}")

    # 尝试不同的内容字段
    content = None
    if hasattr(choice.message, 'content') and choice.message.content:
        content = choice.message.content
    elif hasattr(choice, 'message') and hasattr(choice.message, 'reasoning_content'):
        content = choice.message.reasoning_content
    elif hasattr(choice, 'delta') and hasattr(choice.delta, 'reasoning_content'):
        content = choice.delta.reasoning_content

    if content:
        print(f"响应内容: {content[:200]}{'...' if len(content) > 200 else ''}")
    else:
        print(f"完整响应: {choice}")
else:
    print(f"完整响应: {response}")
print()

# 测试2: 中等查询
print("测试2: 中等查询（max_tokens=500）")
start = time.time()
response = client.chat.completions.create(
    model=os.environ.get('LLM_MODEL'),
    messages=[{'role': 'user', 'content': '请简要介绍废水监测的4种违规类型'}],
    max_tokens=500
)
elapsed = time.time() - start
print(f"耗时: {elapsed:.2f}秒")
if response.choices:
    choice = response.choices[0]
    content = choice.message.content or getattr(choice.message, 'reasoning_content', '')
    if content:
        print(f"响应长度: {len(content)} 字符")
        print(f"响应预览: {content[:150]}...")
print()

# 测试3: 带上下文的查询
context = "你是废水监测系统的AI助手，负责分析监测数据并调用子智能体。"
print("测试3: 带上下文的查询")
start = time.time()
response = client.chat.completions.create(
    model=os.environ.get('LLM_MODEL'),
    messages=[
        {'role': 'system', 'content': context},
        {'role': 'user', 'content': '最近24小时出水COD异常吗？'}
    ],
    max_tokens=500
)
elapsed = time.time() - start
print(f"耗时: {elapsed:.2f}秒")
if response.choices:
    choice = response.choices[0]
    content = choice.message.content or getattr(choice.message, 'reasoning_content', '')
    if content:
        print(f"响应: {content[:200]}...")

print()
print("=" * 60)
print("测试完成")
print("=" * 60)
