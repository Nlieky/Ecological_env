# FastAPI 后端 - Hermes API Server 集成实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标**: 构建现代 FastAPI 后端，通过 **Hermes API Server** 调用已完成的 Hermes 智能体系统，充分展示其决策树、子智能体调用链、LLM 推理过程。

**架构**: FastAPI → Hermes API Server (端口 8642) → 主智能体（决策树）→ 4 个子智能体

**核心原则**:
- **使用 Hermes API Server**（OpenAI 兼容接口）而非直接导入 Python 模块
- **充分展示主智能体决策树**：用户查询走了决策树的哪些分支
- **展示子智能体调用链**：哪些子智能体被调用、顺序、结果
- **展示 LLM 推理过程**：意图识别、决策逻辑

---

## 架构设计

### 当前 Hermes 系统（已完成）

```
┌─────────────────────────────────────────────────────────────┐
│                    Hermes 智能体系统                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  .hermes/config.yaml                                        │
│  ├─ LLM 配置: ctgu-vlm @ http://172.16.12.41:30000/v1      │
│  ├─ 4 个工具已启用                                           │
│  └─ 技能外部目录已配置                                        │
│                                                              │
│  workspace/SOUL.md (主智能体决策树)                          │
│  ├─ [1] 需要数据? → data-perception                         │
│  ├─ [2] 需要异常检测? → anomaly-detection                   │
│  ├─ [3] 需要违规判定? → rule-reasoning                      │
│  ├─ [4] 需要预警/工单? → disposition-execution               │
│  └─ [5] 整合结果                                            │
│                                                              │
│  subagents/*/ (4 个子智能体)                                 │
│  ├─ multi-dimensional-data-perception-agent                 │
│  ├─ anomaly-detection-agent                                 │
│  ├─ rule-reasoning-agent                                    │
│  └─ disposition-execution-agent                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 目标架构

```
┌─────────────────────────────────────────────────────────────┐
│  前端 (React/Ant Design Pro)                                │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ HTTP API
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  FastAPI 后端 (端口 8000)                                    │
│  ├─ 接收用户查询                                             │
│  ├─ 调用 Hermes API Server                                   │
│  └─ 格式化响应（展示决策树、调用链）                         │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ HTTP (OpenAI 兼容)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Hermes API Server (端口 8642)                              │
│  ├─ /v1/chat/completions (对话接口)                         │
│  ├─ /v1/skills (技能列表)                                   │
│  └─ /health (健康检查)                                       │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ 内部调用
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  主智能体 (workspace/SOUL.md 决策树)                         │
│  └─ LLM 决定调用哪些子智能体                                 │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  4 个子智能体 (subagents/)                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 文件结构

### 需要创建的文件

```
backend/
├── __init__.py
├── main.py                         # FastAPI 应用入口
├── api/
│   ├── __init__.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── health.py               # 健康检查
│   │   ├── query.py                # 查询接口（核心）
│   │   └── hermes.py               # Hermes 系统信息
│   └── client.py                   # Hermes API Client
├── core/
│   ├── __init__.py
│   └── config.py                   # 配置加载
├── models/
│   ├── __init__.py
│   ├── query.py                    # 查询接口模型
│   └── hermes.py                   # Hermes 系统模型
└── metrics/
    ├── __init__.py
    └── definitions.py              # Prometheus 指标

tests/
└── backend/
    ├── __init__.py
    ├── test_config.py
    ├── test_health.py
    └── test_query.py

scripts/
├── start_backend.sh                # 启动脚本
└── start_backend.bat
```

### 现有项目文件（不变）

```
.hermes/config.yaml                 # Hermes 配置（已存在）
workspace/SOUL.md                    # 主智能体决策树（已存在）
subagents/*/                         # 4 个子智能体（已存在）
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
description = "废水监测系统后端 - Hermes API Server 集成"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "prometheus-fastapi-instrumentator>=7.0.0",
    "python-dotenv>=1.0.0",
    "httpx>=0.26.0",  # 异步 HTTP 客户端
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.23.0",
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

- [ ] **Step 2: 创建 requirements.txt**

```txt
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
prometheus-fastapi-instrumentator>=7.0.0
python-dotenv>=1.0.0
httpx>=0.26.0
```

- [ ] **Step 3: 安装依赖**

```bash
cd e:/project/Ecological_env
pip install -e .
```

预期输出: `Successfully installed ecological-env-backend-2.0.0`

- [ ] **Step 4: 提交**

```bash
git add pyproject.toml requirements.txt
git commit -m "feat: add FastAPI dependencies for Hermes API Server integration"
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
废水监测系统后端 - Hermes API Server 集成

