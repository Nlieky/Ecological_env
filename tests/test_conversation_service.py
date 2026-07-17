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


def test_get_conversation_not_found():
    """测试获取不存在的对话"""
    service = ConversationService()
    result = service.get_conversation("nonexistent_id")
    assert result is None


def test_list_conversations():
    """测试列出对话"""
    service = ConversationService()

    # 创建多个对话
    for i in range(3):
        request = ConversationCreateRequest(title=f"测试对话{i}")
        service.create_conversation(request)

    # 列出对话
    result = service.list_conversations(page=1, page_size=10)
    assert "conversations" in result
    assert "total_count" in result
    assert len(result["conversations"]) >= 3
    assert result["total_count"] >= 3


def test_list_conversations_with_status_filter():
    """测试带状态过滤的对话列表"""
    service = ConversationService()

    # 创建一个对话
    request = ConversationCreateRequest(title="测试对话")
    created = service.create_conversation(request)

    # 按状态过滤
    result = service.list_conversations(status="active")
    assert "conversations" in result
    # 验证所有返回的对话都是 active 状态
    for conv in result["conversations"]:
        assert conv["status"] == "active"


def test_add_message():
    """测试添加消息"""
    service = ConversationService()

    # 先创建一个对话
    create_request = ConversationCreateRequest(title="测试对话")
    created = service.create_conversation(create_request)

    # 添加消息
    result = service.add_message(
        conversation_id=created["id"],
        role="user",
        content="你好，这是一条测试消息"
    )

    assert "id" in result
    assert "timestamp" in result
    assert result["id"].startswith("msg_")


def test_add_message_increments_count():
    """测试添加消息会增加消息计数"""
    service = ConversationService()

    # 先创建一个对话
    create_request = ConversationCreateRequest(title="测试对话")
    created = service.create_conversation(create_request)

    # 获取初始消息数
    conversation = service.get_conversation(created["id"])
    initial_count = conversation["message_count"]

    # 添加消息
    service.add_message(
        conversation_id=created["id"],
        role="user",
        content="测试消息"
    )

    # 验证消息计数增加
    updated = service.get_conversation(created["id"])
    assert updated["message_count"] == initial_count + 1


def test_add_message_to_nonexistent_conversation():
    """测试向不存在的对话添加消息"""
    service = ConversationService()

    with pytest.raises(ValueError, match="对话不存在"):
        service.add_message(
            conversation_id="nonexistent_id",
            role="user",
            content="测试消息"
        )
