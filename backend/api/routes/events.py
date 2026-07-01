from fastapi import APIRouter, Query
from typing import Optional
from backend.models.event import AlertEvent, EventListResponse, EventEvidence, EventStatusUpdate
from datetime import datetime, timedelta

router = APIRouter()

# Mock event data
_mock_events: list[AlertEvent] = [
    AlertEvent(
        id="evt_001",
        timestamp=(datetime.now() - timedelta(minutes=30)).isoformat(),
        type="cod_high",
        plantId="plant_a",
        severity="high",
        status="pending",
        evidence=EventEvidence(
            dataSnapshot={"cod": 125.0, "pH": 7.2, "ammoniaNitrogen": 8.5},
            operators=[
                {"name": "statistical.trend_detector", "result": "Upward trend detected"},
                {"name": "ml.isolation_forest", "result": {"confidence": 0.92}}
            ],
            rules=[
                {"name": "pH-COD协同规则", "matched": False},
                {"name": "违规模式", "matched": True}
            ],
            llmReasoning="Master agent decision: Multi-dimensional data perception -> Anomaly detection -> Rule reasoning\nConclusion: Data supports COD excessive discharge violation determination"
        )
    ),
    AlertEvent(
        id="evt_002",
        timestamp=(datetime.now() - timedelta(hours=2)).isoformat(),
        type="ph_abnormal",
        plantId="plant_a",
        severity="medium",
        status="processing",
        evidence=EventEvidence(
            dataSnapshot={"pH": 5.5, "cod": 42.0},
            operators=[{"name": "statistical.threshold_check", "result": "pH below lower limit"}],
            rules=[{"name": "pH threshold rule", "matched": True}],
            llmReasoning="pH value below normal range, needs attention"
        )
    ),
    AlertEvent(
        id="evt_003",
        timestamp=(datetime.now() - timedelta(days=1)).isoformat(),
        type="flow_abnormal",
        plantId="plant_a",
        severity="low",
        status="resolved",
        evidence=EventEvidence(
            dataSnapshot={"flow": 0.0},
            operators=[{"name": "connectivity_check", "result": "Sensor offline"}],
            rules=[{"name": "Connectivity rule", "matched": True}],
            llmReasoning="Flow sensor abnormal, maintenance scheduled"
        )
    )
]

@router.get("/events", response_model=EventListResponse)
async def get_events(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    type: Optional[str] = None,
    plantId: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100)
):
    """Get event list"""
    filtered = _mock_events.copy()

    # Apply filters
    if type:
        filtered = [e for e in filtered if e.type == type]
    if plantId:
        filtered = [e for e in filtered if e.plantId == plantId]
    if severity:
        filtered = [e for e in filtered if e.severity == severity]
    if status:
        filtered = [e for e in filtered if e.status == status]

    total = len(filtered)
    start = (page - 1) * pageSize
    end = start + pageSize
    paged = filtered[start:end]

    return EventListResponse(data=paged, total=total)


@router.get("/events/{event_id}", response_model=AlertEvent)
async def get_event_detail(event_id: str):
    """Get event detail"""
    for event in _mock_events:
        if event.id == event_id:
            return event
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Event not found")


@router.put("/events/{event_id}/status", response_model=AlertEvent)
async def update_event_status(event_id: str, update: EventStatusUpdate):
    """Update event status"""
    for event in _mock_events:
        if event.id == event_id:
            event.status = update.status
            return event
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Event not found")


@router.get("/events/export")
async def export_events(
    format: str = Query("json", regex="^(json|xlsx|pdf)$"),
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    type: Optional[str] = None
):
    """Export event report"""
    from fastapi.responses import Response
    if format == "json":
        import json
        content = json.dumps([e.dict() for e in _mock_events], ensure_ascii=False, indent=2)
        return Response(content=content, media_type="application/json")
    else:
        # xlsx/pdf coming soon
        return Response(content="Export feature coming soon", media_type="text/plain")