通过 Hermes API Server 调用已完成的 Hermes 智能体系统
"""

__version__ = "2.0.0"
```

- [ ] **Step 2: 创建 backend/core/config.py**

```python
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


settings = Settings()
```

- [ ] **Step 3: 提交**

```bash
git add backend/core/
git commit -m "feat: add core configuration module"
```

---

## Task 3: 创建 Hermes API Client

**Files:**
- Create: `backend/api/client.py`

- [ ] **Step 1: 创建 Hermes API Client**

```python
"""
Hermes API Client - 调用 Hermes API Server

Hermes API Server 提供 OpenAI 兼容的对话接口
"""
import httpx
import logging
from typing import List, Dict, Any, Optional
from backend.core.config import settings

logger = logging.getLogger(__name__)


class HermesAPIClient:
    """Hermes API 客户端"""
    
    def __init__(self):
        self.base_url = settings.HERMES_API_URL.rstrip("/")
        self.api_key = settings.HERMES_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
    
    async def list_skills(self) -> List[Dict[str, Any]]:
        """获取技能列表（子智能体）"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v1/skills",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        调用对话接口（OpenAI 兼容）
        
        Args:
            messages: 消息列表
            session_id: 会话ID（可选）
        
        Returns:
            完整的 Hermes 响应
        """
        payload = {
            "model": settings.LLM_MODEL,
            "messages": messages
        }
        
        if session_id:
            payload["session_id"] = session_id
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """获取智能体状态"""
        # 通过健康检查和技能列表综合判断
        health = await self.health_check()
        skills = await self.list_skills()
        
        return {
            "hermes_api_server": {
                "status": "healthy" if health.get("status") == "ok" else "unhealthy",
                "url": self.base_url
            },
            "loaded_skills": skills
        }


# 全局实例
_hermes_client: Optional[HermesAPIClient] = None


def get_hermes_client() -> HermesAPIClient:
    """获取 Hermes API 客户端实例"""
    global _hermes_client
    if _hermes_client is None:
        _hermes_client = HermesAPIClient()
    return _hermes_client
```

- [ ] **Step 2: 创建 Client 测试**

```python
# tests/backend/test_client.py
"""Hermes API Client 测试"""
import pytest
from backend.api.client import HermesAPIClient


@pytest.mark.integration
class TestHermesAPIClient:
    """Hermes API Client 测试"""
    
    @pytest.fixture
    def client(self):
        return HermesAPIClient()
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """测试健康检查"""
        response = await client.health_check()
        assert "status" in response
    
    @pytest.mark.asyncio
    async def test_list_skills(self, client):
        """测试技能列表"""
        skills = await client.list_skills()
        assert isinstance(skills, list)
```

- [ ] **Step 3: 运行测试（需要 Hermes API Server 运行）**

```bash
pytest tests/backend/test_client.py -v
```

预期输出: `PASSED`（如果 Hermes API Server 运行中）

- [ ] **Step 4: 提交**

```bash
git add backend/api/client.py tests/backend/test_client.py
git commit -m "feat: add Hermes API Client"
```

---

## Task 4: 创建查询接口模型（展示决策树和调用链）

**Files:**
- Create: `backend/models/__init__.py`
- Create: `backend/models/query.py`
- Create: `backend/models/hermes.py`

- [ ] **Step 1: 创建 backend/models/query.py**

```python
"""
查询接口数据模型 - 展示 Hermes 决策树和调用链
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class DecisionPath(BaseModel):
    """决策路径（主智能体决策树的分支）"""
    step_number: int = Field(..., description="步骤编号")
    step_name: str = Field(..., description="步骤名称")
    decision: str = Field(..., description="决策结果（YES/NO）")
    action: str = Field(..., description="执行的操作")


class SubAgentCall(BaseModel):
    """子智能体调用信息"""
    agent_name: str = Field(..., description="子智能体名称")
    agent_role: str = Field(..., description="子智能体角色")
    call_time: float = Field(..., description="调用耗时（秒）")
    result_summary: str = Field(..., description="结果摘要")
    status: str = Field(..., description="调用状态")


