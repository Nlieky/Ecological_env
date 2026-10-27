# shared/framework/hermes_agent/agent/identity_loader.py
"""身份文件加载器 - 支持从自定义路径加载身份文件"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# 身份文件列表（与hermes_constants保持一致）
IDENTITY_FILES = [
    "IDENTITY.md",    # 身份卡片
    "SOUL.md",        # 身份和个性
    "AGENTS.md",      # 工作区规范
    "MEMORY.md",      # 长期记忆
    "USER.md",        # 用户信息
    "TOOLS.md",       # 工具配置
    "HEARTBEAT.md"    # 周期性任务
]


def load_identity_files_from_path(identity_path: Path, filenames=None) -> Optional[str]:
    """从指定路径加载所有身份文件并组合成提示

    Args:
        identity_path: 身份文件所在目录路径

    Returns:
        组合后的身份文件内容，如果没有找到任何文件则返回 None
    """
    if not identity_path.exists():
        logger.debug(f"Identity path does not exist: {identity_path}")
        return None

    parts = []
    for filename in (IDENTITY_FILES if filenames is None else filenames):
        file_path = identity_path / filename
        if not file_path.exists():
            logger.debug(f"Identity file not found: {file_path}")
            continue

        try:
            content = file_path.read_text(encoding="utf-8").strip()
            if not content:
                continue
            parts.append(f"## {filename}\n\n{content}")
        except Exception as e:
            logger.debug(f"Could not read identity file {file_path}: {e}")

    # 主智能体编排技能不再预加载（2026-07-27）：改用 hermes 原生 skill_view，
    # 主智能体用 skill_view('orchestrator-core') 读编排技能（HERMES_HOME=workspace 作用域）。
    # 引导见 workspace/AGENTS.md。与子智能体机制统一（均 hermes 原生 skill_view）。

    if not parts:
        return None

    return "\n\n".join(parts)


def load_single_identity_file(identity_path: Path, filename: str) -> Optional[str]:
    """从指定路径加载单个身份文件

    Args:
        identity_path: 身份文件所在目录路径
        filename: 要加载的文件名

    Returns:
        文件内容，如果文件不存在则返回 None
    """
    file_path = identity_path / filename
    if not file_path.exists():
        return None

    try:
        content = file_path.read_text(encoding="utf-8").strip()
        return content if content else None
    except Exception as e:
        logger.debug(f"Could not read identity file {file_path}: {e}")
        return None


def resolve_identity_path(identity_path: str | Path | None, project_root: Path) -> Path:
    """解析身份文件路径

    Args:
        identity_path: 身份文件路径（相对或绝对）
        project_root: 项目根目录

    Returns:
        解析后的绝对路径
    """
    if not identity_path:
        return project_root / "workspace"

    identity_path = Path(identity_path)
    if identity_path.is_absolute():
        return identity_path

    # 相对路径：相对于项目根目录
    return project_root / identity_path
