#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
疑似规则知识库
功能：基于专家经验的疑似判定规则
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import math


class RuleType(Enum):
    """规则类型"""
    SINGLE_INDICATOR = "单指标规则"      # 单指标规则
    MULTI_INDICATOR = "多指标规则"      # 多指标规则
    TIME_SERIES = "时序规则"           # 时序规则
    CORRELATION = "相关性规则"         # 相关性规则
    PROCESS = "工艺规则"               # 工艺规则


@dataclass
class SuspicionRule:
    """疑似规则"""
    rule_id: str
    name: str
    description: str
    rule_type: RuleType
    conditions: List[str]      # 触发条件
    evidence: List[str]        # 证据
    suspicion_score: float     # 疑似分数 0-1
    legal_reference: str       # 法律依据


# ==================== 疑似规则定义 ====================

RULES: List[SuspicionRule] = [

    # R1: 恒定值规则（插瓶干扰）
    SuspicionRule(
        rule_id="R001",
        name="多指标恒定值检测",
        description="连续N个监测周期，多个污染物指标数值保持恒定",
        rule_type=RuleType.MULTI_INDICATOR,
        conditions=[
            "至少2个指标的标准差<0.1",
            "监测周期数>=5",
        ],
        evidence=[
            "数据缺乏自然波动",
            "符合插瓶干扰特征",
            "多指标同步恒定"
        ],
        suspicion_score=0.85,
        legal_reference="水污染防治法第三十九条"
    ),

    # R2: 数据过度平滑
    SuspicionRule(
        rule_id="R002",
        name="数据变异系数过低",
        description="多个指标的变异系数（CV）显著低于正常水平",
        rule_type=RuleType.MULTI_INDICATOR,
        conditions=[
            "至少2个指标的CV<0.05",
            "均值>0"
        ],
        evidence=[
            "数据过度平滑",
            "不符合真实监测数据特征",
            "疑似数据造假"
        ],
        suspicion_score=0.75,
        legal_reference="水污染防治法第三十九条"
    ),

    # R3: 法规超标
    SuspicionRule(
        rule_id="R003",
        name="污染物超标排放",
        description="出水污染物浓度超过排放标准限值",
        rule_type=RuleType.SINGLE_INDICATOR,
        conditions=[
            "指标值>法规限值",
            "或指标值<法规下限"
        ],
        evidence=[
            "直接违反排放标准",
            "超标倍数可计算处罚",
            "需立即整改"
        ],
        suspicion_score=1.0,
        legal_reference="水污染防治法第八十三条"
    ),

    # R4: 进出水相似
    SuspicionRule(
        rule_id="R004",
        name="进出水浓度相似",
        description="进出水污染物浓度高度相似，去除率极低",
        rule_type=RuleType.MULTI_INDICATOR,
        conditions=[
            "至少2个指标进出水相似度>0.95",
            "或去除率<10%"
        ],
        evidence=[
            "疑似旁路排放",
            "处理设施未正常运行",
            "污染物未被去除"
        ],
        suspicion_score=0.90,
        legal_reference="水污染防治法第三十九条"
    ),

    # R5: 多指标同步变化
    SuspicionRule(
        rule_id="R005",
        name="多指标同步异常变化",
        description="多个污染物指标呈现异常同步的变化趋势",
        rule_type=RuleType.CORRELATION,
        conditions=[
            "至少3个指标间相关系数>0.9",
            "变化趋势一致"
        ],
        evidence=[
            "疑似稀释排放",
            "人为操作痕迹明显",
            "不符合自然处理规律"
        ],
        suspicion_score=0.70,
        legal_reference="水污染防治法第三十九条"
    ),

    # R6: 流量异常
    SuspicionRule(
        rule_id="R006",
        name="排放流量与处理能力不匹配",
        description="排放流量远超设计处理能力",
        rule_type=RuleType.SINGLE_INDICATOR,
        conditions=[
            "流量>设计能力120%",
            "或流量突然增大"
        ],
        evidence=[
            "可能存在旁路排放",
            "或稀释排放",
            "需核实处理能力"
        ],
        suspicion_score=0.60,
        legal_reference="水污染防治法第十条"
    ),

    # R7: pH异常
    SuspicionRule(
        rule_id="R007",
        name="pH值异常",
        description="pH值超出正常范围或恒定",
        rule_type=RuleType.SINGLE_INDICATOR,
        conditions=[
            "pH<6 或 pH>9",
            "或pH标准差<0.05"
        ],
        evidence=[
            "不符合生化处理要求",
            "可能影响处理效果",
            "或存在数据异常"
        ],
        suspicion_score=0.50,
        legal_reference="排放标准"
    ),

    # R8: 去除率异常
    SuspicionRule(
        rule_id="R008",
        name="污染物去除率异常",
        description="污染物去除率明显高于或低于正常水平",
        rule_type=RuleType.PROCESS,
        conditions=[
            "去除率>95%或<10%",
            "且进水浓度在正常范围"
        ],
        evidence=[
            "去除率过高可能数据造假",
            "去除率过低设施未运行",
            "需核实工艺参数"
        ],
        suspicion_score=0.65,
        legal_reference="水污染防治法第十条"
    ),

    # R9: 断电/停机期间有数据
    SuspicionRule(
        rule_id="R009",
        name="停机期间数据异常",
        description="设备停机期间仍有监测数据",
        rule_type=RuleType.TIME_SERIES,
        conditions=[
            "设备状态为停止",
            "但数据持续产生"
        ],
        evidence=[
            "数据造假",
            "或设备状态记录不准确",
            "需核实现场情况"
        ],
        suspicion_score=0.95,
        legal_reference="水污染防治法第三十九条"
    ),

    # R10: 非工作时间数据规律性
    SuspicionRule(
        rule_id="R010",
        name="非工作时间数据异常",
        description="夜间或节假日数据与工作时间差异过大",
        rule_type=RuleType.TIME_SERIES,
        conditions=[
            "非工作时间数据恒定",
            "或非工作时间数据显著优于工作时间"
        ],
        evidence=[
            "疑似插瓶干扰",
            "或选择性造假",
            "非工作时间监管薄弱"
        ],
        suspicion_score=0.80,
        legal_reference="水污染防治法第三十九条"
    ),
]