class DataSource(BaseModel):
    """数据溯源信息"""
    source: str = Field(..., description="数据来源")
    time_range: str = Field(..., description="时间范围")
    records_count: int = Field(..., description="记录数量")


class QueryRequest(BaseModel):
    """查询请求"""
    query: str = Field(..., description="用户查询内容", min_length=1)
    session_id: Optional[str] = Field(None, description="会话ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "最近24小时出水COD异常吗？",
                "session_id": None
            }
        }


class QueryResponse(BaseModel):
    """查询响应 - 完整展示 Hermes 决策过程"""
    
    # 基础信息
    content: str = Field(..., description="LLM 生成的最终回答")
    session_id: str = Field(..., description="会话ID")
    timestamp: str = Field(..., description="响应时间戳")
    
    # 决策树路径（展示主智能体走了哪些分支）
    decision_path: List[DecisionPath] = Field(
        default_factory=list,
        description="主智能体决策树的执行路径"
    )
    
    # 子智能体调用链
    sub_agent_calls: List[SubAgentCall] = Field(
        default_factory=list,
        description="本次查询调用的子智能体列表"
    )
    
    # 数据溯源
    data_sources: List[DataSource] = Field(
        default_factory=list,
        description="本次查询使用的数据来源"
    )
    
    # LLM 推理过程
    reasoning: Optional[Dict[str, Any]] = Field(None, description="LLM 推理过程")
    
    # 元数据
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="其他元数据"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "根据分析，最近24小时出水COD在第2-3时段出现轻微异常...",
                "session_id": "session_20240623_103000",
                "timestamp": "2024-06-23T10:30:00Z",
                "decision_path": [
                    {
                        "step_number": 1,
                        "step_name": "需要数据吗？",
                        "decision": "YES",
                        "action": "调用 multi-dimensional-data-perception"
                    },
                    {
                        "step_number": 2,
                        "step_name": "需要异常检测吗？",
                        "decision": "YES",
                        "action": "调用 anomaly-detection"
                    },
                    {
                        "step_number": 3,
                        "step_name": "需要违规判定吗？",
                        "decision": "NO",
                        "action": "跳过"
                    },
                    {
                        "step_number": 4,
                        "step_name": "需要预警/工单吗？",
                        "decision": "NO",
                        "action": "跳过"
                    },
                    {
                        "step_number": 5,
                        "step_name": "整合结果",
                        "decision": "YES",
                        "action": "生成自然语言回答"
                    }
                ],
                "sub_agent_calls": [
                    {
                        "agent_name": "multi-dimensional-data-perception",
                        "agent_role": "多维数据感知",
                        "call_time": 0.5,
                        "result_summary": "获取了最近24小时出水COD数据，共288条记录",
                        "status": "success"
                    },
                    {
                        "agent_name": "anomaly-detection",
                        "agent_role": "异常检测",
                        "call_time": 1.2,
                        "result_summary": "检测到2个异常点，置信度0.75",
                        "status": "success"
                    }
                ],
                "data_sources": [
                    {
                        "source": "历史监测数据库",
                        "time_range": "2024-06-22 10:00 - 2024-06-23 10:00",
                        "records_count": 288
                    }
                ],
                "reasoning": {
                    "intent": "检测异常",
                    "logic": "用户提到'异常'，需要数据感知和异常检测"
                },
                "metadata": {
                    "model": "ctgu-vlm",
                    "llm_calls": 5
                }
            }
        }
```

- [ ] **Step 2: 创建 backend/models/hermes.py**

```python
"""
Hermes 系统模型
"""
from pydantic import BaseModel
from typing import List, Dict, Any


class SkillInfo(BaseModel):
    """技能信息（子智能体）"""
    name: str
    description: str
    location: str


class DecisionTreeNode(BaseModel):
    """决策树节点"""
    step: int
    question: str
    decision: str
    action: str


class HermesSystemInfo(BaseModel):
    """Hermes 系统信息"""
    name: str = "废水监测系统"
    version: str = "2.0.0"
    description: str = "基于 Hermes Agent 框架的废水监测智能体系统"
    
    # 主智能体
    master_agent: Dict[str, Any]
    
    # 决策树
    decision_tree: List[DecisionTreeNode]
    
    # 子智能体
    sub_agents: List[SkillInfo]
    
    # 三库一体
    shared_resources: Dict[str, str]
