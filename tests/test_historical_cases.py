#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试历史案例保存功能
"""

import json
import sys
from pathlib import Path

# 项目路径
PROJECT_ROOT = Path("E:/project/Ecological_env")
HISTORICAL_CASES_FILE = PROJECT_ROOT / "shared" / "knowledge" / "violation_patterns" / "historical_cases.json"


def test_historical_cases_save():
    """测试保存历史案例"""
    print("="*60)
    print("测试：历史案例保存功能")
    print("="*60)

    # 读取当前历史案例库
    print(f"\n[1] 读取历史案例库文件: {HISTORICAL_CASES_FILE}")
    if not HISTORICAL_CASES_FILE.exists():
        print("[ERROR] 历史案例库文件不存在")
        return False

    with open(HISTORICAL_CASES_FILE, 'r', encoding='utf-8') as f:
        cases_data = json.load(f)

    print(f"[OK] 历史案例库已加载")
    print(f"     - 总案例数: {cases_data['statistics']['total_cases']}")
    print(f"     - 按类型统计: {cases_data['statistics']['by_type']}")
    print(f"     - 按置信度统计: {cases_data['statistics']['by_confidence']}")

    # 模拟一个违规判定结果
    print("\n[2] 模拟违规判定结果...")
    mock_result = {
        "task_id": "test_rule_reasoning_001",
        "status": "completed",
        "violations": [
            {
                "type": "dilution_discharge",
                "confidence": 0.85,
                "evidence": ["流量突增", "COD浓度成比例下降"],
                "timestamp": "2026-07-06 14:30:00"
            }
        ],
        "reasoning": "检测到流量突增且COD浓度成比例下降，符合稀释排放特征",
        "confidence": "high",
        "metadata": {
            "subagent": "rule-reasoning",
            "timestamp": "2026-07-06T14:30:00"
        }
    }
    print(f"[OK] 模拟结果已创建")
    print(f"     - 违规类型: {mock_result['violations'][0]['type']}")
    print(f"     - 置信度: {mock_result['confidence']}")

    # 导入保存函数
    print("\n[3] 导入保存函数...")
    sys.path.insert(0, str(PROJECT_ROOT / "subagents" / "rule-reasoning-agent"))
    try:
        from agent_main import save_to_historical_cases
        print("[OK] 保存函数已导入")
    except ImportError as e:
        print(f"[ERROR] 导入失败: {e}")
        return False

    # 测试保存
    print("\n[4] 测试保存功能...")
    success = save_to_historical_cases(mock_result, mock_result['task_id'])
    if not success:
        print("[ERROR] 保存失败")
        return False
    print("[OK] 保存成功")

    # 验证保存结果
    print("\n[5] 验证保存结果...")
    with open(HISTORICAL_CASES_FILE, 'r', encoding='utf-8') as f:
        updated_data = json.load(f)

    print(f"[OK] 历史案例库已更新")
    print(f"     - 总案例数: {updated_data['statistics']['total_cases']}")
    print(f"     - 新增案例: {updated_data['statistics']['total_cases'] - cases_data['statistics']['total_cases']}")

    # 测试无违规情况
    print("\n[6] 测试无违规情况...")
    no_violation_result = {
        "task_id": "test_no_violation_001",
        "status": "completed",
        "violations": [],
        "reasoning": "未检测到异常，数据正常",
        "confidence": "high",
        "metadata": {}
    }
    success = save_to_historical_cases(no_violation_result, no_violation_result['task_id'])
    if not success:
        print("[ERROR] 保存失败")
        return False

    # 验证无违规时不应增加案例数
    with open(HISTORICAL_CASES_FILE, 'r', encoding='utf-8') as f:
        final_data = json.load(f)

    case_count_unchanged = final_data['statistics']['total_cases'] == updated_data['statistics']['total_cases']
    if case_count_unchanged:
        print("[OK] 无违规时未增加案例数（符合预期）")
    else:
        print(f"[ERROR] 无违规时案例数增加（不符合预期）")
        return False

    print("\n" + "="*60)
    print("所有测试通过！")
    print("="*60)
    return True


if __name__ == "__main__":
    success = test_historical_cases_save()
    sys.exit(0 if success else 1)
