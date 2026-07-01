# 证据链记录系统实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标**: 构建后端日志数据库系统，完整记录系统工作流程（API调用、主智能体决策、子智能体执行、算子调用、LLM调用、系统错误）

**架构**: 使用 SQLAlchemy ORM 创建日志表，通过中间件和装饰器记录系统操作，提供查询接口和展示界面。

**技术栈**: SQLAlchemy、FastAPI、SQLite

---

## 文件结构

```
backend/
├── database/
│   ├── __init__.py
│   ├── base.py                    # SQLAlchemy Base 和 engine
│   ├── session.py                 # 数据库会话管理
│   └── init_db.py                 # 数据库初始化脚本
├── models/
│   ├── logging.py                 # 日志模型（新增）
│   ├── event.py                   # 事件模型（已存在）
│   └── ...
├── api/
│   └── routes/
│       └── logs.py                # 日志查询接口（新增）
├── middleware/
│   ├── __init__.py
│   └── logging_middleware.py      # API 调用日志中间件（新增）
├── utils/
│   ├── __init__.py
│   └── loggers.py                # 日志记录工具（新增）
├── main.py                        # 更新：导入日志路由
└── requirements.txt                # 更新：添加 SQLAlchemy

frontend/
└── src/
    └── views/
        └── Logs.vue               # 日志展示界面（新增）
```

---

## 任务分解

### Phase 1: 数据库初始化

### Task 1: 添加依赖并创建数据库配置

**Files:**
- Modify: `requirements.txt`
- Create: `backend/database/base.py`
- Create: `backend/database/session.py`
- Create: `backend/database/__init__.py`

- [ ] **Step 1: 更新 requirements.txt**

```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
prometheus-fastapi-instrumentator>=7.0.0
python-dotenv>=1.0.0
httpx>=0.26.0
sqlalchemy>=2.0.0
```

- [ ] **Step 2: 安装新依赖**

```bash
cd e:/project/Ecological_env
ecological_env\Scripts\python.exe -m pip install sqlalchemy>=2.0.0
```

- [ ] **Step 3: 创建数据库基类 database/base.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import StaticPool
import os

# 数据库文件路径
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
DB_PATH = os.path.join(DB_DIR, "ecological_logs.db")

# 确保 logs 目录存在
os.makedirs(DB_DIR, exist_ok=True)

# 数据库 URL
DATABASE_URL = f"sqlite:///{DB_PATH}"

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # SQLite 单线程
    echo=False  # 生产环境设为 False
)

# 声明基类
Base = declarative_base()
```

- [ ] **Step 4: 创建会话管理 database/session.py**

```python
from sqlalchemy.orm import sessionmaker
from backend.database.base import engine

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 5: 创建数据库模块 __init__.py**

```python
from backend.database.base import engine, Base, DATABASE_URL
from backend.database.session import get_db

__all__ = ["engine", "Base", "DATABASE_URL", "get_db"]
```

- [ ] **Step 6: 提交**

```bash
git add requirements.txt backend/database/
git commit -m "feat: add SQLAlchemy database configuration"
```

---

### Task 2: 创建日志数据模型

**Files:**
- Create: `backend/models/logging.py`

- [ ] **Step 1: 创建日志模型 models/logging.py**

