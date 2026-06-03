# subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/time_alignment.py
"""
时序对齐模块 - 处理不同数据源的时间对齐
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

# Constants
DEFAULT_LAG_HOURS = 2
MINUTES_PER_HOUR = 60
DEFAULT_INTERVAL_MINUTES = 5  # 5分钟间隔
TIME_TOLERANCE_SECONDS = 300  # 5分钟内的容差（秒）
DATETIME_FORMAT = "%Y-%m-%d %H:%M"

# Field names
FIELD_MONITORING_TIME = "监测时间"

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

# Logger for this module
logger = logging.getLogger(__name__)


class TimeAlignmentModule:
    """时序对齐模块"""

    # 默认滞后小时数（测试需要验证的类属性）
    default_lag_hours = DEFAULT_LAG_HOURS

    def __init__(self, default_lag_hours: int = DEFAULT_LAG_HOURS):
        self.default_lag_hours = default_lag_hours
        self.lag_records = int(default_lag_hours * MINUTES_PER_HOUR / DEFAULT_INTERVAL_MINUTES)

    def align_with_lag(
        self,
        influent: List[Dict[str, Any]],
        effluent: List[Dict[str, Any]],
        lag_hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """使用时间滞后对齐进出水数据

        Args:
            influent: 进水数据列表
            effluent: 出水数据列表
            lag_hours: 滞后小时数，默认使用default_lag_hours

        Returns:
            对齐后的数据
        """
        # Input validation
        if not isinstance(influent, list):
            logger.error(f"Invalid influent type: expected list, got {type(influent).__name__}")
            return self._get_empty_error_result("Invalid influent data type")

        if not isinstance(effluent, list):
            logger.error(f"Invalid effluent type: expected list, got {type(effluent).__name__}")
            return self._get_empty_error_result("Invalid effluent data type")

        # Validate lag_hours
        if lag_hours is None:
            lag_hours = self.default_lag_hours

        if not isinstance(lag_hours, (int, float)) or lag_hours < 0:
            logger.error(f"Invalid lag_hours: {lag_hours}. Must be a non-negative number.")
            return self._get_empty_error_result("Invalid lag_hours value")

        lag_hours = int(lag_hours)

        # Handle empty input cases explicitly
        if not influent or not effluent:
            logger.info(f"Empty input data - influent: {len(influent)}, effluent: {len(effluent)}")
            return self._get_empty_success_result(lag_hours)

        # 转换为DataFrame便于处理
        if HAS_PANDAS:
            return self._align_with_pandas(influent, effluent, lag_hours)
        else:
            return self._align_without_pandas(influent, effluent, lag_hours)

    def _get_empty_error_result(self, message: str) -> Dict[str, Any]:
        """获取空错误结果"""
        return {
            "status": "error",
            "message": message
        }

    def _get_empty_success_result(self, lag_hours: int) -> Dict[str, Any]:
        """获取空成功结果"""
        return {
            "status": "success",
            "alignment_method": "time_lag",
            "lag_hours": lag_hours,
            "aligned_pairs": [],
            "alignment_count": 0,
            "aligned": []
        }

    def _align_with_pandas(
        self,
        influent: List[Dict[str, Any]],
        effluent: List[Dict[str, Any]],
        lag_hours: int
    ) -> Dict[str, Any]:
        """使用pandas进行时间对齐"""
        inf_df = pd.DataFrame(influent)
        eff_df = pd.DataFrame(effluent)

        if FIELD_MONITORING_TIME not in inf_df.columns or FIELD_MONITORING_TIME not in eff_df.columns:
            logger.error(f"Missing timestamp column '{FIELD_MONITORING_TIME}' in data")
            return self._get_empty_error_result(f"Missing timestamp column '{FIELD_MONITORING_TIME}'")

        # 转换时间戳
        try:
            inf_df[FIELD_MONITORING_TIME] = pd.to_datetime(inf_df[FIELD_MONITORING_TIME])
            eff_df[FIELD_MONITORING_TIME] = pd.to_datetime(eff_df[FIELD_MONITORING_TIME])
        except Exception as e:
            logger.error(f"Error converting timestamps: {e}")
            return self._get_empty_error_result(f"Invalid timestamp format: {e}")

        # 对齐：进水时间t对应出水时间t+lag_hours
        aligned_pairs = []
        for idx, inf_row in inf_df.iterrows():
            inf_time = inf_row[FIELD_MONITORING_TIME]
            target_time = inf_time + timedelta(hours=lag_hours)

            # 查找匹配的出水记录
            matching_eff = eff_df[
                (eff_df[FIELD_MONITORING_TIME] - target_time).abs() < timedelta(minutes=DEFAULT_INTERVAL_MINUTES)
            ]

            if not matching_eff.empty:
                eff_row = matching_eff.iloc[0]
                aligned_pairs.append({
                    "influent_time": inf_time.strftime(DATETIME_FORMAT),
                    "effluent_time": eff_row[FIELD_MONITORING_TIME].strftime(DATETIME_FORMAT),
                    "influent": inf_row.to_dict(),
                    "effluent": eff_row.to_dict()
                })

        return {
            "status": "success",
            "alignment_method": "time_lag",
            "lag_hours": lag_hours,
            "aligned_pairs": aligned_pairs,
            "alignment_count": len(aligned_pairs),
            "aligned": aligned_pairs  # For test compatibility
        }

    def _align_without_pandas(
        self,
        influent: List[Dict[str, Any]],
        effluent: List[Dict[str, Any]],
        lag_hours: int
    ) -> Dict[str, Any]:
        """不使用pandas进行时间对齐"""
        aligned_pairs = []
        for inf_record in influent:
            if FIELD_MONITORING_TIME not in inf_record:
                logger.warning(f"Influent record missing '{FIELD_MONITORING_TIME}' field")
                continue

            try:
                inf_time = datetime.fromisoformat(inf_record[FIELD_MONITORING_TIME].replace(" ", "T"))
            except (ValueError, AttributeError) as e:
                logger.warning(f"Invalid timestamp format in influent record: {inf_record.get(FIELD_MONITORING_TIME)}, error: {e}")
                continue
            target_time = inf_time + timedelta(hours=lag_hours)

            # 查找匹配的出水记录
            for eff_record in effluent:
                if FIELD_MONITORING_TIME not in eff_record:
                    logger.warning(f"Effluent record missing '{FIELD_MONITORING_TIME}' field")
                    continue

                try:
                    eff_time = datetime.fromisoformat(eff_record[FIELD_MONITORING_TIME].replace(" ", "T"))
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Invalid timestamp format in effluent record: {eff_record.get(FIELD_MONITORING_TIME)}, error: {e}")
                    continue
                time_diff = abs((eff_time - target_time).total_seconds())

                if time_diff < TIME_TOLERANCE_SECONDS:
                    aligned_pairs.append({
                        "influent_time": inf_time.strftime(DATETIME_FORMAT),
                        "effluent_time": eff_time.strftime(DATETIME_FORMAT),
                        "influent": inf_record,
                        "effluent": eff_record
                    })
                    break

        return {
            "status": "success",
            "alignment_method": "time_lag",
            "lag_hours": lag_hours,
            "aligned_pairs": aligned_pairs,
            "alignment_count": len(aligned_pairs),
            "aligned": aligned_pairs  # For test compatibility
        }


# Module-level export for unit test validation
default_lag_hours = TimeAlignmentModule.default_lag_hours
