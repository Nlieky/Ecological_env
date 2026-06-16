#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
意图-算子映射表

定义查询意图到异常检测算子的映射规则，支持基于意图和数据特征的动态算子选择。

功能：
1. 意图映射层：查询意图 → 算子类型
2. 数据特征适配层：数据特征 → 算子筛选
3. 算子组合层：多个算子协同工作
"""

import logging
from typing import Dict, List, Any, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class IntentOperatorMapper:
    """
    意图-算子映射器

    基于查询意图和数据特征动态选择合适的异常检测算子。
    """

    # ========== 意图映射表 ==========

    # 意图类型到算子类型的映射
    INTENT_TO_OPERATORS = {
        # 单指标异常检测
        "single_anomaly": {
            "primary": ["zscore", "iqr"],
            "fallback": ["isolation_forest"],
            "description": "单指标异常检测"
        },

        # 相关性分析
        "correlation": {
            "primary": ["correlation_pearson", "correlation_spearman"],
            "fallback": [],
            "description": "多指标相关性分析"
        },

        # 趋势分析
        "trend": {
            "primary": ["trend_linear", "trend_mann_kendall"],
            "fallback": ["moving_average"],
            "description": "时序趋势分析"
        },

        # 多指标异常检测
        "multi_anomaly": {
            "primary": ["ecod", "lof"],
            "fallback": ["isolation_forest"],
            "description": "多指标联合异常检测"
        },

        # 模式识别
        "pattern": {
            "primary": ["zscore", "iqr", "moving_average"],
            "fallback": ["isolation_forest"],
            "description": "时序模式识别"
        },

        # 综合分析（默认）
        "comprehensive": {
            "primary": ["zscore", "iqr", "isolation_forest"],
            "fallback": ["ecod", "lof"],
            "description": "综合异常分析"
        }
    }

    # 分析类型到意图类型的映射
    ANALYSIS_TYPE_TO_INTENT = {
        "anomaly": "single_anomaly",
        "correlation": "correlation",
        "trend": "trend",
        "multi_anomaly": "multi_anomaly",
        "pattern": "pattern",
        "comprehensive": "comprehensive"
    }

    # ========== 数据特征适配规则 ==========

    # 数据量到算子的适配
    DATA_SIZE_ADAPTER = {
        "small": {  # < 100 样本
            "preferred": ["zscore", "iqr", "grubbs"],
            "avoid": ["isolation_forest", "ecod", "lof", "vae"],
            "reason": "小样本量不适合复杂模型"
        },
        "medium": {  # 100-1000 样本
            "preferred": ["zscore", "iqr", "isolation_forest", "moving_average"],
            "avoid": ["vae"],
            "reason": "中等样本量适合统计和基础ML算子"
        },
        "large": {  # > 1000 样本
            "preferred": ["isolation_forest", "ecod", "lof", "one_class_svm"],
            "avoid": [],
            "reason": "大样本量可以使用复杂模型"
        }
    }

    # 周期性到算子的适配
    SEASONAL_ADAPTER = {
        "has_seasonal": {
            "add_operators": ["seasonal_decompose"],
            "reason": "检测到周期性，添加季节性分解算子"
        }
    }

    # ========== 算子组合规则 ==========

    # 算子组合模板
    OPERATOR_COMBINATIONS = {
        "anomaly_then_correlation": {
            "stage1": ["zscore", "iqr"],
            "stage2": ["correlation_pearson"],
            "description": "先异常检测，后相关性分析"
        },
        "trend_then_change_point": {
            "stage1": ["trend_linear"],
            "stage2": ["change_point"],
            "description": "先趋势分析，后突变点检测"
        },
        "multi_stage_anomaly": {
            "stage1": ["zscore", "iqr"],
            "stage2": ["isolation_forest"],
            "stage3": ["ecod"],
            "description": "多阶段异常检测：统计→ML→高维"
        }
    }

    # ========== 可用算子注册表 ==========

    # 当前可用的算子（需要与 operator_adapter.py 中的算子一致）
    AVAILABLE_OPERATORS = {
        # 统计类
        "zscore": {"category": "statistical", "type": "single", "requires_normalization": False},
        "iqr": {"category": "statistical", "type": "single", "requires_normalization": False},
        "grubbs": {"category": "statistical", "type": "single", "requires_normalization": False},
        "moving_average": {"category": "statistical", "type": "single", "requires_normalization": False},

        # 机器学习类
        "isolation_forest": {"category": "ml", "type": "single", "requires_normalization": False},
        "one_class_svm": {"category": "ml", "type": "single", "requires_normalization": True},

        # PyOD类（如果可用）
        "hbos": {"category": "pyod", "type": "single", "requires_normalization": False},
        "ecod": {"category": "pyod", "type": "multi", "requires_normalization": False},
        "knn": {"category": "pyod", "type": "single", "requires_normalization": True},
        "lof": {"category": "pyod", "type": "multi", "requires_normalization": True},
        "abod": {"category": "pyod", "type": "single", "requires_normalization": False},

        # 深度学习类（如果可用）
        "vae": {"category": "dl", "type": "single", "requires_normalization": True},

        # 特征分析类（待整合）
        "correlation_pearson": {"category": "feature", "type": "multi", "requires_normalization": False},
        "correlation_spearman": {"category": "feature", "type": "multi", "requires_normalization": False},
        "trend_linear": {"category": "feature", "type": "single", "requires_normalization": False},
        "trend_mann_kendall": {"category": "feature", "type": "single", "requires_normalization": False}
    }

    def __init__(self):
        """初始化意图-算子映射器"""
        self.name = "意图-算子映射器"
        self.version = "1.0.0"
        logger.info(f"[INIT] {self.name} v{self.version} initialized")

    def select_operators_by_intent(
        self,
        intent: Dict[str, Any],
        data: Optional[pd.DataFrame] = None,
        available_operators: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        基于意图和数据特征选择算子

        Args:
            intent: 查询意图字典
                {
                    "analysis_types": ["anomaly", "correlation"],  # 分析类型列表
                    "indicators": ["COD", "pH"],                   # 指标列表
                    "query_type": "single" | "multi"               # 查询类型
                }
            data: 输入数据（用于评估数据特征）
            available_operators: 实际可用的算子列表（用于过滤）

        Returns:
            算子选择结果
                {
                    "selected_operators": ["zscore", "iqr"],
                    "fallback_operators": ["isolation_forest"],
                    "reason": "...",
                    "intent_matched": true
                }
        """
        logger.info(f"[MAPPING] 开始选择算子...")
        logger.info(f"[MAPPING] 意图: {intent}")

        # 1. 确定意图类型
        intent_type = self._determine_intent_type(intent)
        logger.info(f"[MAPPING] 意图类型: {intent_type}")

        # 2. 获取基础算子列表（从意图映射表）
        intent_config = self.INTENT_TO_OPERATORS.get(intent_type, self.INTENT_TO_OPERATORS["comprehensive"])
        primary_operators = intent_config["primary"].copy()
        fallback_operators = intent_config["fallback"].copy()

        # 3. 数据特征适配
        if data is not None and not data.empty:
            size_category = self._assess_data_size(data)
            logger.info(f"[MAPPING] 数据量类别: {size_category}")

            # 应用数据量适配
            size_adapter = self.DATA_SIZE_ADAPTER.get(size_category, {})
            preferred = size_adapter.get("preferred", [])
            avoid = size_adapter.get("avoid", [])

            # 调整算子列表
            if preferred:
                # 优先使用推荐的算子
                primary_operators = [op for op in preferred if op in primary_operators] + \
                                   [op for op in primary_operators if op not in preferred]

            if avoid:
                # 移除不推荐的算子
                primary_operators = [op for op in primary_operators if op not in avoid]
                fallback_operators = [op for op in fallback_operators if op not in avoid]

        # 4. 过滤实际可用的算子
        if available_operators is not None:
            primary_operators = [op for op in primary_operators if op in available_operators]
            fallback_operators = [op for op in fallback_operators if op in available_operators]

        # 5. 确保至少有一个算子
        if not primary_operators:
            if fallback_operators:
                primary_operators = fallback_operators
                fallback_operators = []
            else:
                # 使用默认算子
                primary_operators = ["zscore", "iqr"]
                logger.warning(f"[MAPPING] 没有可用算子，使用默认算子")

        result = {
            "selected_operators": primary_operators,
            "fallback_operators": fallback_operators,
            "intent_type": intent_type,
            "reason": f"基于意图类型 '{intent_type}' 选择算子",
            "intent_matched": True
        }

        if data is not None and not data.empty:
            result["data_size_category"] = self._assess_data_size(data)

        logger.info(f"[MAPPING] 选择结果: {result['selected_operators']}")

        return result

    def _determine_intent_type(self, intent: Dict[str, Any]) -> str:
        """
        确定意图类型

        Args:
            intent: 查询意图字典

        Returns:
            意图类型字符串
        """
        analysis_types = intent.get("analysis_types", [])
        indicators = intent.get("indicators", [])

        # 如果没有指定分析类型，使用综合分析
        if not analysis_types:
            return "comprehensive"

        # 如果有多个分析类型，使用综合分析
        if len(analysis_types) > 1:
            return "comprehensive"

        # 单个分析类型
        analysis_type = analysis_types[0]

        # 映射到意图类型
        intent_type = self.ANALYSIS_TYPE_TO_INTENT.get(analysis_type, "single_anomaly")

        # 特殊情况：多指标相关性和趋势分析
        if analysis_type in ["correlation", "multi_anomaly"] and len(indicators) < 2:
            logger.warning(f"[MAPPING] {analysis_type} 需要多个指标，但只提供了 {len(indicators)} 个")

        return intent_type

    def _assess_data_size(self, data: pd.DataFrame) -> str:
        """
        评估数据量类别

        Args:
            data: 输入数据

        Returns:
            数据量类别: "small", "medium", "large"
        """
        n_samples = len(data)

        if n_samples < 100:
            return "small"
        elif n_samples < 1000:
            return "medium"
        else:
            return "large"

    def get_operator_info(self, operator_name: str) -> Optional[Dict[str, Any]]:
        """
        获取算子信息

        Args:
            operator_name: 算子名称

        Returns:
            算子信息字典，如果算子不存在则返回 None
        """
        return self.AVAILABLE_OPERATORS.get(operator_name)

    def get_available_operators(self, category: Optional[str] = None) -> List[str]:
        """
        获取可用算子列表

        Args:
            category: 算子类别筛选（可选）

        Returns:
            算子名称列表
        """
        if category is None:
            return list(self.AVAILABLE_OPERATORS.keys())

        return [
            name for name, info in self.AVAILABLE_OPERATORS.items()
            if info.get("category") == category
        ]

    def get_intent_description(self, intent_type: str) -> str:
        """
        获取意图类型描述

        Args:
            intent_type: 意图类型

        Returns:
            意图描述
        """
        config = self.INTENT_TO_OPERATORS.get(intent_type)
        if config:
            return config.get("description", "")
        return ""


