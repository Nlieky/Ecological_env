from pydantic import BaseModel
from typing import Optional, Dict


class WaterMetrics(BaseModel):
    pH: float
    cod: float
    ammoniaNitrogen: float
    totalNitrogen: float
    totalPhosphorus: float
    flow: float


class MetricStatus(BaseModel):
    status: str  # normal, abnormal, offline


class PlantData(BaseModel):
    id: str
    name: str
    status: str  # online, offline
    metrics: Optional[WaterMetrics] = None
    metricStatus: Optional[Dict[str, str]] = None
    lastUpdate: str