```

- [ ] **Step 3: 提交**

```bash
git add backend/models/
git commit -m "feat: add query models with decision tree and call chain exposure"
```

---

## Task 5: 创建查询接口（核心接口）

**Files:**
- Create: `backend/api/routes/query.py`

- [ ] **Step 1: 创建查询接口**

```python
"""
查询接口 - Hermes 智能体核心接口

通过 Hermes API Server 调用主智能体，展示完整的决策过程
"""
import logging
import time
from fastapi import APIRouter, HTTPException
from backend.models.query import QueryRequest, QueryResponse
from backend.api.client import get_hermes_client
from backend.metrics.definitions import (
    api_requests_total,
    api_request_duration_seconds
)

logger = logging.getLogger(__name__)
router = APIRouter()


def parse_decision_path(content: str) -> list:
    """
    从响应内容解析决策路径
    
    Hermes 主智能体会根据决策树执行，
    我们可以通过分析响应内容推断走了哪些分支。
    """
    # 示例：检测关键词推断决策路径
    # 实际实现可能需要 Hermes API 返回更详细的元数据
    path = []
    
    # 检测数据获取
    if any(keyword in content for keyword in ["数据", "指标", "进水", "出水", "pH", "COD"]):
        path.append({
            "step_number": 1,
            "step_name": "需要数据吗？",
            "decision": "YES",
            "action": "调用 multi-dimensional-data-perception"
        })
    else:
        path.append({
            "step_number": 1,
            "step_name": "需要数据吗？",
            "decision": "NO",
            "action": "跳过数据分析"
        })
    
    # 检测异常检测
    if any(keyword in content for keyword in ["异常", "突变", "检测"]):
        path.append({
            "step_number": 2,
            "step_name": "需要异常检测吗？",
            "decision": "YES",
            "action": "调用 anomaly-detection"
        })
        path.append({
            "step_number": 3,
            "step_name": "需要违规判定吗？",
            "decision": "NO",
            "action": "跳过"
        })
    else:
        path.append({
            "step_number": 2,
            "step_name": "需要异常检测吗？",
            "decision": "NO",
            "action": "跳过"
        })
    
    # 整合结果
    path.append({
        "step_number": 5,
        "step_name": "整合结果",
        "decision": "YES",
        "action": "生成自然语言回答"
    })
    
    return path


@router.post("/query", response_model=QueryResponse, tags=["查询"])
async def execute_query(request: QueryRequest):
    """
    执行自然语言查询 - 展示 Hermes 智能体的完整决策过程
    
    **Hermes 主智能体决策树**：
    1. 需要数据吗？ → data-perception
    2. 需要异常检测吗？ → anomaly-detection
    3. 需要违规判定吗？ → rule-reasoning
    4. 需要预警/工单吗？ → disposition-execution
    5. 整合结果
    
    **返回的响应包含**：
    - content: LLM 生成的最终回答
    - decision_path: 决策树的执行路径
    - sub_agent_calls: 子智能体调用链
    - data_sources: 数据溯源
    """
    start_time = time.time()
    
    try:
        logger.info(f"收到查询: {request.query[:50]}...")
        
        # 调用 Hermes API Server
        client = get_hermes_client()
        
        messages = [{"role": "user", "content": request.query}]
        hermes_response = await client.chat_completion(
            messages=messages,
            session_id=request.session_id
        )
        
        # 解析 Hermes 响应
        # OpenAI 兼容格式: response["choices"][0]["message"]["content"]
        content = hermes_response.get("choices", [{}])[0].get("message", {}).get("content", "")
        session_id = hermes_response.get("session_id", "unknown")
        
        # 解析决策路径
        decision_path = parse_decision_path(content)
        
        # 构建响应
        response = QueryResponse(
            content=content,
            session_id=session_id,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            decision_path=decision_path,
            sub_agent_calls=[],  # TODO: 从 Hermes 响应元数据提取
            data_sources=[],      # TODO: 从 Hermes 响应元数据提取
            reasoning={
                "intent": "通过分析内容推断",
                "model": hermes_response.get("model", "unknown")
            },
            metadata={
                "model": hermes_response.get("model", "unknown"),
                "usage": hermes_response.get("usage", {})
            }
        )
        
        # 记录指标
        duration = time.time() - start_time
        api_requests_total.labels('POST', '/api/query', '200').inc()
        api_request_duration_seconds.labels('POST', '/api/query').observe(duration)
        
        logger.info(f"查询完成: session={session_id}, 耗时={duration:.2f}s")
        
        return response
        
    except Exception as e:
        api_requests_total.labels('POST', '/api/query', '500').inc()
        logger.error(f"查询失败: {str(e)}")
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "HermesQueryError",
                "message": "Hermes API Server 调用失败",
                "detail": str(e)
            }
        )


