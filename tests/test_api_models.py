"""API模型测试"""

import pytest
from backend.models.api import (
    StandardResponse,
    ConversationListResponse,
    ConversationCreateRequest,
    HistoryQueryRequest,
    RealtimeDataResponse
)
from backend.models.realtime import WaterMetrics


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
        influent=WaterMetrics(
            pH=7.5,
            cod=250.0,
            ammoniaNitrogen=15.0,
            totalNitrogen=25.0,
            totalPhosphorus=3.0,
            flow=100.5
        ),
        effluent=WaterMetrics(
            pH=7.2,
            cod=30.0,
            ammoniaNitrogen=2.0,
            totalNitrogen=10.0,
            totalPhosphorus=0.5,
            flow=100.5
        ),
        flow_rate=100.5,
        quality_score=0.98
    )
    assert response.timestamp == "2026-07-17T10:00:00Z"
    assert response.influent.pH == 7.5
    assert response.influent.cod == 250.0
    assert response.effluent.pH == 7.2
    assert response.effluent.cod == 30.0
    assert response.flow_rate == 100.5
    assert response.quality_score == 0.98


def test_realtime_data_response_timestamp_validation():
    """测试时间戳格式验证"""
    # 有效的 ISO 8601 格式应该通过
    valid_timestamps = [
        "2026-07-17T10:00:00Z",
        "2026-07-17T10:00:00+08:00",
        "2026-07-17T10:00:00-05:00",
        "2026-07-17 10:00:00+00:00",  # Python datetime fromisoformat 支持
    ]
    for ts in valid_timestamps:
        response = RealtimeDataResponse(
            timestamp=ts,
            influent=WaterMetrics(
                pH=7.0, cod=100.0, ammoniaNitrogen=10.0,
                totalNitrogen=20.0, totalPhosphorus=2.0, flow=50.0
            ),
            effluent=WaterMetrics(
                pH=7.0, cod=50.0, ammoniaNitrogen=5.0,
                totalNitrogen=15.0, totalPhosphorus=1.0, flow=50.0
            ),
            flow_rate=50.0,
            quality_score=0.95
        )
        assert response.timestamp == ts

    # 无效的时间戳格式应该抛出异常
    invalid_timestamps = [
        "not-a-timestamp",
        "2026-07-17",  # 缺少时间
        "10:00:00",  # 缺少日期
        "2026-07-17T10:00:00",  # 缺少时区信息（Python fromisoformat 不接受）
    ]
    for ts in invalid_timestamps:
        with pytest.raises(ValueError, match="Invalid timestamp format"):
            RealtimeDataResponse(
                timestamp=ts,
                influent=WaterMetrics(
                    pH=7.0, cod=100.0, ammoniaNitrogen=10.0,
                    totalNitrogen=20.0, totalPhosphorus=2.0, flow=50.0
                ),
                effluent=WaterMetrics(
                    pH=7.0, cod=50.0, ammoniaNitrogen=5.0,
                    totalNitrogen=15.0, totalPhosphorus=1.0, flow=50.0
                ),
                flow_rate=50.0,
                quality_score=0.95
            )


def test_history_query_request_aggregation_validation():
    """测试聚合方式验证"""
    # 有效的聚合方式
    valid_aggregations = ["raw", "hourly", "daily"]
    for agg in valid_aggregations:
        request = HistoryQueryRequest(aggregation=agg)
        assert request.aggregation == agg

    # 无效的聚合方式应该抛出异常
    with pytest.raises(ValueError):
        HistoryQueryRequest(aggregation="invalid")


def test_history_query_request_time_range_validation():
    """测试时间范围验证"""
    # 有效的时间范围
    valid_ranges = ["1h", "6h", "24h", "7d", "30d", "90d"]
    for tr in valid_ranges:
        request = HistoryQueryRequest(time_range=tr)
        assert request.time_range == tr

    # 无效的时间范围应该抛出异常
    with pytest.raises(ValueError):
        HistoryQueryRequest(time_range="invalid")

    with pytest.raises(ValueError):
        HistoryQueryRequest(time_range="48h")  # 不在允许列表中
