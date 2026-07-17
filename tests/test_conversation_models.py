"""测试对话相关的数据模型"""

import pytest
from datetime import datetime
from backend.database.base import engine, Base
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
