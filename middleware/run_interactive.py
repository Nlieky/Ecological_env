#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人机交互层启动脚本

使用方式：
    python run_interactive.py

或者在本目录执行：
    python interactive.py
"""

import sys
from pathlib import Path

# 添加项目路径
MIDDLEWARE_DIR = Path(__file__).parent
PROJECT_ROOT = MIDDLEWARE_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "shared" / "configs"))

# 导入交互模块
from interactive import HumanComputerInterface

if __name__ == "__main__":
    interface = HumanComputerInterface()
    interface.run()
