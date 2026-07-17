# 后端FastAPI模块化重构 - Phase 1 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构后端FastAPI为专业数据服务层，实现核心数据查询和对话历史持久化功能

**Architecture:** 采用模块化架构，将后端重新定位为数据服务层，与Agent服务(8642)形成清晰职责分离。使用RESTful设计、混合持久化策略，保持向后兼容。

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, Alembic, SQLite

---

## 文件结构概览

### 新创建文件
```
backend/
├── api/v1/
│   ├── __init__.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── realtime.py
│   │   ├── history.py
│   │   └── quality.py
│   └── conversations/
│       ├── __init__.py
│       └── conversations.py
├── services/
│   ├── __init__.py
│   ├── data_service.py
│   └── conversation_service.py
├── models/
│   ├── conversation.py
│   └── monitoring.py
└── exceptions.py
```

### 修改文件
- `backend/main.py` - 注册v1路由
- `backend/core/config.py` - 添加新配置
- `backend/database/base.py` - 添加新表定义

---

## Task 1: 创建统一异常处理系统

**Files:**
- Create: `backend/exceptions.py`
- Test: `tests/test_exceptions.py`

- [ ] **Step 1: Write the failing test**

创建测试文件 `tests/test_exceptions.py`:

```python
import pytest
from backend.exceptions import (
    BackendException,
    DataUnavailableException,
    ValidationException,
    ExternalServiceException,
    ResourceNotFoundException
)

def test_backend_exception_basic():
    """测试基础异常类"""
    exc = BackendException("TEST_CODE", "Test message")
    assert exc.code == "TEST_CODE"
    assert exc.message == "Test message"
    assert exc.details == {}

def test_backend_exception_with_details():
    """测试带详情的异常"""
    details = {"source": "test", "retry_after": 30}
    exc = BackendException("TEST_CODE", "Test message", details)
    assert exc.details == details

def test_data_unavailable_exception():
    """测试数据不可用异常"""
    exc = DataUnavailableException("Data source unavailable")
    assert exc.code == "DATA_SOURCE_UNAVAILABLE"
    assert "unavailable" in exc.message.lower()

def test_validation_exception():
    """测试验证异常"""
    exc = ValidationException("Invalid parameter")
    assert exc.code == "VALIDATION_ERROR"

def test_external_service_exception():
    """测试外部服务异常"""
    exc = ExternalServiceException("Service timeout")
    assert exc.code == "EXTERNAL_SERVICE_ERROR"

def test_resource_not_found_exception():
    """测试资源不存在异常"""
    exc = ResourceNotFoundException("Resource not found")
    assert exc.code == "RESOURCE_NOT_FOUND"
```

- [ ] **Step 2: Run test to verify it fails**

运行: `cd E:/project/Ecological_env && python -m pytest tests/test_exceptions.py -v`
预期: FAIL，错误信息应显示 "No module named 'backend.exceptions'"

- [ ] **Step 3: Write minimal implementation**

创建文件 `backend/exceptions.py`:

```python
"""
统一异常处理系统

定义后端服务的自定义异常类，提供统一的错误响应格式。
"""

class BackendException(Exception):
    """基础异常类
    
    所有后端异常的基类，提供统一的错误码、消息和详情字段。
    """
    
    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self):
        """转换为字典格式，用于API响应"""
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details
        }


class DataUnavailableException(BackendException):
    """数据不可用异常
    
    当数据源暂时不可用或数据获取失败时抛出。
    """
    
    def __init__(self, message: str = "Data source unavailable", details: dict = None):
        super().__init__("DATA_SOURCE_UNAVAILABLE", message, details)


class ValidationException(BackendException):
    """数据验证异常
    
    当请求参数验证失败时抛出。
    """
    
    def __init__(self, message: str = "Validation failed", details: dict = None):
        super().__init__("VALIDATION_ERROR", message, details)


class ExternalServiceException(BackendException):
    """外部服务异常
    
    当外部服务（如Agent服务）调用失败时抛出。
    """
    
    def __init__(self, message: str = "External service error", details: dict = None):
        super().__init__("EXTERNAL_SERVICE_ERROR", message, details)


class ResourceNotFoundException(BackendException):
    """资源不存在异常
    
    当请求的资源不存在时抛出。
    """
    
    def __init__(self, message: str = "Resource not found", details: dict = None):
        super().__init__("RESOURCE_NOT_FOUND", message, details)


class DatabaseException(BackendException):
    """数据库异常
    
    当数据库操作失败时抛出。
    """
    
    def __init__(self, message: str = "Database error", details: dict = None):
        super().__init__("DATABASE_ERROR", message, details)


class RateLimitExceededException(BackendException):
    """速率限制异常
    
    当超过API调用速率限制时抛出。
    """
    
    def __init__(self, message: str = "Rate limit exceeded", details: dict = None):
        super().__init__("RATE_LIMIT_EXCEEDED", message, details)
```

- [ ] **Step 4: Run test to verify it passes**

运行: `cd E:/project/Ecological_env && python -m pytest tests/test_exceptions.py -v`
预期: PASS，所有7个测试通过

- [ ] **Step 5: Commit**

```bash
cd E:/project/Ecological_env
git add backend/exceptions.py tests/test_exceptions.py
git commit -m "feat: add unified exception handling system"
```

---

## Task 2: 扩展数据库模型（添加对话相关表）

**Files:**
- Modify: `backend/database/base.py`
- Create: `backend/models/conversation.py`
- Test: `tests/test_conversation_models.py`

- [ ] **Step 1: Write the failing test**

创建测试文件 `tests/test_conversation_models.py`:

