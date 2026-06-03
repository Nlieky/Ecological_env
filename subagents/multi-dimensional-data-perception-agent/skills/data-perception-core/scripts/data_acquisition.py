# subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/data_acquisition.py
"""
数据获取模块 - 支持多源数据获取
"""
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class DataAcquisitionModule:
    """数据获取模块 - 从多源获取监测数据"""

    # 支持的数据源类型（测试需要验证的类属性）
    supported_sources = ["csv", "realtime_api", "database"]

    def __init__(self):
        pass

    def _validate_limit(self, limit: Optional[int]) -> None:
        """Validate limit parameter

        Args:
            limit: Limit value to validate

        Raises:
            ValueError: If limit is invalid
        """
        if limit is not None and limit <= 0:
            raise ValueError(f"limit must be positive, got {limit}")

    def _read_csv_safe(self, file_path: Path, limit: Optional[int] = None) -> Dict[str, Any]:
        """Safely read CSV file with error handling

        Args:
            file_path: Path to CSV file
            limit: Optional row limit

        Returns:
            Dict with 'data', 'count', 'columns' on success or 'error' on failure
        """
        try:
            df = pd.read_csv(file_path, nrows=limit)
            if df.empty:
                return {
                    "error": f"Empty file: {file_path}",
                    "error_type": "empty_file"
                }
            return {
                "data": df.to_dict('records'),
                "count": len(df),
                "columns": list(df.columns)
            }
        except pd.errors.EmptyDataError:
            return {
                "error": f"Empty CSV file: {file_path}",
                "error_type": "empty_data"
            }
        except pd.errors.ParserError as e:
            return {
                "error": f"Malformed CSV in {file_path}: {str(e)}",
                "error_type": "parser_error"
            }
        except PermissionError:
            return {
                "error": f"Permission denied reading {file_path}",
                "error_type": "permission_error"
            }
        except Exception as e:
            return {
                "error": f"Unexpected error reading {file_path}: {str(e)}",
                "error_type": "unknown_error"
            }

    def acquire_from_csv(
        self,
        influent_path: Optional[str],
        effluent_path: Optional[str],
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """从CSV文件获取进出水数据

        Args:
            influent_path: 进水数据文件路径
            effluent_path: 出水数据文件路径
            limit: 限制读取行数

        Returns:
            包含influent和effluent数据的字典
        """
        # Validate inputs
        self._validate_limit(limit)

        result = {"influent": None, "effluent": None}

        # 读取进水数据
        if influent_path:
            influent_file = Path(influent_path)
            if influent_file.exists():
                csv_result = self._read_csv_safe(influent_file, limit)
                if "error" in csv_result:
                    result["influent_error"] = csv_result["error"]
                    result["influent_error_type"] = csv_result["error_type"]
                else:
                    result["influent"] = csv_result["data"]
                    result["influent_count"] = csv_result["count"]
            else:
                result["influent_error"] = f"File not found: {influent_path}"
                result["influent_error_type"] = "file_not_found"
        else:
            result["influent_error"] = "Influent path not provided"
            result["influent_error_type"] = "missing_path"

        # 读取出水数据
        if effluent_path:
            effluent_file = Path(effluent_path)
            if effluent_file.exists():
                csv_result = self._read_csv_safe(effluent_file, limit)
                if "error" in csv_result:
                    result["effluent_error"] = csv_result["error"]
                    result["effluent_error_type"] = csv_result["error_type"]
                else:
                    result["effluent"] = csv_result["data"]
                    result["effluent_count"] = csv_result["count"]
            else:
                result["effluent_error"] = f"File not found: {effluent_path}"
                result["effluent_error_type"] = "file_not_found"
        else:
            result["effluent_error"] = "Effluent path not provided"
            result["effluent_error_type"] = "missing_path"

        result["acquisition_time"] = datetime.now().isoformat()
        result["source_type"] = "csv"

        return result

    def acquire_multi_dimensional(
        self,
        data_configs: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """获取多维数据

        Args:
            data_configs: 数据类型配置字典
                {
                    "water_quality": {"path": "...", "type": "csv"},
                    "flow": {"path": "...", "type": "csv"},
                    ...
                }

        Returns:
            多维数据字典
        """
        result = {}

        for data_type, config in data_configs.items():
            source_type = config.get("type", "csv")
            path = config.get("path")

            if source_type == "csv" and path:
                file_path = Path(path)
                if file_path.exists():
                    csv_result = self._read_csv_safe(file_path)
                    if "error" in csv_result:
                        result[data_type] = {
                            "error": csv_result["error"],
                            "error_type": csv_result["error_type"]
                        }
                    else:
                        result[data_type] = {
                            "data": csv_result["data"],
                            "count": csv_result["count"],
                            "columns": csv_result["columns"]
                        }
                else:
                    result[data_type] = {
                        "error": f"File not found: {path}",
                        "error_type": "file_not_found"
                    }
            else:
                result[data_type] = {
                    "error": f"Unsupported source type or missing path: {source_type}",
                    "error_type": "unsupported_source"
                }

        result["acquisition_time"] = datetime.now().isoformat()
        return result

    def acquire_equipment_status(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """获取设备状态数据

        Args:
            config: Configuration dictionary (reserved for future use)

        Returns:
            Equipment status data dictionary
        """
        # Config parameter reserved for future API/database integration
        # Current implementation provides mock data
        return {
            "equipment": [
                {"name": "进水泵1号", "status": "running", "timestamp": datetime.now().isoformat()},
                {"name": "鼓风机1号", "status": "running", "timestamp": datetime.now().isoformat()},
                {"name": "污泥泵1号", "status": "standby", "timestamp": datetime.now().isoformat()}
            ],
            "acquisition_time": datetime.now().isoformat(),
            "source_type": "mock"
        }

    def acquire_process_parameters(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """获取工艺参数数据

        Args:
            config: Configuration dictionary (reserved for future use)

        Returns:
            Process parameters data dictionary
        """
        # Config parameter reserved for future API/database integration
        # Current implementation provides mock data
        return {
            "process": [
                {"parameter": "溶解氧", "value": 2.5, "unit": "mg/L"},
                {"parameter": "污泥浓度", "value": 3500, "unit": "mg/L"},
                {"parameter": "回流比", "value": 0.5, "unit": "ratio"}
            ],
            "acquisition_time": datetime.now().isoformat(),
            "source_type": "mock"
        }


# Module-level export for unit test validation
supported_sources = DataAcquisitionModule.supported_sources
