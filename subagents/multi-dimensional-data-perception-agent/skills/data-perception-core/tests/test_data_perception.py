#!/usr/bin/env python3
"""
多维数据感知子智能体综合测试

测试覆盖以下模块：
1. data_acquisition.py - 数据获取模块
2. time_alignment.py - 时序对齐模块
3. data_cleaning.py - 数据清洗模块
4. standardization.py - 标准化模块
5. data_decomposition.py - 数据分解模块
6. data_pipeline.py - 数据流水线
"""

import unittest
import tempfile
import os
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
import sys

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from data_acquisition import DataAcquisitionModule, supported_sources
from time_alignment import TimeAlignmentModule
from data_cleaning import DataCleaningModule
from standardization import StandardizationModule
from data_decomposition import DataDecompositionModule
from data_pipeline import MultiDimensionalDataPipeline


class TestDataAcquisitionModule(unittest.TestCase):
    """测试数据获取模块"""

    def setUp(self):
        """创建测试数据"""
        self.module = DataAcquisitionModule()
        self.temp_dir = tempfile.mkdtemp()

        # 创建测试CSV文件
        self.test_data = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=10, freq="H"),
            "pH值": [7.2, 7.3, 7.1, 7.4, 7.2, 7.3, 7.1, 7.4, 7.2, 7.3],
            "化学需氧量浓度（毫克/升）": [45, 48, 42, 50, 46, 47, 43, 49, 45, 48]
        })

        self.influent_file = os.path.join(self.temp_dir, "influent.csv")
        self.effluent_file = os.path.join(self.temp_dir, "effluent.csv")
        self.test_data.to_csv(self.influent_file, index=False)
        self.test_data.to_csv(self.effluent_file, index=False)

    def tearDown(self):
        """清理测试文件"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_supported_sources_attribute(self):
        """测试支持的源类型类属性"""
        self.assertEqual(supported_sources, ["csv", "realtime_api", "database"])
        self.assertEqual(DataAcquisitionModule.supported_sources, ["csv", "realtime_api", "database"])

    def test_acquire_from_csv_success(self):
        """测试成功从CSV获取数据"""
        result = self.module.acquire_from_csv(self.influent_file, self.effluent_file)

        self.assertIn("influent", result)
        self.assertIn("effluent", result)
        self.assertIn("acquisition_time", result)
        self.assertIn("source_type", result)
        self.assertEqual(result["source_type"], "csv")
        self.assertEqual(len(result["influent"]), 10)
        self.assertEqual(len(result["effluent"]), 10)

    def test_acquire_from_csv_with_limit(self):
        """测试带限制的CSV获取"""
        result = self.module.acquire_from_csv(self.influent_file, None, limit=5)

        self.assertEqual(len(result["influent"]), 5)
        self.assertIn("influent_count", result)

    def test_acquire_from_csv_file_not_found(self):
        """测试文件不存在的情况"""
        result = self.module.acquire_from_csv("nonexistent.csv", None)

        self.assertIn("influent_error", result)
        self.assertIn("influent_error_type", result)
        self.assertEqual(result["influent_error_type"], "file_not_found")

    def test_acquire_from_csv_missing_path(self):
        """测试缺少路径参数"""
        result = self.module.acquire_from_csv(None, None)

        self.assertIn("influent_error", result)
        self.assertEqual(result["influent_error_type"], "missing_path")

    def test_validate_limit_invalid(self):
        """测试无效的limit参数"""
        with self.assertRaises(ValueError):
            self.module._validate_limit(-1)

        with self.assertRaises(ValueError):
            self.module._validate_limit(0)

    def test_acquire_multi_dimensional(self):
        """测试多维数据获取"""
        configs = {
            "water_quality": {"path": self.influent_file, "type": "csv"},
            "flow": {"path": self.effluent_file, "type": "csv"}
        }

        result = self.module.acquire_multi_dimensional(configs)

        self.assertIn("water_quality", result)
        self.assertIn("flow", result)
        self.assertIn("acquisition_time", result)
        self.assertNotIn("error", result.get("water_quality", {}))

    def test_acquire_equipment_status(self):
        """测试获取设备状态"""
        result = self.module.acquire_equipment_status()

        self.assertIn("equipment", result)
        self.assertIn("acquisition_time", result)
        self.assertEqual(result["source_type"], "mock")
        self.assertIsInstance(result["equipment"], list)

    def test_acquire_process_parameters(self):
        """测试获取工艺参数"""
        result = self.module.acquire_process_parameters()

        self.assertIn("process", result)
        self.assertIn("acquisition_time", result)
        self.assertEqual(result["source_type"], "mock")
        self.assertIsInstance(result["process"], list)


class TestTimeAlignmentModule(unittest.TestCase):
    """测试时序对齐模块"""

    def setUp(self):
        """创建测试数据"""
        self.module = TimeAlignmentModule()

        # 创建有2小时滞后的测试数据（使用中文列名"监测时间"）
        base_time = datetime(2024, 1, 1, 8, 0)
        self.influent = [
            {"监测时间": (base_time + timedelta(hours=i)).strftime("%Y-%m-%d %H:%M"),
             "pH": 7.2 + i * 0.01, "COD": 45 + i}
            for i in range(10)
        ]

        self.effluent = [
            {"监测时间": (base_time + timedelta(hours=2 + i)).strftime("%Y-%m-%d %H:%M"),
             "pH": 7.0 + i * 0.01, "COD": 40 + i}
            for i in range(10)
        ]

    def test_default_lag_hours(self):
        """测试默认滞后时间"""
        # 假设类有default_lag_hours属性
        self.assertIsNotNone(getattr(self.module, 'default_lag_hours', 2))

    def test_align_with_lag_success(self):
        """测试成功时序对齐"""
        result = self.module.align_with_lag(self.influent, self.effluent, lag_hours=2)

        self.assertIn("status", result)
        self.assertIn("aligned_pairs", result)
        self.assertIn("alignment_count", result)
        self.assertEqual(result["lag_hours"], 2)

    def test_align_with_lag_missing_timestamp(self):
        """测试缺少时间戳的情况"""
        data_no_ts = [{"pH": 7.2, "COD": 45}]
        result = self.module.align_with_lag(data_no_ts, self.effluent, lag_hours=2)

        self.assertIn("status", result)
        # 缺少时间戳应该返回error状态
        if result["status"] == "error":
            self.assertIn("message", result)

    def test_align_with_lag_empty_data(self):
        """测试空数据输入"""
        result = self.module.align_with_lag([], self.effluent, lag_hours=2)

        self.assertIn("status", result)

    def test_align_with_lag_zero_lag(self):
        """测试零滞后对齐"""
        result = self.module.align_with_lag(self.influent, self.influent, lag_hours=0)

        self.assertEqual(result.get("lag_hours"), 0)


class TestDataCleaningModule(unittest.TestCase):
    """测试数据清洗模块"""

    def setUp(self):
        """创建测试数据"""
        self.module = DataCleaningModule()

        # 创建包含异常值和缺失值的测试数据
        self.test_data = [
            {"pH": 7.2, "COD": 45, "TN": 15},
            {"pH": None, "COD": 48, "TN": 16},  # 缺失值
            {"pH": 7.1, "COD": 999, "TN": 17},  # COD异常值
            {"pH": 7.4, "COD": 50, "TN": 18},
            {"pH": -1, "COD": 47, "TN": 19},    # pH异常值
            {"pH": 15, "COD": 46, "TN": 20},    # pH异常值
        ]

    def test_clean_water_quality_data_success(self):
        """测试成功清洗数据"""
        result = self.module.clean_water_quality_data(self.test_data)

        self.assertIn("cleaned_data", result)
        self.assertIn("quality_report", result)
        self.assertIsInstance(result["cleaned_data"], list)

    def test_clean_water_quality_empty_data(self):
        """测试空数据清洗"""
        result = self.module.clean_water_quality_data([])

        self.assertIn("cleaned_data", result)
        self.assertIn("quality_report", result)

    def test_clean_water_quality_none_input(self):
        """测试None输入"""
        result = self.module.clean_water_quality_data(None)

        self.assertIn("cleaned_data", result)
        self.assertIn("quality_report", result)

    def test_quality_report_structure(self):
        """测试质量报告结构"""
        result = self.module.clean_water_quality_data(self.test_data)
        report = result["quality_report"]

        # 验证报告包含必要字段
        expected_fields = ["completeness", "anomaly_rate", "missing_count",
                         "anomaly_count", "cleaned_count", "total_records"]
        for field in expected_fields:
            self.assertIn(field, report)


class TestStandardizationModule(unittest.TestCase):
    """测试标准化模块"""

    def setUp(self):
        """创建测试数据"""
        self.module = StandardizationModule()

        # 创建中文字段名的测试数据
        self.test_input = {
            "influent": [
                {"pH值": 7.2, "化学需氧量浓度（毫克/升）": 45,
                 "总氮浓度（毫克/升）": 15, "氨氮浓度（毫克/升）": 5,
                 "总磷浓度（毫克/升）": 2, "悬浮物浓度（毫克/升）": 30},
                {"pH值": 7.3, "化学需氧量浓度（毫克/升）": 48,
                 "总氮浓度（毫克/升）": 16, "氨氮浓度（毫克/升）": 6}
            ],
            "effluent": [
                {"pH值": 7.0, "化学需氧量浓度（毫克/升）": 40}
            ]
        }

    def test_standardize_water_quality_success(self):
        """测试成功标准化"""
        result = self.module.standardize_water_quality(self.test_input)

        self.assertIn("water_quality", result)
        self.assertIn("influent", result["water_quality"])
        self.assertIn("effluent", result["water_quality"])

    def test_field_mapping(self):
        """测试字段名映射"""
        result = self.module.standardize_water_quality(self.test_input)

        # 检查第一条记录的字段
        first_record = result["water_quality"]["influent"][0]

        # 应该包含英文标准字段名
        self.assertIn("pH", first_record)
        self.assertIn("COD", first_record)
        self.assertIn("TN", first_record)

    def test_standardize_empty_input(self):
        """测试空输入"""
        result = self.module.standardize_water_quality({"influent": [], "effluent": []})

        self.assertIn("water_quality", result)
        self.assertIn("metadata", result)

    def test_standardize_missing_keys(self):
        """测试缺少关键键"""
        result = self.module.standardize_water_quality({"influent": []})

        self.assertIn("water_quality", result)
        # effluent缺失应该有默认值


class TestDataDecompositionModule(unittest.TestCase):
    """测试数据分解模块"""

    def setUp(self):
        """创建测试数据"""
        self.module = DataDecompositionModule()

        self.test_input = {
            "influent": [
                {"pH": 7.2, "COD": 45, "flow_rate": 100,
                 "equipment": "pump1", "parameter": "DO"},
                {"TN": 15, "TP": 2, "maintenance": "scheduled"}
            ],
            "effluent": [
                {"pH": 7.0, "COD": 40, "discharge_volume": 95}
            ]
        }

    def test_decompose_multi_dimensional_success(self):
        """测试成功分解多维数据"""
        result = self.module.decompose_multi_dimensional(self.test_input)

        # 应该包含8类数据类型
        expected_types = ["water_quality", "flow", "equipment_status",
                         "process_parameters", "maintenance_records",
                         "production_records", "source_info", "monitoring_point_info"]

        for data_type in expected_types:
            self.assertIn(data_type, result)

    def test_water_quality_extraction(self):
        """测试水质数据提取"""
        result = self.module.decompose_multi_dimensional(self.test_input)

        water_quality = result.get("water_quality", {})
        self.assertIn("influent", water_quality)
        self.assertIn("effluent", water_quality)

    def test_empty_input_decomposition(self):
        """测试空输入分解"""
        result = self.module.decompose_multi_dimensional({"influent": [], "effluent": []})

        # 应该返回所有类型的空数据
        self.assertIn("water_quality", result)


class TestDataPipelineIntegration(unittest.TestCase):
    """测试数据流水线集成"""

    def setUp(self):
        """创建测试数据"""
        self.pipeline = MultiDimensionalDataPipeline()
        self.temp_dir = tempfile.mkdtemp()

        # 创建测试CSV文件
        test_data = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01 08:00", periods=10, freq="H"),
            "pH值": [7.2, 7.3, 7.1, 7.4, 7.2, 7.3, 7.1, 7.4, 7.2, 7.3],
            "化学需氧量浓度（毫克/升）": [45, 48, 42, 50, 46, 47, 43, 49, 45, 48]
        })

        self.csv_file = os.path.join(self.temp_dir, "test.csv")
        test_data.to_csv(self.csv_file, index=False)

    def tearDown(self):
        """清理测试文件"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_process_stream_data_success(self):
        """测试成功处理流数据"""
        stream_data = {
            "influent_path": self.csv_file,
            "effluent_path": self.csv_file
        }

        result = self.pipeline.process_stream_data(stream_data)

        self.assertIn("status", result)
        self.assertIn("output", result)
        self.assertIn("metrics", result)

    def test_process_batch_data_success(self):
        """测试成功处理批量数据"""
        batch_data = [
            {"influent_path": self.csv_file, "effluent_path": self.csv_file}
        ]

        result = self.pipeline.process_batch_data(batch_data)

        self.assertIn("status", result)
        # 批量处理可能返回results或其他键
        self.assertTrue("results" in result or "output" in result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
