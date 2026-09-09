# tests/events/test_events_api.py
"""events 路由真数据源测试：分页筛选/详情/状态机/export路由顺序/空表。"""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    db_dir = tmp_path_factory.mktemp("ev")
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import backend.database.base as base
    import backend.models.alert_event  # noqa: F401
    import backend.models.conversation  # noqa: F401
    import backend.models.logging  # noqa: F401
    import backend.models.agent_config  # noqa: F401
    engine = create_engine(f"sqlite:///{db_dir}/t.db", connect_args={"check_same_thread": False})
    base.Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    import backend.services.event_service as es
    es.SessionLocal = TestSession

    from backend.models.alert_event import AlertEvent, EventSeverity, EventStatus
    s = TestSession()
    for i, (sev, st) in enumerate([("high", "pending"), ("medium", "processing"), ("low", "resolved")]):
        s.add(AlertEvent(
            id=f"evt_t{i:03d}", timestamp=datetime(2026, 9, 8, 10, i, 0),
            session_id=f"session_ev_{i}", conversation_id=None,
            plant_id="当阳市金桥污水处理厂一期",
            violation_types=["插瓶干扰"] if i == 0 else ["稀释排放"],
            severity=EventSeverity(sev), action="立即调查取证" if i == 0 else "现场核查",
            confidence=0.8 + i * 0.05,
            evidence=[{"category": "anomaly", "indicator": "COD", "value": 501.9,
                       "timestamp": "2026-07-14 12:00:00", "score": 0.78,
                       "expected_range": [65.6, 96.2]}],
            work_order={"id": f"WO-{i}"} if i < 2 else None,
            status=EventStatus(st)))
    s.commit()
    s.close()

    from backend.main import app
    yield TestClient(app)
    engine.dispose()


def test_list_pagination_and_filters(client):
    r = client.get("/api/events")
    assert r.status_code == 200
    assert r.json()["total"] == 3
    assert client.get("/api/events", params={"severity": "high"}).json()["total"] == 1
    assert client.get("/api/events", params={"status": "resolved"}).json()["total"] == 1
    assert client.get("/api/events", params={"type": "插瓶"}).json()["total"] == 1
    assert client.get("/api/events", params={"plantId": "当阳市金桥污水处理厂一期"}).json()["total"] == 3
    assert client.get("/api/events", params={"plantId": "不存在的厂"}).json()["total"] == 0
    r6 = client.get("/api/events", params={
        "start_time": "2026-09-08T09:00:00", "end_time": "2026-09-08T10:01:00"})
    assert r6.json()["total"] == 2  # 10:00/10:01 在窗内,10:02 出窗
    assert len(client.get("/api/events", params={"page": 2, "pageSize": 2}).json()["data"]) == 1


def test_detail_and_404(client):
    r = client.get("/api/events/evt_t000")
    assert r.status_code == 200
    d = r.json()
    assert d["plantId"] == "当阳市金桥污水处理厂一期"
    assert d["evidence"][0]["indicator"] == "COD"
    assert d["workOrder"]["id"] == "WO-0"
    assert client.get("/api/events/evt_nope").status_code == 404


def test_status_state_machine(client):
    assert client.put("/api/events/evt_t000/status", json={"status": "processing"}).status_code == 200
    assert client.put("/api/events/evt_t000/status", json={"status": "resolved"}).status_code == 200
    assert client.put("/api/events/evt_t000/status", json={"status": "pending"}).status_code == 400  # 回退
    assert client.put("/api/events/evt_t000/status", json={"status": "resolved"}).status_code == 200  # 幂等重放
    assert client.put("/api/events/evt_t000/status", json={"status": "banana"}).status_code == 400  # 非法值
    assert client.put("/api/events/evt_nope/status", json={"status": "resolved"}).status_code == 404


def test_export_route_before_detail(client):
    r = client.get("/api/events/export")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) == 3


def test_empty_db_empty_state(client, tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import backend.database.base as base
    import backend.models.alert_event  # noqa: F401
    import backend.services.event_service as es
    eng2 = create_engine(f"sqlite:///{tmp_path}/empty.db", connect_args={"check_same_thread": False})
    base.Base.metadata.create_all(bind=eng2)
    S2 = sessionmaker(bind=eng2)
    saved = es.SessionLocal
    es.SessionLocal = S2
    try:
        from backend.main import app as app2
        c2 = TestClient(app2)
        assert c2.get("/api/events").json() == {"data": [], "total": 0}
    finally:
        es.SessionLocal = saved
        eng2.dispose()
