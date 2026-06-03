# subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/standardization.py
"""
标准化模块 - 数据格式统一
"""
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class StandardizationModule:
    """标准化模块"""

    # 字段名映射表（测试需要验证的类属性）
    field_mapping = {
        "pH值": "pH",
        "化学需氧量浓度（毫克/升）": "COD",
        "总氮浓度（毫克/升）": "TN",
        "氨氮浓度（毫克/升）": "NH3_N",
        "总磷浓度（毫克/升）": "TP",
        "悬浮物浓度（毫克/升）": "SS",
        "流量（升/秒）": "flow_rate",
        "排放量（吨）": "discharge_volume"
    }

    def __init__(self):
        pass

    def standardize_water_quality(
        self,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """标准化水质数据格式

        Args:
            input_data: 包含influent和effluent的输入数据

        Returns:
            标准化后的数据
        """
        # Input validation
        if input_data is None:
            logger.warning("Received None input for standardization")
            return {
                "water_quality": {
                    "influent": [],
                    "effluent": []
                },
                "metadata": {
                    "skipped_count": 0,
                    "total_input_records": 0
                },
                "error": "Input data is None"
            }

        if not isinstance(input_data, dict):
            logger.warning(f"Invalid input type: expected dict, got {type(input_data)}")
            return {
                "water_quality": {
                    "influent": [],
                    "effluent": []
                },
                "metadata": {
                    "skipped_count": 0,
                    "total_input_records": 0
                },
                "error": f"Invalid input type: {type(input_data)}"
            }

        # Check for required keys
        has_influent = "influent" in input_data
        has_effluent = "effluent" in input_data

        if not has_influent and not has_effluent:
            logger.warning("Input data missing both 'influent' and 'effluent' keys")
            return {
                "water_quality": {
                    "influent": [],
                    "effluent": []
                },
                "metadata": {
                    "skipped_count": 0,
                    "total_input_records": 0
                },
                "error": "Input data missing both 'influent' and 'effluent' keys"
            }

        logger.info(f"Starting standardization (influent: {has_influent}, effluent: {has_effluent})")

        result = {
            "water_quality": {
                "influent": [],
                "effluent": []
            }
        }

        skipped_count = 0
        total_input_records = 0

        # 标准化进水数据
        if has_influent:
            influent_data = input_data["influent"]
            if not isinstance(influent_data, list):
                logger.warning(f"Influent data is not a list: {type(influent_data)}")
                influent_data = []

            for record in influent_data:
                total_input_records += 1
                if not isinstance(record, dict):
                    logger.warning(f"Skipping non-dict record in influent: {type(record)}")
                    skipped_count += 1
                    continue
                standardized = self._standardize_record(record)
                result["water_quality"]["influent"].append(standardized)

        # 标准化出水数据
        if has_effluent:
            effluent_data = input_data["effluent"]
            if not isinstance(effluent_data, list):
                logger.warning(f"Effluent data is not a list: {type(effluent_data)}")
                effluent_data = []

            for record in effluent_data:
                total_input_records += 1
                if not isinstance(record, dict):
                    logger.warning(f"Skipping non-dict record in effluent: {type(record)}")
                    skipped_count += 1
                    continue
                standardized = self._standardize_record(record)
                result["water_quality"]["effluent"].append(standardized)

        result["metadata"] = {
            "skipped_count": skipped_count,
            "total_input_records": total_input_records
        }

        logger.info(f"Standardization complete: {len(result['water_quality']['influent'])} influent records, "
                    f"{len(result['water_quality']['effluent'])} effluent records, "
                    f"{skipped_count} skipped out of {total_input_records} total")

        return result

    def _standardize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """标准化单条记录

        Args:
            record: 原始记录字典

        Returns:
            标准化后的记录字典
        """
        if record is None:
            logger.warning("Received None record for standardization")
            return {}

        if not isinstance(record, dict):
            logger.warning(f"Invalid record type: expected dict, got {type(record)}")
            return {}

        standardized = {}

        for key, value in record.items():
            # 应用字段映射
            new_key = self.field_mapping.get(key, key)
            standardized[new_key] = value

        return standardized


# Module-level export for unit test validation
field_mapping = StandardizationModule.field_mapping