```python
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, Float, Enum
from sqlalchemy.sql import func
from backend.database.base import Base
import enum


class LogLevel(enum.Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class APICallLog(Base):
    """API 调用日志"""
    __tablename__ = 'api_call_logs'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=func.now(), index=True)
    method = Column(String(10))  # GET/POST/PUT/DELETE
    path = Column(String(255), index=True)  # /api/query
    user_id = Column(String(64), index=True)  # 用户ID
    request_params = Column(JSON)  # 请求参数
    response_status = Column(Integer)  # 200/400/500
    latency_ms = Column(Float)  # 耗时
    error_message = Column(Text, nullable=True)


class MasterAgentDecisionLog(Base):
    """主智能体决策日志"""
    __tablename__ = 'master_agent_decision_logs'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=func.now(), index=True)
    session_id = Column(String(64), index=True)  # 会话ID
    user_query = Column(Text)  # 用户查询
    intent = Column(String(64))  # 意图识别结果
    decision_path = Column(JSON)  # 决策路径
    subagents_called = Column(JSON)  # 调用的子智能体列表
    reasoning_summary = Column(Text)  # 推理摘要
    total_latency_ms = Column(Float)  # 总耗时


class SubAgentExecutionLog(Base):
    """子智能体执行日志"""
    __tablename__ = 'sub_agent_execution_logs'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=func.now(), index=True)
    session_id = Column(String(64), index=True)
    subagent_name = Column(String(64), index=True)  # 子智能体名称
    input_params = Column(JSON)  # 输入参数
    output_result = Column(JSON)  # 输出结果
    execution_time_ms = Column(Float)  # 执行耗时
    status = Column(String(20))  # success/failed
    error_message = Column(Text, nullable=True)


class OperatorCallLog(Base):
    """算子调用日志"""
    __tablename__ = 'operator_call_logs'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=func.now(), index=True)
    session_id = Column(String(64), index=True)
    subagent_name = Column(String(64))  # 调用该算子的子智能体
    operator_name = Column(String(128), index=True)  # 算子名称
    category = Column(String(32))  # statistical/ml/deep_learning
    input_params = Column(JSON)  # 输入参数
    output_result = Column(JSON)  # 输出结果
    execution_time_ms = Column(Float)
    status = Column(String(20))


class LLMCallLog(Base):
    """LLM 调用日志"""
    __tablename__ = 'llm_call_logs'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=func.now(), index=True)
    session_id = Column(String(64), index=True)
    provider = Column(String(64))  # ctgu-vlm
    model = Column(String(64))  # 具体模型名
    purpose = Column(String(32))  # intent_planning/response_formatting
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    total_tokens = Column(Integer)
    estimated_cost = Column(Float, nullable=True)  # 预估成本
    latency_ms = Column(Float)
    request_summary = Column(JSON)  # 简化的请求内容
    status = Column(String(20))


class SystemErrorLog(Base):
    """系统错误日志"""
    __tablename__ = 'system_error_logs'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=func.now(), index=True)
    level = Column(String(20), index=True)  # ERROR/CRITICAL/WARNING
    module = Column(String(64), index=True)  # backend/api/subagent_xxx
    error_type = Column(String(64))  # Exception类型
    error_message = Column(Text)
    stack_trace = Column(Text)
    context = Column(JSON)  # 额外上下文
```

- [ ] **Step 2: 提交**

```bash
git add backend/models/logging.py
git commit -m "feat: add logging data models"
```

---

### Task 3: 创建数据库初始化脚本

**Files:**
- Create: `backend/database/init_db.py`

- [ ] **Step 1: 创建初始化脚本 database/init_db.py**

```python
"""
初始化日志数据库
运行此脚本创建所有日志表
"""
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from backend.database.base import engine, Base
from backend.models.logging import (
    APICallLog,
    MasterAgentDecisionLog,
    SubAgentExecutionLog,
    OperatorCallLog,
    LLMCallLog,
    SystemErrorLog
)


def init_db():
    """创建所有日志表"""
    print("正在初始化日志数据库...")
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    print(f"✓ 日志数据库初始化完成: {engine.url}")
    print("已创建以下表:")
    print("  - api_call_logs")
    print("  - master_agent_decision_logs")
    print("  - sub_agent_execution_logs")
    print("  - operator_call_logs")
    print("  - llm_call_logs")
    print("  - system_error_logs")


if __name__ == "__main__":
    init_db()
```

- [ ] **Step 2: 运行初始化脚本**

```bash
ecological_env\Scripts\python.exe -m backend.database.init_db
```

预期输出：
```
正在初始化日志数据库...
✓ 日志数据库初始化完成: sqlite:///e:/project/Ecological_env/logs/ecological_logs.db
已创建以下表:
  - api_call_logs
  - master_agent_decision_logs
  - sub_agent_execution_logs
  - operator_call_logs
  - llm_call_logs
  - system_error_logs
```

- [ ] **Step 3: 验证数据库文件**

```bash
ls -la logs/
```

应该看到 `ecological_logs.db` 文件

- [ ] **Step 4: 提交**

```bash
git add backend/database/init_db.py
git commit -m "feat: add database initialization script"
```

---

### Phase 2: 日志记录工具

### Task 4: 创建日志记录工具函数