```python
import pytest
from datetime import datetime
from backend.database.base import engine, Base, SessionLocal
from backend.models.conversation import (
    Conversation, 
    ConversationMessage, 
    MasterDecision,
    SubagentCall
)

def test_conversation_model():
    """测试对话模型"""
    conv = Conversation(
        id="test_conv_001",
        user_id="test_user",
        title="测试对话",
        status="active"
    )
    assert conv.id == "test_conv_001"
    assert conv.status == "active"
    assert conv.message_count == 0

def test_conversation_message_model():
    """测试消息模型"""
    msg = ConversationMessage(
        id="test_msg_001",
        conversation_id="test_conv_001",
        role="user",
        content="你好"
    )
    assert msg.role == "user"
    assert msg.content == "你好"

def test_master_decision_model():
    """测试决策记录模型"""
    decision = MasterDecision(
        id="test_decision_001",
        conversation_id="test_conv_001",
        user_query="查询数据",
        intent="data_query"
    )
    assert decision.intent == "data_query"

def test_subagent_call_model():
    """测试子智能体调用模型"""
    call = SubagentCall(
        id="test_call_001",
        conversation_id="test_conv_001",
        subagent_name="anomaly-detection",
        status="success"
    )
    assert call.subagent_name == "anomaly-detection"
```

- [ ] **Step 2: Run test to verify it fails**

运行: `cd E:/project/Ecological_env && python -m pytest tests/test_conversation_models.py -v`
预期: FAIL，错误信息应显示 "No module named 'backend.models.conversation'"

- [ ] **Step 3: Write minimal implementation**

首先创建 `backend/models/conversation.py`:

```python
"""对话相关的数据模型"""

from sqlalchemy import Column, String, Integer, Text, Enum as SQLEnum, TIMESTAMP, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.database.base import Base
import enum


class ConversationStatus(str, enum.Enum):
    """对话状态枚举"""
    ACTIVE = "active"
    COMPLETED = "completed"
    ERROR = "error"


class MessageRole(str, enum.Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class SubagentCallStatus(str, enum.Enum):
    """子智能体调用状态枚举"""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


class Conversation(Base):
    """对话历史表"""
    __tablename__ = "conversations"
    
    id = Column(String(50), primary_key=True)
    user_id = Column(String(50), nullable=True)
    title = Column(String(200), nullable=True)
    started_at = Column(TIMESTAMP, nullable=True)
    ended_at = Column(TIMESTAMP, nullable=True)
    message_count = Column(Integer, default=0)
    status = Column(SQLEnum(ConversationStatus), default=ConversationStatus.ACTIVE)
    metadata = Column(JSON, nullable=True)


class ConversationMessage(Base):
    """消息记录表"""
    __tablename__ = "conversation_messages"
    
    id = Column(String(50), primary_key=True)
    conversation_id = Column(String(50), ForeignKey("conversations.id", ondelete="CASCADE"))
    role = Column(SQLEnum(MessageRole), nullable=False)
    content = Column(Text, nullable=True)
    tool_call_info = Column(JSON, nullable=True)
    timestamp = Column(TIMESTAMP, nullable=True)
    
    # 关系
    conversation = relationship("Conversation", backref="messages")


class MasterDecision(Base):
    """决策记录表"""
    __tablename__ = "master_decisions"
    
    id = Column(String(50), primary_key=True)
    conversation_id = Column(String(50), ForeignKey("conversations.id", ondelete="SET NULL"))
    user_query = Column(Text, nullable=True)
    intent = Column(String(100), nullable=True)
    decision_path = Column(JSON, nullable=True)
    subagents_called = Column(JSON, nullable=True)
    reasoning_summary = Column(Text, nullable=True)
    total_latency_ms = Column(Integer, nullable=True)
    timestamp = Column(TIMESTAMP, nullable=True)


class SubagentCall(Base):
    """子智能体调用表"""
    __tablename__ = "subagent_calls"
    
    id = Column(String(50), primary_key=True)
    conversation_id = Column(String(50), ForeignKey("conversations.id", ondelete="SET NULL"))
    subagent_name = Column(String(50), nullable=True)
    task_description = Column(Text, nullable=True)
    input_params = Column(JSON, nullable=True)
    output_result = Column(JSON, nullable=True)
    status = Column(SQLEnum(SubagentCallStatus), nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    timestamp = Column(TIMESTAMP, nullable=True)
```

- [ ] **Step 4: Run test to verify it passes**

运行: `cd E:/project/Ecological_env && python -m pytest tests/test_conversation_models.py -v`
预期: PASS，所有4个测试通过

- [ ] **Step 5: Commit**

```bash
cd E:/project/Ecological_env
git add backend/models/conversation.py tests/test_conversation_models.py
git commit -m "feat: add conversation database models"
```

---

## Task 3: 创建监控数据模型

**Files:**
- Create: `backend/models/monitoring.py`
- Test: `tests/test_monitoring_models.py`

- [ ] **Step 1: Write the failing test**

创建测试文件 `tests/test_monitoring_models.py`:

```python
import pytest
from backend.models.monitoring import (
    MonitoringData,
    DataQualityMetric,
    SystemHealth,
    Alert
)

def test_monitoring_data_model():
    """测试监测数据模型"""
    data = MonitoringData(
        timestamp="2026-07-17T15:30:00Z",
        influent_pH=7.2,
        influent_COD=150.5,
        effluent_pH=6.8,
        effluent_COD=35.2
    )
    assert data.influent_pH == 7.2
    assert data.effluent_COD == 35.2

def test_data_quality_metric_model():
    """测试数据质量指标模型"""
    metric = DataQualityMetric(
        completeness_rate=0.98,
        missing_data_count=15,
        anomaly_count=3
    )
    assert metric.completeness_rate == 0.98
    assert metric.missing_data_count == 15
```

- [ ] **Step 2: Run test to verify it fails**

运行: `cd E:/project/Ecological_env && python -m pytest tests/test_monitoring_models.py -v`
预期: FAIL，错误信息应显示 "No module named 'backend.models.monitoring'"

- [ ] **Step 3: Write minimal implementation**

创建文件 `backend/models/monitoring.py`:

