"""API请求和响应模型"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from backend.models.realtime import WaterMetrics


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

    time_range: Literal["1h", "6h", "24h", "7d", "30d", "90d"] = Field(
        default="24h", description="时间范围"
    )
    indicators: Optional[str] = Field(None, description="指标列表（逗号分隔）")
    aggregation: Literal["raw", "hourly", "daily"] = Field(
        default="raw", description="聚合方式"
    )
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=50, ge=1, le=100, description="每页数量")


class RealtimeDataResponse(BaseModel):
    """实时数据响应"""

    timestamp: str = Field(..., description="数据时间戳")
    influent: WaterMetrics = Field(..., description="进水数据")
    effluent: WaterMetrics = Field(..., description="出水数据")
    flow_rate: float = Field(..., description="流量")
    quality_score: float = Field(..., description="数据质量评分")

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp_format(cls, v: str) -> str:
        """验证时间戳为有效的 ISO 8601 格式"""
        if not v:
            raise ValueError("Timestamp cannot be empty")

        # 检查是否包含时区信息（Z或±HH:MM）
        has_tz = v.endswith("Z") or "+" in v or (v.rfind("-") > 10 and v.rfind("-") < len(v) - 3)

        if not has_tz:
            raise ValueError(
                f"Invalid timestamp format: {v}. Expected ISO 8601 format with timezone "
                "(e.g., '2026-07-17T10:00:00Z' or '2026-07-17T10:00:00+08:00')"
            )

        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError as e:
            raise ValueError(
                f"Invalid timestamp format: {v}. Expected ISO 8601 format "
                "(e.g., '2026-07-17T10:00:00Z' or '2026-07-17T10:00:00+08:00')"
            ) from e
        return v
