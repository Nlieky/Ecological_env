#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prometheus指标模块
功能：定义和暴露废水监测系统的Prometheus指标
"""

from prometheus_client import Counter, Histogram, Gauge, Info
import logging

logger = logging.getLogger(__name__)

# ==================== 数据流指标 ====================

# 处理的数据记录总数
data_stream_processed = Counter(
    'wastewater_data_stream_processed_total',
    'Total number of data records processed',
    ['stream_type']  # influent, effluent
)

# 数据处理时间
processing_time = Histogram(
    'wastewater_processing_time_seconds',
    'Time spent processing data',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# ==================== 异常检测指标 ====================

# 检测到的异常总数
anomaly_detected = Counter(
    'wastewater_anomaly_detected_total',
    'Total number of anomalies detected',
    ['indicator', 'severity']  # pH, COD, TN, AN, TP; low, medium, high, critical
)

# 当前异常值数量
anomaly_gauge = Gauge(
    'wastewater_anomaly_current',
    'Current number of active anomalies',
    ['indicator']
)

# ==================== 造假检测指标 ====================

# 检测到的造假事件总数
forgery_detected = Counter(
    'wastewater_forgery_detected_total',
    'Total number of forgery events detected',
    ['forgery_type']  # bottle_interference, data_dilution, secret_pipe, etc.
)

# ==================== 违规检测指标 ====================

# 检测到的违规事件总数
violation_detected = Counter(
    'wastewater_violation_detected_total',
    'Total number of regulation violations detected',
    ['violation_type', 'severity']
)

# ==================== 水质指标 ====================

# 当前水质指标值
water_quality_gauge = Gauge(
    'wastewater_water_quality_current',
    'Current water quality indicator values',
    ['stream_type', 'indicator']  # influent/effluent, pH/COD/TN/AN/TP
)

# 超标指标数量
exceedance_count = Gauge(
    'wastewater_exceedance_count',
    'Number of indicators exceeding standards',
    ['stream_type']
)

# ==================== 系统状态指标 ====================

# 子智能体状态
agent_status = Info(
    'wastewater_agent_status',
    'Status of wastewater monitoring agents'
)

# 任务处理时间
task_processing_time = Histogram(
    'wastewater_task_processing_time_seconds',
    'Time spent processing tasks',
    ['agent_type', 'task_type'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
)

# ==================== 数据质量指标 ====================

# 数据有效率
data_quality_rate = Gauge(
    'wastewater_data_quality_rate',
    'Data quality rate (valid records / total records)',
    ['stream_type']
)

# 缺失数据数量
missing_data_count = Gauge(
    'wastewater_missing_data_count',
    'Number of missing data points',
    ['stream_type', 'indicator']
)

# ==================== 告警指标 ====================

# 发送的告警总数
alert_sent = Counter(
    'wastewater_alert_sent_total',
    'Total number of alerts sent',
    ['alert_type', 'channel']  # anomaly, violation; feishu, email, etc.
)

# 告警响应时间
alert_response_time = Histogram(
    'wastewater_alert_response_time_seconds',
    'Time taken to respond to alerts',
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
)


def update_water_quality_metrics(stream_type, data):
    """
    更新水质指标

    Args:
        stream_type: 'influent' 或 'effluent'
        data: 包含水质指标值的字典
    """
    indicator_mapping = {
        'pH值': 'pH',
        '化学需氧量浓度（毫克/升）': 'COD',
        '总氮浓度（毫克/升）': 'TN',
        '氨氮浓度（毫克/升）': 'AN',
        '总磷浓度（毫克/升）': 'TP'
    }

    for chinese_name, english_name in indicator_mapping.items():
        if chinese_name in data:
            value = float(data[chinese_name])
            water_quality_gauge.labels(
                stream_type=stream_type,
                indicator=english_name
            ).set(value)


def update_processing_metrics(stream_type, processing_duration):
    """
    更新处理指标

    Args:
        stream_type: 'influent' 或 'effluent'
        processing_duration: 处理耗时（秒）
    """
    data_stream_processed.labels(stream_type=stream_type).inc()
    processing_time.observe(processing_duration)


def update_anomaly_metrics(indicator, severity, count=1):
    """
    更新异常指标

    Args:
        indicator: 指标名称
        severity: 严重程度
        count: 异常数量
    """
    anomaly_detected.labels(
        indicator=indicator,
        severity=severity
    ).inc(count)


def reset_current_anomalies():
    """重置当前异常计数"""
    for indicator in ['pH', 'COD', 'TN', 'AN', 'TP']:
        anomaly_gauge.labels(indicator=indicator).set(0)


def get_metrics_summary():
    """获取指标摘要"""
    return {
        'data_stream_processed': data_stream_processed._metrics,
        'anomaly_detected': anomaly_detected._metrics,
        'forgery_detected': forgery_detected._metrics,
        'violation_detected': violation_detected._metrics
    }


if __name__ == '__main__':
    # 测试指标
    logger.info("Prometheus指标模块测试")

    # 测试更新水质指标
    test_data = {
        'pH值': 7.2,
        '化学需氧量浓度（毫克/升）': 45,
        '总氮浓度（毫克/升）': 12,
        '氨氮浓度（毫克/升）': 3.5,
        '总磷浓度（毫克/升）': 0.8
    }

    update_water_quality_metrics('influent', test_data)
    logger.info("测试指标已更新")

    logger.info("可用的指标:")
    logger.info("  - wastewater_data_stream_processed_total")
    logger.info("  - wastewater_anomaly_detected_total")
    logger.info("  - wastewater_water_quality_current")
    logger.info("  - wastewater_processing_time_seconds")
    logger.info("  等等...")
