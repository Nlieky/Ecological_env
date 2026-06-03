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


def _get_classes():
    """动态导入类（避免顶层相对导入问题）"""
    from .operator_adapter import OperatorAdapter
    from .anomaly_scorer import AnomalyScorer
    from .pattern_recognizer import PatternRecognizer
    from .violation_detector import ViolationDetector
    from .confidence_evaluator import ConfidenceEvaluator
    from .time_series_features import TimeSeriesFeatures
    from .correlation_analysis import CorrelationAnalyzer
    from .trend_analysis import TrendAnalyzer
    return {
        'OperatorAdapter': OperatorAdapter,
        'AnomalyScorer': AnomalyScorer,
        'PatternRecognizer': PatternRecognizer,
        'ViolationDetector': ViolationDetector,
        'ConfidenceEvaluator': ConfidenceEvaluator,
        'TimeSeriesFeatures': TimeSeriesFeatures,
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
                     config: dict = None) -> dict:
    """
    异常检测便捷函数

    Args:
        data: 输入特征数据
        indicators: 指标列表
        config: 配置参数

    Returns:
        包含异常、模式、违规和置信度的字典
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

    except Exception as e:
        logger.error(f"[ANOMALY] 异常检测失败: {e}")
        results["error"] = str(e)

    return results


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
        df = pd.DataFrame(data["values"])

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