**Files:**
- Create: `backend/utils/loggers.py`

- [ ] **Step 1: 创建日志记录工具 utils/loggers.py**

```python
"""
日志记录工具函数
用于在系统中各个位置记录结构化日志
"""
import time
import uuid
import traceback
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from backend.database.session import SessionLocal
from backend.models.logging import (
    APICallLog,
    MasterAgentDecisionLog,
    SubAgentExecutionLog,
    OperatorCallLog,
    LLMCallLog,
    SystemErrorLog
)


def log_api_call(
    method: str,
    path: str,
    user_id: str,
    request_params: Dict,
    response_status: int,
    latency_ms: float,
    error_message: Optional[str] = None
):
    """记录 API 调用"""
    db = SessionLocal()
    try:
        log = APICallLog(
            method=method,
            path=path,
            user_id=user_id,
            request_params=request_params,
            response_status=response_status,
            latency_ms=latency_ms,
            error_message=error_message
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to log API call: {e}")
    finally:
        db.close()


def log_master_decision(
    session_id: str,
    user_query: str,
    intent: str,
    decision_path: List[str],
    subagents_called: List[str],
    reasoning_summary: str,
    total_latency_ms: float
):
    """记录主智能体决策"""
    db = SessionLocal()
    try:
        log = MasterAgentDecisionLog(
            session_id=session_id,
            user_query=user_query,
            intent=intent,
            decision_path=decision_path,
            subagents_called=subagents_called,
            reasoning_summary=reasoning_summary,
            total_latency_ms=total_latency_ms
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to log master decision: {e}")
    finally:
        db.close()


def log_subagent_execution(
    session_id: str,
    subagent_name: str,
    input_params: Dict,
    output_result: Dict,
    execution_time_ms: float,
    status: str,
    error_message: Optional[str] = None
):
    """记录子智能体执行"""
    db = SessionLocal()
    try:
        log = SubAgentExecutionLog(
            session_id=session_id,
            subagent_name=subagent_name,
            input_params=input_params,
            output_result=output_result,
            execution_time_ms=execution_time_ms,
            status=status,
            error_message=error_message
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to log subagent execution: {e}")
    finally:
        db.close()


def log_operator_call(
    session_id: str,
    subagent_name: str,
    operator_name: str,
    category: str,
    input_params: Dict,
    output_result: Dict,
    execution_time_ms: float,
    status: str
):
    """记录算子调用"""
    db = SessionLocal()
    try:
        log = OperatorCallLog(
            session_id=session_id,
            subagent_name=subagent_name,
            operator_name=operator_name,
            category=category,
            input_params=input_params,
            output_result=output_result,
            execution_time_ms=execution_time_ms,
            status=status
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to log operator call: {e}")
    finally:
        db.close()


def log_llm_call(
    session_id: str,
    provider: str,
    model: str,
    purpose: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    estimated_cost: Optional[float],
    latency_ms: float,
    request_summary: Dict,
    status: str
):
    """记录 LLM 调用"""
    db = SessionLocal()
    try:
        log = LLMCallLog(
            session_id=session_id,
            provider=provider,
            model=model,
            purpose=purpose,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost=estimated_cost,
            latency_ms=latency_ms,
            request_summary=request_summary,
            status=status
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to log LLM call: {e}")
    finally:
        db.close()


def log_system_error(
    level: str,
    module: str,
    error_type: str,
    error_message: str,
    stack_trace: str,
    context: Optional[Dict] = None
):
    """记录系统错误"""
    db = SessionLocal()
    try:
        log = SystemErrorLog(
            level=level,
            module=module,
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            context=context or {}
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to log system error: {e}")
    finally:
        db.close()


def generate_session_id() -> str:
    """生成唯一会话 ID"""
    return str(uuid.uuid4())
```

- [ ] **Step 2: 创建 utils 模块 __init__.py**

```python
from backend.utils.loggers import (
    log_api_call,
    log_master_decision,
    log_subagent_execution,
    log_operator_call,
    log_llm_call,
    log_system_error,
    generate_session_id
)

__all__ = [
    "log_api_call",
    "log_master_decision",
    "log_subagent_execution",
    "log_operator_call",
    "log_llm_call",
    "log_system_error",
    "generate_session_id"
]
```