```python
"""监控相关的数据模型"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class DataSourceStatus(str, Enum):
    """数据源状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class MonitoringData(BaseModel):
    """实时监测数据模型"""
    
    timestamp: str = Field(..., description="数据时间戳")
    influent: Dict[str, float] = Field(..., description="进水数据")
    effluent: Dict[str, float] = Field(..., description="出水数据")
    flow_rate: float = Field(..., description="流量")
    quality_score: float = Field(..., description="数据质量评分")


class DataQualityMetric(BaseModel):
    """数据质量指标模型"""
    
    completeness_rate: float = Field(..., description="完整率", ge=0, le=1)
    missing_data_count: int = Field(..., description="缺失数据数量", ge=0)
    anomaly_count: int = Field(..., description="异常数据数量", ge=0)
    last_update: str = Field(..., description="最后更新时间")


class SystemHealth(BaseModel):
    """系统健康状态模型"""
    
    overall_status: str = Field(..., description="整体状态")
    components: Dict[str, Dict[str, Any]] = Field(..., description="组件状态")
    uptime_seconds: int = Field(..., description="运行时长（秒）")


class Alert(BaseModel):
    """告警模型"""
    
    id: str = Field(..., description="告警ID")
    severity: str = Field(..., description="严重程度")
    type: str = Field(..., description="告警类型")
    message: str = Field(..., description="告警消息")
    timestamp: str = Field(..., description="告警时间")
    acknowledged: bool = Field(default=False, description="是否已确认")
```

- [ ] **Step 4: Run test to verify it passes**

运行: `cd E:/project/Ecological_env && python -m pytest tests/test_monitoring_models.py -v`
预期: PASS，所有2个测试通过

- [ ] **Step 5: Commit**

```bash
cd E:/project/Ecological_env
git add backend/models/monitoring.py tests/test_monitoring_models.py
git commit -m "feat: add monitoring data models"
```

---

## Task 4: 创建Pydantic请求/响应模型

**Files:**
- Create: `backend/models/api.py`
- Test: `tests/test_api_models.py`

- [ ] **Step 1: Write the failing test**

创建测试文件 `tests/test_api_models.py`:

```python
import pytest
from backend.models.api import (
    StandardResponse,
    ConversationListResponse,
    ConversationCreateRequest,
    HistoryQueryRequest
)

def test_standard_response():
    """测试标准响应模型"""
    response = StandardResponse(
        success=True,
        data={"test": "data"}
    )
    assert response.success is True
    assert response.data == {"test": "data"}

def test_conversation_create_request():
    """测试对话创建请求模型"""
    request = ConversationCreateRequest(
        user_id="test_user",
        title="测试对话"
    )
    assert request.user_id == "test_user"
```

- [ ] **Step 2: Run test to verify it fails**

运行: `cd E:/project/Ecological_env && python -m pytest tests/test_api_models.py -v`
预期: FAIL，错误信息应显示 "No module named 'backend.models.api'"

- [ ] **Step 3: Write minimal implementation**

创建文件 `backend/models/api.py`:

```python
"""API请求和响应模型"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class StandardResponse(BaseModel):
    """标准API响应格式"""
    
    success: bool = Field(..., description="请求是否成功")
    data: Optional[Any] = Field(None, description="响应数据")
    error: Optional[Dict[str, str]] = Field(None, description="错误信息")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class ConversationListResponse(BaseModel):
    """对话列表响应"""
    
    conversations: List[Dict[str, Any]] = Field(..., description="对话列表")
    total_count: int = Field(..., description="总数量")
    page: int = Field(default=1, description="当前页码")


class ConversationCreateRequest(BaseModel):
    """创建对话请求"""
    
    user_id: Optional[str] = Field(None, description="用户ID")
    title: Optional[str] = Field(None, description="对话标题")


class HistoryQueryRequest(BaseModel):
    """历史数据查询请求"""
    
    time_range: str = Field(default="24h", description="时间范围")
    indicators: Optional[str] = Field(None, description="指标列表（逗号分隔）")
    aggregation: str = Field(default="raw", description="聚合方式")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=50, ge=1, le=100, description="每页数量")


class RealtimeDataResponse(BaseModel):
    """实时数据响应"""
    
    timestamp: str = Field(..., description="数据时间戳")
    influent: Dict[str, float] = Field(..., description="进水数据")
    effluent: Dict[str, float] = Field(..., description="出水数据")
    flow_rate: float = Field(..., description="流量")
    quality_score: float = Field(..., description="数据质量评分")
```

- [ ] **Step 4: Run test to verify it passes**

运行: `cd E:/project/Ecological_env && python -m pytest tests/test_api_models.py -v`
预期: PASS，所有2个测试通过

- [ ] **Step 5: Commit**

```bash
cd E:/project/Ecological_env
git add backend/models/api.py tests/test_api_models.py
git commit -m "feat: add API request/response models"
```

---

## Task 5: 创建对话服务层

**Files:**
- Create: `backend/services/conversation_service.py`
- Create: `backend/services/__init__.py`
- Test: `tests/test_conversation_service.py`

- [ ] **Step 1: Write the failing test**

创建测试文件 `tests/test_conversation_service.py`:

```python
import pytest
from backend.services.conversation_service import ConversationService
from backend.models.api import ConversationCreateRequest

def test_conversation_service_init():
    """测试对话服务初始化"""
    service = ConversationService()
    assert service is not None

def test_create_conversation():
    """测试创建对话"""
    service = ConversationService()
    request = ConversationCreateRequest(
        user_id="test_user",
        title="测试对话"
    )
    result = service.create_conversation(request)
    assert "id" in result
    assert result["status"] == "active"

def test_get_conversation():
    """测试获取对话"""
    service = ConversationService()
    # 先创建一个对话
    create_request = ConversationCreateRequest(title="测试")
    created = service.create_conversation(create_request)
    
    # 获取对话
    result = service.get_conversation(created["id"])
    assert result is not None
    assert result["id"] == created["id"]
```

- [ ] **Step 2: Run test to verify it fails**

