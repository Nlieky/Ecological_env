"""
废水监测系统后端 - Hermes API Server 集成

为已完成的 Hermes 智能体系统提供 HTTP 接口
"""
import os
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from backend.exceptions import BackendException
from backend.api.routes import health, query, logs, realtime, events, tracing
from backend.api.v1 import data as v1_data
from backend.api.v1 import conversations as v1_conversations
from backend.core.config import settings
from backend.metrics.definitions import (
    api_requests_total,
    api_request_duration_seconds
)
from backend.middleware import LoggingMiddleware
from backend.utils.loggers import log_system_error


def _log_exception_error(exc: Exception, request: Request) -> None:
    """
    Helper function to log exception errors consistently.

    This function handles the duplicate logging logic that was previously
    in both exception handlers, ensuring consistent error logging across
    all exception types.

    Args:
        exc: The exception that was raised
        request: The FastAPI request object
    """
    try:
        log_system_error(
            level="ERROR",
            module="backend",
            error_type=type(exc).__name__,
            error_message=str(exc),
            stack_trace=traceback.format_exc(),
            context={"path": request.url.path, "method": request.method}
        )
    except Exception as log_error:
        print(f"Failed to log system error: {log_error}")


app = FastAPI(
    title="废水监测系统 API",
    version="2.0.0",
    description="""
## Hermes 智能体 HTTP 接口层

本系统为已完成的 **Hermes 智能体系统** 提供 HTTP 接口，
通过 Hermes API Server 调用主智能体，展示其完整的决策过程。

### 核心接口

- `/api/query` - 查询接口（展示决策树和调用链）
- `/api/health` - 健康检查

### 架构

```
前端 → FastAPI → Hermes API Server → 主智能体（决策树）→ 4 个子智能体
```

详细架构见：`docs/architecture/technical-design.md`
    """,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 日志中间件
app.add_middleware(LoggingMiddleware)

# Prometheus 监控 - 自定义指标端点（兼容 Python 3.8）
from prometheus_client import generate_latest

@app.get("/metrics")
async def metrics():
    """Prometheus 指标端点"""
    from prometheus_client import CONTENT_TYPE_LATEST
    from fastapi.responses import Response
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# 启动废水指标后台更新器（从历史 CSV 模拟实时，填充 wastewater_* gauge 供 Prometheus 抓取）
from backend.metrics.updater import get_updater as _get_ww_updater


@app.on_event("startup")
async def _start_wastewater_metrics():
    _get_ww_updater(interval=5.0).start()
    # 托管 Prometheus 子进程（项目内二进制，不再依赖外部路径）；端口已占用则自动跳过
    from backend.metrics.prometheus_runner import start_prometheus
    start_prometheus()

# 路由注册
app.include_router(health.router, prefix="/api")
app.include_router(query.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(realtime.router, prefix="/api")
app.include_router(events.router, prefix="/api")
app.include_router(tracing.router, prefix="/api")

# 注册v1路由
app.include_router(v1_data.realtime.router, prefix="/api/v1")
app.include_router(v1_data.history.router, prefix="/api/v1")
app.include_router(v1_conversations.conversations.router, prefix="/api/v1")


# 全局异常处理器
@app.exception_handler(BackendException)
async def backend_exception_handler(request: Request, exc: BackendException):
    """后端异常处理器"""
    _log_exception_error(exc, request)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": exc.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理，记录到系统错误日志"""
    _log_exception_error(exc, request)

    # 返回错误响应
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Internal server error",
                "details": {}
            },
            "timestamp": datetime.now().isoformat()
        }
    )


@app.get("/", tags=["根路径"])
async def root():
    """根路径 - 重定向到 API 文档"""
    return RedirectResponse(url="/docs")


@app.on_event("startup")
async def startup():
    """启动时初始化"""
    # 验证 AgentService 可用
    try:
        from backend.services.agent_service import AgentService
        service = AgentService()
        print("[OK] AgentService initialized")
    except Exception as e:
        print(f"[ERROR] AgentService initialization failed: {e}")


@app.on_event("shutdown")
async def shutdown():
    """关闭时清理"""
    pass
