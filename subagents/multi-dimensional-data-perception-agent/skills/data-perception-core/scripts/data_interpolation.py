"""
数据插值模块 - 填补缺失值
"""
import logging
from typing import Dict, Any, List, Optional
import numpy as np

logger = logging.getLogger(__name__)


class DataInterpolationModule:
    """数据插值模块"""

    def __init__(self, max_gap_size: int = 3):
        """
        Args:
            max_gap_size: 最大插值间隔（连续缺失点数），超过此值不插值
        """
        self.max_gap_size = max_gap_size

    def interpolate_timeseries(
        self,
        data: List[Dict[str, Any]],
        timestamp_field: str = "timestamp"
    ) -> Dict[str, Any]:
        """
        对时序数据进行线性插值

        Args:
            data: 时序数据列表
            timestamp_field: 时间戳字段名

        Returns:
            插值后的数据和插值报告
        """
        if not data:
            return {
                "interpolated_data": [],
                "report": {
                    "interpolated_count": 0,
                    "total_gaps": 0,
                    "interpolated_fields": []
                }
            }

        # 识别数值字段
        numeric_fields = self._identify_numeric_fields(data)

        if not numeric_fields:
            return {
                "interpolated_data": data,
                "report": {
                    "interpolated_count": 0,
                    "total_gaps": 0,
                    "interpolated_fields": []
                }
            }

        # 按时间排序
        sorted_data = sorted(data, key=lambda x: x.get(timestamp_field, ""))

        # 对每个数值字段进行插值
        interpolated_data = []
        interpolated_count = 0
        total_gaps = 0
        interpolated_fields_set = set()

        # 首先收集所有字段的值
        field_values = {}
        for field in numeric_fields:
            field_values[field] = [record.get(field) for record in sorted_data]

        # 对每个字段进行插值
        for field in numeric_fields:
            values = field_values[field]
            interpolated_values = list(values)  # 复制一份

            # 找到缺失值位置
            missing_indices = [i for i, v in enumerate(values) if v is None or v == ""]

            if not missing_indices:
                continue

            total_gaps += len(missing_indices)

            # 对每个缺失值进行线性插值
            for idx in missing_indices:
                # 查找前后有效值
                prev_val, next_val = self._find_adjacent_values(values, idx)

                if prev_val is not None and next_val is not None:
                    # 计算间隔大小
                    gap_size = self._count_gap_size(values, idx)

                    if gap_size <= self.max_gap_size:
                        # 线性插值
                        interpolated_value = self._linear_interpolate(
                            prev_val, next_val, gap_size, position=self._position_in_gap(values, idx)
                        )
                        interpolated_values[idx] = interpolated_value
                        interpolated_count += 1
                        interpolated_fields_set.add(field)

            # 更新field_values
            field_values[field] = interpolated_values

        # 重建数据
        for i, record in enumerate(sorted_data):
            new_record = dict(record)
            for field in numeric_fields:
                new_record[field] = field_values[field][i]
                # 标记插值字段
                if record.get(field) is None and new_record[field] is not None:
                    if "_interpolated_fields" not in new_record:
                        new_record["_interpolated_fields"] = []
                    new_record["_interpolated_fields"].append(field)
            interpolated_data.append(new_record)

        return {
            "interpolated_data": interpolated_data,
            "report": {
                "interpolated_count": interpolated_count,
                "total_gaps": total_gaps,
                "interpolated_fields": list(interpolated_fields_set)
            }
        }

    def _identify_numeric_fields(self, data: List[Dict[str, Any]]) -> List[str]:
        """识别数值字段"""
        numeric_fields = []
        if not data:
            return numeric_fields

        first_record = data[0]
        for key, value in first_record.items():
            if isinstance(value, (int, float)) and key != "timestamp":
                numeric_fields.append(key)
            elif isinstance(value, str):
                try:
                    float(value)
                    if key != "timestamp":
                        numeric_fields.append(key)
                except (ValueError, TypeError):
                    pass

        return numeric_fields

    def _find_adjacent_values(self, values: list, idx: int) -> tuple:
        """查找缺失值前后的有效值"""
        prev_val = None
        next_val = None

        # 向前查找
        for i in range(idx - 1, -1, -1):
            val = values[i]
            if val is not None and val != "":
                try:
                    prev_val = float(val)
                    break
                except (ValueError, TypeError):
                    continue

        # 向后查找
        for i in range(idx + 1, len(values)):
            val = values[i]
            if val is not None and val != "":
                try:
                    next_val = float(val)
                    break
                except (ValueError, TypeError):
                    continue

        return prev_val, next_val

    def _count_gap_size(self, values: list, idx: int) -> int:
        """计算缺失间隔大小"""
        gap_size = 1
        # 向前计数
        for i in range(idx - 1, -1, -1):
            if values[i] is None or values[i] == "":
                gap_size += 1
            else:
                break
        # 向后计数
        for i in range(idx + 1, len(values)):
            if values[i] is None or values[i] == "":
                gap_size += 1
            else:
                break
        return gap_size

    def _position_in_gap(self, values: list, idx: int) -> int:
        """计算缺失值在间隔中的位置"""
        position = 0
        # 向前计数
        for i in range(idx - 1, -1, -1):
            if values[i] is None or values[i] == "":
                position += 1
            else:
                break
        return position

    def _linear_interpolate(self, prev_val: float, next_val: float, gap_size: int, position: int = 0) -> float:
        """线性插值计算"""
        if gap_size == 1:
            return (prev_val + next_val) / 2
        else:
            # 在间隔中按比例插值
            ratio = (position + 1) / (gap_size + 1)
            return prev_val + (next_val - prev_val) * ratio
