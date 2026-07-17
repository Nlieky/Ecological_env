"""API模型测试"""

import pytest
from backend.models.api import (
    StandardResponse,
    ConversationListResponse,
    ConversationCreateRequest,
    HistoryQueryRequest,
    RealtimeDataResponse
)


def test_standard_response():
    """测试标准响应模型"""
    response = StandardResponse(
        success=True,
        data={"test": "data"}
    )
    assert response.success is True
    assert response.data == {"test": "data"}
    assert response.error is None
    assert response.metadata is None


def test_standard_response_with_error():
    """测试带错误信息的标准响应"""
    response = StandardResponse(
        success=False,
        error={"code": "ERROR", "message": "Test error"}
    )
    assert response.success is False
    assert response.error == {"code": "ERROR", "message": "Test error"}
    assert response.data is None


def test_standard_response_with_metadata():
    """测试带元数据的标准响应"""
    response = StandardResponse(
        success=True,
        data={"result": "success"},
        metadata={"page": 1, "total": 100}
    )
    assert response.success is True
    assert response.metadata == {"page": 1, "total": 100}


def test_conversation_create_request():
    """测试对话创建请求模型"""
    request = ConversationCreateRequest(
        user_id="test_user",
        title="测试对话"
    )
    assert request.user_id == "test_user"
    assert request.title == "测试对话"


def test_conversation_create_request_optional():
    """测试可选字段的对话创建请求"""
    request = ConversationCreateRequest()
    assert request.user_id is None
    assert request.title is None


def test_conversation_list_response():
    """测试对话列表响应模型"""
    response = ConversationListResponse(
        conversations=[
            {"id": "1", "title": "对话1"},
            {"id": "2", "title": "对话2"}
        ],
        total_count=2,
        page=1
    )
    assert len(response.conversations) == 2
    assert response.total_count == 2
    assert response.page == 1


def test_history_query_request_defaults():
    """测试历史查询请求的默认值"""
    request = HistoryQueryRequest()
    assert request.time_range == "24h"
    assert request.indicators is None
    assert request.aggregation == "raw"
    assert request.page == 1
    assert request.page_size == 50


def test_history_query_request_custom():
    """测试自定义历史查询请求"""
    request = HistoryQueryRequest(
        time_range="7d",
        indicators="pH,COD,TN",
        aggregation="hourly",
        page=2,
        page_size=20
    )
    assert request.time_range == "7d"
    assert request.indicators == "pH,COD,TN"
    assert request.aggregation == "hourly"
    assert request.page == 2
    assert request.page_size == 20


def test_history_query_request_validation():
    """测试历史查询请求的验证"""
    # 页码必须 >= 1
    with pytest.raises(ValueError):
        HistoryQueryRequest(page=0)

    # 页码必须 >= 1
    with pytest.raises(ValueError):
        HistoryQueryRequest(page=-1)

    # page_size 必须 <= 100
    with pytest.raises(ValueError):
        HistoryQueryRequest(page_size=101)


def test_realtime_data_response():
    """测试实时数据响应模型"""
    response = RealtimeDataResponse(
        timestamp="2026-07-17T10:00:00Z",
        influent={"pH": 7.5, "COD": 250.0},
        effluent={"pH": 7.2, "COD": 30.0},
        flow_rate=100.5,
        quality_score=0.98
    )
    assert response.timestamp == "2026-07-17T10:00:00Z"
    assert response.influent == {"pH": 7.5, "COD": 250.0}
    assert response.effluent == {"pH": 7.2, "COD": 30.0}
    assert response.flow_rate == 100.5
    assert response.quality_score == 0.98
