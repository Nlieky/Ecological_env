"""
核心配置模块 - 从环境变量加载配置
"""
import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 确定项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Settings(BaseSettings):
    """应用配置"""

    # FastAPI 配置
    FASTAPI_HOST: str = "0.0.0.0"
    FASTAPI_PORT: int = 8000

    # CORS 配置
    CORS_ORIGINS: List[str] = ["*"]

    # Hermes API Server 配置
    HERMES_API_URL: str = "http://localhost:8642"
    HERMES_API_KEY: str = "sk-hermes-api-key"

    # LLM 配置（用于展示）
    LLM_MODEL: str = "ctgu-vlm"

    # 日志配置
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # 忽略额外的环境变量


settings = Settings()
