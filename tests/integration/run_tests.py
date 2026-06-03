#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端集成测试运行脚本
"""
import sys
import os

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 运行测试文件
test_file = os.path.join(current_dir, "test_end_to_end.py")
with open(test_file, 'r', encoding='utf-8') as f:
    code = f.read()

# 执行测试代码
exec(code)