- [ ] **Step 3: 提交**

```bash
git add backend/utils/
git commit -m "feat: add logging utility functions"
```

---

### Task 5: 创建 API 调用日志中间件

**Files:**
- Create: `backend/middleware/__init__.py`
- Create: `backend/middleware/logging_middleware.py`

- [ ] **Step 1: 创建日志中间件 middleware/logging_middleware.py**

```python
"""
API 调用日志中间件
自动记录所有 API 请求
"""
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Callable
from backend.utils.loggers import log_api_call


class LoggingMiddleware(BaseHTTPMiddleware):
    """API 调用日志中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # 读取请求体（对于 POST/PUT）
        request_params = {}
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                import json
                if body:
                    request_params = json.loads(body.decode())
            except Exception:
                request_params = {"raw": "无法解析"}

        # 处理请求
        response = await call_next(request)

        # 计算耗时
        latency_ms = (time.time() - start_time) * 1000

        # 记录日志
        try:
            log_api_call(
                method=request.method,
                path=request.url.path,
                user_id=request.headers.get("user-id", "anonymous"),
                request_params=request_params,
                response_status=response.status_code,
                latency_ms=latency_ms,
                error_message=None if response.status_code < 400 else "请求失败"
            )
        except Exception as e:
            # 日志记录失败不影响主流程
            print(f"Logging failed: {e}")

        return response
```

- [ ] **Step 2: 创建 middleware 模块 __init__.py**

```python
from backend.middleware.logging_middleware import LoggingMiddleware

__all__ = ["LoggingMiddleware"]
```

- [ ] **Step 3: 在 main.py 中注册中间件**

在 `backend/main.py` 中添加：

```python
from backend.middleware import LoggingMiddleware

app.add_middleware(LoggingMiddleware)
```

添加位置：在 CORS 中间件之后

```python
app = FastAPI(...)

# CORS
app.add_middleware(...)

# 日志中间件
app.add_middleware(LoggingMiddleware)
```

- [ ] **Step 4: 测试中间件**

启动服务并访问任意接口：

```bash
curl http://localhost:8001/api/health
```

检查数据库是否有日志记录：

```bash
ecological_env\Scripts\python.exe -c "from backend.database.session import SessionLocal; from backend.models.logging import APICallLog; db = SessionLocal(); print(db.query(APICallLog).count()); db.close()"
```

应该输出大于 0 的数字

- [ ] **Step 5: 提交**

```bash
git add backend/middleware/ backend/main.py
git commit -m "feat: add API logging middleware"
```

---

### Phase 3: 日志查询接口

### Task 6: 创建日志查询 API

**Files:**
- Create: `backend/api/routes/logs.py`
- Modify: `backend/main.py`

- [ ] **Step 1: 创建日志查询模型 models/log_query.py**

```python
from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class LogQueryParams(BaseModel):
    """日志查询参数"""
    log_type: str  # api/master/subagent/operator/llm/error
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    page: int = 1
    page_size: int = 50


class LogEntry(BaseModel):
    """日志条目"""
    id: int
    timestamp: str
    module: str
    content: str
    details: Optional[dict] = None
    latency_ms: Optional[float] = None


class LogListResponse(BaseModel):
    """日志列表响应"""
    data: List[LogEntry]
    total: int


class SessionTraceResponse(BaseModel):
    """会话证据链响应"""
    session_id: str
    api_call: Optional[dict] = None
    master_decision: Optional[dict] = None
    subagent_executions: List[dict] = []
    operator_calls: List[dict] = []
    llm_calls: List[dict] = []
```

- [ ] **Step 2: 创建日志查询接口 api/routes/logs.py**

