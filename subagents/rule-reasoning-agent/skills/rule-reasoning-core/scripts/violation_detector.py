"""
违规判定器 - 基于规则和异常特征判定违规类型

Code Quality Improvements:
- Added proper error handling for file operations
- Added logging instead of warnings for unimplemented conditions
- Extracted magic numbers to named constants with documentation
- Added input validation for public methods
- Moved imports to module level
- Improved duration parsing robustness
"""
import yaml
import logging
import warnings
from pathlib import Path
from typing import Dict, Any, List, Optional

# Configure module-level logger
logger = logging.getLogger(__name__)


# ============================================
# Constants (Magic Numbers Extraction)
# ============================================

# Confidence calculation constants
DEFAULT_BASE_CONFIDENCE = 0.7
STABLE_ANOMALY_CONFIDENCE_BOOST = 0.15
SUDDEN_ANOMALY_CONFIDENCE_BOOST = 0.10
LONG_DURATION_CONFIDENCE_BOOST = 0.10
LONG_DURATION_HOURS_THRESHOLD = 4
MAX_CONFIDENCE = 1.0

# Duration parsing constants
SUPPORTED_TIME_UNITS = {'h': 'hours', 'm': 'minutes', 's': 'seconds', 'd': 'days'}
DEFAULT_TIME_UNIT = 'h'  # Default to hours if no unit specified

# Anomaly type constants
ANOMALY_TYPE_STABLE = "平稳异常"
ANOMALY_TYPE_SUDDEN = "突变异常"

# Equipment status constants
EQUIPMENT_STATUS_RUNNING = "running"
EQUIPMENT_STATUS_SHUTDOWN = "shutdown"

# Complex condition types that are not yet implemented
UNIMPLEMENTED_CONDITION_TYPES = {
    "process_check",
    "time_check",
    "multi_indicator_sync",
    "removal_rate_check",
    "flow_check",
    "data_missing_rate",
    "off_hours_check"
}


class ViolationDetectorConfigError(Exception):
    """Exception raised for configuration loading errors."""
    pass


class ViolationDetectorInputError(Exception):
    """Exception raised for invalid input data."""
    pass


