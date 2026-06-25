"""
清理会话目录工具

清理指定天数之前的会话目录，释放存储空间。
"""
import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import re


def cleanup_sessions(days: int = 7) -> int:
    """
    清理指定天数之前的会话目录

    Args:
        days: 保留最近几天的会话（默认 7）

    Returns:
        清理的会话数量
    """
    # 获取 workspace 根目录
    current_dir = Path(__file__).parent.parent.parent.parent
    state_dir = current_dir / "state"

    if not state_dir.exists():
        return 0

    # 计算截止时间
    cutoff_time = datetime.now() - timedelta(days=days)

    # 查找所有会话目录
    session_pattern = re.compile(r'session_\d{8}_\d{6}')
    cleaned_count = 0

    for item in state_dir.iterdir():
        if not item.is_dir():
            continue

        # 检查是否是会话目录
        if not session_pattern.match(item.name):
            continue

        # 从目录名提取时间戳
        try:
            # session_YYYYMMDD_HHMMSS
            timestamp_str = item.name.replace('session_', '').replace('_', '')
            session_time = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")

            # 如果会话早于截止时间，删除
            if session_time < cutoff_time:
                shutil.rmtree(item)
                cleaned_count += 1

        except ValueError:
            # 时间戳解析失败，跳过
            continue

    return cleaned_count


def main():
    """测试入口"""
    print("Testing cleanup_sessions...")

    # 清理 30 天前的会话（测试用）
    count = cleanup_sessions(days=30)
    print(f"Cleaned {count} sessions older than 30 days")

    # 列出当前会话目录
    current_dir = Path(__file__).parent.parent.parent.parent
    state_dir = current_dir / "state"

    if state_dir.exists():
        sessions = list(state_dir.glob("session_*"))
        print(f"Remaining sessions: {len(sessions)}")
        for session in sorted(sessions, reverse=True)[:5]:
            print(f"  - {session.name}")


if __name__ == "__main__":
    main()