```python
from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from backend.database.session import get_db
from backend.models.logging import (
    APICallLog,
    MasterAgentDecisionLog,
    SubAgentExecutionLog,
    OperatorCallLog,
    LLMCallLog,
    SystemErrorLog
)
from backend.models.log_query import LogQueryParams, LogListResponse, LogEntry, SessionTraceResponse
import json

router = APIRouter()


@router.get("/logs", response_model=LogListResponse)
async def query_logs(
    log_type: str = Query(..., regex="^(api|master|subagent|operator|llm|error)$"),
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """统一日志查询接口"""
    
    # 选择表
    table_map = {
        "api": APICallLog,
        "master": MasterAgentDecisionLog,
        "subagent": SubAgentExecutionLog,
        "operator": OperatorCallLog,
        "llm": LLMCallLog,
        "error": SystemErrorLog
    }
    model = table_map[log_type]
    
    # 构建查询
    query = db.query(model)
    
    # 时间过滤
    if start_time:
        query = query.filter(model.timestamp >= datetime.fromisoformat(start_time))
    if end_time:
        query = query.filter(model.timestamp <= datetime.fromisoformat(end_time))
    
    # 获取总数
    total = query.count()
    
    # 分页
    offset = (page - 1) * page_size
    logs = query.order_by(model.timestamp.desc()).offset(offset).limit(page_size).all()
    
    # 转换为响应格式
    data = []
    for log in logs:
        entry = LogEntry(
            id=log.id,
            timestamp=log.timestamp.isoformat(),
            module=log_type,
            content=str(log),
            details=None,
            latency_ms=getattr(log, 'latency_ms', None) or getattr(log, 'execution_time_ms', None)
        )
        data.append(entry)
    
    return LogListResponse(data=data, total=total)


@router.get("/logs/trace/{session_id}", response_model=SessionTraceResponse)
async def get_session_trace(session_id: str, db: Session = Depends(get_db)):
    """获取完整会话的证据链"""
    
    # 查询主智能体决策
    master_log = db.query(MasterAgentDecisionLog).filter(
        MasterAgentDecisionLog.session_id == session_id
    ).first()
    
    # 查询子智能体执行
    subagent_logs = db.query(SubAgentExecutionLog).filter(
        SubAgentExecutionLog.session_id == session_id
    ).all()
    
    # 查询算子调用
    operator_logs = db.query(OperatorCallLog).filter(
        OperatorCallLog.session_id == session_id
    ).all()
    
    # 查询 LLM 调用
    llm_logs = db.query(LLMCallLog).filter(
        LLMCallLog.session_id == session_id
    ).all()
    
    return SessionTraceResponse(
        session_id=session_id,
        master_decision=master_log.__dict__ if master_log else None,
        subagent_executions=[log.__dict__ for log in subagent_logs],
        operator_calls=[log.__dict__ for log in operator_logs],
        llm_calls=[log.__dict__ for log in llm_logs]
    )


@router.get("/logs/export")
async def export_logs(
    log_type: str = Query(..., regex="^(api|master|subagent|operator|llm|error)$"),
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    format: str = Query("json", regex="^(json|xlsx)$"),
    db: Session = Depends(get_db)
):
    """导出日志"""
    # TODO: 实现导出功能
    from fastapi.responses import Response
    return Response(content="导出功能开发中", media_type="text/plain")
```

- [ ] **Step 3: 在 main.py 中注册日志路由**

在 `backend/main.py` 中添加：

```python
from backend.api.routes import health, hermes, query, realtime, events, logs  # 新增 logs

app.include_router(logs.router, prefix="/api")  # 新增
```

- [ ] **Step 4: 测试日志查询接口**

```bash
# 查询 API 日志
curl "http://localhost:8001/api/logs?log_type=api"

# 查询会话证据链（需要先执行一个查询获取 session_id）
curl "http://localhost:8001/api/logs/trace/{session_id}"
```

- [ ] **Step 5: 提交**

```bash
git add backend/api/routes/logs.py backend/models/log_query.py backend/main.py
git commit -m "feat: add logs query API endpoints"
```

---

### Phase 4: 集成到现有代码

### Task 7: 在 query 接口中集成日志记录

**Files:**
- Modify: `backend/api/routes/query.py`

- [ ] **Step 1: 更新 query.py 添加日志记录**

在查询处理函数中添加日志记录：

