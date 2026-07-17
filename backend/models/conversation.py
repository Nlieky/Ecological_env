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
    message_count = Column(Integer, default=0, nullable=False)
    status = Column(SQLEnum(ConversationStatus), default=ConversationStatus.ACTIVE)
    meta_data = Column(JSON, nullable=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.message_count is None:
            self.message_count = 0


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
