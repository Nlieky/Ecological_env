#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度学习算子库

基于专利文档：异常检测模型算子库 - 深度学习类算子

深度学习算子用于处理长序列数据和复杂模式：
1. LSTM自编码器 (LSTMAutoEncoder) - 基于长短期记忆网络的自编码器
2. 变分自编码器 (VariationalAutoEncoder) - 基于变分推断的自编码器
"""

from .lstm_autoencoder import LSTMAutoEncoder
from .variational_autoencoder import VariationalAutoEncoder

__all__ = [
    'LSTMAutoEncoder',
    'VariationalAutoEncoder'
]