# ========== 便捷函数 ==========

def select_operators(
    intent: Dict[str, Any],
    data: Optional[pd.DataFrame] = None,
    available_operators: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    便捷函数：基于意图选择算子

    Args:
        intent: 查询意图
        data: 输入数据
        available_operators: 可用算子列表

    Returns:
        算子选择结果
    """
    mapper = IntentOperatorMapper()
    return mapper.select_operators_by_intent(intent, data, available_operators)


# ========== 入口函数 ==========

def main(intent: Dict[str, Any] = None,
         data: Optional[Dict[str, Any]] = None,
         **kwargs) -> Dict[str, Any]:
    """
    主入口函数 - 意图-算子映射

    Args:
        intent: 查询意图
        data: 数据字典
        **kwargs: 其他参数

    Returns:
        算子选择结果
    """
    import pandas as pd

    # 转换数据格式
    df = None
    if data and "values" in data:
        values_dict = data["values"]
        df = pd.DataFrame(values_dict)

    # 创建映射器并选择算子
    mapper = IntentOperatorMapper()
    result = mapper.select_operators_by_intent(intent, df)

    return {
        "status": "success",
        "operator_selection": result,
        "available_categories": list(set(
            info["category"] for info in mapper.AVAILABLE_OPERATORS.values()
        )),
        "intent_description": mapper.get_intent_description(result.get("intent_type", ""))
    }


def process(intent: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """处理函数别名"""
    return main(intent=intent, **kwargs)


def execute(intent: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """执行函数别名"""
    return main(intent=intent, **kwargs)


# ========== 测试代码 ==========

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    mapper = IntentOperatorMapper()

    print("=" * 80)
    print("意图-算子映射器测试")
    print("=" * 80)

    # 测试场景1：单指标异常检测
    print("\n测试场景1：单指标异常检测")
    intent1 = {
        "analysis_types": ["anomaly"],
        "indicators": ["COD"],
        "query_type": "single"
    }

    result1 = mapper.select_operators_by_intent(intent1)
    print(f"  意图类型: {result1['intent_type']}")
    print(f"  选择算子: {result1['selected_operators']}")
    print(f"  原因: {result1['reason']}")

    # 测试场景2：相关性分析
    print("\n测试场景2：相关性分析")
    intent2 = {
        "analysis_types": ["correlation"],
        "indicators": ["COD", "pH"],
        "query_type": "multi"
    }

    result2 = mapper.select_operators_by_intent(intent2)
    print(f"  意图类型: {result2['intent_type']}")
    print(f"  选择算子: {result2['selected_operators']}")
    print(f"  原因: {result2['reason']}")

    # 测试场景3：综合分析
    print("\n测试场景3：综合分析")
    intent3 = {
        "analysis_types": ["anomaly", "correlation", "trend"],
        "indicators": ["COD", "pH", "TN"],
        "query_type": "multi"
    }

    result3 = mapper.select_operators_by_intent(intent3)
    print(f"  意图类型: {result3['intent_type']}")
    print(f"  选择算子: {result3['selected_operators']}")
    print(f"  原因: {result3['reason']}")

    print("\n" + "=" * 80)
