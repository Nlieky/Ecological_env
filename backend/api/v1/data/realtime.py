"""实时监测数据API"""

from fastapi import APIRouter, Query
from typing import Optional

from backend.services.data_service import DataService
from backend.models.monitoring import MonitoringData, DataQualityMetric
from backend.models.api import StandardResponse
from backend.exceptions import DataUnavailableException

router = APIRouter(tags=["实时监测数据"])

data_service = DataService()


@router.get("/monitoring/realtime", response_model=StandardResponse)
async def get_realtime_data():
    """获取实时监测数据

    返回最新的进水、出水监测数据，包括pH、COD、TN、TP等指标。
    """
    try:
        data = data_service.get_realtime_data()
        return StandardResponse(
            success=True,
            data=data,
            metadata={
                "timestamp": data["timestamp"],
                "data_source": "monitoring_system"
            }
        )
    except DataUnavailableException as e:
        return StandardResponse(
            success=False,
            error=e.to_dict()
        )
    except Exception as e:
        return StandardResponse(
            success=False,
            error={
                "code": "DATA_FETCH_ERROR",
                "message": str(e)
            }
        )


@router.get("/monitoring/quality", response_model=StandardResponse)
async def get_data_quality(
    time_range: str = Query(default="24h", description="时间范围")
):
    """获取数据质量指标

    返回数据完整率、缺失数据数量、异常数据数量等质量指标。
    """
    try:
        data = data_service.get_data_quality(time_range)
        return StandardResponse(
            success=True,
            data=data
        )
    except DataUnavailableException as e:
        return StandardResponse(
            success=False,
            error=e.to_dict()
        )
    except Exception as e:
        return StandardResponse(
            success=False,
            error={
                "code": "QUALITY_FETCH_ERROR",
                "message": str(e)
            }
        )
