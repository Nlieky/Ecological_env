#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试异常检测子智能体
"""

import json
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

# 项目路径
PROJECT_ROOT = Path("E:/project/Ecological_env")

def test_anomaly_detection():
    """测试异常检测子智能体"""

    print("\n" + "="*60)
    print("测试异常检测子智能体")
    print("="*60)

    # 创建会话目录
    session_dir = PROJECT_ROOT / "sessions" / f"test_anomaly_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    session_dir.mkdir(parents=True, exist_ok=True)
    print(f"会话目录: {session_dir}")

    # 创建任务文件
    task = {
        'task_id': 'test_anomaly_001',
        'task': '检测最近24小时数据中的异常',
        'context': {}
    }
    task_file = session_dir / 'task.json'
    with open(task_file, 'w', encoding='utf-8') as f:
        json.dump(task, f, ensure_ascii=False, indent=2)
    print(f"任务文件: {task_file}")

    # 设置环境变量
    env = os.environ.copy()
    env['SESSION_DIR'] = str(session_dir)
    env['SUBAGENT_NAME'] = 'anomaly-detection'

    # 子智能体脚本
    subagent_script = PROJECT_ROOT / "subagents" / "anomaly-detection-agent" / "run_agent.py"

    if not subagent_script.exists():
        print(f"[ERROR] 子智能体脚本不存在: {subagent_script}")
        return False

    print(f"启动子智能体...")

    # 运行子智能体
    try:
        result = subprocess.run(
            [sys.executable, str(subagent_script)],
            env=env,
            capture_output=True,
            timeout=120,
            encoding='utf-8',
            errors='replace'
        )

        print(f"\n返回码: {result.returncode}")

        # 输出文件检查
        print("\n输出文件:")
        for f in session_dir.iterdir():
            size_kb = f.stat().st_size / 1024
            print(f"  - {f.name} ({size_kb:.1f} KB)")

        # 读取结果
        result_file = session_dir / 'result.json'
        llm_result_file = session_dir / 'llm_result.json'
        anomaly_result_file = session_dir / 'anomaly_result.json'

        if result_file.exists():
            print(f"\n✅ result.json 存在")
            with open(result_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"  Status: {data.get('status')}")
            if 'result' in data and isinstance(data['result'], dict):
                summary = data['result'].get('summary', {})
                print(f"  Anomalies: {summary.get('total_anomalies', 'N/A')}")
        else:
            print(f"\n❌ result.json 不存在")

        if llm_result_file.exists():
            print(f"\n✅ llm_result.json 存在")
            with open(llm_result_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            result_text = data.get('result', '')[:200]
            print(f"  内容预览: {result_text}...")
        else:
            print(f"\n❌ llm_result.json 不存在")

        if anomaly_result_file.exists():
            print(f"\n✅ anomaly_result.json 存在 (脚本输出)")
            with open(anomaly_result_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"  Status: {data.get('status')}")
            if 'result' in data:
                summary = data['result'].get('summary', {})
                print(f"  Anomalies: {summary.get('total_anomalies', 'N/A')}")
        else:
            print(f"\n❌ anomaly_result.json 不存在 (脚本未执行)")

        # 检查 stdout
        if result.stdout:
            print(f"\nStdout (最后500字符):")
            stdout_tail = result.stdout[-500:] if len(result.stdout) > 500 else result.stdout
            print(stdout_tail)

        if result.stderr:
            print(f"\nStderr (最后500字符):")
            stderr_tail = result.stderr[-500:] if len(result.stderr) > 500 else result.stderr
            print(stderr_tail)

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print(f"\n[ERROR] 超时 (120秒)")
        return False
    except Exception as e:
        print(f"\n[ERROR] 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_anomaly_detection()
    sys.exit(0 if success else 1)
