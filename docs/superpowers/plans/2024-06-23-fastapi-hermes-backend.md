# FastAPI 后端 + Hermes 智能体集成实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建现代 FastAPI 后端，集成 Hermes 智能体框架，提供 HTTP API 接口，支持 Prometheus 监控，作为废水监测系统的核心服务层。

**Architecture:** FastAPI 提供 REST API 接口，通过 Hermes 框架调用智能体进行 LLM 驱动的任务分析和子智能体调度。后端只做接口转发和数据持久化，不做智能体编排决策。Prometheus 负责系统监控，PostgreSQL 负责业务数据存储。

**Tech Stack:** FastAPI 0.109+, Python 3.12, Pydantic v2, SQLAlchemy 2.0, Prometheus (prometheus-fastapi-instrumentator), Hermes Agent 框架

---

## 文件结构

### 需要创建的文件

```
backend/
├── __init__.py                     # 包初始化文件
├── main.py                         # FastAPI 应用入口
├── api/
│   ├── __init__.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── health.py               # 健康检查接口
│   │   └── query.py                # 查询接口（Hermes 集成）
│   └── dependencies.py            # 依赖注入
├── core/
│   ├── __init__.py
│   ├── config.py                   # 配置加载
│   └── hermes.py                   # Hermes 智能体集成
├── models/
│   ├── __init__.py
│   └── query.py                    # Pydantic 数据模型
├── db/
│   ├── __init__.py
│   ├── session.py                  # 数据库会话
│   └── base.py                     # SQLAlchemy 基类
└── metrics/
    ├── __init__.py
    └── definitions.py              # Prometheus 指标定义

tests/
└── backend/
    ├── __init__.py
    ├── test_config.py              # 配置测试
    ├── test_health.py              # 健康检查测试
    └── test_query.py               # 查询接口测试

pyproject.toml                       # Python 项目配置
requirements.txt                      # 依赖列表（向后兼容）
```

### 需要修改的文件

```
.env                                 # 已存在，添加 FastAPI 相关配置
```

### 现有项目依赖

```
.hermes/config.yaml                  # Hermes 配置（已存在）
subagents/                           # 子智能体目录（已存在）
workspace/                           # 主智能体目录（已存在）
shared/                              # 共享资源（已存在）
```

---

## Task 1: 创建项目依赖配置

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`

- [ ] **Step 1: 创建 pyproject.toml**

```toml
[project]
name = "ecological-env-backend"
version = "2.0.0"
description = "废水监测系统后端 - FastAPI + Hermes 智能体"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "sqlalchemy>=2.0.25",
    "alembic>=1.13.0",
    "psycopg2-binary>=2.9.9",
    "prometheus-fastapi-instrumentator>=7.0.0",
    "python-dotenv>=1.0.0",
    "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.26.0",
    "ruff>=0.1.0",
    "mypy>=1.8.0",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"
```

- [ ] **Step 2: 创建 requirements.txt（向后兼容）**

```txt
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
sqlalchemy>=2.0.25
alembic>=1.13.0
psycopg2-binary>=2.9.9
prometheus-fastapi-instrumentator>=7.0.0
python-dotenv>=1.0.0
python-multipart>=0.0.9
```

- [ ] **Step 3: 安装依赖并验证**

```bash
cd e:/project/Ecological_env
pip install -e .
```

预期输出: `Successfully installed ecological-env-backend-2.0.0`

- [ ] **Step 4: 提交**

```bash
git add pyproject.toml requirements.txt
git commit -m "feat: add FastAPI project dependencies configuration"
```

---

## Task 2: 创建核心配置模块

**Files:**
- Create: `backend/__init__.py`
- Create: `backend/core/__init__.py`
- Create: `backend/core/config.py`

- [ ] **Step 1: 创建 backend/__init__.py**

```python
"""
废水监测系统后端 - FastAPI + Hermes 智能体集成

提供 REST API 接口，集成 Hermes 智能体框架进行 LLM 驱动的任务分析。
"""

__version__ = "2.0.0"
```

- [ ] **Step 2: 创建 backend/core/__init__.py**

```python
"""核心配置模块"""
```

- [ ] **Step 3: 创建 backend/core/config.py**

```python
"""
核心配置模块 - 从环境变量加载配置

所有敏感信息从项目根目录 .env 加载
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
    FASTAPI_DEBUG: bool = False
    
    # CORS 配置
    CORS_ORIGINS: List[str] = ["*"]
    
    # 数据库配置
    DATABASE_URL: str = "sqlite:///./ecological_env.db"
    
    # LLM 配置
    LLM_BASE_URL: str = "http://172.16.12.41:30000/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "ctgu-vlm"
    
    # Hermes 配置
    HERMES_LOAD_SOUL_IDENTITY: bool = True
    HERMES_ENABLED_TOOLSETS: List[str] = ["delegation"]
    
    # Prometheus 配置
    PROMETHEUS_PORT: int = 9090
    ENABLE_PROMETHEUS: bool = True
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 全局配置实例
settings = Settings()
```

- [ ] **Step 4: 创建配置测试**

```python
# tests/backend/test_config.py
"""配置模块测试"""
import os
from pathlib import Path
import pytest
from backend.core.config import settings, PROJECT_ROOT


def test_project_root_exists():
    """测试项目根目录存在"""
    assert PROJECT_ROOT.exists()
    assert (PROJECT_ROOT / ".env").exists()


def test_settings_load():
    """测试配置加载"""
    assert settings.FASTAPI_PORT == 8000
    assert settings.LLM_MODEL == "ctgu-vlm"
    assert settings.ENABLE_PROMETHEUS is True


def test_llm_config_from_env():
    """测试 LLM 配置从环境变量加载"""
    # .env 中的值
    assert "172.16.12.41" in settings.LLM_BASE_URL
    assert settings.LLM_API_KEY != ""
```

- [ ] **Step 5: 运行测试验证配置加载**

```bash
cd e:/project/Ecological_env
pytest tests/backend/test_config.py -v
```

预期输出: `PASSED test_config.py`

- [ ] **Step 6: 提交**

```bash
git add backend/ tests/backend/
git commit -m "feat: add core configuration module with environment loading"
```

---

## Task 3: 创建数据库基础模块

**Files:**
- Create: `backend/db/__init__.py`
- Create: `backend/db/base.py`
- Create: `backend/db/session.py`

- [ ] **Step 1: 创建 backend/db/__init__.py**

```python
"""数据库模块"""
```

- [ ] **Step 2: 创建 backend/db/base.py**

```python
"""
SQLAlchemy 基类配置

