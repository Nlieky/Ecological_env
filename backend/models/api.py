"""API请求和响应模型"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


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
