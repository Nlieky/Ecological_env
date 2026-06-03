#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专用算子库

基于专利文档：异常检测模型算子库 - 专用类算子

专用算子用于检测特定的违规模式：
1. 恒定检测器 (constant_detector) - 检测插瓶干扰
2. 变点检测器 (change_point_detector) - 检测突变点
3. 平滑度检测器 (smoothness_detector) - 检测人工拟合
4. 造假检测器 (forgery_detector) - 检测恶意逃避
"""

from .constant_detector import ConstantDetector
from .change_point_detector import ChangePointDetector
from .smoothness_detector import SmoothnessDetector
from .forgery_detector import ForgeryDetector

__all__ = [
    'ConstantDetector',
    'ChangePointDetector',
    'SmoothnessDetector',
    'ForgeryDetector'
]
