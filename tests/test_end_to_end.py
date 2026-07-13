#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端测试：主智能体调用子智能体

测试流程：
1. multi-dimensional-data-perception-agent → 获取数据
2. 读取数据结果
"""

import json
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

# 项目路径
PROJECT_ROOT = Path("E:/project/Ecological_env")
SUBAGENTS_ROOT = PROJECT_ROOT / "subagents"

# 环境变量
ENV = {
    'HERMES_HOME': '',
    'SESSION_DIR': '',
    'SUBAGENT_NAME': '',
    'LLM_BASE_URL': 'https://api.longcat.chat/openai/v1',
    'LLM_API_KEY': 'ak_28r4a2c7d5f1b8e3c6d0a9b2f4d7e1c3a6b5f8e2d9c7a1b0f',
    'LLM_MODEL': 'LongCat-2.0'
}


def create_session_dir():
    """创建会话目录 - 使用全局 sessions 目录"""
    session_dir = PROJECT_ROOT / "sessions" / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    session_dir.mkdir(parents=True, exist_ok=True)

    # 创建元数据文件（Hermes 框架格式）
    metadata = {
        'created_at': datetime.now().isoformat(),
        'type': 'test',
        'status': 'active'
    }
    metadata_file = session_dir / '_metadata.json'
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    return str(session_dir)


def create_task_file(session_dir, task_id, task_description, context=None):
    """创建任务文件"""
    task = {
        'task_id': task_id,
        'task': task_description,
        'context': context or {}
    }
    task_file = Path(session_dir) / 'task.json'
    with open(task_file, 'w', encoding='utf-8') as f:
        json.dump(task, f, ensure_ascii=False, indent=2)
    return task_file


def call_subagent(subagent_name, task_description, context=None, timeout=300):
    """调用子智能体"""
    print(f"\n{'='*60}")
    print(f"调用子智能体: {subagent_name}")
    print(f"任务: {task_description}")
    print(f"{'='*60}")

    # 创建会话目录
    session_dir = create_session_dir()
    print(f"会话目录: {session_dir}")

    # 创建任务文件
    task_id = f"test_{subagent_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    create_task_file(session_dir, task_id, task_description, context)

    # 设置环境变量
    env = os.environ.copy()
    env['SESSION_DIR'] = session_dir
    env['SUBAGENT_NAME'] = subagent_name
    env.update({k: v for k, v in ENV.items() if v})

    # 子智能体路径
    subagent_dir = SUBAGENTS_ROOT / f"{subagent_name}-agent"
    if not subagent_dir.exists():
        subagent_dir = SUBAGENTS_ROOT / subagent_name

    if not subagent_dir.exists():
        print(f"[ERROR] 子智能体目录不存在: {subagent_dir}")
        return None

    # 运行子智能体
    agent_main = subagent_dir / "agent_main.py"
    if not agent_main.exists():
        # 尝试 run_agent.py
        agent_main = subagent_dir / "run_agent.py"

    if not agent_main.exists():
        print(f"[ERROR] 子智能体入口文件不存在: {agent_main}")
        return None

    print(f"执行脚本: {agent_main}")

    try:
        result = subprocess.run(
            [sys.executable, str(agent_main)],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout,
            cwd=str(subagent_dir),
            env=env
        )

        print(f"返回码: {result.returncode}")

        # 读取结果文件 - 优先使用 result.json（最终结果）
        result_file = Path(session_dir) / 'result.json'
        if result_file.exists():
            with open(result_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        # 兼容旧版本：尝试特定文件名
        result_files = {
            'multi-dimensional-data-perception': 'data_result.json',
            'anomaly-detection': 'anomaly_result.json',
            'rule-reasoning': 'reasoning_result.json',
            'disposition-execution': 'disposition_result.json'
        }

        result_file_name = result_files.get(subagent_name)
        if result_file_name:
            result_file = Path(session_dir) / result_file_name
            if result_file.exists():
                with open(result_file, 'r', encoding='utf-8') as f:
                    return json.load(f)

        # 如果没有结果文件，尝试解析 stdout
        if result.stdout:
            print(f"STDOUT 预览:\n{result.stdout[:500]}...")

        return None

    except subprocess.TimeoutExpired:
        print(f"[ERROR] 超时（{timeout}秒）")
        return None
    except Exception as e:
        print(f"[ERROR] 执行失败: {e}")
        return None


def main():
    """主测试函数"""
    print("="*60)
    print("端到端测试：主智能体调用子智能体")
    print("="*60)

    # 测试1：数据获取
    print("\n【测试1】数据获取")
    data_result = call_subagent(
        "multi-dimensional-data-perception",
        "获取最近24小时的进水和出水数据，包括 pH、COD、TN、NH3-N、TP 等指标"
    )

    if data_result:
        print(f"[OK] 数据获取成功")
        print(f"   状态: {data_result.get('status')}")
        # 新的数据结构：result.influent 是数组
        influent = data_result.get('result', {}).get('influent', [])
        effluent = data_result.get('result', {}).get('effluent', [])
        print(f"   进水记录: {len(influent) if isinstance(influent, list) else 0}")
        print(f"   出水记录: {len(effluent) if isinstance(effluent, list) else 0}")

        # 测试2：异常检测（使用获取的数据）
        print("\n【测试2】异常检测")
        anomaly_result = call_subagent(
            "anomaly-detection",
            "检测最近24小时的异常数据",
            context={'data': data_result.get('data', {})}
        )

        if anomaly_result:
            print(f"[OK] 异常检测成功")
            print(f"   状态: {anomaly_result.get('status')}")
            # 新的数据结构：result.result.summary.total_anomalies
            summary = anomaly_result.get('result', {}).get('summary', {})
            print(f"   异常数量: {summary.get('total_anomalies', 0)}")
            print(f"   异常类型: {summary.get('by_type', {})}")
    else:
        print("[ERROR] 数据获取失败，跳过后续测试")

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)


if __name__ == '__main__':
    main()
