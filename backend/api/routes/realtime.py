from fastapi import APIRouter
from backend.models.realtime import PlantData, WaterMetrics
from datetime import datetime

router = APIRouter()

# Mock data: 4x4 grid, only Plant A has data
_mock_plants = {
    "plant_a": PlantData(
        id="plant_a",
        name="Wastewater Plant A",
        status="online",
        metrics=WaterMetrics(
            pH=7.2,
            cod=45.0,
            ammoniaNitrogen=8.5,
            totalNitrogen=15.0,
            totalPhosphorus=0.8,
            flow=120.0
        ),
        metricStatus={
            "pH": "normal",
            "cod": "normal",
            "ammoniaNitrogen": "normal",
            "totalNitrogen": "normal",
            "totalPhosphorus": "normal",
            "flow": "normal"
        },
        lastUpdate=datetime.now().isoformat()
    )
}

@router.get("/realtime/plants")
async def get_all_plants() -> list[PlantData]:
    """Get all plant data (4x4 grid)"""
    plants = []
    for i in range(1, 17):
        if i == 1:
            plants.append(_mock_plants["plant_a"])
        else:
            plants.append(PlantData(
                id=f"plant_{i}",
                name=f"Plant {i}",
                status="offline",
                metrics=None,
                metricStatus=None,
                lastUpdate=datetime.now().isoformat()
            ))
    return plants

@router.get("/realtime/plants/{plant_id}")
async def get_plant(plant_id: str) -> PlantData:
    """Get single plant data"""
    if plant_id in _mock_plants:
        return _mock_plants[plant_id]
    return PlantData(
        id=plant_id,
        name=f"Plant {plant_id}",
        status="offline",
        metrics=None,
        metricStatus=None,
        lastUpdate=datetime.now().isoformat()
    )
