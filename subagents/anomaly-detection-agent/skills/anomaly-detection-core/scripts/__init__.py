#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异常检测核心技能包

提供算子适配、异常评分、模式识别、违规检测、置信度评估和特征分析功能。
"""

# 移除顶层相对导入，改为在函数内动态导入
__all__ = [
    "OperatorAdapter",
    "AnomalyScorer",
    "PatternRecognizer",
    "ViolationDetector",
    "ConfidenceEvaluator",
    "TimeSeriesFeatures",  # 从feature-analysis迁移
    "CorrelationAnalyzer",  # 从feature-analysis迁移
    "TrendAnalyzer",  # 从feature-analysis迁移
    "detect_anomalies",
    "run_anomaly_detection",
    "extract_features",  # 新增：特征提取入口
    "main",
    "process",
    "execute"
]

__version__ = "2.2.0"


from typing import Dict, List, Any

def standardize_anomaly_output(anomaly_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    标准化异常检测输出格式

    Args:
        anomaly_output: 原始异常检测输出

    Returns:
        标准化后的输出，包含标准格式的anomalies列表
    """
    if not anomaly_output or not isinstance(anomaly_output, dict):
        return {"anomalies": [], "status": "error", "message": "Invalid input"}

    # 获取anomalies列表（支持多种路径）
    anomalies = []
    if "anomalies" in anomaly_output:
        anomalies = anomaly_output["anomalies"]
    elif "result" in anomaly_output and isinstance(anomaly_output["result"], dict):
        result = anomaly_output["result"]
        if "anomalies" in result:
            anomalies = result["anomalies"]
        elif "output" in result and isinstance(result["output"], dict) and "anomalies" in result["output"]:
            anomalies = result["output"]["anomalies"]

    if not anomalies:
        return {
            "anomalies": [],
            "status": "success",
            "message": "No anomalies found",
            "patterns": anomaly_output.get("patterns", {}),
            "violations": anomaly_output.get("violations", [])
        }

    # 标准化每个异常点
    standardized_anomalies = []
    for anomaly in anomalies:
        if not isinstance(anomaly, dict):
            continue

        # 安全地转换分数值
        score_raw = anomaly.get("score", anomaly.get("anomaly_score", 0.5))
        try:
            score = float(score_raw)
        except (ValueError, TypeError):
            score = 0.5

        # 构建标准格式
        std_anomaly = {
            "indicator": _format_indicator(anomaly),
            "times": _format_timestamp(anomaly),
            "score": score,
            "pattern": anomaly.get("pattern", anomaly.get("type", "unknown")),
            "severity": _determine_severity(anomaly)
        }

        standardized_anomalies.append(std_anomaly)

    # 返回标准化输出
    return {
        "anomalies": standardized_anomalies,
        "status": "success",
        "patterns": anomaly_output.get("patterns", {}),
        "violations": anomaly_output.get("violations", []),
        "confidence": anomaly_output.get("confidence", {}),
        "suspicion_level": anomaly_output.get("suspicion_level", "medium"),
        "features": anomaly_output.get("features"),
        "features_error": anomaly_output.get("features_error")
    }

def _format_indicator(anomaly: Dict[str, Any]) -> str:
    """格式化指标名称为标准格式: {source}_{indicator}"""
    indicator = anomaly.get("indicator", anomaly.get("feature", "unknown"))
    source = anomaly.get("source", "effluent")  # 默认为出水

    # 移除可能的单位后缀
    indicator = indicator.replace("（毫克/升）", "").replace("(mg/L)", "")

    # 标准化中文字段名
    field_mapping = {
        "pH值": "pH",
        "化学需氧量浓度": "COD",
        "总氮浓度": "TN",
        "氨氮浓度": "NH3_N",
        "总磷浓度": "TP"
    }

    if indicator in field_mapping:
        indicator = field_mapping[indicator]

    return f"{source}_{indicator}"

def _format_timestamp(anomaly: Dict[str, Any]) -> str:
    """格式化时间戳"""
    # 支持多种时间字段
    time_fields = ["timestamp", "time", "times", "datetime", "监测时间"]

    for field in time_fields:
        if field in anomaly and anomaly[field]:
            time_val = anomaly[field]
            # 如果是整数（索引），返回原值
            if isinstance(time_val, int):
                return str(time_val)
            # 如果是字符串，确保格式
            return str(time_val)

    # 如果没有时间字段，返回空字符串
    return ""