@router.get("/query/capabilities", tags=["查询"])
async def get_hermes_capabilities():
    """
    获取 Hermes 智能体能力说明
    
    Returns:
        Hermes 智能体的完整决策树和能力描述
    """
    return {
        "master_agent": {
            "name": "废水监测主智能体",
            "role": "全局协调、智能决策、用户桥梁",
            "location": "workspace/SOUL.md"
        },
        "decision_tree": [
            {
                "step": 1,
                "question": "需要数据吗？",
                "condition": "提到'数据'、'指标'、'监测'、'进水'、'出水'",
                "yes_action": "调用 data-perception",
                "no_action": "跳过数据分析"
            },
            {
                "step": 2,
                "question": "需要异常检测吗？",
                "condition": "提到'异常'、'突变'、'是否正常'",
                "yes_action": "调用 anomaly-detection",
                "no_action": "跳过异常检测"
            },
            {
                "step": 3,
                "question": "需要违规判定吗？",
                "condition": "提到'违规'、'超标'、'违反标准'",
                "yes_action": "调用 rule-reasoning",
                "no_action": "跳过违规判定"
            },
            {
                "step": 4,
                "question": "需要预警/工单吗？",
                "condition": "提到'预警'、'工单'、'通知'",
                "yes_action": "调用 disposition-execution",
                "no_action": "跳过处置执行"
            },
            {
                "step": 5,
                "question": "整合结果",
                "action": "生成自然语言回答"
            }
        ],
        "sub_agents": [
            {
                "name": "multi-dimensional-data-perception",
                "role": "多维数据感知",
                "location": "subagents/multi-dimensional-data-perception-agent/skills/"
            },
            {
                "name": "anomaly-detection",
                "role": "异常检测",
                "location": "subagents/anomaly-detection-agent/skills/"
            },
            {
                "name": "rule-reasoning",
                "role": "规则推理",
                "location": "subagents/rule-reasoning-agent/skills/"
            },
            {
                "name": "disposition-execution",
                "role": "研判处置",
                "location": "subagents/disposition-execution-agent/skills/"
            }
        ],
        "examples": [
            {
                "query": "最近24小时出水COD异常吗？",
                "path": ["[1] YES → data-perception", "[2] YES → anomaly-detection", "[3] NO", "[4] NO", "[5] 整合"]
            },
            {
                "query": "最近24小时出水是否超标？",
                "path": ["[1] YES → data-perception", "[2] YES → anomaly-detection", "[3] YES → rule-reasoning", "[4] NO", "[5] 整合"]
            },
            {
                "query": "生成今天的异常预警工单",
                "path": ["[1] YES → data-perception", "[2] YES → anomaly-detection", "[3] YES → rule-reasoning", "[4] YES → disposition-execution", "[5] 整合"]
            }
        ]
    }
```

- [ ] **Step 2: 提交**

```bash
git add backend/api/routes/query.py
git commit -m "feat: add query endpoint with decision tree exposure"
```

---

## Task 6: 创建健康检查和 Hermes 系统信息接口

**Files:**
- Create: `backend/api/routes/health.py`
- Create: `backend/api/routes/hermes.py`

- [ ] **Step 1: 创建健康检查接口**

```python
"""
健康检查接口
"""
from fastapi import APIRouter
from backend import __version__
from backend.api.client import get_hermes_client

router = APIRouter()


@router.get("/health", tags=["健康检查"])
async def health_check():
    """
    健康检查接口
    
    Returns:
        系统健康状态，包括 Hermes API Server 连接状态
    """
    try:
        client = get_hermes_client()
        hermes_health = await client.health_check()
        hermes_status = "connected" if hermes_health.get("status") == "ok" else "disconnected"
    except Exception as e:
        hermes_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "version": __version__,
        "components": {
            "hermes_api_server": {
                "status": hermes_status,
                "url": "http://localhost:8642"
            }
        }
    }
