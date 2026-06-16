#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史数据获取器

从CSV文件中获取指定时间范围和指标的历史数据。
支持进水和出水数据的获取、时间过滤和指标筛选。

数据来源:
- E:/project/Ecological_env/data/pollution_water_in.csv (进水数据)
- E:/project/Ecological_env/data/pollution_water_out.csv (出水数据)
"""

import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# 不配置logging，由主应用统一配置
logger = logging.getLogger(__name__)


# 字段名映射：中文字段名到英文字段名
FIELD_MAPPING = {
    "监测时间": "timestamp",
    "pH值": "pH",
    "化学需氧量浓度（毫克/升）": "COD",
    "总氮浓度（毫克/升）": "TN",
    "氨氮浓度（毫克/升）": "NH3-N",
    "总磷浓度（毫克/升）": "TP",
    "悬浮物浓度（毫克/升）": "SS",
    "流量（升/秒）": "flow_rate",
    "排放量（吨）": "discharge_volume",
    "溶解氧（毫克/升）": "DO"
}

# 反向映射：英文字段名到中文字段名
REVERSE_FIELD_MAPPING = {v: k for k, v in FIELD_MAPPING.items()}


class HistoricalDataFetcher:
    """历史数据获取器"""

    def __init__(self, data_dir: str = None):
        """
        初始化数据获取器

        Args:
            data_dir: 数据目录路径（默认自动推导）
        """
        if data_dir is None:
            # 自动推导数据目录位置
            # 从当前文件位置推导：.../subagents/multi-dimensional-data-perception-agent/.../scripts/historical_data_fetcher.py
            # 向上4层到项目根目录，然后进入data
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent.parent.parent.parent.parent
            data_dir = project_root / "data"

        self.data_dir = Path(data_dir)
        self.influent_file = self.data_dir / "pollution_water_in.csv"
        self.effluent_file = self.data_dir / "pollution_water_out.csv"

        print(f"[DATA_FETCHER] Initialized with data dir: {self.data_dir}")

    def fetch_data(
        self,
        time_range: Dict[str, Any],
        indicators: List[str],
        data_source: str = "both"
    ) -> Dict[str, Any]:
        """
        获取指定时间范围和指标的数据

        Args:
            time_range: 时间范围 {"start": datetime, "end": datetime}
            indicators: 指标列表 ["pH", "COD", ...]
            data_source: 数据源 "influent" | "effluent" | "both"

        Returns:
            Dict: 获取的数据
                {
                    "influent": [...],  # 进水数据列表
                    "effluent": [...],  # 出水数据列表
                    "metadata": {
                        "time_range": {...},
                        "indicators": [...],
                        "counts": {"influent": N, "effluent": M}
                    }
                }
        """
        print(f"[DATA_FETCHER] Fetching data: time_range={time_range}, indicators={indicators}, source={data_source}")

        result = {
            "influent": [],
            "effluent": [],
            "metadata": {
                "time_range": time_range,
                "indicators": indicators,
                "counts": {"influent": 0, "effluent": 0}
            }
        }

        # 获取进水数据
        if data_source in ["influent", "both"]:
            result["influent"] = self._fetch_from_file(
                self.influent_file,
                time_range,
                indicators
            )
            result["metadata"]["counts"]["influent"] = len(result["influent"])

        # 获取出水数据
        if data_source in ["effluent", "both"]:
            result["effluent"] = self._fetch_from_file(
                self.effluent_file,
                time_range,
                indicators
            )
            result["metadata"]["counts"]["effluent"] = len(result["effluent"])

        print(f"[DATA_FETCHER] Fetched: influent={result['metadata']['counts']['influent']}, "
                    f"effluent={result['metadata']['counts']['effluent']}")

        return result

    def _fetch_from_file(
        self,
        file_path: Path,
        time_range: Dict[str, Any],
        indicators: List[str]
    ) -> List[Dict[str, Any]]:
        """
        从单个CSV文件获取数据

        Args:
            file_path: CSV文件路径
            time_range: 时间范围
            indicators: 指标列表

        Returns:
            List[Dict]: 数据列表
        """
        if not file_path.exists():
            print(f"[DATA_FETCHER] File not found: {file_path}")
            return []

        try:
            # 读取CSV文件
            df = pd.read_csv(file_path)
            print(f"[DATA_FETCHER] Loaded {len(df)} records from {file_path.name}")

            # 检查是否有时间戳列
            timestamp_col = self._find_timestamp_column(df)
            if timestamp_col is None:
                print(f"[DATA_FETCHER] No timestamp column found in {file_path.name}")
                return self._filter_by_row_count(df, time_range, indicators)

            # 转换时间戳
            df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors='coerce')

            # 过滤时间范围
            start_time = time_range.get("start")
            end_time = time_range.get("end")

            if start_time and end_time:
                # 获取数据的实际年份范围
                data_year_start = df[timestamp_col].dt.year.min()
                data_year_end = df[timestamp_col].dt.year.max()

                # 如果查询年份与数据年份不匹配，进行年份映射
                query_year = start_time.year if hasattr(start_time, 'year') else pd.Timestamp(start_time).year

                if data_year_start and query_year != data_year_start:
                    print(f"[DATA_FETCHER] 年份不匹配: 数据为{data_year_start}年，查询为{query_year}年，进行年份映射")
                    # 将查询时间范围映射到数据年份
                    # 保持相同的月日时分秒，只改变年份
                    if isinstance(start_time, str):
                        start_time = pd.Timestamp(start_time)
                    if isinstance(end_time, str):
                        end_time = pd.Timestamp(end_time)

                    # 映射到数据年份
                    mapped_start = start_time.replace(year=data_year_start)
                    mapped_end = end_time.replace(year=data_year_start)

                    print(f"[DATA_FETCHER] 映射时间范围: {mapped_start} ~ {mapped_end}")
                    start_time = mapped_start
                    end_time = mapped_end

                mask = (df[timestamp_col] >= start_time) & (df[timestamp_col] <= end_time)
                df_filtered = df[mask]

                # 如果过滤后没有数据，返回最近的N条数据
                if len(df_filtered) == 0:
                    print(f"[DATA_FETCHER] 时间过滤无结果，返回最近的数据")
                    # 计算需要的数据条数（基于时间范围）
                    hours_diff = (end_time - start_time).total_seconds() / 3600
                    # 假设数据间隔为5分钟
                    rows_needed = int(hours_diff * 60 / 5) if hours_diff > 0 else 288  # 288 = 24小时的数据
                    df = df.tail(min(rows_needed, len(df)))
                    print(f"[DATA_FETCHER] 返回最近 {len(df)} 条数据作为替代")
                else:
                    df = df_filtered
                    print(f"[DATA_FETCHER] Filtered to {len(df)} records in time range")

            # 重命名字段为英文字段名
            df = self._standardize_field_names(df)

            # 筛选指标
            return self._filter_indicators(df, indicators)

        except Exception as e:
            print(f"[DATA_FETCHER] Error reading {file_path}: {e}")
            return []

    def _find_timestamp_column(self, df: pd.DataFrame) -> Optional[str]:
        """查找时间戳列"""
        # 尝试常见的时间戳列名
        timestamp_candidates = ["监测时间", "timestamp", "time", "时间", "日期"]

        for col in df.columns:
            if col in timestamp_candidates:
                return col

        # 尝试检测（如果列名包含"time"）
        for col in df.columns:
            if "time" in col.lower() or "时间" in col or "日期" in col:
                return col

        return None

    def _standardize_field_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化字段名为英文"""
        rename_map = {}

        for col in df.columns:
            if col in FIELD_MAPPING:
                rename_map[col] = FIELD_MAPPING[col]

        if rename_map:
            df = df.rename(columns=rename_map)
            print(f"[DATA_FETCHER] Renamed columns: {rename_map}")

        return df

    def _filter_indicators(self, df: pd.DataFrame, indicators: List[str]) -> List[Dict[str, Any]]:
        """筛选指定指标的数据"""
        # 默认指标列表（当未指定时使用）
        DEFAULT_INDICATORS = ["pH", "COD", "TN", "NH3-N", "TP", "flow_rate", "discharge_volume"]

        # 如果没有指定指标，使用默认指标
        if not indicators:
            indicators = DEFAULT_INDICATORS
            print(f"[DATA_FETCHER] 未指定指标，使用默认指标: {indicators}")

        # 标准化指标名称（处理大小写问题）
        normalized_indicators = []
        for ind in indicators:
            # 特殊处理pH的大小写
            if ind.upper() == "PH":
                normalized_indicators.append("pH")
            # 特殊处理氨氮的格式
            elif "AMMONIA" in ind.upper() or "NH3" in ind.upper():
                normalized_indicators.append("NH3-N")
            # 其他指标转大写
            else:
                normalized_indicators.append(ind.upper())

        print(f"[DATA_FETCHER] 标准化指标名称: {list(zip(indicators, normalized_indicators))}")

        # 首先找出存在的指标列
        available_indicators = [ind for ind in normalized_indicators if ind in df.columns]

        if not available_indicators:
            print(f"[DATA_FETCHER] No indicator columns found. Available: {list(df.columns)}")
            return []

        # 筛选时间戳和指标列
        columns_to_keep = ["timestamp"] + available_indicators
        df_filtered = df[columns_to_keep].copy()

        # 转换为字典列表
        records = []
        for _, row in df_filtered.iterrows():
            record = {}
            for col in df_filtered.columns:
                value = row[col]
                # 处理NaN值
                if pd.isna(value):
                    if col == "timestamp":
                        continue
                    else:
                        value = None
                # 转换时间戳为字符串
                elif col == "timestamp" and isinstance(value, pd.Timestamp):
                    value = value.strftime("%Y-%m-%d %H:%M:%S")
                # 转换数值类型
                elif col in available_indicators:
                    try:
                        value = float(value)
                    except (ValueError, TypeError):
                        value = None

                record[col] = value

            records.append(record)

        return records

    def _filter_by_row_count(
        self,
        df: pd.DataFrame,
        time_range: Dict[str, Any],
        indicators: List[str]
    ) -> List[Dict[str, Any]]:
        """
        按行数过滤（当没有时间戳列时使用）
        使用最近的N行数据模拟时间范围过滤
        """
        # 解析时间范围计算需要的行数
        start = time_range.get("start")
        end = time_range.get("end")

        if isinstance(start, datetime) and isinstance(end, datetime):
            # 计算时间差（小时）
            hours_diff = (end - start).total_seconds() / 3600

            # 假设数据间隔为5分钟，计算需要的行数
            rows_needed = int(hours_diff * 60 / 5) + 1

            # 取最后N行
            df = df.tail(rows_needed)

        # 标准化字段名
        df = self._standardize_field_names(df)

        # 筛选指标
        return self._filter_indicators(df, indicators)

    def get_available_indicators(self, data_source: str = "influent") -> List[str]:
        """
        获取可用的指标列表

        Args:
            data_source: 数据源

        Returns:
            List[str]: 可用指标列表
        """
        file_path = self.influent_file if data_source == "influent" else self.effluent_file

        if not file_path.exists():
            print(f"[DATA_FETCHER] File not found: {file_path}")
            return []

        try:
            df = pd.read_csv(file_path, nrows=1)  # 只读取第一行
            df = self._standardize_field_names(df)

            # 过滤出数值列（排除时间戳）
            indicators = [col for col in df.columns if col != "timestamp"]
            return indicators

        except Exception as e:
            print(f"[DATA_FETCHER] Error reading indicators: {e}")
            return []

    def get_time_range(self, data_source: str = "influent") -> Optional[Dict[str, str]]:
        """
        获取数据的时间范围

        Args:
            data_source: 数据源

        Returns:
            Dict: {"start": "...", "end": "..."}
        """
        file_path = self.influent_file if data_source == "influent" else self.effluent_file

        if not file_path.exists():
            return None

        try:
            df = pd.read_csv(file_path)
            timestamp_col = self._find_timestamp_column(df)

            if timestamp_col:
                df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors='coerce')
                start = df[timestamp_col].min()
                end = df[timestamp_col].max()

                return {
                    "start": start.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(start) else None,
                    "end": end.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(end) else None
                }

            return None

        except Exception as e:
            print(f"[DATA_FETCHER] Error getting time range: {e}")
            return None


