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

    # Agent服务配置
    # 独立运行的Agent服务地址，后端通过HTTP转发请求
    AGENT_SERVICE_URL: str = "http://localhost:8642"
    AGENT_TIMEOUT: int = 300  # Agent服务请求超时时间（秒）

    # LLM 配置（用于展示）
    LLM_MODEL: str = "ctgu-vlm"

    # 日志配置
    LOG_LEVEL: str = "INFO"

    # 缓存配置
    CACHE_TTL_REALTIME: int = 30
    CACHE_TTL_HISTORY: int = 300
    CACHE_TTL_CONVERSATIONS: int = 3600

    # 数据源配置
    DATA_SOURCE_PATH: str = "./data"
    AGENT_SERVICE_SYNC_INTERVAL: int = 300  # 秒

    # API配置
    API_V1_PREFIX: str = "/api/v1"

    class Config:
        env_file = str(PROJECT_ROOT / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # 忽略额外的环境变量


settings = Settings()

# 调试：验证配置加载
import logging
logger = logging.getLogger(__name__)
# logger.info(f"Loaded HERMES_API_KEY: {settings.HERMES_API_KEY[:2]}***{settings.HERMES_API_KEY[-2:] if len(settings.HERMES_API_KEY) > 4 else '****'}")
# logger.info(f"HERMES_API_URL: {settings.HERMES_API_URL}")