定义所有数据库模型的基类和通用配置
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.core.config import settings

# 创建数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建声明式基类
Base = declarative_base()
```

- [ ] **Step 3: 创建 backend/db/session.py**

```python
"""
数据库会话管理

提供依赖注入用的数据库会话获取函数
"""
from typing import Generator
from sqlalchemy.orm import Session
from backend.db.base import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话（依赖注入）
    
    用法:
        @app.get("/api/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: 创建数据库测试**

```python
# tests/backend/test_db.py
"""数据库模块测试"""
import pytest
from backend.db.base import engine, Base, SessionLocal
from backend.db.session import get_db


def test_database_engine():
    """测试数据库引擎创建"""
    assert engine is not None


def test_session_local():
    """测试会话工厂"""
    session = SessionLocal()
    assert session is not None
    session.close()


def test_get_db():
    """测试依赖注入函数"""
    db_gen = get_db()
    db = next(db_gen)
    assert db is not None
    # 清理
    try:
        next(db_gen)
    except StopIteration:
        pass
```

- [ ] **Step 5: 运行测试验证数据库模块**

```bash
pytest tests/backend/test_db.py -v
```

预期输出: `PASSED test_db.py`

- [ ] **Step 6: 提交**

```bash
git add backend/db/ tests/backend/test_db.py
git commit -m "feat: add database base module and session management"
```

---

## Task 4: 创建 Hermes 智能体集成模块

**Files:**
- Create: `backend/core/hermes.py`

- [ ] **Step 1: 创建 Hermes 集成测试（先写测试）**

```python
# tests/backend/test_hermes.py
"""Hermes 智能体集成测试"""
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

# 添加 Hermes 框架到路径
hermes_path = Path("D:/Hermes/hermes-agent")
if hermes_path.exists():
    sys.path.insert(0, str(hermes_path))


@pytest.mark.skipif(
    not Path("D:/Hermes/hermes-agent").exists(),
    reason="Hermes framework not found"
)
class TestHermesIntegration:
    """Hermes 智能体集成测试"""
    
    @patch('backend.core.hermes.AIAgent')
    def test_init_hermes_agent(self, mock_ai_agent):
        """测试 Hermes 智能体初始化"""
        from backend.core.hermes import init_hermes_agent, HermesAgentConfig
        
        # 创建配置
        config = HermesAgentConfig(
            base_url="http://test.com/v1",
            model="test-model",
            api_key="test-key",
            load_soul_identity=True,
            enabled_toolsets=["delegation"]
        )
        
        # 调用初始化
        agent = init_hermes_agent(config)
        
        # 验证 AIAgent 被正确调用
        mock_ai_agent.assert_called_once()
        assert agent is not None
    
    def test_hermes_config_defaults(self):
        """测试 Hermes 配置默认值"""
        from backend.core.hermes import HermesAgentConfig
        from backend.core.config import settings
        
        config = HermesAgentConfig()
        
        assert config.base_url == settings.LLM_BASE_URL
        assert config.model == settings.LLM_MODEL
        assert config.api_key == settings.LLM_API_KEY
        assert config.load_soul_identity is True
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/backend/test_hermes.py -v
```

预期输出: `FAILED with ImportError: cannot import name 'init_hermes_agent'`

- [ ] **Step 3: 创建 backend/core/hermes.py（最小实现）**

```python
"""
Hermes 智能体集成模块

提供 Hermes AIAgent 的初始化和依赖注入
"""
import sys
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel
from backend.core.config import settings

# 添加 Hermes 框架到路径
HERMES_PATH = Path("D:/Hermes/hermes-agent")
if HERMES_PATH.exists():
    sys.path.insert(0, str(HERMES_PATH))


class HermesAgentConfig(BaseModel):
    """Hermes 智能体配置"""
    base_url: str = settings.LLM_BASE_URL
    model: str = settings.LLM_MODEL
    api_key: str = settings.LLM_API_KEY
    load_soul_identity: bool = settings.HERMES_LOAD_SOUL_IDENTITY
    enabled_toolsets: List[str] = settings.HERMES_ENABLED_TOOLSETS


def init_hermes_agent(config: Optional[HermesAgentConfig] = None):
    """
    初始化 Hermes 智能体
    
    Args:
        config: 智能体配置，如果为 None 则使用默认配置
    
    Returns:
        Hermes AIAgent 实例
    """
    if config is None:
        config = HermesAgentConfig()
    
    try:
        from run_agent import AIAgent
    except ImportError:
        raise ImportError(
            "Hermes framework not found. Please ensure Hermes is installed at: "
            f"{HERMES_PATH}"
        )
    
    return AIAgent(
        base_url=config.base_url,
        model=config.model,
        api_key=config.api_key,
        load_soul_identity=config.load_soul_identity,
        enabled_toolsets=config.enabled_toolsets
    )


# 全局智能体实例（延迟初始化）
_agent = None


def get_hermes_agent():
    """
    获取 Hermes 智能体实例（依赖注入）
    
    用法:
        @app.get("/api/query")
        def query(request: QueryRequest, agent = Depends(get_hermes_agent)):
            return agent.run_conversation(...)
    """
    global _agent
    if _agent is None:
        _agent = init_hermes_agent()
    return _agent
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/backend/test_hermes.py -v
```

预期输出: `PASSED test_hermes.py`

- [ ] **Step 5: 提交**

```bash
git add backend/core/hermes.py tests/backend/test_hermes.py
git commit -m "feat: add Hermes agent integration module"
```

---

## Task 5: 创建 Pydantic 数据模型

**Files:**
- Create: `backend/models/__init__.py`
- Create: `backend/models/query.py`

- [ ] **Step 1: 创建 backend/models/__init__.py**

```python
"""Pydantic 数据模型"""
```

- [ ] **Step 2: 创建 backend/models/query.py**

```python
"""
查询接口的数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class QueryRequest(BaseModel):
    """查询请求模型"""
    query: str = Field(..., description="用户查询内容", min_length=1)
    session_id: Optional[str] = Field(None, description="会话ID，用于多轮对话")
    parameters: Optional[Dict[str, Any]] = Field(None, description="额外参数")


class QueryResponse(BaseModel):
    """查询响应模型"""
    result: str = Field(..., description="LLM 生成的响应结果")
    session_id: str = Field(..., description="会话ID")
    timestamp: str = Field(..., description="响应时间戳")
    model_used: Optional[str] = Field(None, description="使用的模型名称")
    tokens_used: Optional[int] = Field(None, description="消耗的 Token 数")


class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    detail: Optional[str] = Field(None, description="详细错误信息")
```

- [ ] **Step 3: 创建模型测试**

```python
# tests/backend/test_models.py
"""数据模型测试"""
import pytest
from backend.models.query import QueryRequest, QueryResponse, ErrorResponse


def test_query_request_valid():
    """测试有效的查询请求"""
    request = QueryRequest(query="测试查询")
    assert request.query == "测试查询"
    assert request.session_id is None


def test_query_request_with_session():
    """测试带会话ID的查询请求"""
    request = QueryRequest(
        query="测试查询",
        session_id="test-session-123"
    )
    assert request.session_id == "test-session-123"


def test_query_request_min_length():
    """测试查询内容最小长度验证"""
    with pytest.raises(ValueError):
        QueryRequest(query="")


def test_query_response():
    """测试查询响应"""
    response = QueryResponse(
        result="测试结果",
        session_id="test-session",
        timestamp="2024-06-23T10:00:00Z"
    )
    assert response.result == "测试结果"
    assert response.session_id == "test-session"


def test_error_response():
    """测试错误响应"""
    error = ErrorResponse(
        error="ValidationError",
        message="请求参数无效"
    )
    assert error.error == "ValidationError"
    assert error.message == "请求参数无效"
```

- [ ] **Step 4: 运行测试验证模型**

```bash
pytest tests/backend/test_models.py -v
```

预期输出: `PASSED test_models.py`

- [ ] **Step 5: 提交**

```bash
git add backend/models/ tests/backend/test_models.py
git commit -m "feat: add Pydantic data models for query API"
```

---

## Task 6: 创建 Prometheus 监控指标

**Files:**
- Create: `backend/metrics/__init__.py`
- Create: `backend/metrics/definitions.py`

- [ ] **Step 1: 创建 backend/metrics/__init__.py**

```python
"""Prometheus 监控指标"""
```

- [ ] **Step 2: 创建 backend/metrics/definitions.py**

```python
"""
Prometheus 监控指标定义

定义 FastAPI 应用需要暴露的监控指标
"""
from prometheus_client import Counter, Histogram, Summary, Gauge
import time

# API 请求计数器
api_requests_total = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

# API 请求耗时直方图
api_request_duration_seconds = Histogram(
    'api_request_duration_seconds',
    'API request duration in seconds',
    ['method', 'endpoint']
)

# LLM 调用计数器
llm_calls_total = Counter(
    'llm_calls_total',
    'Total LLM calls',
    ['model', 'status']
)

# LLM 调用耗时
llm_call_duration_seconds = Summary(
    'llm_call_duration_seconds',
    'LLM call duration in seconds'
)

# Token 使用计数器
llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total LLM tokens used',
    ['model', 'token_type']  # token_type: prompt, completion
)

# 当前活跃会话数 gauge
active_sessions = Gauge(
    'active_sessions',
    'Number of active sessions'
)
```

- [ ] **Step 3: 创建监控指标测试**

```python
# tests/backend/test_metrics.py
"""监控指标测试"""
from prometheus_client import REGISTRY
from backend.metrics.definitions import (
    api_requests_total,
    api_request_duration_seconds,
    llm_calls_total,
    llm_tokens_total,
    active_sessions
)


def test_api_requests_total():
    """测试 API 请求计数器"""
    api_requests_total.labels('GET', '/api/health', '200').inc()
    
    # 获取指标值
    metric = REGISTRY.get_sample_value('api_requests_total', {'method': 'GET', 'endpoint': '/api/health', 'status': '200'})
    assert metric is not None


def test_llm_calls_total():
    """测试 LLM 调用计数器"""
    llm_calls_total.labels('ctgu-vlm', 'success').inc()
    
    metric = REGISTRY.get_sample_value('llm_calls_total', {'model': 'ctgu-vlm', 'status': 'success'})
    assert metric is not None


def test_llm_tokens_total():
    """测试 Token 使用计数器"""
    llm_tokens_total.labels('ctgu-vlm', 'prompt').inc(100)
    llm_tokens_total.labels('ctgu-vlm', 'completion').inc(50)
    
    prompt_metric = REGISTRY.get_sample_value('llm_tokens_total', {'model': 'ctgu-vlm', 'token_type': 'prompt'})
    completion_metric = REGISTRY.get_sample_value('llm_tokens_total', {'model': 'ctgu-vlm', 'token_type': 'completion'})
    
    assert prompt_metric == 100.0
    assert completion_metric == 50.0


def test_active_sessions():
    """测试活跃会话数"""
    active_sessions.set(5)
    
    metric = REGISTRY.get_sample_value('active_sessions', {})
    assert metric == 5.0
```

- [ ] **Step 4: 运行测试验证监控指标**

```bash
pytest tests/backend/test_metrics.py -v
```

预期输出: `PASSED test_metrics.py`

- [ ] **Step 5: 提交**

```bash
git add backend/metrics/ tests/backend/test_metrics.py
git commit -m "feat: add Prometheus metrics definitions"
```

---

## Task 7: 创建健康检查接口

**Files:**
- Create: `backend/api/__init__.py`
- Create: `backend/api/routes/__init__.py`
- Create: `backend/api/routes/health.py`

- [ ] **Step 1: 创建 backend/api/__init__.py**

```python
"""API 路由模块"""
```

- [ ] **Step 2: 创建 backend/api/routes/__init__.py**

```python
"""API 路由"""
```

- [ ] **Step 3: 创建健康检查测试（先写测试）**

```python
# tests/backend/test_health.py
"""健康检查接口测试"""
from fastapi.testclient import TestClient


def test_health_endpoint():
    """测试健康检查接口"""
    from backend.main import app
    
    client = TestClient(app)
    response = client.get("/api/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_root_redirect():
    """测试根路径重定向到文档"""
    from backend.main import app
    
    client = TestClient(app)
    response = client.get("/")
    
    # 应该重定向到 /docs
    assert response.status_code == 200
```

- [ ] **Step 4: 运行测试验证失败**

```bash
pytest tests/backend/test_health.py -v
```

预期输出: `FAILED with ImportError`

- [ ] **Step 5: 创建 backend/api/routes/health.py**

```python
"""
健康检查接口

提供系统健康状态检查端点
"""
from fastapi import APIRouter
from pydantic import BaseModel
from backend import __version__

router = APIRouter()


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "healthy"
    version: str = __version__
    hermes_connected: bool = False


@router.get("/health", response_model=HealthResponse, tags=["健康检查"])
async def health_check():
    """
    健康检查接口
    
    返回系统状态、版本信息和 Hermes 连接状态
    """
    from backend.core.hermes import _agent
    
    return HealthResponse(
        status="healthy",
        version=__version__,
        hermes_connected=_agent is not None
    )


@router.get("/", tags=["根路径"])
async def root():
    """根路径 - 重定向到 API 文档"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")
```

- [ ] **Step 6: 创建 FastAPI 主应用（支持健康检查测试）**

```python
# backend/main.py（最小版本，只支持健康检查）
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import health
from backend.core.config import settings

app = FastAPI(
    title="废水监测系统 API",
    version="2.0.0",
    description="基于 Hermes 智能体的废水虚假排放监测系统",
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

# 路由注册
app.include_router(health.router, prefix="/api")
```

- [ ] **Step 7: 运行测试验证通过**

```bash
pytest tests/backend/test_health.py -v
```

预期输出: `PASSED test_health.py`

- [ ] **Step 8: 手动测试健康检查**

```bash
cd e:/project/Ecological_env
python -m uvicorn backend.main:app --reload
# 访问 http://localhost:8000/api/health
# 预期输出: {"status":"healthy","version":"2.0.0","hermes_connected":false}
```

- [ ] **Step 9: 提交**

```bash
git add backend/main.py backend/api/ tests/backend/test_health.py
git commit -m "feat: add health check endpoint and main application entry"
```

---

## Task 8: 创建查询接口（Hermes 集成）

**Files:**
- Create: `backend/api/routes/query.py`
- Modify: `backend/main.py`（添加查询路由）
- Create: `backend/api/dependencies.py`

- [ ] **Step 1: 创建依赖注入模块**

```python
# backend/api/dependencies.py
"""
API 依赖注入

提供路由依赖注入函数
"""
from backend.core.hermes import get_hermes_agent
from backend.db.session import get_db

__all__ = ["get_hermes_agent", "get_db"]
```

- [ ] **Step 2: 创建查询接口测试（先写测试）**

```python
# tests/backend/test_query.py
"""查询接口测试"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch


class TestQueryEndpoint:
    """查询接口测试类"""
    
    @pytest.fixture
    def mock_agent_response(self):
        """模拟 Hermes 智能体响应"""
        mock_response = Mock()
        mock_response.content = "这是测试响应"
        mock_response.session_id = "test-session-123"
        mock_response.timestamp = "2024-06-23T10:00:00Z"
        return mock_response
    
    def test_query_endpoint_success(self, mock_agent_response):
        """测试查询接口成功响应"""
        from backend.main import app
        
        # Mock Hermes 智能体
        with patch('backend.api.routes.query.get_hermes_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_agent.run_conversation.return_value = mock_agent_response
            mock_get_agent.return_value = mock_agent
            
            client = TestClient(app)
            response = client.post(
                "/api/query",
                json={"query": "测试查询"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "这是测试响应"
        assert data["session_id"] == "test-session-123"
    
    def test_query_endpoint_with_session(self, mock_agent_response):
        """测试带会话ID的查询"""
        from backend.main import app
        
        with patch('backend.api.routes.query.get_hermes_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_agent.run_conversation.return_value = mock_agent_response
            mock_get_agent.return_value = mock_agent
            
            client = TestClient(app)
            response = client.post(
                "/api/query",
                json={
                    "query": "继续分析",
                    "session_id": "existing-session"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "这是测试响应"
    
    def test_query_endpoint_validation_error(self):
        """测试查询参数验证错误"""
        from backend.main import app
        
        client = TestClient(app)
        response = client.post(
            "/api/query",
            json={"query": ""}  # 空查询应该失败
        )
        
        assert response.status_code == 422  # Validation Error
    
    def test_query_endpoint_hermes_error(self):
        """测试 Hermes 智能体错误"""
        from backend.main import app
        
        with patch('backend.api.routes.query.get_hermes_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_agent.run_conversation.side_effect = Exception("LLM 服务不可用")
            mock_get_agent.return_value = mock_agent
            
            client = TestClient(app)
            response = client.post(
                "/api/query",
                json={"query": "测试查询"}
            )
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
```

- [ ] **Step 3: 运行测试验证失败**

```bash
pytest tests/backend/test_query.py -v
```

预期输出: `FAILED with ImportError`

- [ ] **Step 4: 创建查询接口实现**

```python
# backend/api/routes/query.py
"""
查询接口 - Hermes 智能体集成

提供自然语言查询接口，通过 Hermes 智能体进行 LLM 驱动的任务分析
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from backend.models.query import QueryRequest, QueryResponse, ErrorResponse
from backend.api.dependencies import get_hermes_agent
from backend.metrics.definitions import (
    api_requests_total,
    api_request_duration_seconds,
    llm_calls_total,
    llm_call_duration_seconds,
    llm_tokens_total,
    active_sessions
)
import time

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/query", response_model=QueryResponse, tags=["查询"])
async def execute_query(
    request: QueryRequest,
    agent = Depends(get_hermes_agent)
):
    """
    执行自然语言查询
    
    通过 Hermes 智能体进行 LLM 驱动的任务分析：
    - 意图识别：理解用户查询的真实意图
    - 任务分解：将复杂查询分解为可执行的子任务
    - 子智能体调度：通过 delegate_task 工具调用相应的子智能体
    - 结果聚合：汇总子智能体的分析结果
    
    Args:
        request: 查询请求，包含查询内容和可选的会话ID
        agent: Hermes 智能体实例（依赖注入）
    
    Returns:
        QueryResponse: 查询响应，包含 LLM 生成的结果和会话信息
    
    Raises:
        HTTPException: 当 LLM 调用失败时返回 500 错误
    """
    start_time = time.time()
    
    # 更新活跃会话数
    active_sessions.inc()
    
    try:
        # 构建消息列表
        messages = [{"role": "user", "content": request.query}]
        
        # 如果有会话ID，可以添加历史消息（暂时只支持当前消息）
        
        # 调用 Hermes 智能体
        llm_start = time.time()
        response = await agent.run_conversation(messages)
        llm_duration = time.time() - llm_start
        
        # 记录 LLM 调用指标
        llm_calls_total.labels(
            model=response.get('model', 'unknown'),
            status='success'
        ).inc()
        llm_call_duration_seconds.observe(llm_duration)
        
        # 记录 Token 使用（如果响应中包含）
        if 'usage' in response:
            llm_tokens_total.labels(
                model=response.get('model', 'unknown'),
                token_type='prompt'
            ).inc(response['usage'].get('prompt_tokens', 0))
            llm_tokens_total.labels(
                model=response.get('model', 'unknown'),
                token_type='completion'
            ).inc(response['usage'].get('completion_tokens', 0))
        
        # 构建响应
        result = QueryResponse(
            result=response.content,
            session_id=response.session_id,
            timestamp=response.timestamp,
            model_used=response.get('model'),
            tokens_used=response.get('usage', {}).get('total_tokens')
        )
        
        # 记录 API 请求指标
        duration = time.time() - start_time
        api_requests_total.labels('POST', '/api/query', '200').inc()
        api_request_duration_seconds.labels('POST', '/api/query').observe(duration)
        
        logger.info(
            f"Query completed: session_id={response.session_id}, "
            f"duration={duration:.2f}s, tokens={result.tokens_used}"
        )
        
        return result
        
    except Exception as e:
        # 记录错误指标
        api_requests_total.labels('POST', '/api/query', '500').inc()
        llm_calls_total.labels(
            model='unknown',
            status='error'
        ).inc()
        
        logger.error(f"Query failed: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "查询执行失败",
                "detail": str(e)
            }
        )
    
    finally:
        # 减少活跃会话数
        active_sessions.dec()


@router.get("/query/sessions", tags=["查询"])
async def list_sessions(agent = Depends(get_hermes_agent)):
    """
    列出活跃的会话
    
    注意：当前返回空列表，会话管理功能需要 Hermes 框架支持
    
    Returns:
        活跃会话列表
    """
    # 会话列表需要 Hermes 框架支持
    # 当前返回空列表作为占位符
    return {"sessions": [], "message": "会话管理功能将在后续实现"}
```

- [ ] **Step 5: 修改 backend/main.py 添加查询路由**

```python
# 在 backend/main.py 中添加导入
from backend.api.routes import query

# 在路由注册部分添加
app.include_router(query.router, prefix="/api")
```

修改后的完整 main.py：

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import health, query
from backend.core.config import settings

app = FastAPI(
    title="废水监测系统 API",
    version="2.0.0",
    description="基于 Hermes 智能体的废水虚假排放监测系统",
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

# 路由注册
app.include_router(health.router, prefix="/api")
app.include_router(query.router, prefix="/api")
```

- [ ] **Step 6: 运行测试验证通过**

```bash
pytest tests/backend/test_query.py -v
```

预期输出: `PASSED test_query.py`

- [ ] **Step 7: 提交**

```bash
git add backend/api/routes/query.py backend/api/dependencies.py backend/main.py tests/backend/test_query.py
git commit -m "feat: add query endpoint with Hermes agent integration"
```

---

## Task 9: 集成 Prometheus 监控

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: 修改 main.py 添加 Prometheus 支持**

```python
# 在 backend/main.py 顶部添加导入
from prometheus_fastapi_instrumentator import Instrumentator

# 在 app 创建后添加 Prometheus 集成
Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```

修改后的完整 main.py：

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from backend.api.routes import health, query
from backend.core.config import settings

app = FastAPI(
    title="废水监测系统 API",
    version="2.0.0",
    description="基于 Hermes 智能体的废水虚假排放监测系统",
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

# Prometheus 监控
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# 路由注册
app.include_router(health.router, prefix="/api")
app.include_router(query.router, prefix="/api")
```

- [ ] **Step 2: 创建 Prometheus 集成测试**

```python
# tests/backend/test_prometheus.py
"""Prometheus 监控测试"""
import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY


def test_metrics_endpoint():
    """测试 /metrics 端点"""
    from backend.main import app
    
    client = TestClient(app)
    response = client.get("/metrics")
    
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")


def test_fastapi_metrics_present():
    """测试 FastAPI 默认指标存在"""
    from backend.main import app
    from prometheus_fastapi_instrumentator import Instrumentator
    
    # 确保指标已注册
    Instrumentator().instrument(app).expose(app)
    
    # 检查指标
    metrics = REGISTRY.get_sample_value('http_server_requests_total')
    assert metrics is not None


def test_custom_metrics_present():
    """测试自定义指标存在"""
    from backend.metrics.definitions import (
        api_requests_total,
        llm_calls_total,
        llm_tokens_total,
        active_sessions
    )
    
    # 这些指标应该能正常创建
    assert api_requests_total is not None
    assert llm_calls_total is not None
    assert llm_tokens_total is not None
    assert active_sessions is not None
```

- [ ] **Step 3: 运行测试验证 Prometheus 集成**

```bash
pytest tests/backend/test_prometheus.py -v
```

预期输出: `PASSED test_prometheus.py`

- [ ] **Step 4: 手动验证 metrics 端点**

```bash
# 启动服务
python -m uvicorn backend.main:app --reload

# 访问 metrics 端点
curl http://localhost:8000/metrics

# 预期看到类似输出：
# http_server_requests_total{method="GET",path="/metrics",status="200"} 1.0
# api_requests_total{method="GET",endpoint="/health",status="200"} 1.0
```

- [ ] **Step 5: 提交**

```bash
git add backend/main.py tests/backend/test_prometheus.py
git commit -m "feat: integrate Prometheus monitoring with FastAPI"
```

---

## Task 10: 更新 .env 配置

**Files:**
- Modify: `.env`

- [ ] **Step 1: 在 .env 中添加 FastAPI 配置**

```bash
# 在 .env 文件末尾添加

# ==================== FastAPI 配置 ====================
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
FASTAPI_DEBUG=false
```

- [ ] **Step 2: 验证配置加载**

```python
# 快速验证脚本
from backend.core.config import settings
print(f"FastAPI Host: {settings.FASTAPI_HOST}")
print(f"FastAPI Port: {settings.FASTAPI_PORT}")
print(f"LLM Model: {settings.LLM_MODEL}")
```

运行: `python -c "from backend.core.config import settings; print(settings.dict())"`

预期输出包含 FastAPI 配置

- [ ] **Step 3: 提交**

```bash
git add .env
git commit -m "config: add FastAPI configuration to .env"
```

---

## Task 11: 创建应用启动脚本

**Files:**
- Create: `scripts/start_backend.sh`
- Create: `scripts/start_backend.bat`

- [ ] **Step 1: 创建 Unix 启动脚本**

```bash
# scripts/start_backend.sh
#!/bin/bash
# 启动 FastAPI 后端服务

cd "$(dirname "$0")/.."

echo "Starting FastAPI Backend..."
echo "Project Root: $(pwd)"

# 检查虚拟环境
if [ -d "ecological_env" ]; then
    source ecological_env/Scripts/activate
    echo "Activated virtual environment"
fi

# 设置环境变量
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 启动服务
python -m uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info
```

- [ ] **Step 2: 创建 Windows 启动脚本**

```batch
# scripts/start_backend.bat
@echo off
REM 启动 FastAPI 后端服务

cd /d "%~dp0.."

echo Starting FastAPI Backend...
echo Project Root: %CD%

REM 检查虚拟环境
if exist "ecological_env\Scripts\activate.bat" (
    call ecological_env\Scripts\activate.bat
    echo Activated virtual environment
)

REM 设置环境变量
set PYTHONPATH=%PYTHONPATH%;%CD%

REM 启动服务
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload --log-level info
```

- [ ] **Step 3: 添加执行权限并测试**

```bash
chmod +x scripts/start_backend.sh
./scripts/start_backend.sh
```

预期输出: Uvicorn 服务器启动成功

- [ ] **Step 4: 提交**

```bash
git add scripts/
git commit -m "feat: add backend startup scripts"
```

---

## Task 12: 创建集成测试

**Files:**
- Create: `tests/backend/integration/test_full_api.py`

- [ ] **Step 1: 创建端到端集成测试**

```python
# tests/backend/integration/test_full_api.py
"""
完整的 API 集成测试

测试整个 FastAPI 应用的端到端功能
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch


@pytest.mark.integration
class TestFullAPIIntegration:
    """完整 API 集成测试"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from backend.main import app
        return TestClient(app)
    
    def test_root_to_docs(self, client):
        """测试根路径重定向到文档"""
        response = client.get("/")
        assert response.status_code == 200
        assert "docs" in response.url or "redoc" in response.url
    
    def test_health_check(self, client):
        """测试健康检查"""
        response = client.get("/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert data["status"] == "healthy"
    
    def test_query_with_mocked_hermes(self, client):
        """测试查询接口（Mocked Hermes）"""
        # Mock Hermes 响应
        mock_response = Mock()
        mock_response.content = "这是 LLM 生成的测试响应"
        mock_response.session_id = "test-session-456"
        mock_response.timestamp = "2024-06-23T10:30:00Z"
        mock_response.get = Mock(return_value="ctgu-vlm")
        mock_response.__getitem__ = Mock(side_effect=lambda k: {
            'model': 'ctgu-vlm',
            'usage': {'prompt_tokens': 10, 'completion_tokens': 20, 'total_tokens': 30}
        }.get(k))
        
        with patch('backend.api.routes.query.get_hermes_agent') as mock_get_agent:
            mock_agent = AsyncMock()
            mock_agent.run_conversation.return_value = mock_response
            mock_get_agent.return_value = mock_agent
            
            response = client.post(
                "/api/query",
                json={"query": "最近24小时的出水数据怎么样？"}
            )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["result"] == "这是 LLM 生成的测试响应"
        assert data["session_id"] == "test-session-456"
        assert "timestamp" in data
    
    def test_query_validation_error(self, client):
        """测试查询验证错误"""
        response = client.post(
            "/api/query",
            json={"query": ""}  # 空查询
        )
        
        assert response.status_code == 422
    
    def test_metrics_endpoint(self, client):
        """测试监控指标端点"""
        response = client.get("/metrics")
        
        assert response.status_code == 200
        assert "http_server_requests_total" in response.text
    
    def test_api_docs_available(self, client):
        """测试 API 文档可用"""
        response = client.get("/docs")
        assert response.status_code == 200
        
        response = client.get("/redoc")
        assert response.status_code == 200
    
    def test_cors_headers(self, client):
        """测试 CORS 头"""
        response = client.options("/api/query")
        
        # 检查 CORS 头存在
        assert "access-control-allow-methods" in response.headers
```

- [ ] **Step 2: 运行集成测试**

```bash
pytest tests/backend/integration/ -v
```

预期输出: `PASSED test_full_api.py`

- [ ] **Step 3: 提交**

```bash
git add tests/backend/integration/
git commit -m "test: add full API integration tests"
```

---

## Task 13: 创建 README 文档

**Files:**
- Create: `backend/README.md`

- [ ] **Step 1: 创建后端 README**

```markdown
# 废水监测系统后端 API

基于 FastAPI + Hermes 智能体的废水监测系统后端服务。

## 技术栈

- **FastAPI 0.109+** - 现代高性能 Web 框架
- **Hermes Agent** - LLM 驱动的智能体框架
- **SQLAlchemy 2.0** - ORM
- **Pydantic v2** - 数据验证
- **Prometheus** - 监控指标

## 快速开始

### 安装依赖

```bash
pip install -e .
```

### 配置环境变量

编辑项目根目录 `.env` 文件：

```bash
LLM_BASE_URL=http://your-llm-server:30000/v1
LLM_API_KEY=your-api-key
LLM_MODEL=your-model
```

### 启动服务

```bash
# 方式1：使用启动脚本
./scripts/start_backend.sh  # Unix
scripts\start_backend.bat   # Windows

# 方式2：直接运行
python -m uvicorn backend.main:app --reload
```

服务将在 `http://localhost:8000` 启动。

## API 文档

启动服务后访问：

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 核心接口

### 1. 健康检查

```bash
GET /api/health
```

返回系统状态和版本信息。

### 2. 查询接口

```bash
POST /api/query
Content-Type: application/json

{
  "query": "最近24小时的出水数据怎么样？",
  "session_id": "optional-session-id"
}
```

通过 Hermes 智能体进行 LLM 驱动的任务分析。

### 3. 监控指标

```bash
GET /metrics
```

Prometheus 格式的监控指标。

## 测试

```bash
# 运行所有测试
pytest tests/backend/

# 运行特定测试
pytest tests/backend/test_query.py -v

# 运行集成测试
pytest tests/backend/integration/ -v
```

## 项目结构

```
backend/
├── main.py                 # FastAPI 应用入口
├── api/                    # API 路由
│   ├── routes/
│   │   ├── health.py       # 健康检查
│   │   └── query.py        # 查询接口
│   └── dependencies.py     # 依赖注入
├── core/                   # 核心配置
│   ├── config.py           # 配置加载
│   └── hermes.py           # Hermes 集成
├── models/                 # Pydantic 模型
│   └── query.py
├── db/                     # 数据库
│   ├── base.py
│   └── session.py
└── metrics/                # Prometheus 指标
    └── definitions.py
```

## 开发

### 代码规范

```bash
# 代码格式化
ruff format backend/

# 代码检查
ruff check backend/
```

### 类型检查

```bash
mypy backend/
```

## 许可证

Copyright © 2024 废水监测系统
```

- [ ] **Step 2: 提交**

```bash
git add backend/README.md
git commit -m "docs: add backend API README"
```

---

## Task 14: 创建 Docker 配置

**Files:**
- Create: `backend/Dockerfile`
- Modify: `docker-compose.yml`（更新后端服务配置）

- [ ] **Step 1: 创建 Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY pyproject.toml requirements.txt ./

# 安装 Python 依赖
RUN pip install --no-cache-dir -e .

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/health')"

# 启动命令
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: 创建 .dockerignore**

```
# backend/.dockerignore
__pycache__
*.pyc
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info
dist
build
.env
.venv
venv/
.pytest_cache
.coverage
htmlcov/
.tox
.mypy_cache
.pytest_cache
*.log
tests/
docs/
.git
.gitignore
README.md
```

- [ ] **Step 3: 更新 docker-compose.yml**

在项目根目录创建/更新 docker-compose.yml：

```yaml
version: '3.8'

services:
  # PostgreSQL - 业务数据
  postgres:
    image: postgres:16
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_DB=ecological_env
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  # FastAPI 后端
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/ecological_env
      - LLM_BASE_URL=http://172.16.12.41:30000/v1
      - LLM_API_KEY=sk-4e9a2c7d5f1b8e3c6d0a9b2f4d7e1c3a6b5f8e2d9c7a1b0f
      - LLM_MODEL=ctgu-vlm
      - ENABLE_PROMETHEUS=true
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./workspace:/app/workspace
      - ./subagents:/app/subagents
      - ./shared:/app/shared
      - ./.hermes:/app/.hermes
    restart: unless-stopped

  # Prometheus - 系统监控
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    restart: unless-stopped

  # Grafana - 可视化
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_INSTALL_PLUGINS=
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    restart: unless-stopped

volumes:
  postgres-data:
  prometheus-data:
  grafana-data:
```

- [ ] **Step 4: 测试 Docker 构建**

```bash
cd e:/project/Ecological_env
docker build -f backend/Dockerfile -t ecological-backend .
```

预期输出: `Successfully built ecological-backend`

- [ ] **Step 5: 提交**

```bash
git add backend/Dockerfile backend/.dockerignore docker-compose.yml
git commit -m "feat: add Docker configuration for backend service"
```

---

## Task 15: 最终验证和集成测试

**Files:**
- Create: `tests/backend/integration/test_hermes_real.py`

- [ ] **Step 1: 创建真实 Hermes 集成测试**

```python
# tests/backend/integration/test_hermes_real.py
"""
真实 Hermes 智能体集成测试

注意：这些测试需要真实的 Hermes 框架和 LLM 服务
"""
import pytest
import sys
from pathlib import Path

# 添加 Hermes 框架到路径
hermes_path = Path("D:/Hermes/hermes-agent")
if hermes_path.exists():
    sys.path.insert(0, str(hermes_path))


@pytest.mark.integration
@pytest.mark.skipif(
    not Path("D:/Hermes/hermes-agent").exists(),
    reason="Hermes framework not found"
)
class TestHermesRealIntegration:
    """真实 Hermes 集成测试"""
    
    def test_hermes_agent_initialization(self):
        """测试 Hermes 智能体初始化"""
        from backend.core.hermes import init_hermes_agent, HermesAgentConfig
        from backend.core.config import settings
        
        # 创建配置
        config = HermesAgentConfig(
            base_url=settings.LLM_BASE_URL,
            model=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY
        )
        
        # 初始化智能体
        agent = init_hermes_agent(config)
        
        assert agent is not None
        print(f"Hermes agent initialized: {agent}")
    
    @pytest.mark.asyncio
    async def test_hermes_simple_conversation(self):
        """测试简单的对话功能"""
        from backend.core.hermes import init_hermes_agent, HermesAgentConfig
        from backend.core.config import settings
        
        config = HermesAgentConfig(
            base_url=settings.LLM_BASE_URL,
            model=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY
        )
        
        agent = init_hermes_agent(config)
        
        # 简单对话
        messages = [{"role": "user", "content": "你好"}]
        response = await agent.run_conversation(messages)
        
        assert response is not None
        assert response.content is not None
        print(f"Response: {response.content}")
    
    @pytest.mark.asyncio
    async def test_hermes_query_with_subagent(self):
        """测试需要调用子智能体的查询"""
        from backend.core.hermes import init_hermes_agent, HermesAgentConfig
        from backend.core.config import settings
        
        config = HermesAgentConfig(
            base_url=settings.LLM_BASE_URL,
            model=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY,
            load_soul_identity=True,
            enabled_toolsets=["delegation"]
        )
        
        agent = init_hermes_agent(config)
        
        # 需要调用子智能体的查询
        messages = [{"role": "user", "content": "查询最近进水pH数据"}]
        response = await agent.run_conversation(messages)
        
        assert response is not None
        print(f"Response: {response.content}")
```

- [ ] **Step 2: 运行真实集成测试（可选）**

```bash
# 需要真实的 Hermes 框架和 LLM 服务
pytest tests/backend/integration/test_hermes_real.py -v -s
```

- [ ] **Step 3: 创建最终验证脚本**

```python
# scripts/verify_backend.py
"""后端验证脚本"""
import sys
import subprocess
from pathlib import Path


def run_command(cmd, description):
    """运行命令并报告结果"""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✓ {description} - PASSED")
        if result.stdout:
            print(result.stdout[:500])  # 限制输出长度
    else:
        print(f"✗ {description} - FAILED")
        if result.stderr:
            print(result.stderr[:500])
    
    return result.returncode == 0


def main():
    """运行所有验证"""
    print("Backend Verification Script")
    print("="*60)
    
    tests = [
        ("cd e:/project/Ecological_env && python -m pytest tests/backend/ -v --tb=short",
         "Run all backend tests"),
        
        ("cd e:/project/Ecological_env && python -c 'from backend.main import app; print(\"FastAPI app loaded successfully\")'",
         "Load FastAPI application"),
        
        ("cd e:/project/Ecological_env && python -c 'from backend.core.hermes import init_hermes_agent; print(\"Hermes integration loaded\")'",
         "Load Hermes integration"),
        
        ("cd e:/project/Ecological_env && python -c 'from backend.core.config import settings; print(f\"Config: LLM={settings.LLM_MODEL}\")'",
         "Load configuration"),
    ]
    
    results = []
    for cmd, desc in tests:
        results.append(run_command(cmd, desc))
    
    print(f"\n{'='*60}")
    print("Summary:")
    print(f"{'='*60}")
    
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ All verifications passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} verification(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 运行验证脚本**

```bash
python scripts/verify_backend.py
```

预期输出: `✓ All verifications passed!`

- [ ] **Step 5: 提交**

```bash
git add tests/backend/integration/test_hermes_real.py scripts/verify_backend.py
git commit -m "test: add Hermes real integration tests and verification script"
```

---

## 完成检查清单

在完成所有任务后，验证以下功能：

- [ ] FastAPI 应用可以正常启动（`python -m uvicorn backend.main:app --reload`）
- [ ] 访问 `http://localhost:8000/docs` 可以看到 API 文档
- [ ] 健康检查接口返回正常（`GET /api/health`）
- [ ] 查询接口可以调用（需要真实的 LLM 服务）
- [ ] Prometheus 指标端点正常（`GET /metrics`）
- [ ] 所有测试通过（`pytest tests/backend/ -v`）
- [ ] Docker 镜像可以构建（`docker build -f backend/Dockerfile .`）
- [ ] Docker Compose 可以启动后端服务

## 下一步

完成本计划后，你可以继续：

1. **添加告警接口** - 实现 `/api/alerts` 接口
2. **添加工单接口** - 实现 `/api/workorders` 接口
3. **数据库集成** - 实现查询历史存储
4. **实时数据推送** - 添加 WebSocket 支持
5. **前端集成** - 开发 React 前端对接这些接口

---

**计划结束**