def _determine_severity(anomaly: Dict[str, Any]) -> str:
    """确定严重程度"""
    # 如果已经有severity字段，直接使用
    if "severity" in anomaly:
        return anomaly["severity"]

    # 基于score确定（安全转换）
    score_raw = anomaly.get("score", anomaly.get("anomaly_score", 0.5))
    try:
        score = float(score_raw)
    except (ValueError, TypeError):
        score = 0.5

    if score >= 0.8:
        return "high"
    elif score >= 0.5:
        return "medium"
    else:
        return "low"


def _get_classes():
    """动态导入类（避免顶层相对导入问题）"""
    from .operator_adapter import OperatorAdapter
    from .anomaly_scorer import AnomalyScorer
    from .pattern_recognizer import PatternRecognizer
    from .violation_detector import ViolationDetector
    from .confidence_evaluator import ConfidenceEvaluator
    from .time_series_features import TimeSeriesFeatureExtractor
    from .correlation_analysis import CorrelationAnalyzer
    from .trend_analysis import TrendAnalyzer
    return {
        'OperatorAdapter': OperatorAdapter,
        'AnomalyScorer': AnomalyScorer,
        'PatternRecognizer': PatternRecognizer,
        'ViolationDetector': ViolationDetector,
        'ConfidenceEvaluator': ConfidenceEvaluator,
        'TimeSeriesFeatureExtractor': TimeSeriesFeatureExtractor,
        'TimeSeriesFeatures': TimeSeriesFeatureExtractor,  # 别名兼容
        'CorrelationAnalyzer': CorrelationAnalyzer,
        'TrendAnalyzer': TrendAnalyzer
    }


