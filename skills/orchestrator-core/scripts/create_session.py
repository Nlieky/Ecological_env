"""
创建会话目录工具

为当前对话创建一个独立的会话目录，用于存储任务和结果。
"""
import os
import json
from datetime import datetime
from pathlib import Path


def _project_root() -> Path:
    """标记法找项目根(含 shared/ + workspace/)，位置无关。"""
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "shared").is_dir() and (parent / "workspace").is_dir():
            return parent
    return p.parents[3]


def create_session(**kwargs) -> str:
    """
    创建新的会话目录

    Returns:
        str: 会话目录的绝对路径
        格式: sessions/session_YYYYMMDD_HHMMSS/
    """
    # 获取项目根目录
    current_dir = _project_root()
    sessions_dir = current_dir / "sessions"

    # 确保会话目录存在
    sessions_dir.mkdir(parents=True, exist_ok=True)

    # 生成会话目录名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_name = f"session_{timestamp}"
    session_path = sessions_dir / session_name

    # 创建会话目录
    session_path.mkdir(exist_ok=True)

    # 创建会话元数据文件
    metadata = {
        "session_id": session_name,
        "created_at": datetime.now().isoformat(),
        "status": "initialized"
    }

    metadata_path = session_path / "_metadata.json"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    return str(session_path.absolute())


def get_session_files(session_path: str) -> dict:
    """
    获取会话目录中的所有文件

    Args:
        session_path: 会话目录路径

    Returns:
        dict: 文件类型到路径的映射（只返回存在的文件）
    """
    session = Path(session_path)
    if not session.exists():
        return {}

    files = {
        "metadata": session / "_metadata.json",
        "task": session / "task.json",
        "data_result": session / "data_result.json",
        "anomaly_result": session / "anomaly_result.json",
        "rule_result": session / "rule_reasoning_result.json",
        "disposition_result": session / "disposition_result.json",
        "final_response": session / "final_response.json",
    }

    # 只返回存在的文件
    return {k: str(v) for k, v in files.items() if v.exists()}


def main():
    """测试入口"""
    session_path = create_session()
    print(f"Created session: {session_path}")

    # 验证文件创建
    metadata_file = Path(session_path) / "_metadata.json"
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        print(f"Session metadata: {json.dumps(metadata, indent=2)}")

    # 测试 get_session_files
    files = get_session_files(session_path)
    print(f"Session files: {files}")


if __name__ == "__main__":
    main()