```python
from fastapi import APIRouter, Request
from backend.api.client import get_hermes_client
from backend.utils.loggers import generate_session_id, log_master_decision, log_llm_call
import time

router = APIRouter()

@router.post("/query")
async def query_hermes(request: Request, payload: dict):
    """查询接口，展示完整决策过程"""
    client = get_hermes_client()
    
    # 生成会话 ID
    session_id = generate_session_id()
    start_time = time.time()
    
    try:
        # 调用 Hermes API
        result = await client.query(payload["query"])
        
        # 记录主智能体决策
        latency_ms = (time.time() - start_time) * 1000
        log_master_decision(
            session_id=session_id,
            user_query=payload["query"],
            intent=result.get("intent", "unknown"),
            decision_path=result.get("decision_path", []),
            subagents_called=result.get("subagents_called", []),
            reasoning_summary=result.get("reasoning_summary", ""),
            total_latency_ms=latency_ms
        )
        
        # 返回结果，包含 session_id
        return {
            **result,
            "sessionId": session_id
        }
        
    except Exception as e:
        # 记录错误
        latency_ms = (time.time() - start_time) * 1000
        log_master_decision(
            session_id=session_id,
            user_query=payload["query"],
            intent="error",
            decision_path=[],
            subagents_called=[],
            reasoning_summary=str(e),
            total_latency_ms=latency_ms
        )
        raise
```

注意：实际代码需要根据现有的 query.py 结构调整。

- [ ] **Step 2: 测试日志记录**

```bash
curl -X POST http://localhost:8001/api/query -H "Content-Type: application/json" -d "{\"query\": \"最近异常吗？\"}
```

检查数据库：

```bash
ecological_env\Scripts\python.exe -c "from backend.database.session import SessionLocal; from backend.models.logging import MasterAgentDecisionLog; db = SessionLocal(); print(db.query(MasterAgentDecisionLog).count()); db.close()"
```

应该看到日志数量增加

- [ ] **Step 3: 提交**

```bash
git add backend/api/routes/query.py
git commit -m "feat: integrate logging into query endpoint"
```

---

### Phase 5: 前端日志展示

### Task 8: 创建日志展示页面

**Files:**
- Create: `frontend/src/views/Logs.vue`
- Modify: `frontend/src/router/index.ts`

- [ ] **Step 1: 创建日志展示页面 views/Logs.vue**

```vue
<template>
  <div class="logs-page">
    <div class="page-header">
      <h2>📋 系统日志</h2>
      <div class="header-actions">
        <el-button @click="exportLogs" :loading="exporting">
          <el-icon><Download /></el-icon>
          导出
        </el-button>
      </div>
    </div>

    <div class="log-filters">
      <el-radio-group v-model="activeTab" @change="handleTabChange">
        <el-radio-button value="api">API调用</el-radio-button>
        <el-radio-button value="master">主智能体</el-radio-button>
        <el-radio-button value="subagent">子智能体</el-radio-button>
        <el-radio-button value="operator">算子</el-radio-button>
        <el-radio-button value="llm">LLM</el-radio-button>
        <el-radio-button value="error">错误</el-radio-button>
      </el-radio-group>

      <el-date-picker
        v-model="timeRange"
        type="datetimerange"
        range-separator="至"
        start-placeholder="开始时间"
        end-placeholder="结束时间"
        @change="handleSearch"
      />
    </div>

    <el-table :data="logs" v-loading="loading" stripe>
      <el-table-column prop="timestamp" label="时间" width="180">
        <template #default="{ row }">
          {{ formatTime(row.timestamp) }}
        </template>
      </el-table-column>
      <el-table-column prop="module" label="模块" width="120" />
      <el-table-column prop="content" label="内容" show-overflow-tooltip />
      <el-table-column prop="latency_ms" label="耗时(ms)" width="100" />
    </el-table>

    <el-pagination
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total="total"
      :page-sizes="[10, 20, 50, 100]"
      layout="total, sizes, prev, pager, next, jumper"
      @size-change="handleSearch"
      @current-change="handleSearch"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Download } from '@element-plus/icons-vue'
import axios from 'axios'

const activeTab = ref('api')
const timeRange = ref<[Date, Date] | null>(null)
const logs = ref([])
const loading = ref(false)
const exporting = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const formatTime = (time: string) => {
  return new Date(time).toLocaleString('zh-CN')
}

const handleTabChange = () => {
  currentPage.value = 1
  handleSearch()
}

const handleSearch = async () => {
  loading.value = true
  try {
    const params: any = {
      log_type: activeTab.value,
      page: currentPage.value,
      page_size: pageSize.value
    }
    
    if (timeRange.value) {
      params.start_time = timeRange.value[0].toISOString()
      params.end_time = timeRange.value[1].toISOString()
    }
    
    const response = await axios.get('/api/logs', { params })
    logs.value = response.data.data
    total.value = response.data.total
  } finally {
    loading.value = false
  }
}

const exportLogs = async () => {
  exporting.value = true
  try {
    // TODO: 调用导出接口
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  handleSearch()
})
</script>

<style scoped>
.logs-page {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  color: #303133;
}

.log-filters {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  gap: 16px;
}

.el-pagination {
  margin-top: 16px;
  justify-content: center;
}
</style>
```

