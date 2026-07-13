#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
子智能体注册脚本

> **状态**: 🚧 待实现
> **用途**: 注册新的子智能体到系统

用法:
    python register_subagent.py --name new-agent --path ./subagents/new-agent
"""

import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="注册子智能体")
    parser.add_argument("--name", required=True, help="子智能体名称")
    parser.add_argument("--path", required=True, help="子智能体路径")
    parser.add_argument("--description", help="子智能体描述")

    args = parser.parse_args()

    # TODO: 实现子智能体注册逻辑
    print(f"[TODO] 注册子智能体: {args.name}")
    print(f"[TODO] 路径: {args.path}")

    sys.exit(0)


if __name__ == "__main__":
    main()
