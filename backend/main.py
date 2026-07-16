"""
废水监测系统后端 - Hermes API Server 集成

为已完成的 Hermes 智能体系统提供 HTTP 接口
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from backend.api.routes import health, query, logs, realtime, events, tracing
from backend.core.config import settings
from backend.metrics.definitions import (
    api_requests_total,
    api_request_duration_seconds
)
from backend.middleware import LoggingMiddleware
from backend.utils.loggers import log_system_error

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

# 路由注册
app.include_router(health.router, prefix="/api")
app.include_router(query.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(realtime.router, prefix="/api")
app.include_router(events.router, prefix="/api")
app.include_router(tracing.router, prefix="/api")


# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理，记录到系统错误日志"""
    import traceback

    # 记录错误日志
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

    # 返回错误响应
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
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
