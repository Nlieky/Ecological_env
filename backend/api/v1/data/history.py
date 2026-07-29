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
    page_size: int = Query(default=50, ge=1, le=500, description="每页数量")
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