运行: `cd E:/project/Ecological_env && python -m pytest tests/test_conversation_service.py -v`
预期: FAIL，错误信息应显示 "No module named 'backend.services.conversation_service'"

- [ ] **Step 3: Write minimal implementation**

首先创建 `backend/services/__init__.py`:

```python
"""服务层模块"""
```

然后创建 `backend/services/conversation_service.py`:

```python
"""对话服务层

负责对话历史的管理和持久化。
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from backend.database.session import SessionLocal
from backend.models.conversation import Conversation, ConversationMessage, ConversationStatus
from backend.models.api import ConversationCreateRequest


class ConversationService:
    """对话服务类"""
    
    def __init__(self):
        self.db = SessionLocal
    
    def get_db_session(self) -> Session:
        """获取数据库会话"""
        return self.db()
    
    def create_conversation(self, request: ConversationCreateRequest) -> Dict[str, Any]:
        """创建新对话
        
        Args:
            request: 创建对话请求
            
        Returns:
            包含对话ID的字典
        """
        db = self.get_db_session()
        try:
            conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
            
            conversation = Conversation(
                id=conversation_id,
                user_id=request.user_id,
                title=request.title or "新对话",
                status=ConversationStatus.ACTIVE,
                started_at=datetime.now()
            )
            
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
            
            return {
                "id": conversation.id,
                "user_id": conversation.user_id,
                "title": conversation.title,
                "status": conversation.status.value,
                "started_at": conversation.started_at.isoformat() if conversation.started_at else None
            }
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """获取对话详情
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            对话详情字典，不存在返回None
        """
        db = self.get_db_session()
        try:
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            
            if not conversation:
                return None
            
            return {
                "id": conversation.id,
                "user_id": conversation.user_id,
                "title": conversation.title,
                "status": conversation.status.value,
                "started_at": conversation.started_at.isoformat() if conversation.started_at else None,
                "ended_at": conversation.ended_at.isoformat() if conversation.ended_at else None,
                "message_count": conversation.message_count
            }
        finally:
            db.close()
    
    def list_conversations(self, page: int = 1, page_size: int = 20, 
                          status: Optional[str] = None) -> Dict[str, Any]:
        """列出对话
        
        Args:
            page: 页码
            page_size: 每页数量
            status: 状态过滤
            
        Returns:
            对话列表结果
        """
        db = self.get_db_session()
        try:
            query = db.query(Conversation)
            
            if status:
                query = query.filter(Conversation.status == status)
            
            total_count = query.count()
            conversations = query.offset((page - 1) * page_size).limit(page_size).all()
            
            return {
                "conversations": [
                    {
                        "id": conv.id,
                        "title": conv.title,
                        "started_at": conv.started_at.isoformat() if conv.started_at else None,
                        "message_count": conv.message_count,
                        "status": conv.status.value
                    }
                    for conv in conversations
                ],
                "total_count": total_count,
                "page": page,
                "page_size": page_size
            }
        finally:
            db.close()
    
    def add_message(self, conversation_id: str, role: str, 
                   content: str, tool_call_info: Optional[Dict] = None) -> Dict[str, Any]:
        """添加消息到对话
        
        Args:
            conversation_id: 对话ID
            role: 消息角色
            content: 消息内容
            tool_call_info: 工具调用信息
            
        Returns:
            消息ID
        """
        db = self.get_db_session()
        try:
            message_id = f"msg_{uuid.uuid4().hex[:12]}"
            
            message = ConversationMessage(
                id=message_id,
                conversation_id=conversation_id,
                role=role,
                content=content,
                tool_call_info=tool_call_info,
                timestamp=datetime.now()
            )
            
            # 更新对话的消息计数
            db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).update({"message_count": Conversation.message_count + 1})
            
            db.add(message)
            db.commit()
            
            return {"id": message_id, "timestamp": message.timestamp.isoformat()}
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
```

- [ ] **Step 4: Run test to verify it passes**

运行: `cd E:/project/Ecological_env && python -m pytest tests/test_conversation_service.py -v`
预期: PASS，所有3个测试通过

- [ ] **Step 5: Commit**

```bash
cd E:/project/Ecological_env
git add backend/services/ tests/test_conversation_service.py
git commit -m "feat: add conversation service layer"
```

---

## Task 6: 创建数据服务层

**Files:**
- Create: `backend/services/data_service.py`
- Test: `tests/test_data_service.py`

- [ ] **Step 1: Write the failing test**

创建测试文件 `tests/test_data_service.py`:

```python
import pytest
from backend.services.data_service import DataService

def test_data_service_init():
    """测试数据服务初始化"""
    service = DataService()
    assert service is not None

def test_get_realtime_data():
    """测试获取实时数据"""
    service = DataService()
    result = service.get_realtime_data()
    assert "timestamp" in result
    assert "influent" in result
    assert "effluent" in result

def test_get_data_quality():
    """测试获取数据质量"""
    service = DataService()
    result = service.get_data_quality()
    assert "completeness_rate" in result
    assert "missing_data_count" in result
```

- [ ] **Step 2: Run test to verify it fails**

运行: `cd E:/project/Ecological_env && python -m pytest tests/test_data_service.py -v`
预期: FAIL，错误信息应显示 "No module named 'backend.services.data_service'"

- [ ] **Step 3: Write minimal implementation**

创建文件 `backend/services/data_service.py`:

