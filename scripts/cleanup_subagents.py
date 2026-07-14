#!/usr/bin/env python
"""子智能体目录清理脚本

删除不必要的文件，保持项目整洁
"""

import os
import shutil
from pathlib import Path

# 项目根目录
project_root = Path(__file__).parents[1]
subagents_root = project_root / "subagents"

# 子智能体应该只保留的文件类型
KEEP_IDENTITY_FILES = {"SOUL.md", "AGENTS.md", "MEMORY.md"}
KEEP_SKILL_CONTENTS = {"SKILL.md", "scripts", "references", "__init__.py"}

# 需要删除的文件/目录模式
DELETE_PATTERNS = [
    # 缓存文件
    "__pycache__",
    "*.pyc",
    ".pyc",

    # 临时文件
    ".skills_prompt_snapshot.json",
    "auth.lock",

    # 临时结果
    "*_result.json",
    "data_result.json",
    "summary_result.json",
    "anomaly_result.json",

    # 会话文件
    "sessions",
    "sessions*",

    # 缓存目录
    "cache",

    # 日志目录
    "logs",

    # 测试数据目录
    "data",

    # 废弃文件
    "test_*.py",
]

# 不需要的身份文件（子智能体只有3个身份文件）
UNNECESSARY_IDENTITY_FILES = {
    "IDENTITY.md",
    "TOOLS.md",
    "USER.md",
}

# 不应该在子智能体根目录的运行文件
RUN_FILES_TO_REMOVE = {
    "run_agent.py",
    "run_agent_direct.py",
    "run_agent_wrapper.py",
    "entry.py",
    "anomaly_detection_agent.py",
    "test_main.py",
    "config.json",
    "consensus_config.yaml",
    "disposition_config.yaml",
}


def should_delete_file(file_path: Path) -> bool:
    """判断文件是否应该删除"""
    name = file_path.name
    parent = file_path.parent.name

    # 检查不需要的身份文件
    if name in UNNECESSARY_IDENTITY_FILES:
        return True

    # 检查运行文件
    if name in RUN_FILES_TO_REMOVE and parent not in ["scripts", "references"]:
        return True

    # 检查模式匹配
    for pattern in DELETE_PATTERNS:
        if pattern.startswith("*"):
            if name.endswith(pattern[1:]):
                return True
        elif pattern.endswith("*"):
            if name.startswith(pattern[:-1]):
                return True
        else:
            if name == pattern or parent == pattern:
                return True

    # 检查目录
    if file_path.is_dir():
        if name in ["__pycache__", "cache", "logs", "data", "sessions"]:
            return True
        if name.startswith("sessions"):
            return True

    return False


def cleanup_subagent(subagent_path: Path) -> dict:
    """清理单个子智能体目录"""
    stats = {
        "deleted_files": [],
        "deleted_dirs": [],
        "kept_files": [],
    }

    print(f"\n清理: {subagent_path.name}")

    # 首先处理目录（从深到浅）
    for item in sorted(subagent_path.rglob("*"), key=lambda x: len(x.parts), reverse=True):
        if not item.exists():
            continue

        if should_delete_file(item):
            if item.is_dir():
                try:
                    shutil.rmtree(item)
                    stats["deleted_dirs"].append(str(item.relative_to(subagent_path)))
                    print(f"  [删除目录] {item.relative_to(subagent_path)}")
                except Exception as e:
                    print(f"  [跳过目录] {item.relative_to(subagent_path)}: {e}")
            elif item.is_file():
                try:
                    item.unlink()
                    stats["deleted_files"].append(str(item.relative_to(subagent_path)))
                    print(f"  [删除文件] {item.relative_to(subagent_path)}")
                except Exception as e:
                    print(f"  [跳过文件] {item.relative_to(subagent_path)}: {e}")

    # 列出保留的文件
    for item in sorted(subagent_path.rglob("*")):
        if item.is_file():
            stats["kept_files"].append(str(item.relative_to(subagent_path)))

    return stats


def main():
    """主函数"""
    print("=" * 70)
    print("子智能体目录清理")
    print("=" * 70)

    total_deleted_files = 0
    total_deleted_dirs = 0

    # 处理每个子智能体
    for subagent_dir in sorted(subagents_root.iterdir()):
        if not subagent_dir.is_dir() or subagent_dir.name.startswith("."):
            continue

        stats = cleanup_subagent(subagent_dir)

        total_deleted_files += len(stats["deleted_files"])
        total_deleted_dirs += len(stats["deleted_dirs"])

        print(f"\n保留文件数: {len(stats['kept_files'])}")

    print("\n" + "=" * 70)
    print(f"总计删除文件: {total_deleted_files}")
    print(f"总计删除目录: {total_deleted_dirs}")
    print("=" * 70)


if __name__ == "__main__":
    main()
