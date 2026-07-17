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