```python
"""数据服务层

负责监测数据的查询和处理。
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta


class DataService:
    """数据服务类"""
    
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent.parent / "data"
    
    def get_realtime_data(self) -> Dict[str, Any]:
        """获取实时监测数据
        
        Returns:
            包含实时监测数据的字典
        """
        # 这里应该从实际的数据源获取数据
        # 暂时返回模拟数据
        return {
            "timestamp": datetime.now().isoformat(),
            "influent": {
                "pH": 7.2,
                "COD": 150.5,
                "TN": 25.3,
                "TP": 3.1
            },
            "effluent": {
                "pH": 6.8,
                "COD": 35.2,
                "TN": 8.5,
                "TP": 0.3
            },
            "flow_rate": 120.5,
            "quality_score": 0.95
        }
    
    def get_data_quality(self, time_range: str = "24h") -> Dict[str, Any]:
        """获取数据质量指标
        
        Args:
            time_range: 时间范围
            
        Returns:
            数据质量指标字典
        """
        # 这里应该计算实际的数据质量指标
        # 暂时返回模拟数据
        return {
            "completeness_rate": 0.98,
            "missing_data_count": 15,
            "anomaly_count": 3,
            "last_update": datetime.now().isoformat()
        }
    
    def query_history_data(self, time_range: str = "24h", 
                          indicators: Optional[str] = None,
                          aggregation: str = "raw",
                          page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """查询历史数据
        
        Args:
            time_range: 时间范围
            indicators: 指标列表（逗号分隔）
            aggregation: 聚合方式
            page: 页码
            page_size: 每页数量
            
        Returns:
            历史数据查询结果
        """
        # 这里应该从数据库或文件查询实际数据
        # 暂时返回模拟数据
        return {
            "records": [
                {
                    "timestamp": "2026-07-17T14:00:00Z",
                    "pH": 7.1,
                    "COD": 145.2
                },
                {
                    "timestamp": "2026-07-17T15:00:00Z",
                    "pH": 7.3,
                    "COD": 148.8
                }
            ],
            "summary": {
                "avg_pH": 7.2,
                "max_COD": 150.5,
                "min_TN": 8.2
            },
            "total_count": 2,
            "page": page,
            "page_size": page_size
        }
    
    def get_aggregated_data(self, period: str = "daily", 
                           metrics: str = "avg,max,min") -> Dict[str, Any]:
        """获取聚合统计数据
        
        Args:
            period: 统计周期
            metrics: 统计指标
            
        Returns:
            聚合统计数据
        """
        # 这里应该计算实际的聚合统计
        # 暂时返回模拟数据
        return {
            "period": period,
            "metrics": metrics.split(",") if metrics else [],
            "data": {
                "daily": {
                    "2026-07-17": {
                        "pH_avg": 7.2,
                        "pH_max": 7.5,
                        "pH_min": 6.9,
                        "COD_avg": 140.5,
                        "COD_max": 150.5,
                        "COD_min": 135.2
                    }
                }
            }
        }
```

- [ ] **Step 4: Run test to verify it passes**

运行: `cd E:/project/Ecological_env && python -m pytest tests/test_data_service.py -v`
预期: PASS，所有3个测试通过

- [ ] **Step 5: Commit**

```bash
cd E:/project/Ecological_env
git add backend/services/data_service.py tests/test_data_service.py
git commit -m "feat: add data service layer"
```

---

## Task 7: 创建v1 API路由 - 实时数据端点

**Files:**
- Create: `backend/api/v1/__init__.py`
- Create: `backend/api/v1/data/__init__.py`
- Create: `backend/api/v1/data/realtime.py`
- Test: `tests/test_api_realtime.py`

- [ ] **Step 1: Write the failing test**

创建测试文件 `tests/test_api_realtime.py`:

```python
import pytest
from fastapi.testclient import TestClient
from backend.main import app

def test_realtime_endpoint():
    """测试实时数据端点"""
    client = TestClient(app)
    response = client.get("/api/v1/monitoring/realtime")
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "data" in data

def test_quality_endpoint():
    """测试数据质量端点"""
    client = TestClient(app)
    response = client.get("/api/v1/monitoring/quality")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
```

- [ ] **Step 2: Run test to verify it fails**

运行: `cd E:/project/Ecological_env && python -m pytest tests/test_api_realtime.py -v`
预期: FAIL，错误信息应显示 "404 Not Found"

- [ ] **Step 3: Write minimal implementation**

首先创建 `backend/api/v1/__init__.py`:

```python
"""API v1 路由模块"""
```

创建 `backend/api/v1/data/__init__.py`:

```python
"""数据服务API路由"""
```

创建 `backend/api/v1/data/realtime.py`:

```python
"""实时监测数据API"""

from fastapi import APIRouter, Query
from typing import Optional

from backend.services.data_service import DataService
from backend.models.monitoring import MonitoringData, DataQualityMetric
from backend.models.api import StandardResponse

router = APIRouter(tags=["实时监测数据"])

data_service = DataService()


@router.get("/monitoring/realtime", response_model=StandardResponse)
async def get_realtime_data():
    """获取实时监测数据
    
    返回最新的进水、出水监测数据，包括pH、COD、TN、TP等指标。
    """
    try:
        data = data_service.get_realtime_data()
        return StandardResponse(
            success=True,
            data=data,
            metadata={
                "timestamp": data["timestamp"],
                "data_source": "monitoring_system"
            }
        )
    except Exception as e:
        return StandardResponse(
            success=False,
            error={
                "code": "DATA_FETCH_ERROR",
                "message": str(e)
            }
        )


@router.get("/monitoring/quality", response_model=StandardResponse)
async def get_data_quality(
    time_range: str = Query(default="24h", description="时间范围")
):
    """获取数据质量指标
    
    返回数据完整率、缺失数据数量、异常数据数量等质量指标。
    """
    try:
        data = data_service.get_data_quality(time_range)
        return StandardResponse(
            success=True,
            data=data
        )
    except Exception as e:
        return StandardResponse(
            success=False,
            error={
                "code": "QUALITY_FETCH_ERROR",
                "message": str(e)
            }
        )
```

- [ ] **Step 4: Run test to verify it passes**

首先需要在 `backend/main.py` 中注册路由。修改该文件：

```python
# 在现有路由注册部分添加
from backend.api.v1 import data as v1_data

# 注册v1路由
app.include_router(v1_data.realtime.router, prefix="/api/v1")
```

然后运行测试:
运行: `cd E:/project/Ecological_env && python -m pytest tests/test_api_realtime.py -v`
预期: PASS，所有2个测试通过