- [ ] **Step 2: 更新路由配置 router/index.ts**

添加日志路由：

```typescript
const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', component: () => import('@/views/Dashboard.vue'), meta: { title: '监测大屏' } },
  { path: '/chat', component: () => import('@/views/AIOpsChat.vue'), meta: { title: 'AI 助手' } },
  { path: '/events', component: () => import('@/views/EventCenter.vue'), meta: { title: '事件中心' } },
  { path: '/logs', component: () => import('@/views/Logs.vue'), meta: { title: '系统日志' } }  // 新增
]
```

- [ ] **Step 3: 更新侧边导航 components/layout/SideNav.vue**

添加日志菜单项：

```vue
<el-menu-item index="/logs">
  <el-icon><Document /></el-icon>
  <span>系统日志</span>
</el-menu-item>
```

记得导入 Document 图标：`import { ChatDotRound, Monitor, Bell, Document } from '@element-plus/icons-vue'`

- [ ] **Step 4: 测试日志页面**

访问 http://localhost:3000/logs，验证：
- 日志列表正常显示
- 切换标签页可以查看不同类型日志
- 时间范围过滤正常工作

- [ ] **Step 5: 提交**

```bash
git add frontend/src/views/Logs.vue frontend/src/router/index.ts frontend/src/components/layout/SideNav.vue
git commit -m "feat: add system logs page"
```

---

### Task 9: 更新全局错误处理

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: 添加全局异常处理器**

在 `backend/main.py` 中添加：

```python
from fastapi import Request, status
from fastapi.responses import JSONResponse
from backend.utils.loggers import log_system_error
import traceback


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    # 记录错误日志
    log_system_error(
        level="ERROR",
        module="backend",
        error_type=type(exc).__name__,
        error_message=str(exc),
        stack_trace=traceback.format_exc(),
        context={"path": request.url.path, "method": request.method}
    )
    
    # 返回错误响应
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "内部服务器错误"}
    )
```

- [ ] **Step 2: 测试错误处理**

访问一个不存在的接口，验证错误被记录到数据库：

```bash
curl http://localhost:8001/api/nonexistent
```

检查 system_error_logs 表：

```bash
ecological_env\Scripts\python.exe -c "from backend.database.session import SessionLocal; from backend.models.logging import SystemErrorLog; db = SessionLocal(); print(db.query(SystemErrorLog).count()); db.close()"
```

- [ ] **Step 3: 提交**

```bash
git add backend/main.py
git commit -m "feat: add global exception handler with logging"
```

---

### Task 10: 创建数据库维护脚本

**Files:**
- Create: `backend/database/maintain_db.py`

- [ ] **Step 1: 创建数据库维护脚本**

