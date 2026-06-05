# subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/standardization.py
"""
标准化模块 - 数据格式统一
"""
from typing import Dict, Any, List
import logging
import re

logger = logging.getLogger(__name__)


class FieldMapper:
    """字段映射器 - 支持正则表达式匹配"""

    # 基础映射表（精确匹配）
    EXACT_MAPPING = {
        "pH值": "pH",
        "化学需氧量浓度（毫克/升）": "COD",
        "化学需氧量浓度": "COD",
        "总氮浓度（毫克/升）": "TN",
        "总氮浓度": "TN",
        "氨氮浓度（毫克/升）": "NH3_N",
        "氨氮浓度": "NH3_N",
        "总磷浓度（毫克/升）": "TP",
        "总磷浓度": "TP",
        "悬浮物浓度（毫克/升）": "SS",
        "悬浮物浓度": "SS",
        "流量（升/秒）": "flow_rate",
        "流量": "flow_rate",
        "排放量（吨）": "discharge_volume",
        "排放量": "discharge_volume"
    }

    # 正则模式映射（模糊匹配）
    REGEX_PATTERNS = [
        (r"pH.*", "pH"),
        (r".*化学需氧量.*", "COD"),
        (r".*总氮.*", "TN"),
        (r".*氨氮.*", "NH3_N"),
        (r".*总磷.*", "TP"),
        (r".*悬浮物.*", "SS"),
        (r".*流量.*", "flow_rate"),
        (r".*排放量.*", "discharge_volume")
    ]

    @classmethod
    def map_field(cls, field_name: str) -> str:
        """
        映射字段名到标准名

        Args:
            field_name: 原始字段名

        Returns:
            标准字段名
        """
        # 1. 尝试精确匹配
        if field_name in cls.EXACT_MAPPING:
            return cls.EXACT_MAPPING[field_name]

        # 2. 尝试正则匹配
        for pattern, standard_name in cls.REGEX_PATTERNS:
            if re.search(pattern, field_name):
                return standard_name

        # 3. 未匹配，返回原字段名
        return field_name

    @classmethod
    def get_unmapped_fields(cls, field_names: list) -> list:
        """获取未映射的字段列表"""
        return [f for f in field_names if cls.map_field(f) == f and f not in cls.EXACT_MAPPING.values()]


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

        # Collect all field names from input for unmapped field tracking
        all_field_names = set()
        if has_influent and isinstance(input_data.get("influent"), list):
            for record in input_data["influent"]:
                if isinstance(record, dict):
                    all_field_names.update(record.keys())
        if has_effluent and isinstance(input_data.get("effluent"), list):
            for record in input_data["effluent"]:
                if isinstance(record, dict):
                    all_field_names.update(record.keys())

        result["metadata"] = {
            "skipped_count": skipped_count,
            "total_input_records": total_input_records,
            "unmapped_fields": FieldMapper.get_unmapped_fields(list(all_field_names))
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
            # 应用字段映射（使用FieldMapper支持正则匹配）
            new_key = FieldMapper.map_field(key)
            standardized[new_key] = value

        return standardized


# Module-level export for unit test validation
field_mapping = StandardizationModule.field_mapping