- [ ] **Step 5: Commit**

```bash
cd E:/project/Ecological_env
git add backend/api/v1/ backend/main.py tests/test_api_realtime.py
git commit -m "feat: add v1 realtime monitoring API endpoints"
```

---

## Task 8: 创建历史数据API端点

**Files:**
- Create: `backend/api/v1/data/history.py`
- Test: `tests/test_api_history.py`

- [ ] **Step 1: Write the failing test**

创建测试文件 `tests/test_api_history.py`:

```python
import pytest
from fastapi.testclient import TestClient
from backend.main import app

def test_history_endpoint():
    """测试历史数据端点"""
    client = TestClient(app)
    response = client.get("/api/v1/data/history?time_range=24h")
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "data" in data

def test_aggregated_endpoint():
    """测试聚合数据端点"""
    client = TestClient(app)
    response = client.get("/api/v1/data/aggregated?period=daily")
    assert response.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

运行: `cd E:/project/Ecological_env && python -m pytest tests/test_api_history.py -v`
预期: FAIL，错误信息应显示 "404 Not Found"

- [ ] **Step 3: Write minimal implementation**

创建文件 `backend/api/v1/data/history.py`:

```python
"""历史数据查询API"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from backend.services.data_service import DataService
from backend.models.api import StandardResponse, HistoryQueryRequest

router = APIRouter(tags=["历史数据"])

data_service = DataService()


@router.get("/data/history", response_model=StandardResponse)
async def query_history_data(
    time_range: str = Query(default="24h", description="时间范围（如24h, 7d, 30d）"),
    indicators: Optional[str] = Query(None, description="指标列表（逗号分隔）"),
    aggregation: str = Query(default="raw", description="聚合方式（raw, hourly, daily）"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=50, ge=1, le=100, description="每页数量")
):
    """查询历史监测数据
    
    支持按时间范围、指标、聚合方式查询历史监测数据。
    """
    try:
        data = data_service.query_history_data(
            time_range=time_range,
            indicators=indicators,
            aggregation=aggregation,
            page=page,
            page_size=page_size
        )
        return StandardResponse(
            success=True,
            data=data,
            metadata={
                "total_count": data["total_count"],
                "page": page,
                "page_size": page_size,
                "timestamp": data.get("timestamp")
            }
        )
    except Exception as e:
        return StandardResponse(
            success=False,
            error={
                "code": "HISTORY_QUERY_ERROR",
                "message": str(e)
            }
        )


@router.get("/data/aggregated", response_model=StandardResponse)
async def get_aggregated_data(
    period: str = Query(default="daily", description="统计周期"),
    metrics: str = Query(default="avg,max,min", description="统计指标（逗号分隔）")
):
    """获取聚合统计数据
    
    返回指定时间周期的聚合统计数据，如平均值、最大值、最小值等。
    """
    try:
        data = data_service.get_aggregated_data(period, metrics)
        return StandardResponse(
            success=True,
            data=data
        )
    except Exception as e:
        return StandardResponse(
            success=False,
            error={
                "code": "AGGREGATION_ERROR",
                "message": str(e)
            }
        )
```

- [ ] **Step 4: Run test to verify it passes**

在 `backend/main.py` 中注册路由：

```python
from backend.api.v1.data import history as v1_history

app.include_router(v1_history.router, prefix="/api/v1")
```

运行测试: `cd E:/project/Ecological_env && python -m pytest tests/test_api_history.py -v`
预期: PASS，所有2个测试通过

- [ ] **Step 5: Commit**

```bash
cd E:/project/Ecological_env
git add backend/api/v1/data/history.py backend/main.py tests/test_api_history.py
git commit -m "feat: add history data API endpoints"
```

---

## Task 9: 创建对话历史API端点

**Files:**
- Create: `backend/api/v1/conversations/__init__.py`
- Create: `backend/api/v1/conversations/conversations.py`
- Test: `tests/test_api_conversations.py`

- [ ] **Step 1: Write the failing test**

创建测试文件 `tests/test_api_conversations.py`:

```python
import pytest
from fastapi.testclient import TestClient
from backend.main import app

def test_list_conversations():
    """测试对话列表端点"""
    client = TestClient(app)
    response = client.get("/api/v1/conversations")
    assert response.status_code == 200
    data = response.json()
    assert "success" in data

def test_create_conversation():
    """测试创建对话端点"""
    client = TestClient(app)
    response = client.post("/api/v1/conversations", json={
        "title": "测试对话"
    })
    assert response.status_code == 200

def test_get_conversation_detail():
    """测试获取对话详情端点"""
    client = TestClient(app)
    # 先创建一个对话
    create_response = client.post("/api/v1/conversations", json={
        "title": "测试对话"
    })
    conv_id = create_response.json()["data"]["id"]
    
    # 获取详情
    response = client.get(f"/api/v1/conversations/{conv_id}")
    assert response.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

运行: `cd E:/project/Ecological_env && python -m pytest tests/test_api_conversations.py -v`
预期: FAIL，错误信息应显示 "404 Not Found"

- [ ] **Step 3: Write minimal implementation**

创建文件 `backend/api/v1/conversations/__init__.py`:

```python
"""对话历史API路由"""
```

创建文件 `backend/api/v1/conversations/conversations.py`:

```python
"""对话历史API"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from backend.services.conversation_service import ConversationService
from backend.models.api import (
    StandardResponse, 
    ConversationListResponse, 
    ConversationCreateRequest
)

router = APIRouter(tags=["对话历史"])

conversation_service = ConversationService()


@router.get("/conversations", response_model=StandardResponse)
async def list_conversations(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态过滤")
):
    """获取对话历史列表
    
    返回分页的对话历史列表，支持按状态过滤。
    """
    try:
        result = conversation_service.list_conversations(
            page=page,
            page_size=page_size,
            status=status
        )
        return StandardResponse(
            success=True,
            data=result,
            metadata={
                "total_count": result["total_count"],
                "page": page,
                "page_size": page_size
            }
        )
    except Exception as e:
        return StandardResponse(
            success=False,
            error={
                "code": "CONVERSATION_LIST_ERROR",
                "message": str(e)
            }
        )


