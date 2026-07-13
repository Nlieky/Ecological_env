"""
链路追踪 API 接口
提供链路数据查询、数据源管理等功能
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

router = APIRouter()


# ==================== 数据模型 ====================

class TracingDataSource(BaseModel):
    """链路追踪数据源"""
    id: str
    name: str
    provider: str  # jaeger, zipkin, skywalking
    config: Dict[str, Any]
    enabled: bool
    created_at: str
    updated_at: str


class TraceSpan(BaseModel):
    """链路 Span"""
    traceID: str
    spanID: str
    operationName: str
    duration: int  # 微秒
    startTime: int  # Unix 时间戳（微秒）
    tags: Dict[str, str]
    logs: List[Dict[str, Any]]
    processID: str
    references: Optional[List[Dict[str, str]]] = None


class TraceProcess(BaseModel):
    """链路进程信息"""
    serviceName: str
    tags: Optional[Dict[str, str]] = None


class TraceDetail(BaseModel):
    """链路详情"""
    traceID: str
    spans: List[TraceSpan]
    processes: Dict[str, TraceProcess]


class TraceSearchResult(BaseModel):
    """链路搜索结果"""
    traceID: str
    rootSpanName: str
    rootServiceName: str
    startTime: int
    duration: int
    spanCount: int


class CatalogService(BaseModel):
    """目录服务"""
    name: str
    operations: List[str]


class CatalogResponse(BaseModel):
    """目录响应"""
    services: List[CatalogService]


# ==================== 模拟数据 ====================

# 模拟数据源
_mock_data_sources: List[TracingDataSource] = [
    TracingDataSource(
        id="ds-jaeger-001",
        name="Jaeger 本地",
        provider="jaeger",
        config={"url": "http://localhost:16686"},
        enabled=True,
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00"
    )
]

# 模拟目录数据
_mock_catalog = CatalogResponse(
    services=[
        CatalogService(
            name="wastewater-monitor",
            operations=["GET /api/realtime/plants", "POST /api/query", "GET /api/events"]
        ),
        CatalogService(
            name="hermes-agent",
            operations=["process_query", "call_subagent", "execute_operator"]
        ),
        CatalogService(
            name="database",
            operations=["query", "insert", "update"]
        )
    ]
)

# 模拟链路数据
_mock_traces: Dict[str, TraceDetail] = {}


def _generate_mock_traces():
    """生成模拟链路数据"""
    if _mock_traces:
        return

    trace_id = "trace-001"
    now = int(datetime.now().timestamp() * 1000000)

    _mock_traces[trace_id] = TraceDetail(
        traceID=trace_id,
        spans=[
            TraceSpan(
                traceID=trace_id,
                spanID="span-001",
                operationName="GET /api/realtime/plants",
                duration=1500000,  # 1.5s
                startTime=now,
                tags={"http.method": "GET", "http.url": "/api/realtime/plants", "http.status_code": "200"},
                logs=[
                    {
                        "timestamp": now + 100000,
                        "fields": {"event": "query_start", "query": "SELECT * FROM plants"}
                    },
                    {
                        "timestamp": now + 1400000,
                        "fields": {"event": "query_complete", "row_count": "16"}
                    }
                ],
                processID="p1",
                references=[]
            ),
            TraceSpan(
                traceID=trace_id,
                spanID="span-002",
                operationName="database.query",
                duration=1200000,  # 1.2s
                startTime=now + 100000,
                tags={"db.system": "postgresql", "db.name": "ecological"},
                logs=[
                    {
                        "timestamp": now + 200000,
                        "fields": {"event": "execute", "sql": "SELECT * FROM plants"}
                    },
                    {
                        "timestamp": now + 1300000,
                        "fields": {"event": "result", "rows": "16"}
                    }
                ],
                processID="p2",
                references=[{"refType": "CHILD_OF", "traceID": trace_id, "spanID": "span-001"}]
            ),
            TraceSpan(
                traceID=trace_id,
                spanID="span-003",
                operationName="response.serialize",
                duration=100000,  # 0.1s
                startTime=now + 1400000,
                tags={"library": "json"},
                logs=[],
                processID="p1",
                references=[{"refType": "CHILD_OF", "traceID": trace_id, "spanID": "span-001"}]
            )
        ],
        processes={
            "p1": TraceProcess(serviceName="wastewater-monitor", tags={"hostname": "server-01"}),
            "p2": TraceProcess(serviceName="database", tags={"hostname": "db-01"})
        }
    )

    # 生成更多模拟链路
    for i in range(2, 6):
        trace_id = f"trace-{i:03d}"
        start_time = now - i * 10000000

        _mock_traces[trace_id] = TraceDetail(
            traceID=trace_id,
            spans=[
                TraceSpan(
                    traceID=trace_id,
                    spanID=f"span-{i}-001",
                    operationName="POST /api/query",
                    duration=2000000 + i * 500000,
                    startTime=start_time,
                    tags={"http.method": "POST", "http.url": "/api/query"},
                    logs=[
                        {
                            "timestamp": start_time + 100000,
                            "fields": {"event": "query_received", "query": f"查询 {i}"}
                        },
                        {
                            "timestamp": start_time + 1900000,
                            "fields": {"event": "response_sent", "status": "success"}
                        }
                    ],
                    processID=f"p{i}",
                    references=[]
                )
            ],
            processes={
                f"p{i}": TraceProcess(serviceName="wastewater-monitor", tags={"hostname": "server-01"})
            }
        )


# 初始化模拟数据
_generate_mock_traces()


# ==================== API 端点 ====================

@router.get("/observability/tracing/datasources")
async def get_data_sources() -> List[TracingDataSource]:
    """获取链路追踪数据源列表"""
    return _mock_data_sources


@router.post("/observability/tracing/datasources")
async def create_data_source(data: dict) -> TracingDataSource:
    """创建链路追踪数据源"""
    import uuid
    new_source = TracingDataSource(
        id=f"ds-{uuid.uuid4().hex[:8]}",
        name=data.get("name", "新数据源"),
        provider=data.get("provider", "jaeger"),
        config=data.get("config", {}),
        enabled=data.get("enabled", True),
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    _mock_data_sources.append(new_source)
    return new_source


@router.put("/observability/tracing/datasources/{source_id}")
async def update_data_source(source_id: str, data: dict) -> TracingDataSource:
    """更新链路追踪数据源"""
    for source in _mock_data_sources:
        if source.id == source_id:
            source.name = data.get("name", source.name)
            source.provider = data.get("provider", source.provider)
            source.config = data.get("config", source.config)
            source.enabled = data.get("enabled", source.enabled)
            source.updated_at = datetime.now().isoformat()
            return source
    raise HTTPException(status_code=404, detail="数据源不存在")


@router.delete("/observability/tracing/datasources/{source_id}")
async def delete_data_source(source_id: str):
    """删除链路追踪数据源"""
    for i, source in enumerate(_mock_data_sources):
        if source.id == source_id:
            _mock_data_sources.pop(i)
            return {"message": "删除成功"}
    raise HTTPException(status_code=404, detail="数据源不存在")


@router.post("/observability/tracing/datasources/{source_id}/test_connection")
async def test_data_source_connection(source_id: str):
    """测试链路追踪数据源连接"""
    for source in _mock_data_sources:
        if source.id == source_id:
            if not source.enabled:
                raise HTTPException(status_code=400, detail="数据源未启用")
            return {"status": "ok", "message": "连接测试成功", "latency_ms": 15}
    raise HTTPException(status_code=404, detail="数据源不存在")


@router.get("/observability/tracing/catalog")
async def get_catalog(
    service: Optional[str] = None,
    operation: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000)
) -> CatalogResponse:
    """获取链路目录（服务和操作列表）"""
    services = _mock_catalog.services

    # 按服务名过滤
    if service:
        services = [s for s in services if s.name == service]

    # 按操作名过滤
    if operation:
        services = [
            CatalogService(
                name=s.name,
                operations=[op for op in s.operations if operation.lower() in op.lower()]
            )
            for s in services
        ]
        services = [s for s in services if s.operations]

    return CatalogResponse(services=services[:limit])


@router.post("/observability/tracing/search")
async def search_traces(data: dict) -> List[TraceSearchResult]:
    """搜索链路"""
    service = data.get("service")
    operation = data.get("operation")
    min_duration = data.get("durationMin")
    limit = data.get("limit", 20)

    results = []

    for trace in _mock_traces.values():
        # 检查服务名
        if service:
            process = trace.processes.get(trace.spans[0].processID)
            if not process or process.serviceName != service:
                continue

        # 检查操作名
        if operation and operation not in trace.spans[0].operationName:
            continue

        # 检查最小耗时
        if min_duration and trace.spans[0].duration < min_duration:
            continue

        # 找到根 span
        root_span = next((s for s in trace.spans if not s.references), trace.spans[0])
        process = trace.processes.get(root_span.processID)

        results.append(TraceSearchResult(
            traceID=trace.traceID,
            rootSpanName=root_span.operationName,
            rootServiceName=process.serviceName if process else "unknown",
            startTime=root_span.startTime,
            duration=sum(s.duration for s in trace.spans),
            spanCount=len(trace.spans)
        ))

    # 按开始时间降序排序
    results.sort(key=lambda x: x.startTime, reverse=True)

    return results[:limit]


@router.get("/observability/tracing/traces/{trace_id}")
async def get_trace_detail(trace_id: str) -> TraceDetail:
    """获取链路详情"""
    trace = _mock_traces.get(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="链路不存在")
    return trace
