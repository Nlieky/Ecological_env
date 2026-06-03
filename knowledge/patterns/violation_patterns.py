#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
违规模式知识库
功能：定义和识别典型违规模式
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import math


class PatternType(Enum):
    """违规模式类型"""
    BOTTLE_INTERFERENCE = "bottle_interference"      # 插瓶干扰
    DILUTION_DISCHARGE = "dilution_discharge"        # 稀释排放
    DATA_FABRICATION = "data_fabrication"           # 数据造假
    BYPASS_DISCHARGE = "bypass_discharge"           # 旁路排放
    SAMPLING_FRAUD = "sampling_fraud"               # 采样造假
    INSTRUMENT_TAMPERING = "instrument_tampering"   # 仪器篡改


class SuspicionLevel(Enum):
    """疑似程度"""
    DEFINITE = "确定"      # 确定性违规
    HIGH = "高度疑似"      # 高度疑似
    MODERATE = "疑似"      # 疑似
    LOW = "提示"          # 提示性


@dataclass
class PatternIndicator:
    """模式指标"""
    indicator: str
    condition: str          # 条件描述
    threshold: Optional[float] = None
    expected_value: Optional[str] = None


@dataclass
class ViolationPattern:
    """违规模式"""
    pattern_type: PatternType
    name: str
    description: str
    principle: str            # 作案原理
    characteristics: List[str]  # 特征列表
    indicators: List[PatternIndicator]  # 涉及指标
    detection_methods: List[str]  # 检测方法
    suspicion_level: SuspicionLevel
    legal_basis: str          # 法律依据
    evidence_requirements: List[str]  # 证据要求


# ==================== 违规模式定义 ====================

