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

    # AgentService 配置
    # AgentService 封装了对 Hermes 智能体的调用，通过 HTTP 与 Hermes API 通信
    # 注意：Hermes API 仍运行在 localhost:8642（由 Hermes Agent 框架提供）
    AGENT_SERVICE_URL: str = "http://localhost:8642"
    AGENT_TIMEOUT: int = 600  # AgentService 请求超时时间（秒）— 完整pipeline 4子智能体~280-310s，留余量

    # 前端 dev server（/system/status 六服务探测用，.env 可覆盖）
    FRONTEND_URL: str = "http://localhost:5173"

    # LLM 配置（用于展示）
    LLM_MODEL: str = "ctgu-vlm"

    # 日志配置
    LOG_LEVEL: str = "INFO"

    # 缓存配置
    CACHE_TTL_REALTIME: int = 30
    CACHE_TTL_HISTORY: int = 300
    CACHE_TTL_CONVERSATIONS: int = 3600

    # 数据源配置
    DATA_SOURCE_PATH: str = "./shared/data"
    AGENT_SERVICE_SYNC_INTERVAL: int = 300  # 秒

    # 监测数据后端: influxdb(读 InfluxDB monitoring-data)或 csv(读 shared/data/*.csv)
    MONITORING_DATA_SOURCE: str = "influxdb"
    # InfluxDB v2.7 配置(工业时序数据源,原生 Windows 二进制)
    INFLUXDB_URL: str = "http://localhost:8086"
    INFLUXDB_TOKEN: str = ""
    INFLUXDB_ORG: str = "ecological_env"
    INFLUXDB_BUCKET: str = "monitoring-data"

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
