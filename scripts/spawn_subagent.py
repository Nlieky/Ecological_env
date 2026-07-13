#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
子智能体启动脚本

> **状态**: 🚧 待实现
> **用途**: 通过命令行启动指定的子智能体

用法:
    python spawn_subagent.py --agent multi-dimensional-data-perception
    python spawn_subagent.py --agent anomaly-detection --task "检测异常"
"""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="启动子智能体")
    parser.add_argument(
        "--agent",
        required=True,
        choices=[
            "multi-dimensional-data-perception",
            "anomaly-detection",
            "rule-reasoning",
            "disposition-execution"
        ],
        help="子智能体名称"
    )
    parser.add_argument("--task", help="任务描述")
    parser.add_argument("--session-dir", help="会话目录路径")

    args = parser.parse_args()

    # TODO: 实现子智能体启动逻辑
    print(f"[TODO] 启动子智能体: {args.agent}")
    if args.task:
        print(f"[TODO] 任务: {args.task}")

    sys.exit(0)


if __name__ == "__main__":
    main()
