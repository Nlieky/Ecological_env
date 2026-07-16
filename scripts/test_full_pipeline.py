#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整流程测试 - 测试主智能体调用所有子智能体的完整流程

流程：
1. 多维数据感知子智能体 - 获取监测数据
2. 异常检测子智能体 - 检测异常模式
3. 规则推理子智能体 - 违规判定
4. 预警处置子智能体 - 生成预警工单
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 项目路径
PROJECT_ROOT = Path("E:/project/Ecological_env")
SESSION_DIR = PROJECT_ROOT / "sessions" / f"test_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
SESSION_DIR.mkdir(parents=True, exist_ok=True)

# 设置环境变量
import os
os.environ['SESSION_DIR'] = str(SESSION_DIR)

print("=" * 70)
print("完整流程测试")
print("=" * 70)
print(f"会话目录: {SESSION_DIR}")
print()

# 测试步骤
steps = [
    {
        "name": "1. 多维数据感知子智能体",
        "script": "subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/get_data.py",
        "args": ["--hours", "24"],
        "expected_output": "data_result.json"
    },
    {
        "name": "2. 异常检测子智能体",
        "script": "subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/run_anomaly_detection_simple.py",
        "args": [],
        "expected_output": "anomaly_result.json"
    },
    {
        "name": "3. 规则推理子智能体",
        "script": "subagents/rule-reasoning-agent/skills/rule-reasoning-core/scripts/run_rule_reasoning.py",
        "args": ["--session-dir", str(SESSION_DIR)],
        "expected_output": "rule_reasoning_result.json"
    },
    {
        "name": "4. 预警处置子智能体",
        "script": "subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/run_disposition.py",
        "args": ["--session-dir", str(SESSION_DIR)],
        "expected_output": "disposition_result.json"
    }
]

# 结果存储
results = {}

# 执行每个步骤
for i, step in enumerate(steps, 1):
    print(f"\n{'=' * 70}")
    print(f"步骤 {i}: {step['name']}")
    print(f"{'=' * 70}")
    print(f"脚本: {step['script']}")
    print(f"参数: {step['args']}")
    print()

    script_path = PROJECT_ROOT / step['script']
    if not script_path.exists():
        print(f"[X] 脚本不存在: {script_path}")
        results[step['name']] = {"status": "skipped", "reason": "脚本不存在"}
        continue

    try:
        # 执行脚本
        cmd = [sys.executable, str(script_path)] + step['args']
        print(f"执行命令: {' '.join(cmd)}")
        print()

        result = subprocess.run(
            cmd,
            cwd=str(script_path.parent),
            capture_output=True,
            text=True,
            timeout=60
        )

        # 打印输出
        if result.stdout:
            print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)

        if result.returncode != 0:
            print(f"[X] 执行失败 (返回码: {result.returncode})")
            if result.stderr:
                print(f"错误输出: {result.stderr[-500:]}")
            results[step['name']] = {"status": "failed", "returncode": result.returncode}
            continue

        # 检查输出文件
        output_file = SESSION_DIR / step['expected_output']
        # 也检查子智能体目录
        alt_output_file = PROJECT_ROOT / step['script'].split('/')[0] / step['expected_output']

        found_file = None
        if output_file.exists():
            found_file = output_file
        elif alt_output_file.exists():
            found_file = alt_output_file

        if found_file:
            print(f"\n[OK] 输出文件存在: {found_file}")
            try:
                with open(found_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 提取关键信息
                status = data.get('status', 'unknown')
                print(f"状态: {status}")

                # 根据不同子智能体提取不同信息
                if 'anomaly' in step['name']:
                    anomalies = data.get('result', {}).get('anomalies', [])
                    print(f"异常数量: {len(anomalies)}")
                elif 'rule' in step['name']:
                    has_violation = data.get('result', {}).get('has_violation', False)
                    suspicion = data.get('result', {}).get('suspicion_level_cn', '')
                    print(f"违规判定: {'是' if has_violation else '否'}")
                    print(f"嫌疑等级: {suspicion}")
                elif 'disposition' in step['name']:
                    alert = data.get('result', {}).get('alert', {})
                    print(f"预警级别: {alert.get('level_cn', '')}")
                    print(f"工单编号: {data.get('result', {}).get('work_order', {}).get('id', '')}")

                results[step['name']] = {"status": "success", "output_file": str(found_file)}

            except Exception as e:
                print(f"[X] 读取输出文件失败: {e}")
                results[step['name']] = {"status": "error", "error": str(e)}
        else:
            print(f"[X] 输出文件不存在: {output_file}")
            results[step['name']] = {"status": "no_output", "expected": str(output_file)}

    except subprocess.TimeoutExpired:
        print(f"[X] 执行超时")
        results[step['name']] = {"status": "timeout"}
    except Exception as e:
        print(f"[X] 执行异常: {e}")
        results[step['name']] = {"status": "error", "error": str(e)}

# 打印总结
print(f"\n{'=' * 70}")
print("测试总结")
print(f"{'=' * 70}")

success_count = sum(1 for r in results.values() if r.get('status') == 'success')
total_count = len(results)

for step_name, result in results.items():
    status = result.get('status', 'unknown')
    if status == 'success':
        print(f"[OK] {step_name}: 成功")
    else:
        print(f"[X] {step_name}: {status}")

print(f"\n通过率: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
print(f"会话目录: {SESSION_DIR}")

# 保存测试结果
test_result_file = SESSION_DIR / "test_result.json"
with open(test_result_file, 'w', encoding='utf-8') as f:
    json.dump({
        "timestamp": datetime.now().isoformat(),
        "session_dir": str(SESSION_DIR),
        "results": results,
        "summary": {
            "total": total_count,
            "success": success_count,
            "failed": total_count - success_count,
            "pass_rate": success_count / total_count
        }
    }, f, ensure_ascii=False, indent=2)

print(f"\n测试结果已保存到: {test_result_file}")

# 返回退出码
sys.exit(0 if success_count == total_count else 1)
