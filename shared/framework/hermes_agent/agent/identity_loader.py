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


def load_identity_files_from_path(identity_path: Path) -> Optional[str]:
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
    for filename in IDENTITY_FILES:
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

    # 主智能体编排技能预加载：若 identity_path 下有 skills/orchestrator-core/SKILL.md
    # （只主智能体 workspace 有此路径，子智能体没有 → 天然只对主智能体生效），把全文
    # （剥掉 YAML frontmatter）拼进身份内容，让主智能体读 skill 来决策子智能体调用。
    # 这段内容经 vendored system_prompt.py 的 patch 进入系统提示词 stable tier（持久）。
    skill_path = identity_path / "skills" / "orchestrator-core" / "SKILL.md"
    if skill_path.exists():
        try:
            raw = skill_path.read_text(encoding="utf-8").strip()
            # 剥掉开头 YAML frontmatter（--- name: ... --- 段）
            if raw.startswith("---"):
                chunks = raw.split("---", 2)
                if len(chunks) >= 3:
                    raw = chunks[2].strip()
            if raw:
                parts.append(f"## 主智能体编排技能（orchestrator-core/SKILL.md）\n\n{raw}")
        except Exception as e:
            logger.debug(f"Could not read orchestrator skill {skill_path}: {e}")

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