# 导出类（延迟导入）
def __getattr__(name: str):
    """支持延迟导入"""
    classes = _get_classes()
    if name in classes:
        return classes[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def detect_anomalies(data: "pd.DataFrame", indicators: list,
                     config: dict = None, include_features: bool = False) -> dict:
    """
    异常检测便捷函数

    Args:
        data: 输入特征数据
        indicators: 指标列表
        config: 配置参数
        include_features: 是否包含时间序列特征提取（默认: False）

    Returns:
        包含异常、模式、违规、置信度和可选特征的字典
    """
    import logging
    import pandas as pd
    import numpy as np

    logger = logging.getLogger(__name__)

    if config is None:
        config = {
            "operators": ["zscore", "iqr", "isolation_forest"],
            "pattern_threshold": 0.7,
            "contamination": 0.1
        }

    results = {
        "anomalies": [],
        "patterns": {},
        "violations": [],
        "confidence": {},
        "metadata": config
    }

    try:
        # 动态导入类
        classes = _get_classes()
        OperatorAdapter = classes['OperatorAdapter']
        AnomalyScorer = classes['AnomalyScorer']
        PatternRecognizer = classes['PatternRecognizer']
        ViolationDetector = classes['ViolationDetector']
        ConfidenceEvaluator = classes['ConfidenceEvaluator']

        # 1. 算子适配与检测
        logger.info("[ANOMALY] 应用异常检测算子...")
        adapter = OperatorAdapter()
        operator_results = adapter.apply_operators(
            data, indicators, config.get("operators", ["zscore", "iqr"])
        )

        # 2. 异常评分
        logger.info("[ANOMALY] 计算异常分数...")
        scorer = AnomalyScorer()
        anomaly_scores = scorer.calculate_scores(data, operator_results)
        results["anomaly_scores"] = anomaly_scores

        # 3. 模式识别
        logger.info("[ANOMALY] 识别异常模式...")
        recognizer = PatternRecognizer()
        pattern_threshold = config.get("pattern_threshold", 0.7)
        pattern_results = recognizer.recognize_patterns(
            data, anomaly_scores, pattern_threshold
        )
        results["anomalies"] = pattern_results["anomalies"]
        results["patterns"] = pattern_results["patterns"]

        # 4. 违规检测
        logger.info("[ANOMALY] 检测违规模式...")
        detector = ViolationDetector()
        violation_results = detector.detect_violations(
            pattern_results["anomalies"], data
        )
        results["violations"] = violation_results["violations"]
        results["suspicion_level"] = violation_results["suspicion_level"]

        # 5. 置信度评估
        logger.info("[ANOMALY] 评估置信度...")
        evaluator = ConfidenceEvaluator()
        confidence_results = evaluator.evaluate(
            anomaly_scores, pattern_results, operator_results
        )
        results["confidence"] = confidence_results

        logger.info("[ANOMALY] 异常检测完成")

        # 6. 特征提取（可选）
        if include_features:
            logger.info("[ANOMALY] 提取时间序列特征...")
            try:
                classes = _get_classes()
                TimeSeriesFeatures = classes.get('TimeSeriesFeatures')
                CorrelationAnalyzer = classes.get('CorrelationAnalyzer')
                TrendAnalyzer = classes.get('TrendAnalyzer')

                features = {}

                # 时序特征提取
                if TimeSeriesFeatures:
                    ts_extractor = TimeSeriesFeatures()
                    for indicator in indicators:
                        if indicator in data.columns:
                            series_data = data[indicator].dropna()
                            if len(series_data) > 0:
                                try:
                                    ts_features = ts_extractor.extract_features(series_data)
                                    features[indicator] = ts_features
                                except Exception as e:
                                    logger.warning(f"[ANOMALY] 特征提取失败 {indicator}: {e}")

                # 相关性分析
                if CorrelationAnalyzer:
                    corr_analyzer = CorrelationAnalyzer()
                    corr_data = data[indicators].select_dtypes(include=[np.number])
                    if not corr_data.empty:
                        try:
                            correlations = corr_analyzer.analyze(corr_data, method="pearson")
                            features["_correlations"] = correlations
                        except Exception as e:
                            logger.warning(f"[ANOMALY] 相关性分析失败: {e}")

                # 趋势分析
                if TrendAnalyzer:
                    trend_analyzer = TrendAnalyzer()
                    for indicator in indicators:
                        if indicator in data.columns:
                            series_data = data[indicator].dropna()
                            if len(series_data) > 1:
                                try:
                                    trend = trend_analyzer.analyze_trend(series_data)
                                    if "_trends" not in features:
                                        features["_trends"] = {}
                                    features["_trends"][indicator] = trend
                                except Exception as e:
                                    logger.warning(f"[ANOMALY] 趋势分析失败 {indicator}: {e}")

                results["features"] = features
                logger.info(f"[ANOMALY] 特征提取完成: {len(features)} 个指标")
            except Exception as e:
                logger.error(f"[ANOMALY] 特征提取失败: {e}")
                results["features_error"] = str(e)

    except Exception as e:
        logger.error(f"[ANOMALY] 异常检测失败: {e}")
        results["error"] = str(e)

    # 标准化输出格式
    return standardize_anomaly_output(results)


def extract_features(data: "pd.DataFrame", indicators: list,
                    config: dict = None) -> dict:
    """
    特征提取便捷函数（从feature-analysis迁移）

    Args:
        data: 输入数据
        indicators: 指标列表
        config: 配置参数

    Returns:
        包含时序特征、相关性分析和趋势分析的字典
    """
    import logging
    import pandas as pd

    logger = logging.getLogger(__name__)

    if config is None:
        config = {
            "include_time_features": True,
            "include_correlation": True,
            "include_trend": True,
            "correlation_method": "pearson"
        }

    results = {
        "time_series_features": {},
        "correlations": {},
        "trends": {},
        "metadata": config
    }

    try:
        # 动态导入类
        classes = _get_classes()
        TimeSeriesFeatures = classes.get('TimeSeriesFeatures')
        CorrelationAnalyzer = classes.get('CorrelationAnalyzer')
        TrendAnalyzer = classes.get('TrendAnalyzer')

        # 1. 时序特征提取
        if config.get("include_time_features", True) and TimeSeriesFeatures:
            logger.info("[FEATURE] 提取时序特征...")
            extractor = TimeSeriesFeatures()
            for indicator in indicators:
                if indicator in data.columns:
                    series_data = data[indicator].dropna()
                    if len(series_data) > 0:
                        features = extractor.extract_features(series_data)
                        results["time_series_features"][indicator] = features

        # 2. 相关性分析
        if config.get("include_correlation", True) and CorrelationAnalyzer:
            logger.info("[FEATURE] 分析相关性...")
            analyzer = CorrelationAnalyzer()
            corr_data = data[indicators].select_dtypes(include=[np.number])
            if not corr_data.empty:
                correlations = analyzer.analyze(corr_data, method=config.get("correlation_method", "pearson"))
                results["correlations"] = correlations

        # 3. 趋势分析
        if config.get("include_trend", True) and TrendAnalyzer:
            logger.info("[FEATURE] 分析趋势...")
            trend_analyzer = TrendAnalyzer()
            for indicator in indicators:
                if indicator in data.columns:
                    series_data = data[indicator].dropna()
                    if len(series_data) > 1:
                        trend = trend_analyzer.analyze_trend(series_data)
                        results["trends"][indicator] = trend

        logger.info("[FEATURE] 特征提取完成")

    except Exception as e:
        logger.error(f"[FEATURE] 特征提取失败: {e}")
        results["error"] = str(e)

    return results


def run_anomaly_detection(task: dict) -> dict:
    """
    运行异常检测流程（用于子智能体调用）

    Args:
        task: 任务字典，包含:
            - task_id: 任务ID
            - data: 输入数据
            - indicators: 指标列表
            - config: 配置参数（可选）

    Returns:
        标准格式的结果字典
    """
    import logging
    logger = logging.getLogger(__name__)

    task_id = task.get("task_id", "unknown")
    data = task.get("data")
    indicators = task.get("indicators", [])
    config = task.get("config", {})

    logger.info(f"[TASK-{task_id}] 开始异常检测")

    result = {
        "task_id": task_id,
        "agent": "anomaly-detection-agent",
        "status": "success",
        "result": {},
        "metadata": {
            "indicators": indicators,
            "config": config
        }
    }

    try:
        # 执行异常检测
        detection_result = detect_anomalies(data, indicators, config)
        result["result"] = detection_result

        logger.info(f"[TASK-{task_id}] 异常检测完成")

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        logger.error(f"[TASK-{task_id}] 异常检测失败: {e}")

    return result


# LLM调用入口函数
def main(data: dict = None, indicators: list = None, config: dict = None,
         task: dict = None, **kwargs) -> dict:
    """
    主入口函数 - LLM动态调用

    Args:
        data: 输入数据字典（包含 values）
        indicators: 指标列表
        config: 配置参数
        task: 任务字典
        **kwargs: 其他参数

    Returns:
        异常检测结果
    """
    import pandas as pd
    import logging

    logger = logging.getLogger(__name__)

    # 从task中提取参数
    if task:
        data = data or task.get("data")
        indicators = indicators or task.get("indicators", [])
        config = config or task.get("config")

    # 如果没有指定indicators，从data中提取
    if not indicators and data:
        values = data.get("values", {})
        indicators = list(values.keys())

    # 转换为DataFrame格式
    df = None
    if data and "values" in data:
        values_dict = data["values"]
        # 验证所有数组长度一致
        lengths = [len(v) for v in values_dict.values()]
        if len(set(lengths)) > 1:
            print(f"[ERROR] 数组长度不一致: {dict(zip(values_dict.keys(), lengths))}")
            # 截断到最小长度
            min_len = min(lengths)
            print(f"[ERROR] 截断到最小长度: {min_len}")
            values_dict = {k: v[:min_len] for k, v in values_dict.items()}
        df = pd.DataFrame(values_dict)
        print(f"[DATA] 创建DataFrame: {df.shape}, 列: {list(df.columns)}")

    if df is None or df.empty:
        return {
            "status": "error",
            "error": "No data provided",
            "anomalies": [],
            "patterns": {},
            "violations": [],
            "confidence": {}
        }

    # 根据操作类型选择功能
    operation = kwargs.get("operation", "anomaly_detection")

    if operation == "feature_extraction":
        # 执行特征提取
        result = extract_features(df, indicators, config)
    else:
        # 执行完整异常检测（默认）
        result = detect_anomalies(df, indicators, config)

    result["status"] = "success"

    return result


def process(data: dict, **kwargs) -> dict:
    """处理函数别名"""
    return main(data=data, **kwargs)


def execute(data: dict, **kwargs) -> dict:
    """执行函数别名"""
    return main(data=data, **kwargs)
