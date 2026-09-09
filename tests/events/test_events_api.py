# tests/events/test_events_api.py
"""events 路由真数据源测试：分页筛选/详情/状态机/export路由顺序/空表/tz归一化/枚举422。"""
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
    saved_session_local = es.SessionLocal
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
    es.SessionLocal = saved_session_local  # M3: 还原，勿把已 dispose 的引擎泄漏到进程级
    engine.dispose()


def test_list_pagination_and_filters(client):
    r = client.get("/api/events")
    assert r.status_code == 200
    assert r.json()["total"] == 3
    assert client.get("/api/events", params={"severity": "high"}).json()["total"] == 1
    # M2: status 过滤断言锚定原始数据里就是 resolved 的 evt_t002——
    # 不数 total（状态机测试会把 evt_t000 也推到 resolved，测试顺序一换就翻车）
    r_st = client.get("/api/events", params={"status": "resolved"})
    assert r_st.status_code == 200
    assert "evt_t002" in [e["id"] for e in r_st.json()["data"]]
    assert client.get("/api/events", params={"type": "插瓶"}).json()["total"] == 1
    assert client.get("/api/events", params={"plantId": "当阳市金桥污水处理厂一期"}).json()["total"] == 3
    assert client.get("/api/events", params={"plantId": "不存在的厂"}).json()["total"] == 0
    r6 = client.get("/api/events", params={
        "start_time": "2026-09-08T09:00:00", "end_time": "2026-09-08T10:01:00"})
    assert r6.json()["total"] == 2  # 10:00/10:01 在窗内,10:02 出窗
    assert len(client.get("/api/events", params={"page": 2, "pageSize": 2}).json()["data"]) == 1


def test_time_filter_timezone_normalization(client):
    """I2：aware 输入归一化到本地 naive 再比较（存储是 naive 本地时间）。

    前端 toISOString() 产 Z 后缀：本地 2026-09-08 01:00(+08) → "2026-09-07T17:00:00Z"。
    若不归一化（丢 tz 按字面数值比本地），窗口会错 8 小时——此用例在修复前必挂。
    "2026-09-07T17:00:00Z" 与 "2026-09-08T01:00:00+08:00" 等价于本地 2026-09-08 01:00，
    窗 [本地01:00, 本地10:01] 应命中 10:00/10:01 两条、排除 10:02。
    """
    # naive 起点 + naive 终点（基线，原本就过）
    r2 = client.get("/api/events", params={
        "start_time": "2026-09-08T01:00:00", "end_time": "2026-09-08T10:01:00"})
    assert r2.json()["total"] == 2
    # aware 起点(+08) 应等价于本地 01:00：窗内 2 条（未归一化时按字面 01:00 也是 2 条，
    # 但配合下面的 Z 用例可区分归一化与字面直比）
    r3 = client.get("/api/events", params={
        "start_time": "2026-09-08T01:00:00+08:00", "end_time": "2026-09-08T10:01:00"})
    assert r3.json()["total"] == 2
    # Z 后缀起点（前端 toISOString 形态）＝本地 2026-09-08 01:00。若 tz 被
    # 静默丢弃按字面 17:00(前日) 比，start 仍 <= 10:00 会把全部 3 条都算进窗——
    # 断言 ==2 证明归一化到本地后正确排除了 10:02 之外的错窗扩张。
    r4 = client.get("/api/events", params={
        "start_time": "2026-09-07T17:00:00Z", "end_time": "2026-09-08T10:01:00"})
    assert r4.json()["total"] == 2
    # 纯 Z 窗 [本地01:00, 本地02:00] 无事件（若按字面 UTC 比，17:00~18:00 同样无事件，
    # 该条与上条组合锁行为：错窗扩张必须被归一化挡住）
    r5 = client.get("/api/events", params={
        "start_time": "2026-09-07T17:00:00Z", "end_time": "2026-09-07T18:00:00Z"})
    assert r5.json()["total"] == 0
    # end_time 也给 aware：本地 10:01 ＝ 02:01Z，窗内 2 条（未归一化时 end=02:01 字面
    # 会把 10:00/10:01/10:02 全排除 → 0 条，此条必挂于修复前）
    r6 = client.get("/api/events", params={
        "start_time": "2026-09-07T17:00:00Z", "end_time": "2026-09-08T02:01:00Z"})
    assert r6.json()["total"] == 2


def test_invalid_enum_query_returns_422(client):
    """M4：非法 severity/status 由路由 Literal 校验直接 422（不再静默空结果）。"""
    assert client.get("/api/events", params={"severity": "banana"}).status_code == 422
    assert client.get("/api/events", params={"status": "banana"}).status_code == 422
    # 合法值不受影响
    assert client.get("/api/events", params={"severity": "high"}).status_code == 200
    assert client.get("/api/events", params={"status": "pending"}).status_code == 200


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
