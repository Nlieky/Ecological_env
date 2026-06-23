"""
废水监测系统后端 - Hermes API Server 集成

为已完成的 Hermes 智能体系统提供 HTTP 接口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from backend.api.routes import health, hermes, query
from backend.core.config import settings
from backend.metrics.definitions import (
    api_requests_total,
    api_request_duration_seconds
)

app = FastAPI(
    title="废水监测系统 API",
    version="2.0.0",
    description="""
## Hermes 智能体 HTTP 接口层

本系统为已完成的 **Hermes 智能体系统** 提供 HTTP 接口，
通过 Hermes API Server 调用主智能体，展示其完整的决策过程。

### 核心接口

- `/api/query` - 查询接口（展示决策树和调用链）
- `/api/hermes/system` - Hermes 系统完整信息
- `/api/hermes/skills` - 加载的技能列表
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
app.include_router(hermes.router, prefix="/api")
app.include_router(query.router, prefix="/api")


@app.get("/", tags=["根路径"])
async def root():
    """根路径 - 重定向到 API 文档"""
    return RedirectResponse(url="/docs")


@app.on_event("startup")
async def startup():
    """启动时初始化"""
    from backend.api.client import get_hermes_client
    # 验证 Hermes API Server 连接
    try:
        client = get_hermes_client()
        await client.health_check()
        print("✓ Hermes API Server 连接成功")
    except Exception as e:
        print(f"✗ Hermes API Server 连接失败: {e}")


@app.on_event("shutdown")
async def shutdown():
    """关闭时清理"""
    pass
