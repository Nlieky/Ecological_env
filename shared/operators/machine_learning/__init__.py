#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机器学习算子库

基于专利文档：异常检测模型算子库 - 机器学习类算子

机器学习算子用于无监督异常检测：
1. 孤立森林 (IsolationForest) - 基于随机森林的异常检测
2. One-Class SVM (OneClassSVM) - 支持向量机异常检测
3. 局部异常因子 (LOF) - 基于密度的异常检测
4. 直方图离群值评分 (HBOS) - 基于直方图的异常检测
"""

from .isolation_forest import IsolationForestDetector
from .one_class_svm import OneClassSVMDetector
from .lof import LOFDetector
from .hbos import HBOSDetector

__all__ = [
    'IsolationForestDetector',
    'OneClassSVMDetector',
    'LOFDetector',
    'HBOSDetector'
]