PATTERNS: Dict[PatternType, ViolationPattern] = {

    # 1. 插瓶干扰
    PatternType.BOTTLE_INTERFERENCE: ViolationPattern(
        pattern_type=PatternType.BOTTLE_INTERFERENCE,
        name="插瓶干扰",
        description="采样时插入装有达标水样的小瓶，使采集样品为达标水",
        principle="利用采样窗口期，在采样位置放置预先准备好的达标水样小瓶",
        characteristics=[
            "单个或多个指标恒定不变",
            "数据缺乏自然波动",
            "恒定值通常接近标准限值",
            "多指标同时恒定（如pH=7.5, COD=45）"
        ],
        indicators=[
            PatternIndicator("pH", "标准差", threshold=0.1),
            PatternIndicator("COD", "标准差", threshold=0.1),
            PatternIndicator("TN", "标准差", threshold=0.1),
            PatternIndicator("NH3-N", "标准差", threshold=0.1),
            PatternIndicator("TP", "标准差", threshold=0.1),
        ],
        detection_methods=[
            "标准差检测：连续N点标准差<0.1",
            "变异系数检测：CV<0.05",
            "中位数绝对偏差检测",
            "持续值检测：相同值连续出现>N次"
        ],
        suspicion_level=SuspicionLevel.HIGH,
        legal_basis="水污染防治法第三十九条：禁止篡改、伪造监测数据",
        evidence_requirements=[
            "监测数据缺乏自然波动",
            "多指标同时呈现恒定值",
            "与进水数据变化趋势不符",
            "现场采样记录异常"
        ]
    ),

    # 2. 稀释排放
    PatternType.DILUTION_DISCHARGE: ViolationPattern(
        pattern_type=PatternType.DILUTION_DISCHARGE,
        name="稀释排放",
        description="通过加水稀释污染物浓度，降低监测数值",
        principle="在排放口前注入清水或河水，稀释污染物浓度",
        characteristics=[
            "多指标浓度同步下降",
            "流量异常增大",
            "污染物去除率异常升高",
            "进出水浓度相关性异常"
        ],
        indicators=[
            PatternIndicator("COD", "与TN相关性"),
            PatternIndicator("TN", "与NH3-N相关性"),
            PatternIndicator("flow_rate", "异常增大"),
        ],
        detection_methods=[
            "相关性分析：多指标相关系数>0.9",
            "流量异常检测：流量突变",
            "去除率异常检测",
            "物质平衡分析"
        ],
        suspicion_level=SuspicionLevel.MODERATE,
        legal_basis="水污染防治法第三十九条：禁止利用渗井、渗坑逃避监管",
        evidence_requirements=[
            "多指标浓度同步下降",
            "流量与浓度异常关系",
            "污染物总量不平衡",
            "加水设备或管道痕迹"
        ]
    ),

    # 3. 数据造假
    PatternType.DATA_FABRICATION: ViolationPattern(
        pattern_type=PatternType.DATA_FABRICATION,
        name="数据造假",
        description="编造或篡改监测数据",
        principle="人为编造数据或修改真实监测结果",
        characteristics=[
            "数据过度平滑",
            "缺乏自然波动",
            "统计特征不符合真实规律",
            "数据分布异常"
        ],
        indicators=[
            PatternIndicator("all", "变异系数", threshold=0.05),
            PatternIndicator("all", "偏度", expected_value="接近0"),
            PatternIndicator("all", "峰度", expected_value="接近3"),
        ],
        detection_methods=[
            "变异系数检测：CV<0.05",
            "分布拟合检验",
            "Benford定律检验",
            "时间序列模式识别"
        ],
        suspicion_level=SuspicionLevel.HIGH,
        legal_basis="水污染防治法第三十九条：禁止篡改、伪造监测数据",
        evidence_requirements=[
            "数据统计特征异常",
            "与历史数据模式不符",
            "与同类企业数据差异显著",
            "系统操作日志异常"
        ]
    ),

    # 4. 旁路排放
    PatternType.BYPASS_DISCHARGE: ViolationPattern(
        pattern_type=PatternType.BYPASS_DISCHARGE,
        name="旁路排放",
        description="未经处理直接排放污水",
        principle="绕过处理设施，将进水直接排到出水口",
        characteristics=[
            "进出水浓度相似",
            "去除率为负或接近零",
            "处理设施运行异常",
            "能耗与处理量不符"
        ],
        indicators=[
            PatternIndicator("COD", "进出水差值"),
            PatternIndicator("TN", "进出水差值"),
            PatternIndicator("removal_rate", "去除率", threshold=0.1),
        ],
        detection_methods=[
            "相似度分析：进出水相似度>0.95",
            "去除率检测：去除率<10%",
            "能耗分析",
            "设备运行状态监测"
        ],
        suspicion_level=SuspicionLevel.HIGH,
        legal_basis="水污染防治法第三十九条：禁止私设暗管排放",
        evidence_requirements=[
            "进出水水质相似",
            "去除率异常",
            "旁路管道物理证据",
            "设备运行记录异常"
        ]
    ),

    # 5. 采样造假
    PatternType.SAMPLING_FRAUD: ViolationPattern(
        pattern_type=PatternType.SAMPLING_FRAUD,
        name="采样造假",
        description="在采样环节弄虚作假",
        principle="更换采样位置、时间或样品",
        characteristics=[
            "采样时间规律性异常",
            "特定时段数据异常",
            "与在线监测数据不符"
        ],
        indicators=[
            PatternIndicator("timestamp", "采样间隔"),
            PatternIndicator("value", "与在线数据差异"),
        ],
        detection_methods=[
            "采样时间分析",
            "与在线数据比对",
            "与历史数据比对",
            "现场检查"
        ],
        suspicion_level=SuspicionLevel.MODERATE,
        legal_basis="水污染防治法第三十九条",
        evidence_requirements=[
            "采样记录异常",
            "与在线数据不符",
            "现场采样点异常",
            "样品交接记录异常"
        ]
    ),

    # 6. 仪器篡改
    PatternType.INSTRUMENT_TAMPERING: ViolationPattern(
        pattern_type=PatternType.INSTRUMENT_TAMPERING,
        name="仪器篡改",
        description="篡改监测仪器参数或校准数据",
        principle="修改仪器斜率、截距或校准系数",
        characteristics=[
            "系统性偏差",
            "与真实样品测定结果不符",
            "仪器校准记录异常"
        ],
        indicators=[
            PatternIndicator("all", "系统性偏差"),
            PatternIndicator("calibration", "校准记录"),
        ],
        detection_methods=[
            "标准样品比对",
            "平行样分析",
            "仪器校准检查",
            "与第三方检测比对"
        ],
        suspicion_level=SuspicionLevel.HIGH,
        legal_basis="水污染防治法第三十九条",
        evidence_requirements=[
            "仪器参数设置异常",
            "校准记录异常",
            "与标准样品测定结果不符",
            "操作日志异常"
        ]
    ),
}


# ==================== 模式匹配器 ====================