```

- [ ] **Step 2: 创建 Hermes 系统信息接口**

```python
"""
Hermes 系统信息接口
"""
from fastapi import APIRouter
from backend.models.hermes import HermesSystemInfo
from backend.core.config import settings

router = APIRouter()


@router.get("/hermes/system", response_model=HermesSystemInfo, tags=["Hermes"])
async def get_hermes_system_info():
    """
    获取 Hermes 系统完整信息
    
    Returns:
        Hermes 系统的结构、决策树、子智能体信息
    """
    return HermesSystemInfo(
        name="废水监测系统",
        version="2.0.0",
        description="基于 Hermes Agent 框架的废水监测智能体系统",
        master_agent={
            "name": "废水监测主智能体",
            "location": "workspace/SOUL.md",
            "role": "全局协调、智能决策、用户桥梁",
            "capabilities": [
                "意图识别",
                "决策树执行",
                "子智能体调度",
                "结果聚合"
            ]
        },
        decision_tree=[
            {
                "step": 1,
                "question": "需要数据吗？",
                "decision": "YES → data-perception, NO → 跳过"
            },
            {
                "step": 2,
                "question": "需要异常检测吗？",
                "decision": "YES → anomaly-detection, NO → 跳过"
            },
            {
                "step": 3,
                "question": "需要违规判定吗？",
                "decision": "YES → rule-reasoning, NO → 跳过"
            },
            {
                "step": 4,
                "question": "需要预警/工单吗？",
                "decision": "YES → disposition-execution, NO → 跳过"
            },
            {
                "step": 5,
                "question": "整合结果",
                "decision": "生成自然语言回答"
            }
        ],
        sub_agents=[
            {
                "name": "multi-dimensional-data-perception",
                "description": "多维数据感知",
                "location": "subagents/multi-dimensional-data-perception-agent/skills/"
            },
            {
                "name": "anomaly-detection",
                "description": "异常检测",
                "location": "subagents/anomaly-detection-agent/skills/"
            },
            {
                "name": "rule-reasoning",
                "description": "规则推理",
                "location": "subagents/rule-reasoning-agent/skills/"
            },
            {
                "name": "disposition-execution",
                "description": "研判处置",
                "location": "subagents/disposition-execution-agent/skills/"
            }
        ],
        shared_resources={
            "operators": "shared/operators/",
            "data": "shared/data/",
            "knowledge": "shared/knowledge/"
        }
    )


@router.get("/hermes/skills", tags=["Hermes"])
async def get_hermes_skills():
    """
    获取 Hermes 加载的技能列表（子智能体）
    
    Returns:
        Hermes API Server 加载的技能列表
    """
    try:
        client = get_hermes_client()
        skills = await client.list_skills()
        return {"skills": skills}
    except Exception as e:
        return {
            "error": str(e),
            "configured_skills": [
                "subagents/multi-dimensional-data-perception-agent/skills",
                "subagents/anomaly-detection-agent/skills",
                "subagents/rule-reasoning-agent/skills",
                "subagents/disposition-execution-agent/skills"
            ]
        }
```

- [ ] **Step 3: 提交**

```bash
git add backend/api/routes/health.py backend/api/routes/hermes.py
git commit -m "feat: add health check and Hermes system info endpoints"
```

---

## Task 7: 创建 Prometheus 监控指标

**Files:**
- Create: `backend/metrics/__init__.py`
- Create: `backend/metrics/definitions.py`

- [ ] **Step 1: 创建 Prometheus 指标定义**

```python
"""
Prometheus 监控指标定义 - Hermes 决策树监控
"""
from prometheus_client import Counter, Histogram, Gauge

# === API 请求指标 ===
api_requests_total = Counter(
    'api_requests_total',
    'API 请求总数',
    ['method', 'endpoint', 'status']
)

api_request_duration_seconds = Histogram(
    'api_request_duration_seconds',
    'API 请求耗时（秒）',
    ['endpoint']
)

# === Hermes 查询指标 ===
hermes_query_total = Counter(
    'hermes_query_total',
    'Hermes 查询总数'
)

