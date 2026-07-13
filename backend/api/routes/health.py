"""
健康检查接口
"""
from fastapi import APIRouter
from backend import __version__
import os
import sys
from pathlib import Path

router = APIRouter()


@router.get("/health", tags=["健康检查"])
async def health_check():
    """
    健康检查接口

    Returns:
        系统健康状态，包括 AIAgent 配置状态
    """
    # 检查 hermes-agent 包是否已安装
    try:
        import run_agent
        hermes_available = True
        hermes_status = "installed"
    except ImportError:
        hermes_available = False
        hermes_status = "not_installed"

    # 检查项目目录
    project_dir = Path(__file__).parent.parent.parent.resolve()
    project_available = project_dir.exists()

    # 检查环境变量
    env_configured = all([
        os.environ.get("LLM_BASE_URL"),
        os.environ.get("LLM_MODEL")
    ])

    # 检查身份文件
    soul_exists = (project_dir / "workspace" / "SOUL.md").exists()

    return {
        "status": "healthy",
        "version": __version__,
        "implementation": "Direct AIAgent Call (hermes-agent package)",
        "components": {
            "hermes_framework": {
                "status": hermes_status,
                "note": "hermes-agent should be installed via: pip install hermes-agent"
            },
            "project_directory": {
                "status": "ok" if project_available else "not_found",
                "path": str(project_dir)
            },
            "environment_config": {
                "status": "configured" if env_configured else "missing",
                "llm_base_url": os.environ.get("LLM_BASE_URL", "not_set"),
                "llm_model": os.environ.get("LLM_MODEL", "not_set")
            },
            "identity_files": {
                "status": "loaded" if soul_exists else "not_found",
                "soul_md": "workspace/SOUL.md"
            }
        }
    }
