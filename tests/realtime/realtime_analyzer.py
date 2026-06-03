#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时分析引擎
功能：流式处理数据到达后立即分析，支持滑动窗口和增量统计

基于专利参数：
- IQR系数：1.5
- 窗口大小：5
- 污染率：0.1
- 相似度阈值：0.8
"""

import collections
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Deque
from statistics import mean, median, stdev
import copy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== 告警级别定义 ====================

class AlertLevel:
    """告警级别"""
    CRITICAL = "critical"  # 紧急：法规超标
    HIGH = "high"          # 重要：疑似违规模式
    MEDIUM = "medium"      # 一般：数据异常
    LOW = "low"            # 低：提示信息


# ==================== 违规模式定义 ====================

VIOLATION_PATTERNS = {
    "bottle_interference": {
        "name": "插瓶干扰",
        "description": "采样时插入装有达标水样的小瓶",
        "indicators": ["恒定值", "数据过度平滑"],
        "threshold": {"std_threshold": 0.1}
    },
    "dilution_discharge": {
        "name": "稀释排放",
        "description": "通过加水稀释污染物浓度",
        "indicators": ["多指标同步下降", "流量异常增大"],
        "threshold": {"correlation_threshold": 0.9}
    },
    "data_fabrication": {
        "name": "数据造假",
        "description": "数据过度平滑，缺乏自然波动",
        "indicators": ["标准差过小", "变异系数过低"],
        "threshold": {"cv_threshold": 0.05}
    },
    "bypass_discharge": {
        "name": "旁路排放",
        "description": "未经处理直接排放",
        "indicators": ["进出水浓度相似", "去除率为负"],
        "threshold": {"similarity_threshold": 0.95, "removal_negative": True}
    }
}


# ==================== 法规限值 ====================

REGULATORY_LIMITS = {
    "pH": {"min": 6.0, "max": 9.0, "unit": ""},
    "COD": {"max": 50.0, "unit": "mg/L"},
    "TN": {"max": 15.0, "unit": "mg/L"},
    "NH3-N": {"max": 5.0, "unit": "mg/L"},
    "TP": {"max": 0.5, "unit": "mg/L"},
    "SS": {"max": 10.0, "unit": "mg/L"}
}


# ==================== 数据类定义 ====================

@dataclass
class StatisticsState:
    """增量统计状态"""
    count: int = 0
    sum: float = 0.0
    sum_sq: float = 0.0  # 平方和，用于计算方差
    min_val: float = float('inf')
    max_val: float = float('-inf')

    def update(self, value: float):
        """更新统计状态"""
        if value is None:
            return
        self.count += 1
        self.sum += value
        self.sum_sq += value * value
        self.min_val = min(self.min_val, value)
        self.max_val = max(self.max_val, value)

    @property
    def mean(self) -> float:
        """计算均值"""
        return self.sum / self.count if self.count > 0 else 0.0

    @property
    def variance(self) -> float:
        """计算方差"""
        if self.count < 2:
            return 0.0
        return (self.sum_sq - self.sum * self.sum / self.count) / (self.count - 1)

    @property
    def std(self) -> float:
        """计算标准差"""
        return self.variance ** 0.5

    @property
    def range(self) -> Tuple[float, float]:
        """获取范围"""
        return (self.min_val, self.max_val) if self.count > 0 else (0.0, 0.0)


@dataclass
class AnomalyResult:
    """异常检测结果"""
    indicator: str
    value: float
    is_anomaly: bool
    anomaly_type: str
    score: float
    threshold: float
    message: str


@dataclass
class ViolationResult:
    """违规模式检测结果"""
    pattern_type: str
    pattern_name: str
    suspicion: float  # 疑似程度 0-1
    level: str
    evidence: Dict[str, Any]
    timestamp: str


@dataclass
class AnalysisResult:
    """实时分析结果"""
    timestamp: str
    has_anomaly: bool
    has_violation: bool
    anomalies: List[AnomalyResult]
    violations: List[ViolationResult]
    statistics: Dict[str, Dict[str, float]]
    metadata: Dict[str, Any] = field(default_factory=dict)


# ==================== 实时分析引擎 ====================

class RealTimeAnalyzer:
    """
    实时分析引擎

    功能：
    1. 滑动窗口管理（最近N条数据）
    2. 增量统计更新
    3. 实时异常检测（流式算法）
    4. 违规模式匹配
    5. 告警判定
    """

    # 指标映射（中文字段名 -> 英文标准名）
    FIELD_MAPPING = {
        "pH值": "pH",
        "化学需氧量浓度（毫克/升）": "COD",
        "总氮浓度（毫克/升）": "TN",
        "氨氮浓度（毫克/升）": "NH3-N",
        "总磷浓度（毫克/升）": "TP",
        "悬浮物浓度（毫克/升）": "SS",
        "流量（升/秒）": "flow_rate",
        "排放量（吨）": "discharge_volume"
    }

    def __init__(self, window_size: int = 24, iqr_multiplier: float = 1.5,
                 min_samples: int = 3):
        """
        初始化实时分析引擎

        Args:
            window_size: 滑动窗口大小（默认24条数据）
            iqr_multiplier: IQR系数（专利要求1.5）
            min_samples: 最小样本数（低于此值不进行异常检测）
        """
        self.window_size = window_size
        self.iqr_multiplier = iqr_multiplier
        self.min_samples = min_samples

        # 滑动窗口（存储最近N条数据）
        self.window: Deque[Dict[str, Any]] = collections.deque(maxlen=window_size)

        # 增量统计状态（每个指标独立维护）
        self.statistics: Dict[str, StatisticsState] = {}

        # 告警计数
        self.alert_counts: Dict[str, int] = {}

        logger.info(f"[INIT] 实时分析引擎初始化")
        logger.info(f"[INIT] 窗口大小: {window_size}, IQR系数: {iqr_multiplier}")

    def _normalize_field_name(self, field_name: str) -> Optional[str]:
        """标准化字段名"""
        return self.FIELD_MAPPING.get(field_name, field_name)

    def _safe_float(self, value: Any) -> Optional[float]:
        """安全转换为浮点数"""
        if value is None:
            return None
        try:
            val_str = str(value).strip()
            if val_str in ['/', '', 'NA', 'N/A', 'null', 'None']:
                return None
            return float(val_str)
        except (ValueError, TypeError):
            return None

    def _extract_indicators(self, data: Dict[str, Any]) -> Dict[str, float]:
        """提取指标值"""
        indicators = {}
        for field, value in data.items():
            norm_field = self._normalize_field_name(field)
            if norm_field and norm_field in ["pH", "COD", "TN", "NH3-N", "TP", "SS", "flow_rate"]:
                float_val = self._safe_float(value)
                if float_val is not None:
                    indicators[norm_field] = float_val
        return indicators

    def _update_statistics(self, indicators: Dict[str, float]):
        """增量更新统计状态"""
        for name, value in indicators.items():
            if name not in self.statistics:
                self.statistics[name] = StatisticsState()
            self.statistics[name].update(value)

    def _calculate_window_stats(self, indicator: str) -> Dict[str, float]:
        """计算窗口统计（基于窗口内数据）"""
        values = []
        for record in self.window:
            # 检查effluent数据（重点监测出水）
            effluent = record.get("effluent", {})
            if isinstance(effluent, dict):
                for field, value in effluent.items():
                    norm_field = self._normalize_field_name(field)
                    if norm_field == indicator:
                        float_val = self._safe_float(value)
                        if float_val is not None:
                            values.append(float_val)

        if len(values) < 2:
            return {"count": len(values), "mean": 0, "std": 0, "min": 0, "max": 0}

        return {
            "count": len(values),
            "mean": mean(values),
            "std": stdev(values) if len(values) > 1 else 0,
            "min": min(values),
            "max": max(values),
            "median": median(values)
        }

    def _detect_regulatory_exceedance(self, indicators: Dict[str, float]) -> List[AnomalyResult]:
        """检测法规超标"""
        results = []

        for name, value in indicators.items():
            if name not in REGULATORY_LIMITS:
                continue

            limits = REGULATORY_LIMITS[name]

            # 检查下限（pH）
            if "min" in limits and value < limits["min"]:
                results.append(AnomalyResult(
                    indicator=name,
                    value=value,
                    is_anomaly=True,
                    anomaly_type="regulatory_low",
                    score=1.0,
                    threshold=limits["min"],
                    message=f"{name}低于法规限值: {value} < {limits['min']}"
                ))

            # 检查上限
            if "max" in limits and value > limits["max"]:
                results.append(AnomalyResult(
                    indicator=name,
                    value=value,
                    is_anomaly=True,
                    anomaly_type="regulatory_high",
                    score=1.0,
                    threshold=limits["max"],
                    message=f"{name}超过法规限值: {value} > {limits['max']}"
                ))

        return results

    def _detect_constant_value(self, indicator: str, stats: Dict[str, float]) -> Optional[AnomalyResult]:
        """检测恒定值异常（插瓶干扰特征）"""
        if stats["count"] < self.min_samples:
            return None

        std = stats["std"]
        mean_val = stats["mean"]

        # 标准差过小说明值几乎不变
        if std < 0.1:
            return AnomalyResult(
                indicator=indicator,
                value=mean_val,
                is_anomaly=True,
                anomaly_type="constant_value",
                score=1.0 - min(std * 10, 1.0),  # std越小，分数越高
                threshold=0.1,
                message=f"{indicator}恒定在{mean_val:.2f}附近（标准差={std:.4f}）"
            )

        return None

    def _detect_iqr_anomaly(self, indicator: str, stats: Dict[str, float]) -> Optional[AnomalyResult]:
        """检测IQR异常（基于窗口数据）"""
        if stats["count"] < 4:
            return None

        values = []
        for record in self.window:
            # 检查effluent数据
            effluent = record.get("effluent", {})
            if isinstance(effluent, dict):
                for field, value in effluent.items():
                    norm_field = self._normalize_field_name(field)
                    if norm_field == indicator:
                        float_val = self._safe_float(value)
                        if float_val is not None:
                            values.append(float_val)

        if len(values) < 4:
            return None

        # 计算IQR
        sorted_vals = sorted(values)
        q1_idx = int(len(values) * 0.25)
        q3_idx = int(len(values) * 0.75)
        q1 = sorted_vals[q1_idx]
        q3 = sorted_vals[q3_idx]
        iqr = q3 - q1

        if iqr == 0:
            return None

        lower_bound = q1 - self.iqr_multiplier * iqr
        upper_bound = q3 + self.iqr_multiplier * iqr

        # 检查最新值是否异常
        latest_val = values[-1]
        if latest_val < lower_bound:
            return AnomalyResult(
                indicator=indicator,
                value=latest_val,
                is_anomaly=True,
                anomaly_type="iqr_low",
                score=(lower_bound - latest_val) / (iqr + 1e-8),
                threshold=lower_bound,
                message=f"{indicator}={latest_val:.2f}低于下界{lower_bound:.2f}"
            )
        elif latest_val > upper_bound:
            return AnomalyResult(
                indicator=indicator,
                value=latest_val,
                is_anomaly=True,
                anomaly_type="iqr_high",
                score=(latest_val - upper_bound) / (iqr + 1e-8),
                threshold=upper_bound,
                message=f"{indicator}={latest_val:.2f}高于上界{upper_bound:.2f}"
            )

        return None

    def _detect_violation_patterns(self, anomalies: List[AnomalyResult],
                                   window_stats: Dict[str, Dict[str, float]]) -> List[ViolationResult]:
        """违规模式匹配"""
        violations = []

        # 1. 检测插瓶干扰（多个指标恒定）
        constant_indicators = []
        for indicator, stats in window_stats.items():
            if stats["count"] >= self.min_samples and stats["std"] < 0.1:
                constant_indicators.append(indicator)

        if len(constant_indicators) >= 2:
            # 至少两个指标恒定，疑似插瓶
            suspicion = min(0.5 + len(constant_indicators) * 0.1, 1.0)
            violations.append(ViolationResult(
                pattern_type="bottle_interference",
                pattern_name=VIOLATION_PATTERNS["bottle_interference"]["name"],
                suspicion=suspicion,
                level=AlertLevel.HIGH,
                evidence={
                    "constant_indicators": constant_indicators,
                    "values": {ind: window_stats[ind]["mean"] for ind in constant_indicators}
                },
                timestamp=datetime.now().isoformat()
            ))

        # 2. 检测法规超标
        for anomaly in anomalies:
            if anomaly.anomaly_type.startswith("regulatory_"):
                violations.append(ViolationResult(
                    pattern_type="regulatory_exceedance",
                    pattern_name="法规超标",
                    suspicion=1.0,
                    level=AlertLevel.CRITICAL,
                    evidence={
                        "indicator": anomaly.indicator,
                        "value": anomaly.value,
                        "limit": anomaly.threshold,
                        "message": anomaly.message
                    },
                    timestamp=datetime.now().isoformat()
                ))

        # 3. 检测数据造假（过度平滑）
        smooth_indicators = []
        for indicator, stats in window_stats.items():
            if stats["count"] >= self.min_samples and stats["mean"] > 0:
                cv = stats["std"] / abs(stats["mean"])  # 变异系数
                if cv < 0.05:
                    smooth_indicators.append(indicator)

        if len(smooth_indicators) >= 2:
            violations.append(ViolationResult(
                pattern_type="data_fabrication",
                pattern_name=VIOLATION_PATTERNS["data_fabrication"]["name"],
                suspicion=0.7,
                level=AlertLevel.HIGH,
                evidence={
                    "smooth_indicators": smooth_indicators,
                    "cv_values": {ind: window_stats[ind]["std"] / abs(window_stats[ind]["mean"])
                                 for ind in smooth_indicators}
                },
                timestamp=datetime.now().isoformat()
            ))

        return violations

    def process_new_data(self, influent_data: Dict[str, Any],
                        effluent_data: Dict[str, Any]) -> AnalysisResult:
        """
        处理新到达的数据

        Args:
            influent_data: 进水数据
            effluent_data: 出水数据

        Returns:
            AnalysisResult: 分析结果
        """
        timestamp = datetime.now().isoformat()

        # 1. 更新滑动窗口
        self.window.append({
            "timestamp": timestamp,
            "influent": copy.deepcopy(influent_data),
            "effluent": copy.deepcopy(effluent_data)
        })

        # 2. 提取出水指标（重点监测出水）
        effluent_indicators = self._extract_indicators(effluent_data)

        # 3. 增量更新统计
        self._update_statistics(effluent_indicators)

        # 4. 计算窗口统计
        window_stats = {}
        for indicator in ["pH", "COD", "TN", "NH3-N", "TP", "SS"]:
            stats = self._calculate_window_stats(indicator)
            if stats["count"] > 0:
                window_stats[indicator] = stats

        # 5. 实时异常检测
        anomalies = []

        # 5.1 法规超标检测
        regulatory_anomalies = self._detect_regulatory_exceedance(effluent_indicators)
        anomalies.extend(regulatory_anomalies)

        # 5.2 恒定值检测
        if len(self.window) >= self.min_samples:
            for indicator, stats in window_stats.items():
                if stats["count"] >= self.min_samples:
                    constant_anomaly = self._detect_constant_value(indicator, stats)
                    if constant_anomaly:
                        anomalies.append(constant_anomaly)

        # 5.3 IQR异常检测
        if len(self.window) >= 4:
            for indicator, stats in window_stats.items():
                if stats["count"] >= 4:
                    iqr_anomaly = self._detect_iqr_anomaly(indicator, stats)
                    if iqr_anomaly:
                        anomalies.append(iqr_anomaly)

        # 6. 违规模式匹配
        violations = self._detect_violation_patterns(anomalies, window_stats)

        # 7. 更新告警计数
        for v in violations:
            key = v.pattern_type
            self.alert_counts[key] = self.alert_counts.get(key, 0) + 1

        return AnalysisResult(
            timestamp=timestamp,
            has_anomaly=len(anomalies) > 0,
            has_violation=len(violations) > 0,
            anomalies=anomalies,
            violations=violations,
            statistics=window_stats,
            metadata={
                "window_size": len(self.window),
                "total_alerts": sum(self.alert_counts.values())
            }
        )

    def get_statistics(self) -> Dict[str, Any]:
        """获取当前统计信息"""
        stats = {}
        for name, state in self.statistics.items():
            stats[name] = {
                "count": state.count,
                "mean": state.mean,
                "std": state.std,
                "min": state.min_val,
                "max": state.max_val,
                "range": state.range
            }
        return {
            "statistics": stats,
            "window_size": len(self.window),
            "alert_counts": self.alert_counts
        }

    def reset(self):
        """重置分析器状态"""
        self.window.clear()
        self.statistics.clear()
        self.alert_counts.clear()
        logger.info("[RESET] 分析器状态已重置")


# ==================== 便捷函数 ====================

def create_realtime_analyzer(window_size: int = 24,
                              iqr_multiplier: float = 1.5) -> RealTimeAnalyzer:
    """
    创建实时分析器

    Args:
        window_size: 滑动窗口大小
        iqr_multiplier: IQR系数

    Returns:
        RealTimeAnalyzer实例
    """
    return RealTimeAnalyzer(
        window_size=window_size,
        iqr_multiplier=iqr_multiplier
    )


if __name__ == "__main__":
    # 测试代码
    import json

    analyzer = create_realtime_analyzer(window_size=5)

    # 模拟正常数据
    print("测试正常数据...")
    for i in range(10):
        influent = {"pH值": 7.0 + i * 0.01, "化学需氧量浓度（毫克/升）": 100 + i * 5}
        effluent = {"pH值": 7.5 + i * 0.01, "化学需氧量浓度（毫克/升）": 45 + i * 2}

        result = analyzer.process_new_data(influent, effluent)

        if result.has_violation:
            print(f"[告警] {result.violations[0].pattern_name}: {result.violations[0].evidence}")

    print("\n测试恒定值异常（插瓶干扰）...")
    # 模拟恒定值异常
    for i in range(10):
        influent = {"pH值": 7.2, "化学需氧量浓度（毫克/升）": 45.0}
        effluent = {"pH值": 7.5, "化学需氧量浓度（毫克/升）": 45.0}

        result = analyzer.process_new_data(influent, effluent)

        if result.has_violation:
            for v in result.violations:
                print(f"[告警] {v.pattern_name} (疑似度={v.suspicion:.2f})")
                print(f"       证据: {v.evidence}")

    print("\n测试法规超标...")
    # 模拟超标
    influent = {"pH值": 7.0, "化学需氧量浓度（毫克/升）": 100.0}
    effluent = {"pH值": 7.5, "化学需氧量浓度（毫克/升）": 75.0}  # 超标

    result = analyzer.process_new_data(influent, effluent)

    if result.has_violation:
        for v in result.violations:
            print(f"[告警] {v.pattern_name} (级别={v.level})")
            print(f"       证据: {v.evidence}")

    print("\n当前统计:")
    stats = analyzer.get_statistics()
    print(json.dumps(stats, indent=2, ensure_ascii=False))