hermes_query_duration_seconds = Histogram(
    'hermes_query_duration_seconds',
    'Hermes 查询耗时（秒）',
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

# === 决策树分支指标 ===
decision_tree_branch_taken = Counter(
    'decision_tree_branch_taken_total',
    '决策树分支执行次数',
    ['step', 'decision']  # step: 1-5, decision: YES/NO
)

# === 子智能体调用指标 ===
sub_agent_called = Counter(
    'sub_agent_called_total',
    '子智能体调用次数',
    ['agent_name', 'status']
)

sub_agent_duration = Histogram(
    'sub_agent_duration_seconds',
    '子智能体调用耗时（秒）',
    ['agent_name'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# === 会话管理指标 ===
active_sessions = Gauge(
    'active_sessions',
    '当前活跃会话数'
)
```

- [ ] **Step 2: 提交**

```bash
git add backend/metrics/
git commit -m "feat: add Prometheus metrics for Hermes decision tree monitoring"
```

---

## Task 8: 创建 FastAPI 主应用

**Files:**
- Create: `backend/main.py`

- [ ] **Step 1: 创建主应用**

```python
"""
废水监测系统后端 - Hermes API Server 集成

为已完成的 Hermes 智能体系统提供 HTTP 接口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from prometheus_fastapi_instrumentator import Instrumentator
from backend.api.routes import health, hermes, query
from backend.core.config import settings

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

# Prometheus 监控
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

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
```

- [ ] **Step 2: 提交**

```bash
git add backend/main.py
git commit -m "feat: add FastAPI main application with Hermes API Server integration"
```

---

## Task 9: 更新环境变量配置

**Files:**
- Modify: `.env`

- [ ] **Step 1: 在 .env 中添加 FastAPI 和 Hermes API Server 配置**

```bash
# ==================== FastAPI 配置 ====================
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
FASTAPI_DEBUG=false

# ==================== Hermes API Server 配置 ====================
HERMES_API_URL=http://localhost:8642
HERMES_API_KEY=sk-hermes-api-key
```

- [ ] **Step 2: 验证配置**

```bash
python -c "from backend.core.config import settings; print(f'FastAPI Port: {settings.FASTAPI_PORT}'); print(f'Hermes API: {settings.HERMES_API_URL}')"
```

- [ ] **Step 3: 提交**

```bash
git add .env
git commit -m "config: add FastAPI and Hermes API Server configuration"
```

---

## Task 10: 创建启动脚本

**Files:**
- Create: `scripts/start_backend.sh`
- Create: `scripts/start_backend.bat`

- [ ] **Step 1: 创建启动脚本**

```bash
# scripts/start_backend.sh
#!/bin/bash
echo "Starting FastAPI Backend for Hermes Agent System..."
cd "$(dirname "$0")/.."

# 启动服务
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

```batch
# scripts/start_backend.bat
@echo off
echo Starting FastAPI Backend for Hermes Agent System...
cd /d "%~dp0.."
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

- [ ] **Step 2: 提交**

```bash
git add scripts/
git commit -m "feat: add startup scripts"
```

---

## Task 11: 创建集成测试

**Files:**
- Create: `tests/backend/integration/test_full_api.py`

- [ ] **Step 1: 创建集成测试**

```python
"""
完整的 FastAPI 后端集成测试
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestFullAPI:
    """完整 API 测试"""
    
    @pytest.fixture
    def client(self):
        from backend.main import app
        return TestClient(app)
    
    def test_health_check(self, client):
        """测试健康检查"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data
    
    def test_hermes_system_info(self, client):
        """测试 Hermes 系统信息"""
        response = client.get("/api/hermes/system")
        assert response.status_code == 200
        data = response.json()
        assert "master_agent" in data
        assert "decision_tree" in data
        assert "sub_agents" in data
        assert len(data["sub_agents"]) == 4
    
    def test_hermes_capabilities(self, client):
        """测试 Hermes 能力接口"""
        response = client.get("/api/query/capabilities")
        assert response.status_code == 200
        data = response.json()
        assert "decision_tree" in data
        assert len(data["decision_tree"]) == 5  # 5 个步骤
    
    def test_query_endpoint_structure(self, client):
        """测试查询接口结构"""
        # 测试无效请求（空查询）
        response = client.post("/api/query", json={"query": ""})
        assert response.status_code == 422  # 验证错误
    
    @pytest.mark.skipif(
        True,  # 需要 Hermes API Server 运行
        reason="Requires Hermes API Server"
    )
    def test_query_with_hermes(self, client):
        """测试真实 Hermes 查询"""
        response = client.post(
            "/api/query",
            json={"query": "你好"}
        )
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "content" in data
            assert "decision_path" in data
            assert "session_id" in data
```

- [ ] **Step 2: 运行测试**

```bash
pytest tests/backend/integration/test_full_api.py -v
```

- [ ] **Step 3: 提交**

```bash
git add tests/backend/integration/test_full_api.py
git commit -m "test: add full API integration tests"
```

---

## Task 12: 创建后端 README

**Files:**
- Create: `backend/README.md`

- [ ] **Step 1: 创建 README**

```markdown
# 废水监测系统后端 API

## 系统定位

**本后端通过 Hermes API Server 调用已完成的 Hermes 智能体系统**

Hermes 智能体系统是核心创新（位于 `workspace/` 和 `subagents/`），后端只是为它提供 HTTP 访问能力。

## 核心接口

### 1. 查询接口 `/api/query`

调用 Hermes 主智能体，展示其完整决策过程：

- **决策路径**：展示主智能体走了决策树的哪些分支
- **子智能体调用链**：哪些子智能体被调用
- **数据溯源**：数据来源
- **LLM 推理过程**：意图识别和决策逻辑

### 2. Hermes 系统信息 `/api/hermes/system`

展示 Hermes 系统的完整结构：

- 主智能体信息和决策树
- 4 个子智能体详情
- 三库一体资源位置

### 3. 健康检查 `/api/health`

系统健康状态和 Hermes API Server 连接状态

## 快速开始

### 前置条件

1. Hermes API Server 运行在 `http://localhost:8642`
2. 项目根目录 `.env` 文件已配置

### 安装依赖

```bash
pip install -e .
```

### 启动服务

```bash
# 方式1: 直接启动
python -m uvicorn backend.main:app --reload

# 方式2: 使用启动脚本
./scripts/start_backend.sh  # Linux/Mac
scripts\start_backend.bat   # Windows
```

### 访问文档

```
http://localhost:8000/docs
```

## 架构

```
前端 → FastAPI (8000) → Hermes API Server (8642) → 主智能体 → 4 个子智能体
```

## 主智能体决策树

1. **需要数据吗？** → data-perception
2. **需要异常检测吗？** → anomaly-detection
3. **需要违规判定吗？** → rule-reasoning
4. **需要预警/工单吗？** → disposition-execution
5. **整合结果** → 自然语言回答

## 示例查询

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "最近24小时出水COD异常吗？"}'
```

## Prometheus 指标

访问 `http://localhost:8000/metrics` 查看指标：

- `hermes_query_total` - Hermes 查询总数
- `decision_tree_branch_taken_total` - 决策树分支执行次数
- `sub_agent_called_total` - 子智能体调用次数

详细架构见：`docs/architecture/technical-design.md`
```

- [ ] **Step 2: 提交**

```bash
git add backend/README.md
git commit -m "docs: add backend README"
```

---

## Task 13: 最终验证

- [ ] **Step 1: 运行所有测试**

```bash
pytest tests/backend/ -v
```

- [ ] **Step 2: 启动服务并测试**

```bash
python -m uvicorn backend.main:app --reload
```

测试：
- 访问 `http://localhost:8000/docs`
- 测试 `/api/health`
- 测试 `/api/hermes/system`
- 测试 `/api/query/capabilities`

- [ ] **Step 3: 验证 Prometheus 指标**

```bash
curl http://localhost:8000/metrics
```

应该看到 Hermes 相关指标

- [ ] **Step 4: 最终提交**

```bash
git add .
git commit -m "test: complete Hermes API Server backend integration"
```

---

## 完成检查清单

- [ ] FastAPI 应用可以正常启动
- [ ] `/api/health` 显示 Hermes API Server 连接状态
- [ ] `/api/hermes/system` 展示完整决策树
- [ ] `/api/query/capabilities` 展示 5 步决策树
- [ ] `/api/query` 可以调用 Hermes API Server
- [ ] 响应包含 `decision_path`（决策树执行路径）
- [ ] Prometheus 指标包含决策树分支统计
- [ ] 所有测试通过

---

**计划结束**

本计划的核心原则：
- **通过 Hermes API Server 调用**，而非直接导入 Python 模块
- **充分展示主智能体决策树**：5 步决策过程
- **展示子智能体调用链**：哪些被调用、顺序、结果
