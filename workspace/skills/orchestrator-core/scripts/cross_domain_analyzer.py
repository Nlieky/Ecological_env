#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨领域分析器
功能：协调双数据流（进水+出水）分析

基于专利文档：双数据流处理
基于防洪四预框架：跨领域分析
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class StreamData:
    """数据流"""
    stream_id: str
    stream_type: str  # influent（进水）或 effluent（出水）
    data: Dict[str, Any]
    indicators: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CorrelationResult:
    """相关性分析结果"""
    stream1_id: str
    stream2_id: str
    correlation_coefficient: float
    p_value: float = 0.0
    significance: str = ""  # significant, moderate, weak
    description: str = ""


@dataclass
class DualStreamAnalysisResult:
    """双数据流分析结果"""
    influent_summary: Dict[str, Any]
    effluent_summary: Dict[str, Any]
    correlations: Dict[str, CorrelationResult]
    treatment_efficiency: Dict[str, float]
    cross_stream_anomalies: List[Dict[str, Any]]
    analysis_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class CrossDomainAnalyzer:
    """
    跨领域分析器

    提供双数据流（进水+出水）联合分析：
    1. 双数据流联合分析
    2. 相关性计算
    3. 处理效率分析
    4. 跨数据流异常检测
    """

    # 常见指标及正常去除率范围
    INDICATOR_REMOVAL_RATES = {
        "COD": (0.80, 0.95),    # 80-95%
        "BOD": (0.85, 0.98),    # 85-98%
        "SS": (0.85, 0.95),     # 85-95%
        "TN": (0.50, 0.80),     # 50-80%
        "NH3-N": (0.80, 0.98),  # 80-98%
        "TP": (0.70, 0.90)      # 70-90%
    }

    def __init__(self):
        """初始化跨领域分析器"""
        self.name = "跨领域分析器"
        self.version = "2.1.0"
        logger.info(f"[INIT] {self.name} v{self.version} initialized")

    def analyze_dual_stream(self, influent: StreamData, effluent: StreamData) -> DualStreamAnalysisResult:
        """
        双数据流联合分析

        Args:
            influent: 进水数据
            effluent: 出水数据

        Returns:
            双数据流分析结果
        """
        logger.info(f"[DUAL_STREAM] 双数据流分析: {influent.stream_id} vs {effluent.stream_id}")

        # 提取摘要
        influent_summary = self._extract_stream_summary(influent)
        effluent_summary = self._extract_stream_summary(effluent)

        # 计算相关性
        correlations = self._calculate_correlations(influent, effluent)

        # 分析处理效率
        treatment_efficiency = self._analyze_treatment_efficiency(influent, effluent)

        # 跨数据流异常检测
        cross_stream_anomalies = self._detect_cross_stream_anomalies(
            influent, effluent, correlations, treatment_efficiency
        )

        return DualStreamAnalysisResult(
            influent_summary=influent_summary,
            effluent_summary=effluent_summary,
            correlations=correlations,
            treatment_efficiency=treatment_efficiency,
            cross_stream_anomalies=cross_stream_anomalies
        )

    def _extract_stream_summary(self, stream: StreamData) -> Dict[str, Any]:
        """提取数据流摘要"""
        summary = {
            "stream_id": stream.stream_id,
            "stream_type": stream.stream_type,
            "indicators": stream.indicators,
            "data_points": len(stream.data.get("values", [])),
            "time_range": stream.data.get("time_range", {})
        }

        # 计算统计值
        if "values" in stream.data:
            values = stream.data["values"]
            if values:
                summary["statistics"] = {
                    "mean": np.mean(values),
                    "std": np.std(values),
                    "min": np.min(values),
                    "max": np.max(values)
                }

        return summary

    def calculate_correlation(self, stream1: StreamData, stream2: StreamData,
                             indicator: str) -> CorrelationResult:
        """
        计算两数据流相关性

        Args:
            stream1: 数据流1
            stream2: 数据流2
            indicator: 指标名称

        Returns:
            相关性结果
        """
        # 获取数据
        values1 = stream1.data.get("values", [])
        values2 = stream2.data.get("values", [])

        if len(values1) != len(values2) or len(values1) < 2:
            return CorrelationResult(
                stream1_id=stream1.stream_id,
                stream2_id=stream2.stream_id,
                correlation_coefficient=0.0,
                significance="insufficient_data",
                description="数据不足或长度不匹配"
            )

        # 计算皮尔逊相关系数
        corr_coef = np.corrcoef(values1, values2)[0, 1]

        # 判断显著性
        if abs(corr_coef) >= 0.7:
            significance = "significant"
            description = "强相关"
        elif abs(corr_coef) >= 0.4:
            significance = "moderate"
            description = "中等相关"
        elif abs(corr_coef) >= 0.2:
            significance = "weak"
            description = "弱相关"
        else:
            significance = "negligible"
            description = "几乎无相关"

        return CorrelationResult(
            stream1_id=stream1.stream_id,
            stream2_id=stream2.stream_id,
            correlation_coefficient=float(corr_coef),
            significance=significance,
            description=description
        )

    def _calculate_correlations(self, influent: StreamData, effluent: StreamData) -> Dict[str, CorrelationResult]:
        """计算各指标的相关性"""
        correlations = {}

        # 找出共同指标
        common_indicators = set(influent.indicators) & set(effluent.indicators)

        for indicator in common_indicators:
            # 提取该指标的数据
            influent_indicator_data = {
                "stream_id": f"{influent.stream_id}_{indicator}",
                "values": influent.data.get(indicator, [])
            }
            effluent_indicator_data = {
                "stream_id": f"{effluent.stream_id}_{indicator}",
                "values": effluent.data.get(indicator, [])
            }

            # 计算相关性
            corr = self.calculate_correlation(
                StreamData(influent.stream_id, influent.stream_type, influent_indicator_data),
                StreamData(effluent.stream_id, effluent.stream_type, effluent_indicator_data),
                indicator
            )

            correlations[indicator] = corr

        return correlations

    def _analyze_treatment_efficiency(self, influent: StreamData, effluent: StreamData) -> Dict[str, float]:
        """分析处理效率（去除率）"""
        efficiency = {}

        # 计算各指标的去除率
        for indicator in influent.indicators:
            if indicator not in effluent.indicators:
                continue

            influent_values = influent.data.get(indicator, [])
            effluent_values = effluent.data.get(indicator, [])

            if influent_values and effluent_values:
                influent_avg = np.mean(influent_values)
                effluent_avg = np.mean(effluent_values)

                if influent_avg > 0:
                    removal_rate = (influent_avg - effluent_avg) / influent_avg
                    efficiency[indicator] = float(removal_rate)

        return efficiency

    def _detect_cross_stream_anomalies(self, influent: StreamData, effluent: StreamData,
                                       correlations: Dict[str, CorrelationResult],
                                       efficiency: Dict[str, float]) -> List[Dict[str, Any]]:
        """跨数据流异常检测"""
        anomalies = []

        # 检测去除率异常
        for indicator, rate in efficiency.items():
            normal_range = self.INDICATOR_REMOVAL_RATES.get(indicator)
            if normal_range:
                min_rate, max_rate = normal_range
                if rate < min_rate:
                    anomalies.append({
                        "type": "去除率过低",
                        "indicator": indicator,
                        "value": rate,
                        "normal_range": normal_range,
                        "severity": "high" if rate < min_rate * 0.8 else "medium",
                        "description": f"{indicator}去除率({rate:.1%})低于正常范围({min_rate:.1%}-{max_rate:.1%})"
                    })
                elif rate > max_rate:
                    anomalies.append({
                        "type": "去除率异常偏高",
                        "indicator": indicator,
                        "value": rate,
                        "normal_range": normal_range,
                        "severity": "low",
                        "description": f"{indicator}去除率({rate:.1%})异常高于正常范围({min_rate:.1%}-{max_rate:.1%})，可能存在数据问题"
                    })

        # 检测相关性异常
        for indicator, corr in correlations.items():
            if corr.significance == "negligible" and indicator in ["pH", "COD"]:
                anomalies.append({
                    "type": "相关性异常",
                    "indicator": indicator,
                    "value": corr.correlation_coefficient,
                    "description": f"进出水{indicator}相关性异常低({corr.correlation_coefficient:.2f})",
                    "severity": "medium"
                })

        # 检测进水异常高但出水正常（可能稀释）
        for indicator in influent.indicators:
            if indicator not in effluent.indicators:
                continue

            influent_values = influent.data.get(indicator, [])
            effluent_values = effluent.data.get(indicator, [])

            if influent_values and effluent_values:
                influent_avg = np.mean(influent_values)
                effluent_avg = np.mean(effluent_values)

                # 进水高但出水低，且去除率异常
                removal_rate = efficiency.get(indicator, 0)
                if influent_avg > effluent_avg * 2 and removal_rate > 0.95:
                    anomalies.append({
                        "type": "疑似稀释排放",
                        "indicator": indicator,
                        "influent_avg": float(influent_avg),
                        "effluent_avg": float(effluent_avg),
                        "description": f"{indicator}进水浓度({influent_avg:.1f})远高于出水({effluent_avg:.1f})，可能存在稀释",
                        "severity": "high"
                    })

        return anomalies

    def detect_anomalies_across_streams(self, streams: List[StreamData]) -> List[Dict[str, Any]]:
        """
        跨数据流异常检测

        Args:
            streams: 数据流列表

        Returns:
            异常列表
        """
        anomalies = []

        # 分离进水和出水数据流
        influent_streams = [s for s in streams if s.stream_type == "influent"]
        effluent_streams = [s for s in streams if s.stream_type == "effluent"]

        # 对每个进水-出水对进行分析
        for influent in influent_streams:
            for effluent in effluent_streams:
                result = self.analyze_dual_stream(influent, effluent)
                anomalies.extend(result.cross_stream_anomalies)

        return anomalies


