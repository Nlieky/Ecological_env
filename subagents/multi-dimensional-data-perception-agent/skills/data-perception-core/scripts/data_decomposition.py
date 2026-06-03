# subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/data_decomposition.py
"""
数据分解模块 - 将复合数据按类型分解
"""
import logging
from typing import Dict, Any, List

# Constants for data types
DATA_TYPE_WATER_QUALITY = "water_quality"
DATA_TYPE_FLOW = "flow"
DATA_TYPE_EQUIPMENT_STATUS = "equipment_status"
DATA_TYPE_PROCESS_PARAMETERS = "process_parameters"
DATA_TYPE_MAINTENANCE_RECORDS = "maintenance_records"
DATA_TYPE_PRODUCTION_RECORDS = "production_records"
DATA_TYPE_SOURCE_INFO = "source_info"
DATA_TYPE_MONITORING_POINT_INFO = "monitoring_point_info"

# Constants for source types
SOURCE_TYPE_INFLUENT = "influent"
SOURCE_TYPE_EFFLUENT = "effluent"

# Constants for field names
FIELD_MONITORING_TIME = "监测时间"
DEFAULT_TIMESTAMP = ""

# Logger for this module
logger = logging.getLogger(__name__)


class DataDecompositionModule:
    """数据分解模块"""

    # 数据类型映射（测试需要验证的类属性）
    data_type_mapping = {
        "pH": DATA_TYPE_WATER_QUALITY,
        "pH值": DATA_TYPE_WATER_QUALITY,
        "化学需氧量": DATA_TYPE_WATER_QUALITY,
        "化学需氧量浓度（毫克/升）": DATA_TYPE_WATER_QUALITY,
        "总氮": DATA_TYPE_WATER_QUALITY,
        "总氮浓度（毫克/升）": DATA_TYPE_WATER_QUALITY,
        "氨氮": DATA_TYPE_WATER_QUALITY,
        "氨氮浓度（毫克/升）": DATA_TYPE_WATER_QUALITY,
        "总磷": DATA_TYPE_WATER_QUALITY,
        "总磷浓度（毫克/升）": DATA_TYPE_WATER_QUALITY,
        "悬浮物": DATA_TYPE_WATER_QUALITY,
        "悬浮物浓度（毫克/升）": DATA_TYPE_WATER_QUALITY,
        "流量": DATA_TYPE_FLOW,
        "流量（升/秒）": DATA_TYPE_FLOW,
        "排放量": DATA_TYPE_FLOW,
        "排放量（吨）": DATA_TYPE_FLOW
    }

    def __init__(self):
        pass

    def decompose_multi_dimensional(
        self,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分解多维数据

        Args:
            input_data: 原始数据，包含influent和effluent

        Returns:
            按8类数据类型分解的数据
        """
        # Input validation
        if not isinstance(input_data, dict):
            logger.error(f"Invalid input type: expected dict, got {type(input_data).__name__}")
            return self._get_empty_result()

        result = self._get_empty_result()

        # 分解进水数据
        if SOURCE_TYPE_INFLUENT in input_data:
            influent_data = input_data[SOURCE_TYPE_INFLUENT]
            if not isinstance(influent_data, list):
                logger.error(f"Invalid influent data type: expected list, got {type(influent_data).__name__}")
            else:
                for record in influent_data:
                    self._classify_record(record, result, SOURCE_TYPE_INFLUENT)

        # 分解出水数据
        if SOURCE_TYPE_EFFLUENT in input_data:
            effluent_data = input_data[SOURCE_TYPE_EFFLUENT]
            if not isinstance(effluent_data, list):
                logger.error(f"Invalid effluent data type: expected list, got {type(effluent_data).__name__}")
            else:
                for record in effluent_data:
                    self._classify_record(record, result, SOURCE_TYPE_EFFLUENT)

        return result

    def _get_empty_result(self) -> Dict[str, Any]:
        """获取空的分解结果结构"""
        return {
            DATA_TYPE_WATER_QUALITY: {SOURCE_TYPE_INFLUENT: [], SOURCE_TYPE_EFFLUENT: []},
            DATA_TYPE_FLOW: {SOURCE_TYPE_INFLUENT: [], SOURCE_TYPE_EFFLUENT: []},
            DATA_TYPE_EQUIPMENT_STATUS: [],
            DATA_TYPE_PROCESS_PARAMETERS: [],
            DATA_TYPE_MAINTENANCE_RECORDS: [],
            DATA_TYPE_PRODUCTION_RECORDS: [],
            DATA_TYPE_SOURCE_INFO: {},
            DATA_TYPE_MONITORING_POINT_INFO: {}
        }

    def _classify_record(
        self,
        record: Dict[str, Any],
        result: Dict[str, Any],
        source_type: str
    ) -> None:
        """将记录分类到对应的数据类型

        Args:
            record: 要分类的记录
            result: 结果字典
            source_type: 来源类型（influent或effluent）
        """
        # Input validation
        if not isinstance(record, dict):
            logger.warning(f"Invalid record type: expected dict, got {type(record).__name__}")
            return

        if source_type not in (SOURCE_TYPE_INFLUENT, SOURCE_TYPE_EFFLUENT):
            logger.warning(f"Invalid source_type: {source_type}")
            return

        water_quality_data = {}
        flow_data = {}

        for key, value in record.items():
            data_type = self.data_type_mapping.get(key)

            if data_type == DATA_TYPE_WATER_QUALITY:
                water_quality_data[key] = value
            elif data_type == DATA_TYPE_FLOW:
                flow_data[key] = value
            # Records that don't match data_type_mapping are silently ignored
            # (unmapped fields are not included in the decomposition)

        # 添加时间戳
        timestamp = record.get(FIELD_MONITORING_TIME, DEFAULT_TIMESTAMP)
        if water_quality_data:
            water_quality_data[FIELD_MONITORING_TIME] = timestamp
            result[DATA_TYPE_WATER_QUALITY][source_type].append(water_quality_data)

        if flow_data:
            flow_data[FIELD_MONITORING_TIME] = timestamp
            result[DATA_TYPE_FLOW][source_type].append(flow_data)


# Module-level export for unit test validation
data_type_mapping = DataDecompositionModule.data_type_mapping
