"""对话服务层测试"""

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
