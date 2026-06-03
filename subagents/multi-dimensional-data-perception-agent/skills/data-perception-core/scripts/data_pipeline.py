"""
多维数据感知流水线
整合5个预处理模块，提供统一的数据处理接口
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MultiDimensionalDataPipeline:
    """多维数据感知流水线 - 整合5个预处理模块"""

    def __init__(self):
        """初始化流水线，加载所有预处理模块"""
        # 导入所有模块
        from data_acquisition import DataAcquisitionModule
        from standardization import StandardizationModule
        from time_alignment import TimeAlignmentModule
        from data_cleaning import DataCleaningModule
        from data_decomposition import DataDecompositionModule

        # 初始化模块
        self.acquisition = DataAcquisitionModule()
        self.standardization = StandardizationModule()
        self.time_alignment = TimeAlignmentModule()
        self.cleaning = DataCleaningModule()
        self.decomposition = DataDecompositionModule()

        logger.info("[PIPELINE] 多维数据感知流水线初始化完成")

    def process_stream_data(self, stream_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理来自stream的双数据流数据

        Args:
            stream_data: 来自Flask /api/dual-stream的数据
                {
                    "influent": {...},  # 进水数据
                    "effluent": {...},  # 出水数据
                    "timestamp": "..."
                }

        Returns:
            处理结果字典，包含：
            - status: 处理状态
            - stages: 各阶段处理结果
            - output: 最终输出数据
            - metrics: 处理指标
        """
        result = {
            "status": "success",
            "stages": {},
            "output": {},
            "metrics": {
                "start_time": datetime.now().isoformat(),
                "stage_count": 0
            }
        }

        try:
            # 阶段1: 数据获取和标准化
            logger.info("[PIPELINE] 阶段1: 数据获取和标准化")

            # 标准化进水数据
            influent_std = self.standardization.standardize_water_quality({
                "influent": stream_data.get("influent", {})
            })
            result["stages"]["standardization_influent"] = influent_std

            # 标准化出水数据
            effluent_std = self.standardization.standardize_water_quality({
                "effluent": stream_data.get("effluent", {})
            })
            result["stages"]["standardization_effluent"] = effluent_std

            result["metrics"]["stage_count"] += 1

            # 阶段2: 数据清洗
            logger.info("[PIPELINE] 阶段2: 数据清洗")

            influent_list = [stream_data.get("influent", {})]
            effluent_list = [stream_data.get("effluent", {})]

            influent_cleaned = self.cleaning.clean_water_quality_data(influent_list)
            effluent_cleaned = self.cleaning.clean_water_quality_data(effluent_list)

            result["stages"]["cleaning"] = {
                "influent": influent_cleaned,
                "effluent": effluent_cleaned
            }
            result["metrics"]["stage_count"] += 1

            # 阶段3: 数据分解
            logger.info("[PIPELINE] 阶段3: 数据分解")

            decomposed = self.decomposition.decompose_multi_dimensional({
                "influent": stream_data.get("influent", {}),
                "effluent": stream_data.get("effluent", {})
            })
            result["stages"]["decomposition"] = decomposed
            result["metrics"]["stage_count"] += 1

            # 构建输出
            result["output"] = {
                "influent": {
                    "original": stream_data.get("influent", {}),
                    "standardized": influent_std.get("water_quality", {}).get("influent", []),
                    "cleaned": influent_cleaned.get("cleaned_data", [])
                },
                "effluent": {
                    "original": stream_data.get("effluent", {}),
                    "standardized": effluent_std.get("water_quality", {}).get("effluent", []),
                    "cleaned": effluent_cleaned.get("cleaned_data", [])
                },
                "decomposed_types": list(decomposed.keys()) if isinstance(decomposed, dict) else []
            }

            result["metrics"]["end_time"] = datetime.now().isoformat()
            result["metrics"]["success"] = True

            logger.info(f"[PIPELINE] 处理完成: {result['metrics']['stage_count']}个阶段")

        except Exception as e:
            logger.error(f"[PIPELINE] 处理失败: {e}")
            result["status"] = "error"
            result["error"] = str(e)
            result["metrics"]["success"] = False

        return result

    def process_batch_data(self, data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """处理批量数据（用于时序分析）

        Args:
            data_list: 数据列表，每个元素包含influent和effluent

        Returns:
            批量处理结果
        """
        results = []
        for idx, data in enumerate(data_list):
            logger.info(f"[PIPELINE] 处理批量数据 {idx+1}/{len(data_list)}")
            result = self.process_stream_data(data)
            results.append(result)

        return {
            "status": "success",
            "total": len(results),
            "results": results
        }