class ViolationDetector:
    """违规判定器

    基于规则和异常特征判定违规类型，支持误报过滤。
    """

    # 违规判定规则（测试需要验证的类属性，实际值从YAML加载）
    rules = {}

    def __init__(self, rule_config_path: str = "shared/configs/rule_config.yaml"):
        """初始化违规判定器

        Args:
            rule_config_path: 规则配置文件路径，相对于项目根目录或绝对路径

        Raises:
            ViolationDetectorConfigError: 如果配置文件无法加载或解析失败
        """
        self.rule_config_path = Path(rule_config_path)
        self.rules = self._load_rules()
        self.false_positive_filters = self._load_false_positive_filters()

    def _load_rules(self) -> Dict[str, Any]:
        """加载违规判定规则

        Returns:
            规则字典，如果配置不存在则返回空字典

        Raises:
            ViolationDetectorConfigError: 如果配置文件不存在或解析失败
        """
        config_path = self._resolve_config_path()
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config.get('rules', {})
        except FileNotFoundError:
            logger.error(f"Rule configuration file not found: {config_path}")
            raise ViolationDetectorConfigError(f"Configuration file not found: {config_path}")
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML configuration: {e}")
            raise ViolationDetectorConfigError(f"Invalid YAML in configuration file: {e}")
        except Exception as e:
            logger.error(f"Unexpected error loading configuration: {e}")
            raise ViolationDetectorConfigError(f"Failed to load configuration: {e}")

    def _load_false_positive_filters(self) -> Dict[str, Any]:
        """加载误报过滤规则

        Returns:
            误报过滤规则字典，如果配置不存在则返回空字典

        Raises:
            ViolationDetectorConfigError: 如果配置文件不存在或解析失败
        """
        config_path = self._resolve_config_path()
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config.get('false_positive_filters', {})
        except FileNotFoundError:
            logger.error(f"Rule configuration file not found: {config_path}")
            raise ViolationDetectorConfigError(f"Configuration file not found: {config_path}")
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML configuration: {e}")
            raise ViolationDetectorConfigError(f"Invalid YAML in configuration file: {e}")
        except Exception as e:
            logger.error(f"Unexpected error loading configuration: {e}")
            raise ViolationDetectorConfigError(f"Failed to load configuration: {e}")

    def _resolve_config_path(self) -> Path:
        """解析配置文件路径

        首先尝试使用传入的相对/绝对路径，如果不存在则尝试从项目根目录解析。

        Returns:
            解析后的配置文件路径
        """
        if self.rule_config_path.exists():
            return self.rule_config_path
        # Navigate from scripts/ up to project root
        project_root = Path(__file__).parent.parent.parent.parent.parent.parent
        return project_root / "shared" / "configs" / "rule_config.yaml"

    def detect_violation(
        self,
        anomaly_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """检测违规

        先检查是否为误报，然后逐一匹配违规规则。

        Args:
            anomaly_data: 异常数据字典，必须包含 type 字段
            context: 上下文信息字典，包含设备状态等

        Returns:
            违规检测结果字典，包含:
            - violation_type: 违规类型（None表示未匹配）
            - confidence: 置信度 (0.0-1.0)
            - reasoning: 推理说明
            - suspicion_level: 可疑度等级
            - legal_reference: 法律依据
            或
            - filtered: True表示已过滤
            - filter_reason: 过滤原因

        Raises:
            ViolationDetectorInputError: 如果输入数据无效
        """
        # Input validation
        if not isinstance(anomaly_data, dict):
            raise ViolationDetectorInputError("anomaly_data must be a dictionary")
        if not isinstance(context, dict):
            raise ViolationDetectorInputError("context must be a dictionary")
        if "type" not in anomaly_data:
            raise ViolationDetectorInputError("anomaly_data must contain 'type' field")

        # 先检查是否为误报
        filtered_result = self._check_false_positive(anomaly_data, context)
        if filtered_result:
            return {
                "filtered": True,
                "filter_reason": filtered_result.get("filter_reason"),
                "verification": filtered_result.get("verification", "")
            }

        # 逐一匹配违规规则
        for rule_id, rule in self.rules.items():
            if self._match_rule(anomaly_data, context, rule):
                return {
                    "violation_type": rule.get("name"),
                    "suspicion_level": rule.get("suspicion_level"),
                    "confidence": self._calculate_confidence(anomaly_data, rule),
                    "reasoning": {
                        "anomaly_type": anomaly_data.get("type"),
                        "matched_rules": self._get_matched_conditions(rule),
                        "process_check": self._get_process_check(context),
                        "conclusion": rule.get("reasoning")
                    },
                    "legal_reference": rule.get("legal_reference", "")
                }

        return {
            "violation_type": None,
            "confidence": 0.0,
            "reasoning": "异常特征未匹配任何违规规则"
        }

    def _check_false_positive(
        self,
        anomaly_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """检查是否为误报

        Args:
            anomaly_data: 异常数据字典
            context: 上下文信息字典

        Returns:
            匹配的误报过滤规则，如果不匹配则返回 None
        """
        for filter_id, filter_rule in self.false_positive_filters.items():
            if self._match_rule(anomaly_data, context, filter_rule):
                return filter_rule
        return None

    def _match_rule(
        self,
        anomaly_data: Dict[str, Any],
        context: Dict[str, Any],
        rule: Dict[str, Any]
    ) -> bool:
        """匹配规则

        规则的所有条件都必须匹配才返回 True。

        Args:
            anomaly_data: 异常数据字典
            context: 上下文信息字典
            rule: 规则字典

        Returns:
            True 表示所有条件都匹配，False 表示至少有一个条件不匹配
        """
        conditions = rule.get("conditions", [])
        for condition in conditions:
            if not self._match_condition(anomaly_data, context, condition):
                return False
        return True

    def _match_condition(
        self,
        anomaly_data: Dict[str, Any],
        context: Dict[str, Any],
        condition: Dict[str, Any]
    ) -> bool:
        """匹配单个条件

        Args:
            anomaly_data: 异常数据字典
            context: 上下文信息字典
            condition: 条件字典

        Returns:
            True 表示条件匹配，False 表示不匹配
        """
        condition_type = condition.get("type")

        if condition_type == "anomaly_match":
            return self._match_anomaly_condition(anomaly_data, condition)
        elif condition_type == "equipment_check":
            return self._match_equipment_condition(context, condition)
        elif condition_type == "equipment_status":
            return self._match_equipment_status(context, condition)
        elif condition_type == "maintenance_record":
            return self._match_maintenance_record_condition(context, condition)
        elif condition_type in UNIMPLEMENTED_CONDITION_TYPES:
            # Log unimplemented condition type
            logger.debug(
                f"Complex condition type '{condition_type}' is not implemented, "
                f"treating as non-matching. Condition: {condition}"
            )
            return False  # Return False to avoid false matches

        # Default to False for unknown condition types
        logger.warning(f"Unknown condition type: '{condition_type}', treating as non-matching")
        return False

    def _match_anomaly_condition(
        self,
        anomaly_data: Dict[str, Any],
        condition: Dict[str, Any]
    ) -> bool:
        """匹配异常条件

        Args:
            anomaly_data: 异常数据字典
            condition: 条件字典

        Returns:
            True 表示异常类型和持续时间都匹配
        """
        anomaly_type = condition.get("anomaly_type")
        if anomaly_data.get("type") != anomaly_type:
            return False

        # Check minimum duration
        min_duration = condition.get("min_duration")
        if min_duration and anomaly_data.get("duration"):
            duration_str = anomaly_data.get("duration", "")
            anomaly_duration_hours = self._parse_duration_to_hours(duration_str)
            min_duration_hours = self._parse_duration_to_hours(min_duration)

            if anomaly_duration_hours < min_duration_hours:
                return False

        return True

    def _match_equipment_condition(
        self,
        context: Dict[str, Any],
        condition: Dict[str, Any]
    ) -> bool:
        """匹配设备条件

        Args:
            context: 上下文信息字典
            condition: 条件字典

        Returns:
            True 表示设备状态和维护状态都匹配
        """
        equipment_status = condition.get("equipment_status")
        if context.get("equipment_status") != equipment_status:
            return False

        not_in_maintenance = condition.get("not_in_maintenance", False)
        if not_in_maintenance and context.get("in_maintenance"):
            return False

        return True

    def _match_equipment_status(
        self,
        context: Dict[str, Any],
        condition: Dict[str, Any]
    ) -> bool:
        """匹配设备状态

        Args:
            context: 上下文信息字典
            condition: 条件字典

        Returns:
            True 表示设备状态匹配
        """
        status = condition.get("status")
        return context.get("equipment_status") == status

    def _match_maintenance_record_condition(
        self,
        context: Dict[str, Any],
        condition: Dict[str, Any]
    ) -> bool:
        """匹配维护记录条件

        For false positive filter, check if maintenance record exists.

        Args:
            context: 上下文信息字典
            condition: 条件字典

        Returns:
            True 表示维护记录状态匹配条件要求
        """
        has_record = condition.get("has_record", False)
        if has_record:
            return context.get("maintenance_record", False) is True
        # If condition doesn't require maintenance record, this condition doesn't filter
        return True

    def _parse_duration_to_hours(self, duration_str: str) -> float:
        """将时长字符串解析为小时数

        Args:
            duration_str: 时长字符串，如 "2h", "90m", "3600s"

        Returns:
            小时数（浮点数），如果解析失败返回 0.0
        """
        if not duration_str or not isinstance(duration_str, str):
            logger.warning(f"Invalid duration string: {duration_str}")
            return 0.0

        duration_str = duration_str.strip()

        # Extract numeric value and unit
        unit = duration_str[-1] if duration_str else ''
        try:
            value = float(duration_str[:-1]) if len(duration_str) > 1 else 0.0
        except ValueError:
            logger.warning(f"Failed to parse duration value from: {duration_str}")
            return 0.0

        # Convert to hours
        if unit == 'h':
            return value
        elif unit == 'm':
            return value / 60.0
        elif unit == 's':
            return value / 3600.0
        elif unit == 'd':
            return value * 24.0
        else:
            # Try without unit suffix (assume hours)
            try:
                return float(duration_str)
            except ValueError:
                logger.warning(f"Unknown duration format: {duration_str}, assuming 0 hours")
                return 0.0

    def _calculate_confidence(
        self,
        anomaly_data: Dict[str, Any],
        rule: Dict[str, Any]
    ) -> float:
        """计算违规置信度

        Args:
            anomaly_data: 异常数据字典
            rule: 规则字典

        Returns:
            置信度 (0.0-1.0)
        """
        base_confidence = DEFAULT_BASE_CONFIDENCE

        anomaly_type = anomaly_data.get("type")
        if anomaly_type == ANOMALY_TYPE_STABLE:
            base_confidence += STABLE_ANOMALY_CONFIDENCE_BOOST
        elif anomaly_type == ANOMALY_TYPE_SUDDEN:
            base_confidence += SUDDEN_ANOMALY_CONFIDENCE_BOOST

        duration = anomaly_data.get("duration", "")
        duration_hours = self._parse_duration_to_hours(duration)
        if duration_hours >= LONG_DURATION_HOURS_THRESHOLD:
            base_confidence += LONG_DURATION_CONFIDENCE_BOOST

        return min(base_confidence, MAX_CONFIDENCE)

    def _get_matched_conditions(self, rule: Dict[str, Any]) -> List[str]:
        """获取匹配的条件描述

        Args:
            rule: 规则字典

        Returns:
            条件描述列表
        """
        conditions = rule.get("conditions", [])
        matched = []
        for cond in conditions:
            cond_type = cond.get("type")
            if cond_type == "anomaly_match":
                matched.append(f"异常类型匹配: {cond.get('anomaly_type')}")
            elif cond_type == "equipment_check":
                matched.append(f"设备状态: {cond.get('equipment_status')}")
        return matched

    def _get_process_check(self, context: Dict[str, Any]) -> str:
        """获取工艺检查描述

        Args:
            context: 上下文信息字典

        Returns:
            工艺检查描述字符串
        """
        if context.get("equipment_status") == EQUIPMENT_STATUS_RUNNING:
            return "设备正常工作中"
        elif context.get("equipment_status") == EQUIPMENT_STATUS_SHUTDOWN:
            return "设备已停运"
        return "设备状态未知"


# Module-level export for unit test validation
rules = ViolationDetector.rules
