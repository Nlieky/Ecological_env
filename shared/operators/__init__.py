#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异常检测模型算子库

基于专利文档：异常检测模型算子库

算子分类：
1. 统计类（statistical）：zscore、iqr、grubbs、moving_average
2. 机器学习类（machine_learning）：isolation_forest、one_class_svm、lof、hbos
3. 深度学习类（deep_learning）：lstm_autoencoder、variational_autoencoder
4. 专用类（specialized）：constant_detector、change_point_detector、smoothness_detector、forgery_detector
"""

# 机器学习类算子
from .machine_learning import (
    IsolationForestDetector,
    OneClassSVMDetector,
    LOFDetector,
    HBOSDetector
)

# 深度学习类算子
from .deep_learning import (
    LSTMAutoEncoder,
    VariationalAutoEncoder
)

# 专用类算子
from .specialized import (
    ConstantDetector,
    ChangePointDetector,
    SmoothnessDetector,
    ForgeryDetector
)

__all__ = [
    # 机器学习类
    'IsolationForestDetector',
    'OneClassSVMDetector',
    'LOFDetector',
    'HBOSDetector',
    # 深度学习类
    'LSTMAutoEncoder',
    'VariationalAutoEncoder',
    # 专用类
    'ConstantDetector',
    'ChangePointDetector',
    'SmoothnessDetector',
    'ForgeryDetector'
]

# 算子类型映射
OPERATOR_TYPES = {
    'statistical': ['zscore', 'iqr', 'grubbs', 'moving_average'],
    'machine_learning': ['isolation_forest', 'one_class_svm', 'lof', 'hbos'],
    'deep_learning': ['lstm_autoencoder', 'variational_autoencoder'],
    'specialized': ['constant_detector', 'change_point_detector', 'smoothness_detector', 'forgery_detector']
}

# 算子类映射
OPERATOR_CLASSES = {
    # 机器学习类
    'isolation_forest': IsolationForestDetector,
    'one_class_svm': OneClassSVMDetector,
    'lof': LOFDetector,
    'hbos': HBOSDetector,
    # 深度学习类
    'lstm_autoencoder': LSTMAutoEncoder,
    'variational_autoencoder': VariationalAutoEncoder,
    # 专用类
    'constant_detector': ConstantDetector,
    'change_point_detector': ChangePointDetector,
    'smoothness_detector': SmoothnessDetector,
    'forgery_detector': ForgeryDetector
}


def get_operator(operator_name: str, **kwargs):
    """
    获取算子实例

    Args:
        operator_name: 算子名称
        **kwargs: 算子参数

    Returns:
        算子实例
    """
    operator_class = OPERATOR_CLASSES.get(operator_name)
    if operator_class is None:
        raise ValueError(f"未知算子: {operator_name}")
    return operator_class(**kwargs)


def list_operators(operator_type: str = None) -> list:
    """
    列出可用算子

    Args:
        operator_type: 算子类型（None表示全部）

    Returns:
        算子名称列表
    """
    if operator_type is None:
        return list(OPERATOR_CLASSES.keys())
    return OPERATOR_TYPES.get(operator_type, [])
