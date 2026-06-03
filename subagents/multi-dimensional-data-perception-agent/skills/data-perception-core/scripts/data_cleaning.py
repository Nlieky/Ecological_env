# subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/data_cleaning.py
"""
数据清洗模块 - 数据质量控制
"""
from typing import Dict, Any, List
import numpy as np
import logging

logger = logging.getLogger(__name__)


class DataCleaningModule:
    """数据清洗模块"""

    # 各指标的合理范围（测试需要验证的类属性）
    valid_ranges = {
        "pH值": (0, 14),
        "pH": (0, 14),
        "化学需氧量浓度（毫克/升）": (0, 1000),
        "COD": (0, 1000),
        "总氮浓度（毫克/升）": (0, 100),
        "TN": (0, 100),
        "氨氮浓度（毫克/升）": (0, 50),
        "NH3_N": (0, 50),
        "总磷浓度（毫克/升）": (0, 20),
        "TP": (0, 20),
        "悬浮物浓度（毫克/升）": (0, 500),
        "SS": (0, 500)
    }

    def __init__(self):
        pass

    def clean_water_quality_data(
        self,
        data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """清洗水质数据

        Args:
            data: 原始数据列表

        Returns:
            清洗后的数据和质控报告
        """
        # Input validation
        if data is None:
            logger.warning("Received None input for data cleaning")
            return {
                "cleaned_data": [],
                "quality_report": {
                    "completeness": 0,
                    "anomaly_rate": 0,
                    "missing_count": 0,
                    "anomaly_count": 0,
                    "cleaned_count": 0,
                    "total_records": 0
                },
                "error": "Input data is None"
            }

        if not isinstance(data, list):
            logger.warning(f"Invalid input type: expected list, got {type(data)}")
            return {
                "cleaned_data": [],
                "quality_report": {
                    "completeness": 0,
                    "anomaly_rate": 0,
                    "missing_count": 0,
                    "anomaly_count": 0,
                    "cleaned_count": 0,
                    "total_records": 0
                },
                "error": f"Invalid input type: {type(data)}"
            }

        if len(data) == 0:
            logger.info("Received empty data list for cleaning")
            return {
                "cleaned_data": [],
                "quality_report": {
                    "completeness": 1.0,
                    "anomaly_rate": 0,
                    "missing_count": 0,
                    "anomaly_count": 0,
                    "cleaned_count": 0
                }
            }

        logger.info(f"Starting data cleaning for {len(data)} records")
        cleaned_data = []
        missing_count = 0
        anomaly_count = 0

        for record in data:
            if not isinstance(record, dict):
                logger.warning(f"Skipping invalid record (not a dict): {type(record)}")
                anomaly_count += 1
                continue

            cleaned_record = {}
            record_has_anomaly = False

            for key, value in record.items():
                # 检查缺失值
                if value is None or value == "" or value == "/":
                    missing_count += 1
                    cleaned_record[key] = None
                    continue

                # 检查异常值
                if key in self.valid_ranges:
                    min_val, max_val = self.valid_ranges[key]
                    try:
                        num_value = float(value)
                        if num_value < min_val or num_value > max_val:
                            anomaly_count += 1
                            record_has_anomaly = True
                            cleaned_record[key] = None
                        else:
                            cleaned_record[key] = num_value
                    except (ValueError, TypeError):
                        anomaly_count += 1
                        cleaned_record[key] = None
                else:
                    cleaned_record[key] = value

            if not record_has_anomaly:
                cleaned_data.append(cleaned_record)

        # 计算质量指标 - 使用实际字段数量而非固定范围数量
        total_values = sum(len(record) for record in data if isinstance(record, dict))
        if total_values > 0:
            completeness = 1 - (missing_count / total_values)
            anomaly_rate = anomaly_count / total_values
        else:
            completeness = 0
            anomaly_rate = 0

        quality_report = {
            "completeness": round(completeness, 3),
            "anomaly_rate": round(anomaly_rate, 3),
            "missing_count": missing_count,
            "anomaly_count": anomaly_count,
            "cleaned_count": len(cleaned_data),
            "total_records": len(data)
        }

        logger.info(f"Data cleaning complete: {len(cleaned_data)} records cleaned, "
                    f"{missing_count} missing values, {anomaly_count} anomalies detected")

        return {
            "cleaned_data": cleaned_data,
            "quality_report": quality_report
        }


# Module-level export for unit test validation
valid_ranges = DataCleaningModule.valid_ranges