# 便捷函数
def fetch_historical_data(
    time_range: Dict[str, Any],
    indicators: List[str],
    data_source: str = "both",
    data_dir: str = None
) -> Dict[str, Any]:
    """
    便捷的历史数据获取函数

    Args:
        time_range: 时间范围
        indicators: 指标列表
        data_source: 数据源
        data_dir: 数据目录（可选）

    Returns:
        Dict: 获取的数据
    """
    fetcher = HistoricalDataFetcher(data_dir)
    return fetcher.fetch_data(time_range, indicators, data_source)


if __name__ == "__main__":
    # 测试代码
    print("=== 历史数据获取器测试 ===\n")

    from datetime import timedelta

    fetcher = HistoricalDataFetcher()

    # 测试时间范围
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=24)
    time_range = {"start": start_time, "end": end_time}

    print(f"时间范围: {start_time} ~ {end_time}")
    print()

    # 测试指标
    indicators = ["pH", "COD"]
    print(f"指标: {indicators}")
    print()

    # 获取数据
    result = fetcher.fetch_data(time_range, indicators, data_source="influent")

    print(f"获取到 {len(result['influent'])} 条进水数据")
    print()

    # 显示前几条数据
    if result["influent"]:
        print("前5条数据:")
        for record in result["influent"][:5]:
            print(f"  {record}")

    # 测试可用指标
    print()
    print("可用指标:")
    available = fetcher.get_available_indicators("influent")
    print(f"  {available}")