@router.post("/conversations", response_model=StandardResponse)
async def create_conversation(request: ConversationCreateRequest):
    """创建新对话
    
    创建一个新的对话记录，用于存储对话历史。
    """
    try:
        result = conversation_service.create_conversation(request)
        return StandardResponse(
            success=True,
            data=result,
            metadata={"timestamp": result.get("started_at")}
        )
    except Exception as e:
        return StandardResponse(
            success=False,
            error={
                "code": "CONVERSATION_CREATE_ERROR",
                "message": str(e)
            }
        )


@router.get("/conversations/{conversation_id}", response_model=StandardResponse)
async def get_conversation(conversation_id: str):
    """获取对话详情
    
    获取指定对话的详细信息，包括所有消息历史。
    """
    try:
        result = conversation_service.get_conversation(conversation_id)
        
        if not result:
            return StandardResponse(
                success=False,
                error={
                    "code": "CONVERSATION_NOT_FOUND",
                    "message": f"对话 {conversation_id} 不存在"
                }
            )
        
        return StandardResponse(
            success=True,
            data=result
        )
    except Exception as e:
        return StandardResponse(
            success=False,
            error={
                "code": "CONVERSATION_GET_ERROR",
                "message": str(e)
            }
        )
```

- [ ] **Step 4: Run test to verify it passes**

在 `backend/main.py` 中注册路由：

```python
from backend.api.v1 import conversations as v1_conversations

app.include_router(v1_conversations.conversations.router, prefix="/api/v1")
```

运行测试: `cd E:/project/Ecological_env && python -m pytest tests/test_api_conversations.py -v`
预期: PASS，所有3个测试通过

- [ ] **Step 5: Commit**

```bash
cd E:/project/Ecological_env
git add backend/api/v1/conversations/ backend/main.py tests/test_api_conversations.py
git commit -m "feat: add conversation history API endpoints"
```

---

## Task 10: 更新配置和错误处理器

**Files:**
- Modify: `backend/core/config.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Update config**

在 `backend/core/config.py` 中添加新配置：

```python
# 在Settings类中添加以下配置

# 缓存配置
CACHE_TTL_REALTIME: int = 30
CACHE_TTL_HISTORY: int = 300
CACHE_TTL_CONVERSATIONS: int = 3600

# 数据源配置
DATA_SOURCE_PATH: str = "./data"
AGENT_SERVICE_SYNC_INTERVAL: int = 300  # 秒

# API配置
API_V1_PREFIX: str = "/api/v1"
```

- [ ] **Step 2: Update main.py error handler**

在 `backend/main.py` 中更新全局异常处理器：

```python
# 替换现有的全局异常处理器
@app.exception_handler(BackendException)
async def backend_exception_handler(request: Request, exc: BackendException):
    """后端异常处理器"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": exc.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
    )
```

在文件顶部添加导入：

```python
from backend.exceptions import BackendException
```

- [ ] **Step 3: Run integration test**

启动后端服务并测试：
```bash
cd E:/project/Ecological_env
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

测试端点：
```bash
curl http://localhost:8000/api/v1/monitoring/realtime
curl http://localhost:8000/api/v1/conversations
```

- [ ] **Step 4: Commit**

```bash
cd E:/project/Ecological_env
git add backend/core/config.py backend/main.py
git commit -m "feat: update config and error handling for v1 API"
```

---

## Task 11: 数据库迁移和初始化

**Files:**
- Create: `alembic/versions/001_add_conversations_tables.py`
- Test: `tests/test_database_migration.py`

- [ ] **Step 1: Create Alembic migration**

创建数据库迁移脚本 `alembic/versions/001_add_conversations_tables.py`:

```python
"""add conversations tables

Revision ID: 001_add_conversations
Create Date: 2026-07-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql, postgresql

# revision identifiers
revision = '001_add_conversations'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 创建 conversations 表
    op.create_table(
        'conversations',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('user_id', sa.String(50), nullable=True),
        sa.Column('title', sa.String(200), nullable=True),
        sa.Column('started_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('ended_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('message_count', sa.Integer(), default=0),
        sa.Column('status', sa.Enum('active', 'completed', 'error', name='conversationstatus'), default='active'),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Index('idx_user_id', 'user_id'),
        sa.Index('idx_status', 'status'),
        sa.Index('idx_started_at', 'started_at')
    )
    
    # 创建 conversation_messages 表
    op.create_table(
        'conversation_messages',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('conversation_id', sa.String(50), sa.ForeignKey('conversations.id', ondelete='CASCADE')),
        sa.Column('role', sa.Enum('user', 'assistant', 'tool', name='messagerole'), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('tool_call_info', sa.JSON(), nullable=True),
        sa.Column('timestamp', sa.TIMESTAMP(), nullable=True),
        sa.Index('idx_conversation_id', 'conversation_id'),
        sa.Index('idx_timestamp', 'timestamp')
    )
    
    # 创建 master_decisions 表
    op.create_table(
        'master_decisions',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('conversation_id', sa.String(50), sa.ForeignKey('conversations.id', ondelete='SET NULL')),
        sa.Column('user_query', sa.Text(), nullable=True),
        sa.Column('intent', sa.String(100), nullable=True),
        sa.Column('decision_path', sa.JSON(), nullable=True),
        sa.Column('subagents_called', sa.JSON(), nullable=True),
        sa.Column('reasoning_summary', sa.TEXT(), nullable=True),
        sa.Column('total_latency_ms', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.TIMESTAMP(), nullable=True),
        sa.Index('idx_conversation_id', 'conversation_id'),
        sa.Index('idx_timestamp', 'timestamp')
    )
    
    # 创建 subagent_calls 表
    op.create_table(
        'subagent_calls',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('conversation_id', sa.String(50), sa.ForeignKey('conversations.id', ondelete='SET NULL')),
        sa.Column('subagent_name', sa.String(50), nullable=True),
        sa.Column('task_description', sa.TEXT(), nullable=True),
        sa.Column('input_params', sa.JSON(), nullable=True),
        sa.Column('output_result', sa.JSON(), nullable=True),
        sa.Column('status', sa.Enum('success', 'error', 'timeout', name='subagentcallstatus'), nullable=True),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.TIMESTAMP(), nullable=True),
        sa.Index('idx_conversation_id', 'conversation_id'),
        sa.Index('idx_subagent_name', 'subagent_name'),
        sa.Index('idx_timestamp', 'timestamp')
    )


def downgrade():
    op.drop_table('subagent_calls')
    op.drop_table('master_decisions')
    op.drop_table('conversation_messages')
    op.drop_table('conversations')
```

- [ ] **Step 2: Run migration**

```bash
cd E:/project/Ecological_env
alembic upgrade head
```

- [ ] **Step 3: Verify tables created**

```bash
cd E:/project/Ecological_env
python -c "
from backend.database.base import engine
from backend.models.conversation import Conversation
print('Tables created successfully')
"
```

- [ ] **Step 4: Commit**

```bash
cd E:/project/Ecological_env
git add alembic/versions/001_add_conversations_tables.py
git commit -m "feat: add database migration for conversation tables"
```

---

## Task 12: 集成测试和文档更新

**Files:**
- Create: `tests/test_integration.py`
- Modify: `docs/api-documentation.md`

- [ ] **Step 1: Write integration test**

创建 `tests/test_integration.py`:

```python
"""集成测试"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.conversation_service import ConversationService