# 命令行测试
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    analyzer = CrossDomainAnalyzer()

    print("=" * 80)
    print("跨领域分析器测试")
    print("=" * 80)

    # 创建测试数据
    import numpy as np

    # 进水数据
    influent_data = {
        "pH": list(np.random.normal(7.5, 0.5, 100)),
        "COD": list(np.random.normal(300, 50, 100)),
        "values": list(np.random.normal(100, 20, 100))
    }

    # 出水数据
    effluent_data = {
        "pH": list(np.random.normal(7.2, 0.3, 100)),
        "COD": list(np.random.normal(50, 10, 100)),
        "values": list(np.random.normal(30, 5, 100))
    }

    influent = StreamData(
        stream_id="influent_001",
        stream_type="influent",
        data=influent_data,
        indicators=["pH", "COD"]
    )

    effluent = StreamData(
        stream_id="effluent_001",
        stream_type="effluent",
        data=effluent_data,
        indicators=["pH", "COD"]
    )

    # 执行双数据流分析
    print("\n1. 双数据流分析:")
    print("-" * 80)

    result = analyzer.analyze_dual_stream(influent, effluent)

    print(f"进水摘要: {result.influent_summary}")
    print(f"出水摘要: {result.effluent_summary}")

    # 相关性结果
    print(f"\n2. 相关性分析:")
    print("-" * 80)

    for indicator, corr in result.correlations.items():
        print(f"  {indicator}: {corr.correlation_coefficient:.3f} ({corr.description})")

    # 处理效率
    print(f"\n3. 处理效率:")
    print("-" * 80)

    for indicator, rate in result.treatment_efficiency.items():
        print(f"  {indicator}去除率: {rate:.1%}")

    # 跨数据流异常
    print(f"\n4. 跨数据流异常:")
    print("-" * 80)

    if result.cross_stream_anomalies:
        for anomaly in result.cross_stream_anomalies:
            print(f"  - {anomaly['type']}: {anomaly['description']}")
            print(f"    严重程度: {anomaly['severity']}")
    else:
        print("  未检测到跨数据流异常")

    # 单独测试相关性计算
    print(f"\n5. 单独测试相关性计算:")
    print("-" * 80)

    corr_result = analyzer.calculate_correlation(influent, effluent, "pH")
    print(f"  pH相关性: {corr_result.correlation_coefficient:.3f}")
    print(f"  显著性: {corr_result.significance}")
    print(f"  描述: {corr_result.description}")

    print("\n" + "=" * 80)