class PatternMatcher:
    """违规模式匹配器"""

    def __init__(self):
        """初始化匹配器"""
        self.patterns = PATTERNS

    def match_bottle_interference(self, stats: Dict[str, Dict[str, float]]) -> tuple[bool, float]:
        """
        匹配插瓶干扰模式

        Args:
            stats: 指标统计字典，如 {"pH": {"std": 0.05, "mean": 7.5}, ...}

        Returns:
            (是否匹配, 疑似度)
        """
        constant_indicators = []
        for indicator, stat in stats.items():
            if stat.get("std", 1.0) < 0.1:
                constant_indicators.append(indicator)

        # 至少两个指标恒定
        if len(constant_indicators) >= 2:
            suspicion = min(0.5 + len(constant_indicators) * 0.1, 1.0)
            return True, suspicion

        return False, 0.0

    def match_dilution_discharge(self, stats: Dict[str, Dict[str, float]],
                                correlations: Dict[str, float]) -> tuple[bool, float]:
        """
        匹配稀释排放模式

        Args:
            stats: 指标统计字典
            correlations: 相关性字典，如 {"COD_TN": 0.95}

        Returns:
            (是否匹配, 疑似度)
        """
        # 检查高相关性
        high_corr_count = sum(1 for corr in correlations.values() if corr > 0.9)

        if high_corr_count >= 2:
            suspicion = 0.6 + high_corr_count * 0.1
            return True, min(suspicion, 1.0)

        return False, 0.0

    def match_data_fabrication(self, stats: Dict[str, Dict[str, float]]) -> tuple[bool, float]:
        """
        匹配数据造假模式

        Args:
            stats: 指标统计字典

        Returns:
            (是否匹配, 疑似度)
        """
        smooth_indicators = []
        for indicator, stat in stats.items():
            mean_val = stat.get("mean", 0)
            if mean_val > 0:
                cv = stat.get("std", 0) / abs(mean_val)
                if cv < 0.05:
                    smooth_indicators.append(indicator)

        # 至少两个指标过度平滑
        if len(smooth_indicators) >= 2:
            suspicion = 0.7
            return True, suspicion

        return False, 0.0

    def match_bypass_discharge(self, influent_stats: Dict[str, Dict[str, float]],
                               effluent_stats: Dict[str, Dict[str, float]]) -> tuple[bool, float]:
        """
        匹配旁路排放模式

        Args:
            influent_stats: 进水统计
            effluent_stats: 出水统计

        Returns:
            (是否匹配, 疑似度)
        """
        similar_indicators = []

        for indicator in influent_stats:
            if indicator not in effluent_stats:
                continue

            in_mean = influent_stats[indicator].get("mean", 0)
            out_mean = effluent_stats[indicator].get("mean", 0)

            if in_mean > 0:
                similarity = 1 - abs(in_mean - out_mean) / in_mean
                if similarity > 0.95:
                    similar_indicators.append(indicator)

        if len(similar_indicators) >= 2:
            return True, 0.9

        return False, 0.0

    def match_all(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        匹配所有违规模式

        Args:
            data: 数据字典，包含:
                - stats: 指标统计
                - correlations: 相关性（可选）
                - influent_stats: 进水统计（可选）

        Returns:
            匹配结果列表
        """
        results = []
        stats = data.get("stats", {})
        correlations = data.get("correlations", {})
        influent_stats = data.get("influent_stats", {})

        # 插瓶干扰
        matched, suspicion = self.match_bottle_interference(stats)
        if matched:
            pattern = self.patterns[PatternType.BOTTLE_INTERFERENCE]
            results.append({
                "pattern_type": pattern.pattern_type.value,
                "name": pattern.name,
                "suspicion": suspicion,
                "level": suspicion_to_level(suspicion),
                "characteristics": pattern.characteristics[:2]  # 主要特征
            })

        # 稀释排放
        if correlations:
            matched, suspicion = self.match_dilution_discharge(stats, correlations)
            if matched:
                pattern = self.patterns[PatternType.DILUTION_DISCHARGE]
                results.append({
                    "pattern_type": pattern.pattern_type.value,
                    "name": pattern.name,
                    "suspicion": suspicion,
                    "level": suspicion_to_level(suspicion),
                    "characteristics": pattern.characteristics[:2]
                })

        # 数据造假
        matched, suspicion = self.match_data_fabrication(stats)
        if matched:
            pattern = self.patterns[PatternType.DATA_FABRICATION]
            results.append({
                "pattern_type": pattern.pattern_type.value,
                "name": pattern.name,
                "suspicion": suspicion,
                "level": suspicion_to_level(suspicion),
                "characteristics": pattern.characteristics[:2]
            })

        # 旁路排放
        if influent_stats:
            matched, suspicion = self.match_bypass_discharge(influent_stats, stats)
            if matched:
                pattern = self.patterns[PatternType.BYPASS_DISCHARGE]
                results.append({
                    "pattern_type": pattern.pattern_type.value,
                    "name": pattern.name,
                    "suspicion": suspicion,
                    "level": suspicion_to_level(suspicion),
                    "characteristics": pattern.characteristics[:2]
                })

        return results


def suspicion_to_level(suspicion: float) -> str:
    """将疑似度转换为级别"""
    if suspicion >= 0.9:
        return "critical"
    elif suspicion >= 0.7:
        return "high"
    elif suspicion >= 0.5:
        return "medium"
    else:
        return "low"


# ==================== 便捷函数 ====================

def create_pattern_matcher() -> PatternMatcher:
    """创建模式匹配器"""
    return PatternMatcher()


def get_pattern_info(pattern_type: PatternType) -> Optional[ViolationPattern]:
    """获取违规模式信息"""
    return PATTERNS.get(pattern_type)


if __name__ == "__main__":
    # 测试
    print("违规模式知识库测试")
    print("=" * 60)

    matcher = create_pattern_matcher()

    # 测试插瓶干扰
    test_stats = {
        "pH": {"std": 0.05, "mean": 7.5},
        "COD": {"std": 0.03, "mean": 45.0},
        "TN": {"std": 0.04, "mean": 8.0},
    }

    print("\n1. 插瓶干扰检测:")
    matched, suspicion = matcher.match_bottle_interference(test_stats)
    print(f"   匹配: {matched}, 疑似度: {suspicion:.2f}")

    # 测试所有模式
    print("\n2. 全模式匹配:")
    results = matcher.match_all({"stats": test_stats})
    for r in results:
        print(f"   {r['name']}: 疑似度={r['suspicion']:.2f}, 级别={r['level']}")