def test_full_conversation_flow():
    """测试完整的对话流程"""
    client = TestClient(app)
    
    # 1. 创建对话
    response = client.post("/api/v1/conversations", json={
        "title": "集成测试对话"
    })
    assert response.status_code == 200
    conv_data = response.json()["data"]
    conv_id = conv_data["id"]
    
    # 2. 获取对话列表
    response = client.get("/api/v1/conversations")
    assert response.status_code == 200
    conv_list = response.json()["data"]["conversations"]
    assert any(c["id"] == conv_id for c in conv_list)
    
    # 3. 获取对话详情
    response = client.get(f"/api/v1/conversations/{conv_id}")
    assert response.status_code == 200
    conv_detail = response.json()["data"]
    assert conv_detail["id"] == conv_id
    
    # 4. 测试实时数据
    response = client.get("/api/v1/monitoring/realtime")
    assert response.status_code == 200
    realtime_data = response.json()["data"]
    assert "influent" in realtime_data
    
    # 5. 测试历史数据
    response = client.get("/api/v1/data/history?time_range=24h")
    assert response.status_code == 200
    history_data = response.json()["data"]
    assert "records" in history_data

def test_api_error_handling():
    """测试API错误处理"""
    client = TestClient(app)
    
    # 测试不存在的对话
    response = client.get("/api/v1/conversations/nonexistent_id")
    assert response.status_code == 200
    assert response.json()["success"] is False
```

- [ ] **Step 2: Run integration tests**

```bash
cd E:/project/Ecological_env && python -m pytest tests/test_integration.py -v
```

- [ ] **Step 3: Create API documentation**

创建 `docs/api-documentation.md`:

```markdown
# 后端API文档 (v1)

## 基础信息

- **Base URL**: `http://localhost:8000`
- **API版本**: v1
- **认证**: 暂无（后续添加）

## 核心端点

### 1. 实时监测数据

#### 获取实时数据
\`\`\`bash
GET /api/v1/monitoring/realtime
\`\`\`

#### 获取数据质量
\`\`\`bash
GET /api/v1/monitoring/quality?time_range=24h
\`\`\`

### 2. 历史数据查询

#### 查询历史数据
\`\`\`bash
GET /api/v1/data/history?time_range=24h&indicators=pH,COD
\`\`\`

#### 获取聚合统计
\`\`\`bash
GET /api/v1/data/aggregated?period=daily&metrics=avg,max
\`\`\`

### 3. 对话历史

#### 获取对话列表
\`\`\`bash
GET /api/v1/conversations?page=1&page_size=20
\`\`\`

#### 创建对话
\`\`\`bash
POST /api/v1/conversations
Content-Type: application/json

{
  "title": "新对话",
  "user_id": "user_123"
}
\`\`\`

#### 获取对话详情
\`\`\`bash
GET /api/v1/conversations/{conversation_id}
\`\`\`

## 响应格式

所有端点返回统一的响应格式：

\`\`\`json
{
  "success": true,
  "data": {...},
  "error": null,
  "metadata": {...}
}
\`\`\`

## 错误码

- `VALIDATION_ERROR`: 参数验证失败
- `DATA_SOURCE_UNAVAILABLE`: 数据源不可用
- `RESOURCE_NOT_FOUND`: 资源不存在
- `EXTERNAL_SERVICE_ERROR`: 外部服务错误
- `DATABASE_ERROR`: 数据库错误
```

- [ ] **Step 4: Final commit**

```bash
cd E:/project/Ecological_env
git add tests/test_integration.py docs/api-documentation.md
git commit -m "test: add integration tests and API documentation"
```

---

## 完成检查清单

在完成所有任务后，请验证：

- [ ] 所有单元测试通过 (`pytest tests/ -v`)
- [ ] 集成测试通过 (`pytest tests/test_integration.py -v`)
- [ ] 数据库表已创建 (`alembic current`)
- [ ] API文档可访问 (`http://localhost:8000/docs`)
- [ ] 所有端点返回标准响应格式
- [ ] 错误处理正常工作
- [ ] 向后兼容（现有端点仍可用）

---

**计划完成时间**: 2026-07-17
**预计工作量**: 2-3周
**Phase**: Phase 1 - 核心数据服务
