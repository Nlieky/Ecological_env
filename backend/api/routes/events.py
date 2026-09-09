"""事件中心路由——SQLite 真数据源（alert_events 表）。

全走 EventService（不直查 DB），export 必须定义在 /{event_id} 之前，
否则 "export" 会被当成 event_id 命中详情路由（旧版 404 根因）。
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from backend.models.event import AlertEvent, EventListResponse, EventStatusUpdate
from backend.services.event_service import EventService

router = APIRouter()

event_service = EventService()


@router.get("/events/export")
async def export_events(
    format: str = Query("json", pattern="^(json|xlsx|pdf)$"),
    start_time: str | None = None,
    end_time: str | None = None,
    type: str | None = None,
):
    """导出事件报告（json 全量列表；xlsx/pdf 待实现→501）。"""
    if format != "json":
        return Response(content="xlsx/pdf export not implemented yet", media_type="text/plain", status_code=501)
    result = event_service.list_events(start_time=start_time, end_time=end_time,
                                       type_q=type, page=1, page_size=10000)
    import json
    content = json.dumps(result["data"], ensure_ascii=False, indent=2)
    return Response(content=content, media_type="application/json")


@router.get("/events", response_model=EventListResponse)
async def get_events(
    start_time: str | None = None,
    end_time: str | None = None,
    type: str | None = None,
    plantId: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
):
    """事件列表（分页+筛选，timestamp 倒序）"""
    return event_service.list_events(
        start_time=start_time, end_time=end_time, type_q=type,
        plant_id=plantId, severity=severity, status=status,
        page=page, page_size=pageSize)


@router.get("/events/{event_id}", response_model=AlertEvent)
async def get_event_detail(event_id: str):
    """事件详情"""
    ev = event_service.get_event(event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    return ev


@router.put("/events/{event_id}/status", response_model=AlertEvent)
async def update_event_status(event_id: str, update: EventStatusUpdate):
    """更新事件状态（白名单状态机：pending→processing→resolved/ignored，终态只容许幂等重放）"""
    try:
        ev = event_service.update_status(event_id, update.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    return ev