```python
"""
日志数据库维护脚本
提供日志清理、统计等功能
"""
import sys
import os
from datetime import datetime, timedelta

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from backend.database.session import SessionLocal
from backend.models.logging import (
    APICallLog,
    MasterAgentDecisionLog,
    SubAgentExecutionLog,
    OperatorCallLog,
    LLMCallLog,
    SystemErrorLog
)


def get_log_stats():
    """获取日志统计信息"""
    db = SessionLocal()
    try:
        stats = {}
        
        stats['api_calls'] = db.query(APICallLog).count()
        stats['master_decisions'] = db.query(MasterAgentDecisionLog).count()
        stats['subagent_executions'] = db.query(SubAgentExecutionLog).count()
        stats['operator_calls'] = db.query(OperatorCallLog).count()
        stats['llm_calls'] = db.query(LLMCallLog).count()
        stats['system_errors'] = db.query(SystemErrorLog).count()
        
        print("=== 日志统计 ===")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        return stats
    finally:
        db.close()


def clean_old_logs(days: int = 30):
    """清理指定天数之前的日志"""
    db = SessionLocal()
    try:
        cutoff_time = datetime.now() - timedelta(days=days)
        
        models = [
            APICallLog,
            MasterAgentDecisionLog,
            SubAgentExecutionLog,
            OperatorCallLog,
            LLMCallLog
        ]
        
        total_deleted = 0
        for model in models:
            deleted = db.query(model).filter(model.timestamp < cutoff_time).delete()
            total_deleted += deleted
            print(f"  {model.__tablename__}: 删除 {deleted} 条记录")
        
        db.commit()
        print(f"✓ 共删除 {total_deleted} 条旧日志")
    finally:
        db.close()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="日志数据库维护")
    parser.add_argument('action', choices=['stats', 'clean'], help='操作类型')
    parser.add_argument('--days', type=int, default=30, help='清理多少天之前的日志')
    
    args = parser.parse_args()
    
    if args.action == 'stats':
        get_log_stats()
    elif args.action == 'clean':
        print(f"清理 {args.days} 天之前的日志:")
        clean_old_logs(args.days)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 测试维护脚本**

```bash
# 查看统计
ecological_env\Scripts\python.exe -m backend.database.maintain_db stats

# 清理 90 天前的日志（慎用）
ecological_env\Scripts\python.exe -m backend.database.maintain_db clean --days 90
```

- [ ] **Step 3: 提交**

```bash
git add backend/database/maintain_db.py
git commit -m "feat: add database maintenance script"
```

---

### Task 11: 更新文档

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: 更新 README.md 添加日志系统说明**

在 README.md 中添加日志系统部分：

```markdown
## 日志系统

系统会自动记录以下类型的日志：

- **API 调用日志**: 记录所有 API 请求
- **主智能体决策日志**: 记录意图识别、子智能体调用链
- **子智能体执行日志**: 记录子智能体的输入输出
- **算子调用日志**: 记录算子调用的参数和结果
- **LLM 调用日志**: 记录 LLM 调用的 Token 消耗
- **系统错误日志**: 记录系统异常

### 查询日志

```bash
# 前端界面
访问 http://localhost:3000/logs

# API 接口
curl "http://localhost:8001/api/logs?log_type=api&page=1&page_size=50"
```

### 会话证据链

通过 session_id 可以查询完整会话的证据链：

```bash
curl "http://localhost:8001/api/logs/trace/{session_id}"
```

### 数据库维护

```bash
# 查看日志统计
python -m backend.database.maintain_db stats

# 清理旧日志（90 天前）
python -m backend.database.maintain_db clean --days 90
```
```

- [ ] **Step 2: 更新 CLAUDE.md 添加日志系统说明**

在 CLAUDE.md 的核心模块部分添加：

```markdown
### 日志系统

- `backend/database/` - SQLAlchemy 数据库配置
  - `base.py` - 数据库引擎和基类
  - `session.py` - 会话管理
  - `init_db.py` - 初始化脚本
  - `maintain_db.py` - 维护脚本
- `backend/models/logging.py` - 日志数据模型
- `backend/api/routes/logs.py` - 日志查询接口
- `backend/middleware/logging_middleware.py` - API 调用日志中间件
- `backend/utils/loggers.py` - 日志记录工具函数
```

- [ ] **Step 3: 提交**

```bash
git add README.md CLAUDE.md
git commit -m "docs: add logging system documentation"
```

---

## 完成检查清单

- [ ] 数据库配置正确，日志表创建成功
- [ ] 所有日志模型正确实现
- [ ] API 调用日志中间件正常工作
- [ ] 日志记录工具函数可用
- [ ] 日志查询 API 正常
- [ ] 前端日志展示页面正常
- [ ] 全局异常处理器正常工作
- [ ] 数据库维护脚本可用
- [ ] 文档已更新

---

## 注意事项

1. **数据库性能**: SQLite 适合中小规模，如果日志量很大建议考虑 PostgreSQL 或 MySQL
2. **敏感信息**: 日志中可能包含敏感信息，生产环境需考虑脱敏
3. **日志清理**: 建议定期清理旧日志，避免数据库过大
4. **异步日志**: 当前是同步写入，高并发场景可能需要考虑异步队列