# ==================== 规则引擎 ====================

class SuspicionRuleEngine:
    """疑似规则引擎"""

    def __init__(self):
        """初始化规则引擎"""
        self.rules = RULES
        # 创建规则索引
        self._rule_index = {
            "single": [r for r in RULES if r.rule_type == RuleType.SINGLE_INDICATOR],
            "multi": [r for r in RULES if r.rule_type == RuleType.MULTI_INDICATOR],
            "time": [r for r in RULES if r.rule_type == RuleType.TIME_SERIES],
            "correlation": [r for r in RULES if r.rule_type == RuleType.CORRELATION],
            "process": [r for r in RULES if r.rule_type == RuleType.PROCESS],
        }

    def evaluate_all(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        评估所有规则

        Args:
            data: 数据字典，包含:
                - stats: 指标统计
                - influent_stats: 进水统计（可选）
                - limits: 法规限值（可选）
                - correlations: 相关性（可选）

        Returns:
            触发的规则列表
        """
        triggered = []

        stats = data.get("stats", {})
        influent_stats = data.get("influent_stats", {})

        # R001: 多指标恒定值
        constant_indicators = [ind for ind, s in stats.items()
                              if s.get("std", 1) < 0.1]
        if len(constant_indicators) >= 2:
            triggered.append(self._format_rule_result(
                self.rules[0],  # R001
                evidence={"constant_indicators": constant_indicators}
            ))

        # R002: 变异系数过低
        smooth_indicators = []
        for ind, s in stats.items():
            mean = s.get("mean", 0)
            if mean > 0:
                cv = s.get("std", 0) / abs(mean)
                if cv < 0.05:
                    smooth_indicators.append(ind)
        if len(smooth_indicators) >= 2:
            triggered.append(self._format_rule_result(
                self.rules[1],  # R002
                evidence={"smooth_indicators": smooth_indicators}
            ))

        # R004: 进出水相似
        if influent_stats:
            similar_indicators = []
            for ind in stats:
                if ind in influent_stats:
                    in_mean = influent_stats[ind].get("mean", 0)
                    out_mean = stats[ind].get("mean", 0)
                    if in_mean > 0:
                        similarity = 1 - abs(in_mean - out_mean) / in_mean
                        if similarity > 0.95:
                            similar_indicators.append(ind)
            if len(similar_indicators) >= 2:
                triggered.append(self._format_rule_result(
                    self.rules[3],  # R004
                    evidence={"similar_indicators": similar_indicators}
                ))

        # R005: 多指标同步
        correlations = data.get("correlations", {})
        high_corr = [k for k, v in correlations.items() if v > 0.9]
        if len(high_corr) >= 2:
            triggered.append(self._format_rule_result(
                self.rules[4],  # R005
                evidence={"high_correlations": high_corr}
            ))

        return triggered

    def _format_rule_result(self, rule: SuspicionRule,
                            evidence: Dict[str, Any]) -> Dict[str, Any]:
        """格式化规则结果"""
        return {
            "rule_id": rule.rule_id,
            "name": rule.name,
            "suspicion_score": rule.suspicion_score,
            "level": "critical" if rule.suspicion_score >= 0.9 else
                    "high" if rule.suspicion_score >= 0.7 else
                    "medium" if rule.suspicion_score >= 0.5 else "low",
            "evidence": evidence,
            "legal_reference": rule.legal_reference
        }

    def get_rule_by_id(self, rule_id: str) -> Optional[SuspicionRule]:
        """根据ID获取规则"""
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule
        return None

    def search_rules(self, keyword: str) -> List[SuspicionRule]:
        """搜索规则"""
        return [r for r in self.rules
                if keyword in r.name or keyword in r.description]


# ==================== 便捷函数 ====================

def create_rule_engine() -> SuspicionRuleEngine:
    """创建规则引擎"""
    return SuspicionRuleEngine()


if __name__ == "__main__":
    # 测试
    print("疑似规则引擎测试")
    print("=" * 60)

    engine = create_rule_engine()

    # 测试数据
    test_data = {
        "stats": {
            "pH": {"std": 0.03, "mean": 7.5},
            "COD": {"std": 0.02, "mean": 45.0},
            "TN": {"std": 0.04, "mean": 8.0},
        },
        "influent_stats": {
            "pH": {"std": 0.1, "mean": 7.0},
            "COD": {"std": 5.0, "mean": 100.0},
            "TN": {"std": 2.0, "mean": 15.0},
        },
        "correlations": {
            "COD_TN": 0.98,
            "COD_TP": 0.95
        }
    }

    print("\n触发的规则:")
    results = engine.evaluate_all(test_data)
    for r in results:
        print(f"\n{r['name']}:")
        print(f"  疑似度: {r['suspicion_score']:.2f}")
        print(f"  级别: {r['level']}")
        print(f"  证据: {r['evidence']}")
        print(f"  法律依据: {r['legal_reference']}")

    # 搜索规则
    print("\n\n搜索'插瓶'相关规则:")
    for rule in engine.search_rules("插瓶"):
        print(f"  {rule.rule_id}: {rule.name}")
