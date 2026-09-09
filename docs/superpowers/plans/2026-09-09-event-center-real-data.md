# 事件中心真实化（子项目 2/4）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 处置子智能体的研判结果（disposition_result.json）→ alert_events 表 → /api/events 真数据 → 前端事件中心/告警中心，替换 3 条内存 mock；顺手修三个既有 bug。

**Architecture:** backend 落库 conversations 的同一位置调采集器（EventService.collect_from_session）扫 session 目录入库；events 路由换 SQLite 数据源（签名不变）；agent 服务的 done 事件补 session_dir 字段供采集器定位目录。前端仅改 EventCenterView 详情抽屉（真证据结构渲染）+ store 参数 bug。

**Tech Stack:** SQLAlchemy（现有 ecological_logs.db）/ FastAPI / Vue3 + Element Plus / pytest + Vitest

**Spec:** `docs/superpowers/specs/2026-09-09-event-center-real-data-design.md`

---

## 工程约定（执行前必读）

- Python 一律 venv 全路径 `$PY` = `/e/project/Ecological_env/ecological_env/Scripts/python.exe`（Windows Git Bash）。裸 python 禁用。
- pytest：`$PY -m pytest tests/events/ -v`（项目根跑；pythonpath 已配）。
- 前端：`cd frontend && npm test`；type-check `npx vue-tsc --noEmit`（存量 3 错在 ChatMessage/GrafanaView，别碰）。
- backend :8000 运行中（无 --reload）——验证用临时端口起独立实例（`$PY -m uvicorn backend.main:app --port 8021`），验完 kill；或 curl 现端口验证已注册路由时注意新路由要重启才生效。
- 提交：中文消息 + `feat(events)/fix(events)/test(events)` 前缀 + 结尾 `Co-Authored-By: Claude <noreply@anthropic.com>`。
- 真实参照文件：sessions/session_20260806_092743_b373f6/（含 disposition_result.json/anomaly_result.json/rule_reasoning_result.json/task.json 全套）。

## 关键背景事实（实现者必读）

1. **session 目录 ≠ session_id**：目录名是 `session_<YYYYmmdd_HHMMSS>_<hex6>`（start_agent.py `_fresh_session_dir`），done 事件只带 session_id（如 `s_20260908_...`）。采集器要拿到目录路径，需 agent 服务 done 事件补 `session_dir` 字段（本计划 Task 1 做）。
2. **disposition_result.json 形状**：`{task_id, status, result: {suspicion_level(high|medium|low|none), suspicion_level_cn, violation_types[], action, confidence, work_order|null, report|null, evidence_points[]}, metadata: {subagent, timestamp, anomaly_task_id, violation_task_id}}`。evidence_points 两类：`category=anomaly`（indicator/timestamp/value/score/expected_range）与 `category=expert_pattern`（pattern/pattern_key/match_score/confidence/suspicion_level）。
3. **query.py 两个落库点**：非流式 :160、流式 :325（`conversation_service.record_exchange`），采集器挂这两处之后。
4. **建表惯例**：参照 backend/models/conversation.py（Base/字符串主键/SQLEnum/JSON 列）；新模型要加进 backend/database/init_db.py 的 import 清单才会 create_all。
5. **mock 路由现状**：backend/api/routes/events.py 全内存；`/events/export` 注册在 `/{event_id}` 后（404 根因）；PUT status 无校验。
6. **run_disposition bug**：末尾打印 `output["result"]["alert"]` 但该键不存在，成功存盘后 KeyError。
7. **前端类型**：frontend/src/api/types/api.types.ts:148-167 的 AlertEvent（severity low|medium|high、status 四态、evidence? 可选）；EventCenterView 详情抽屉现在渲染 dataSnapshot/operators/rules。

---

### Task 1: alert_events 表 + 采集器 + done 事件补 session_dir

**Files:**
- Create: `backend/models/alert_event.py`
- Create: `backend/services/event_service.py`
- Modify: `backend/database/init_db.py`（import 清单加 AlertEvent）
- Modify: `scripts/start_agent.py`（done 事件两处 q.put 补 `session_dir`）
- Test: `tests/events/test_event_service.py`

- [ ] **Step 1: 写失败的采集器测试**

```python
# tests/events/test_event_service.py
"""事件采集器测试：各等级入库/none 不入/幂等/损坏文件/厂名解析。"""
import json
from pathlib import Path

import pytest

from backend.services.event_service import EventService, _parse_plant_id


@pytest.fixture
def svc(tmp_path, monkeypatch):
    """采集器指向临时 sessions 根 + 临时库。"""
    # 库隔离：让 SessionLocal 指向临时文件
    import backend.database.base as base
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(f"sqlite:///{tmp_path}/test.db", connect_args={"check_same_thread": False})
    base.Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    import backend.services.event_service as es
    monkeypatch.setattr(es, "SessionLocal", TestSession)
    s = EventService(sessions_root=tmp_path)
    yield s
    engine.dispose()


def make_session(root: Path, name: str, level: str, plant: str = "当阳市金桥污水处理厂一期"):
    sd = root / name
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "disposition_result.json").write_text(json.dumps({
        "task_id": f"task_{name}", "status": "completed",
        "result": {
            "suspicion_level": level,
            "suspicion_level_cn": {"high": "高风险", "medium": "中风险",
                                    "low": "低风险", "none": "无违规"}[level],
            "violation_types": ["插瓶干扰"],
            "action": "立即调查取证" if level == "high" else "现场核查",
            "confidence": 0.85,
            "work_order": {"id": "WO-1"} if level != "none" else None,
            "report": None,
            "evidence_points": [
                {"category": "anomaly", "indicator": "COD", "value": 501.9,
                 "timestamp": "2026-07-14 12:00:00", "score": 0.78, "expected_range": [65.6, 96.2]},
                {"category": "expert_pattern", "pattern": "插瓶干扰", "pattern_key": "bottle_interference",
                 "match_score": 0.9, "confidence": 0.95, "suspicion_level": "critical"},
            ],
        },
        "metadata": {"subagent": "disposition-execution-agent",
                     "timestamp": "2026-08-06T09:27:55.824856"},
    }, ensure_ascii=False), encoding="utf-8")
    (sd / "task.json").write_text(json.dumps({
        "task_id": f"task_{name}", "task": f"查询{plant}最近24小时数据并研判",
        "context": "", "output_format": "json", "timeout": 300,
    }, ensure_ascii=False), encoding="utf-8")
    return sd


def test_collect_high_medium_low_in_none_skipped(svc, tmp_path):
    for lvl in ("high", "medium", "low", "none"):
        make_session(tmp_path, f"session_t1_{lvl}", lvl)
    got = []
    for lvl in ("high", "medium", "low", "none"):
        r = svc.collect_from_session(f"session_t1_{lvl}")
        got.append(r is not None)
    assert got == [True, True, True, False]  # none 不入


def test_collect_idempotent(svc, tmp_path):
    make_session(tmp_path, "session_t2", "high")
    assert svc.collect_from_session("session_t2") is not None
    assert svc.collect_from_session("session_t2") is None  # 二次采集幂等跳过


def test_missing_and_corrupt_files_silent(svc, tmp_path):
    assert svc.collect_from_session("session_not_exist") is None
    bad = tmp_path / "session_bad"
    bad.mkdir()
    (bad / "disposition_result.json").write_text("{not json", encoding="utf-8")
    assert svc.collect_from_session("session_bad") is None


def test_plant_id_parsed_from_task(svc, tmp_path):
    make_session(tmp_path, "session_t3", "medium")
    ev = svc.collect_from_session("session_t3")
    assert ev["plant_id"] == "当阳市金桥污水处理厂一期"


def test_plant_id_alias(svc, tmp_path):
    sd = make_session(tmp_path, "session_t4", "low", plant="金桥")
    ev = svc.collect_from_session("session_t4")
    assert ev["plant_id"] == "当阳市金桥污水处理厂一期"  # 别名经 plant_aliases 归一


def test_parse_plant_id_unknown():
    assert _parse_plant_id("今天天气怎么样") == "unknown"


def test_incomplete_status_skipped(svc, tmp_path):
    sd = make_session(tmp_path, "session_t5", "high")
    d = json.loads((sd / "disposition_result.json").read_text(encoding="utf-8"))
    d["status"] = "failed"
    (sd / "disposition_result.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    assert svc.collect_from_session("session_t5") is None
```

- [ ] **Step 2: 跑测试确认失败**

`$PY -m pytest tests/events/test_event_service.py -v` → ModuleNotFoundError: backend.services.event_service

- [ ] **Step 3: 实现模型 + 采集器**

`backend/models/alert_event.py`（遵循 conversation.py 惯例）：

```python
"""预警事件表——处置子智能体研判结果的采集落地（事件中心/告警中心真数据源）。"""
import enum
from sqlalchemy import Column, String, TIMESTAMP, Float, JSON, Enum as SQLEnum

from backend.database.base import Base


class EventSeverity(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class EventStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    resolved = "resolved"
    ignored = "ignored"


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id = Column(String(50), primary_key=True)                # evt_<uuid12>
    timestamp = Column(TIMESTAMP, nullable=False)            # 研判完成时刻
    session_id = Column(String(64), unique=True, index=True) # 溯源+幂等键
    conversation_id = Column(String(50), nullable=True)
    plant_id = Column(String(100), nullable=False, default="unknown")
    violation_types = Column(JSON, default=list)             # ["插瓶干扰", ...]
    severity = Column(SQLEnum(EventSeverity), nullable=False)
    action = Column(String(100), default="")
    confidence = Column(Float, nullable=True)
    evidence = Column(JSON, default=list)                    # evidence_points 原文
    work_order = Column(JSON, nullable=True)
    status = Column(SQLEnum(EventStatus), default=EventStatus.pending, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False)
    updated_at = Column(TIMESTAMP, nullable=False)
```

`backend/services/event_service.py`（采集器 + 查询/状态服务，本任务先做采集部分，查询方法 Task 2 补）：

```python
"""事件服务：从 session 目录采集处置研判结果入库 + 事件查询/状态流转。

采集时机：backend 落库 conversations 的同一位置（query.py 两个 record_exchange
之后）调用 collect_from_session——与对话持久化同链路，agent 服务仅 done 事件
多带 session_dir 字段。幂等靠 session_id 唯一索引（同会话多轮研判以最后一轮
目录为准：重复采集直接跳过，不更新旧事件——简单可预期）。
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from backend.database.session import SessionLocal
from backend.models.alert_event import AlertEvent, EventSeverity

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SEVERITY_CN = {"high": "高风险", "medium": "中风险", "low": "低风险"}

# 厂名解析：层级 yaml 全部厂全称 + 别名表（别名→全称归一）
def _plant_lookup() -> tuple[set[str], dict[str, str]]:
    import yaml
    hp = _PROJECT_ROOT / "shared" / "data" / "plant-hierarchy.yaml"
    try:
        data = yaml.safe_load(hp.read_text(encoding="utf-8")) or {}
    except Exception:
        return set(), {}
    plants, aliases = set(), {}
    for city, districts in data.items():
        if not isinstance(districts, dict):
            continue
        for _district, plist in districts.items():
            if isinstance(plist, list):
                plants.update(plist)
    for alias, full in (data.get("plant_aliases") or {}).items():
        aliases[alias] = full
        plants.add(full)
    return plants, aliases


def _parse_plant_id(text: str) -> str:
    """从 task 文本解析厂全称：先全称包含匹配（取最长），再别名表。"""
    if not text:
        return "unknown"
    plants, aliases = _plant_lookup()
    hits = [p for p in plants if p in text]
    if hits:
        return max(hits, key=len)  # 最长命中防子串
    for alias, full in sorted(aliases.items(), key=lambda x: -len(x[0])):
        if alias in text:
            return full
    return "unknown"


def _parse_ts(s: str) -> datetime:
    """ISO 字符串→datetime（失败回退当前时刻）。"""
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return datetime.now()


class EventService:
    def __init__(self, sessions_root: Optional[Path] = None):
        self.sessions_root = Path(sessions_root) if sessions_root else _PROJECT_ROOT / "sessions"

    # ---------- 采集 ----------
    def collect_from_session(self, session_dir_name: str,
                             conversation_id: Optional[str] = None) -> Optional[dict]:
        """读 <sessions_root>/<session_dir_name>/disposition_result.json 入库。

        入库条件：status=completed 且 suspicion_level != none。
        幂等：session 已有事件 → 跳过返回 None。
        文件缺失/损坏 → None（静默，debug 日志）。
        """
        f = self.sessions_root / session_dir_name / "disposition_result.json"
        if not f.exists():
            return None
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[events] disposition_result 解析失败({session_dir_name}): {e}")
            return None
        result = data.get("result") or {}
        if data.get("status") != "completed":
            return None
        level = result.get("suspicion_level")
        if level not in _SEVERITY_CN:
            return None  # none / 未知等级不入

        db: Session = SessionLocal()
        try:
            exists = db.query(AlertEvent).filter(
                AlertEvent.session_id == session_dir_name).first()
            if exists:
                return None
            task_text = ""
            tj = self.sessions_root / session_dir_name / "task.json"
            if tj.exists():
                try:
                    task_text = (json.loads(tj.read_text(encoding="utf-8"))
                                 .get("task", ""))
                except Exception:
                    pass
            ev = AlertEvent(
                id=f"evt_{uuid.uuid4().hex[:12]}",
                timestamp=_parse_ts((data.get("metadata") or {}).get("timestamp", "")),
                session_id=session_dir_name,
                conversation_id=conversation_id,
                plant_id=_parse_plant_id(task_text),
                violation_types=result.get("violation_types") or [],
                severity=EventSeverity(level),
                action=result.get("action", ""),
                confidence=result.get("confidence"),
                evidence=result.get("evidence_points") or [],
                work_order=result.get("work_order"),
                status="pending",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db.add(ev)
            db.commit()
            return self._to_dict(ev)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _to_dict(ev: AlertEvent) -> dict:
        return {
            "id": ev.id,
            "timestamp": ev.timestamp.isoformat() if ev.timestamp else "",
            "sessionId": ev.session_id,
            "conversationId": ev.conversation_id,
            "plantId": ev.plant_id,
            "violationTypes": ev.violation_types or [],
            "severity": ev.severity.value if ev.severity else "low",
            "action": ev.action or "",
            "confidence": ev.confidence,
            "evidence": ev.evidence or [],
            "workOrder": ev.work_order,
            "status": ev.status.value if ev.status else "pending",
            "createdAt": ev.created_at.isoformat() if ev.created_at else "",
            "updatedAt": ev.updated_at.isoformat() if ev.updated_at else "",
        }
```

注意：
- `status="pending"` 传字符串给 SQLEnum 列 SQLAlchemy 会自动转（str enum）；若报错改 `EventStatus.pending`。
- monkeypatch 测试替换的是模块级 `SessionLocal` 引用——event_service.py 里**必须**以 `SessionLocal()` 模块级引用调用（如上），不能 from-import 成本地名。

`backend/database/init_db.py`：import 清单加 `from backend.models.alert_event import AlertEvent  # noqa: F401`。

- [ ] **Step 4: agent 服务 done 事件补 session_dir**

`scripts/start_agent.py` 两处 `q.put({"type": "done", ...})`（:623 与 :667 附近）与非流式 response dict（:403 附近）：各补 `"session_dir": <本轮目录名>`。目录名获取：`self._session_dirs.get(session_id)` 的 `Path(...).name`。具体：
- 非流式 `process_query` 的 response dict：`"session_dir": Path(self._session_dirs.get(session_id, "")).name if session_id in self._session_dirs else None`
- 流式两处 q.put done：同上（封装一个小 helper `_cur_session_dir(session_id)` 返回目录名字符串或 None）。
- backend `query.py` 透传时非流式把 `resp_json.get("session_dir")` 取出、流式解析 done 事件的 `evt.get("session_dir")`——本任务先只在 agent 侧补字段 + query.py **暂存不消费**（Task 2 接线采集器时用）。为避免 Task 2 无字段可用，本步骤在 query.py 两个落库点各加一行注释占位：`# TODO(Task2): event_service.collect_from_session(session_dir, conversation_id)`。

- [ ] **Step 5: 跑测试确认通过**

`$PY -m pytest tests/events/test_event_service.py -v` → 8 个 PASS。
`$PY -m pytest tests/ -q` → 无回归（events 8 + knowledge_graph 32 + 其他）。

- [ ] **Step 6: 建表验证 + 提交**

```bash
$PY backend/database/init_db.py   # 输出表清单应含 alert_events
$PY -c "import sqlite3; c=sqlite3.connect('shared/data/ecological_logs.db'); print([r for r in c.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='alert_events'\")])"
git add backend/models/alert_event.py backend/services/event_service.py backend/database/init_db.py scripts/start_agent.py tests/events/test_event_service.py
git commit -m "feat(events): alert_events表+采集器(非none入库/幂等/厂名别名解析)+done事件补session_dir"
```

---

### Task 2: events 路由换真数据源 + 状态机 + 采集接线

**Files:**
- Modify: `backend/api/routes/events.py`（整文件重写）
- Modify: `backend/models/event.py`（Pydantic 改真结构）
- Modify: `backend/api/routes/query.py`（两处落库点接采集器）
- Test: `tests/events/test_events_api.py`

- [ ] **Step 1: 写失败的 API 测试**

```python
# tests/events/test_events_api.py
"""events 路由真数据源测试：分页筛选/详情/状态机/export路由顺序/空表。"""
import json
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    db_dir = tmp_path_factory.mktemp("ev")
    # 独立引擎 + 建表
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import backend.database.base as base
    import backend.models.alert_event  # noqa: F401 确保模型注册
    engine = create_engine(f"sqlite:///{db_dir}/t.db", connect_args={"check_same_thread": False})
    base.Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    import backend.services.event_service as es
    es.SessionLocal = TestSession
    import backend.api.routes.events as ev_routes
    ev_routes.SessionLocal = TestSession  # 路由直查也走它（若路由经 service 则只改 service）

    # 造 3 条不同等级/状态的事件
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
            status=EventStatus(st), created_at=datetime.now(), updated_at=datetime.now()))
    s.commit(); s.close()

    from backend.main import app
    yield TestClient(app)
    engine.dispose()


def test_list_pagination_and_filters(client):
    r = client.get("/api/events")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    ids = [e["id"] for e in body["data"]]
    assert len(ids) == 3
    # severity 过滤
    r2 = client.get("/api/events", params={"severity": "high"})
    assert r2.json()["total"] == 1
    assert r2.json()["data"][0]["severity"] == "high"
    # status 过滤
    r3 = client.get("/api/events", params={"status": "resolved"})
    assert r3.json()["total"] == 1
    # violation_types 模糊（type 参数）
    r4 = client.get("/api/events", params={"type": "插瓶"})
    assert r4.json()["total"] == 1
    # plantId 过滤
    r5 = client.get("/api/events", params={"plantId": "当阳市金桥污水处理厂一期"})
    assert r5.json()["total"] == 3
    # 时间窗（真正实现）
    r6 = client.get("/api/events", params={
        "start_time": "2026-09-08T09:00:00", "end_time": "2026-09-08T10:01:00"})
    assert r6.json()["total"] == 2  # 10:00/10:01 两条在窗内
    # 分页
    r7 = client.get("/api/events", params={"page": 2, "pageSize": 2})
    assert len(r7.json()["data"]) == 1


def test_detail_and_404(client):
    r = client.get("/api/events/evt_t000")
    assert r.status_code == 200
    d = r.json()
    assert d["plantId"] == "当阳市金桥污水处理厂一期"
    assert d["evidence"][0]["indicator"] == "COD"
    assert d["workOrder"]["id"] == "WO-0"
    assert client.get("/api/events/evt_nope").status_code == 404


def test_status_state_machine(client):
    # pending → processing 合法
    assert client.put("/api/events/evt_t000/status", json={"status": "processing"}).status_code == 200
    # processing → resolved 合法
    assert client.put("/api/events/evt_t000/status", json={"status": "resolved"}).status_code == 200
    # resolved → pending 回退 400
    r = client.put("/api/events/evt_t000/status", json={"status": "pending"})
    assert r.status_code == 400
    # 同状态幂等重放 200
    assert client.put("/api/events/evt_t000/status", json={"status": "resolved"}).status_code == 200
    # 非法目标值 400
    assert client.put("/api/events/evt_t000/status", json={"status": "banana"}).status_code == 400
    # 恢复 evt_t000 供后续测试
    from backend.models.alert_event import EventStatus
    # （module fixture 内数据共享，改回 processing→resolved 流转已完成，无需恢复）


def test_export_route_before_detail(client):
    """export 不再被 /{event_id} 吞掉。"""
    r = client.get("/api/events/export")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) == 3


def test_empty_db_empty_state(client, tmp_path):
    """空表返回空态（用独立空库实例）。"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import backend.database.base as base
    import backend.models.alert_event  # noqa: F401
    import backend.services.event_service as es
    import backend.api.routes.events as ev_routes
    eng2 = create_engine(f"sqlite:///{tmp_path}/empty.db", connect_args={"check_same_thread": False})
    base.Base.metadata.create_all(bind=eng2)
    S2 = sessionmaker(bind=eng2)
    saved_s, saved_r = es.SessionLocal, ev_routes.SessionLocal
    es.SessionLocal = ev_routes.SessionLocal = S2
    try:
        c2 = TestClient(__import__("backend.main", fromlist=["app"]).app)
        r = c2.get("/api/events")
        assert r.json() == {"data": [], "total": 0}
    finally:
        es.SessionLocal, ev_routes.SessionLocal = saved_s, saved_r
        eng2.dispose()
```

- [ ] **Step 2: 跑测试确认失败**（现 mock 路由不读库、无状态机——多数断言会挂）

- [ ] **Step 3: 重写 `backend/models/event.py`（Pydantic 真结构）**

```python
"""事件 API schema（真数据源版）——对齐 alert_events 表与处置输出结构。"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class IndicatorAnomaly(BaseModel):
    """指标异常点（evidence_points category=anomaly）"""
    indicator: str = ""
    timestamp: str = ""
    value: Optional[float] = None
    score: Optional[float] = None
    expected_range: Optional[List[float]] = None


class PatternHit(BaseModel):
    """专家模式命中（evidence_points category=expert_pattern）"""
    pattern: str = ""
    pattern_key: str = ""
    match_score: Optional[float] = None
    confidence: Optional[float] = None
    suspicion_level: str = ""


class AlertEvent(BaseModel):
    id: str
    timestamp: str
    sessionId: str = ""
    conversationId: Optional[str] = None
    plantId: str = ""
    violationTypes: List[str] = []
    severity: str
    action: str = ""
    confidence: Optional[float] = None
    evidence: List[Dict[str, Any]] = []
    workOrder: Optional[Dict[str, Any]] = None
    status: str
    createdAt: str = ""
    updatedAt: str = ""


class EventListResponse(BaseModel):
    data: List[AlertEvent]
    total: int


class EventStatusUpdate(BaseModel):
    status: str
```

- [ ] **Step 4: 重写 `backend/api/routes/events.py`**

要点（完整实现，非占位）：
- 删 mock 列表与旧 Pydantic import
- `router = APIRouter(tags=["事件中心"])`
- **export 路由定义在最前**：`GET /events/export?format=json`——json 全量（service 查全部转 dict 列表）；format=xlsx/pdf 返回 501 文本（现状是 "coming soon"，改带状态码）
- `GET /events`：query 参数保持 `start_time/end_time/type/plantId/severity/status/page/pageSize`；经 EventService 新增查询方法（Task 2 内给 service 补 `list_events(filters, page, page_size) -> {data, total}`）——SQLite where 动态拼：severity/status 枚举值校验（非法返回 422 或空，选空+warning）；type→`violation_types LIKE %"值"%`（JSON 列 text 匹配）；plantId 等值；时间窗 timestamp between；order_by timestamp desc；分页 offset/limit
- `GET /events/{event_id}`：查无 404
- `PUT /events/{event_id}/status`：状态机合法集 `{(p,p),(p,processing),(p,resolved),(p,ignored),(processing,processing),(processing,resolved),(processing,ignored)}`；非法 400 `{"detail": "非法状态流转: <cur> → <new>"}`；目标值非四枚举 400
- service 层补 `list_events/get_event/update_status`（都走 SessionLocal 短会话；_to_dict 已有）

- [ ] **Step 5: query.py 接线采集器（两处）**

非流式 :160 record_exchange 成功后：
```python
        # 采集处置研判事件（失败不阻断主链路）
        try:
            session_dir = resp_json.get("session_dir") if isinstance(resp_json, dict) else None
            if session_dir:
                event_service.collect_from_session(session_dir, conversation_id=final_session_id)
        except Exception as ev_err:
            logger.warning(f"Event collection failed: {ev_err}")
```
（变量名按实际作用域调整；非流式的响应变量名读上下文确认）

流式 :325 had_done 分支 record_exchange 后：
```python
            # 采集处置研判事件（session_dir 来自 done 事件，Task1 已补字段）
            try:
                session_dir = last_session_dir  # 流式解析时暂存 evt.get("session_dir")
                if session_dir:
                    event_service.collect_from_session(session_dir, conversation_id=final_session_id)
            except Exception as ev_err:
                logger.warning(f"Event collection failed: {ev_err}")
```
（done 事件解析处加 `last_session_dir = evt.get("session_dir")`；模块顶部 `event_service = EventService()`）

同时删掉 Task 1 留的两行 TODO 注释。

- [ ] **Step 6: 跑全部测试**

`$PY -m pytest tests/events/ -v` → 13 个 PASS（8 service + 5 api）；全套无回归。

- [ ] **Step 7: 临时实例端到端验证**

```bash
$PY -m uvicorn backend.main:app --port 8021 &   # 后台
curl -s "http://localhost:8021/api/events" | head -c 200       # 空表 {data:[],total:0}
# 用真实历史 session 手动喂一次采集（模拟一轮研判完成）：
$PY -c "
import sys; sys.path.insert(0, '.')
from backend.services.event_service import EventService
r = EventService().collect_from_session('session_20260806_092743_b373f6')
print('采集结果:', r is not None, '(该 session 是 none 级,应为 None)')"
kill %1
```

- [ ] **Step 8: 提交**

```bash
git add backend/api/routes/events.py backend/models/event.py backend/api/routes/query.py backend/services/event_service.py tests/events/test_events_api.py
git commit -m "feat(events): /api/events换SQLite真数据源——状态机校验+时间窗过滤+export路由顺序修复+采集器接线落库点"
```

---

### Task 3: 前端真证据渲染 + 三 bug 修复

**Files:**
- Modify: `frontend/src/views/EventCenterView.vue`（type 列 + 详情抽屉证据区）
- Modify: `frontend/src/stores/events.ts`（pageSize bug）
- Modify: `frontend/src/api/types/api.types.ts`（AlertEvent 类型对齐）
- Modify: `subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/run_disposition.py`（打印 KeyError 修复）
- Test: `frontend/src/views/__tests__/eventEvidence.spec.ts`（转换函数）

- [ ] **Step 1: 写失败的转换函数测试**

```typescript
// frontend/src/views/__tests__/eventEvidence.spec.ts
import { describe, it, expect } from 'vitest'
import { splitEvidence } from '@/views/EventCenterView.vue'

describe('splitEvidence（evidence_points 真结构拆分）', () => {
  const evidence = [
    { category: 'anomaly', indicator: 'COD', value: 501.9, timestamp: '2026-07-14 12:00:00',
      score: 0.78, expected_range: [65.6, 96.2] },
    { category: 'expert_pattern', pattern: '插瓶干扰', pattern_key: 'bottle_interference',
      match_score: 0.9, confidence: 0.95, suspicion_level: 'critical' },
    { category: 'anomaly', indicator: 'TN', value: 4.23, timestamp: '2026-07-14 00:00:00',
      score: 0.79, expected_range: [4.84, 5.435] },
  ]

  it('按 category 拆成指标异常点与模式命中两组', () => {
    const { anomalies, patterns } = splitEvidence(evidence as any)
    expect(anomalies).toHaveLength(2)
    expect(patterns).toHaveLength(1)
    expect(anomalies[0]).toMatchObject({ indicator: 'COD', value: 501.9 })
    expect(patterns[0]).toMatchObject({ pattern: '插瓶干扰', match_score: 0.9 })
  })

  it('未知 category 落入 anomalies 兜底不丢数据', () => {
    const { anomalies, patterns } = splitEvidence([
      { category: 'weird', indicator: 'X' } as any,
    ])
    expect(anomalies).toHaveLength(1)
    expect(patterns).toHaveLength(0)
  })

  it('空数组安全', () => {
    const r = splitEvidence([])
    expect(r.anomalies).toHaveLength(0)
    expect(r.patterns).toHaveLength(0)
  })
})
```

注意：从 .vue 导出纯函数需 `<script setup>` 外加一个普通 `<script>` 块导出（Vue SFC 支持双 script），或把函数抽到 `frontend/src/views/eventEvidence.ts` 再 import——**选后者**（更干净），测试 import 路径相应改 `@/views/eventEvidence`，EventCenterView 也从该文件 import。

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 实现**

`frontend/src/views/eventEvidence.ts`：
```typescript
// frontend/src/views/eventEvidence.ts
/** evidence_points 真结构 → 详情抽屉渲染数据的纯转换 */
export interface EvidenceAnomaly {
  indicator: string
  timestamp: string
  value: number | null
  score: number | null
  expected_range: number[] | null
}
export interface EvidencePattern {
  pattern: string
  pattern_key: string
  match_score: number | null
  confidence: number | null
  suspicion_level: string
}

export function splitEvidence(evidence: Record<string, unknown>[]): {
  anomalies: EvidenceAnomaly[]
  patterns: EvidencePattern[]
} {
  const anomalies: EvidenceAnomaly[] = []
  const patterns: EvidencePattern[] = []
  for (const e of evidence ?? []) {
    if ((e.category as string) === 'expert_pattern') {
      patterns.push({
        pattern: String(e.pattern ?? ''),
        pattern_key: String(e.pattern_key ?? ''),
        match_score: typeof e.match_score === 'number' ? e.match_score : null,
        confidence: typeof e.confidence === 'number' ? e.confidence : null,
        suspicion_level: String(e.suspicion_level ?? ''),
      })
    } else {
      // anomaly 及未知 category 兜底（不丢数据）
      anomalies.push({
        indicator: String(e.indicator ?? ''),
        timestamp: String(e.timestamp ?? ''),
        value: typeof e.value === 'number' ? e.value : null,
        score: typeof e.score === 'number' ? e.score : null,
        expected_range: Array.isArray(e.expected_range) ? (e.expected_range as number[]) : null,
      })
    }
  }
  return { anomalies, patterns }
}
```

`EventCenterView.vue` 改动点：
1. type 列：`{{ (row.violationTypes || []).join('、') || '—' }}`
2. 详情抽屉：旧 evidence 区（dataSnapshot/operators/rules/llmReasoning）整块替换为：
   - 「研判行动」行：action + confidence 百分比
   - 「指标异常点」el-table：指标/时间/实测值/期望区间(join '-')/得分
   - 「专家模式命中」列表：pattern + match_score + confidence + suspicion_level tag
   - 「工单」摘要（workOrder 非空时）：id + generated_at + recommended_actions 前三条
3. 详情 meta 行 plantId 直显真实厂名（无需映射表——后端存的就是全称）
4. 从 `@/views/eventEvidence` import splitEvidence

`frontend/src/api/types/api.types.ts`：AlertEvent 接口字段对齐（violationTypes/evidence: Record<string,unknown>[]/workOrder/sessionId/createdAt 等，删旧 EventEvidence 三结构——先 grep 引用，若 AIOpsChat 等处引用旧类型需同步）。

`frontend/src/stores/events.ts`：默认参数 `{page:1, pageSize:20}`。

`run_disposition.py` 修复（:258 附近）：
```python
    # 旧代码打印 output["result"]["alert"]（不存在键,存盘后 KeyError）→ 改打实际字段
    print(f"[disposition] 完成: level={output['result']['suspicion_level']}, "
          f"action={output['result']['action']}, "
          f"violations={output['result']['violation_types']}, "
          f"evidence={len(output['result']['evidence_points'])}条")
```

- [ ] **Step 4: 跑测试 + type-check**

`cd frontend && npm test` → 全过（28 存量 + 3 新）；`npx vue-tsc --noEmit | grep -iE "event"` → 无输出。

run_disposition 修复验证：
```bash
$PY -c "
import subprocess, sys, shutil, tempfile, json
from pathlib import Path
# 复制真实 session 到临时目录跑（脚本以 cwd/session 定位输入,读脚本开头确认参数用法;
# 若脚本从 SESSION_DIR 环境变量读,设 env 指向临时副本）
src = Path('sessions/session_20260806_092743_b373f6')
tmp = Path(tempfile.mkdtemp()) / 's'
shutil.copytree(src, tmp)
import os
env = {**os.environ, 'SESSION_DIR': str(tmp)}
r = subprocess.run([sys.executable, 'subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/run_disposition.py'],
                   capture_output=True, text=True, env=env, timeout=120)
print('returncode:', r.returncode)
print('stdout tail:', r.stdout[-200:] if r.stdout else '')
assert r.returncode == 0, r.stderr[-500:]
print('OK 不再 KeyError')"
```
（run_disposition.py 的输入定位方式以实际代码为准——先读其 main/argparse 部分再调整调用方式；目标是验证打印不再崩。）

- [ ] **Step 5: 提交**

```bash
git add frontend/src/views/EventCenterView.vue frontend/src/views/eventEvidence.ts frontend/src/views/__tests__/eventEvidence.spec.ts frontend/src/stores/events.ts frontend/src/api/types/api.types.ts subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/run_disposition.py
git commit -m "feat(events): 前端真证据渲染(指标异常点+专家模式命中+工单摘要)+store参数修复+run_disposition打印KeyError修复"
```

---

### Task 4: 端到端联调 + 收尾

- [ ] **Step 1: 重启真实服务栈验证**

backend :8000 是旧进程——kill 后重启（同参数 0.0.0.0:8000，日志 %TEMP%/eco_backend.log）。agent 服务 :8642 也要重启（Task 1 改了 start_agent.py）。

- [ ] **Step 2: 端到端一轮真研判**

用 Playwright 或 curl 在 http://localhost:5173/chat 问一个会触发处置的问题（如"金桥最近24小时有没有违规，怎么处置"），等流式完成（~2 分钟）后：
```bash
curl -s "http://localhost:8000/api/events" | head -c 400
# 期望: 若研判非 none → {data:[{plantId:"当阳市金桥污水处理厂一期",...}],total:1}
#       若 none → {data:[],total:0}(none 不入,符合设计)
```
打开 http://localhost:5173/events 确认列表/详情/状态流转；http://localhost:5173/alerts 确认统计卡。

- [ ] **Step 3: 全量回归**

`$PY -m pytest tests/ -q` + `cd frontend && npm test` → 全绿。

- [ ] **Step 4: CLAUDE.md 补条目 + 提交**

Key Files 区"知识图谱"条目后追加：

```markdown
### 事件中心真实化（2026-09-09 子项目 2/4）
- `backend/models/alert_event.py`：alert_events 表（severity/status 枚举、evidence/work_order JSON、session_id 唯一防重复采集）
- `backend/services/event_service.py`：采集器（query.py 两处落库点调 collect_from_session，非 none 入库）+ 查询/状态机服务
- `backend/api/routes/events.py`：真数据源（export 路由已修序、PUT status 状态机校验、时间窗过滤真实现）
- `frontend/src/views/eventEvidence.ts`：evidence_points 拆分纯函数（指标异常点+专家模式命中）
- 后续子项目：3 智能体集成（图查询+研判写回）→ 4 根因分析（消费本表事件）
```

```bash
git add CLAUDE.md
git commit -m "docs: CLAUDE.md 补事件中心真实化条目"
```

---

## Self-Review 记录

- **Spec 覆盖**：表模型（Task1）、采集器+幂等+厂名解析（Task1）、done 补 session_dir（Task1）、API 五端点+状态机+export 修序+时间窗（Task2）、query.py 接线（Task2）、前端真证据+type 列+store bug（Task3）、run_disposition KeyError（Task3）、测试四层（pytest×2+Vitest+E2E）（Task1-4）、不回灌历史（Task2 Step7 验证 none 场景即其精神）✓
- **占位符扫描**：Task2 Step4 是"要点"而非全码（路由重写较大）——但每项行为都有精确规格+测试锁定，属可执行规格而非 TBD；Task3 Step4 的 run_disposition 验证脚本标注了"以实际代码为准"的适配点
- **类型一致性**：_to_dict 的 camelCase 键（plantId/violationTypes/workOrder）与 Pydantic 新模型、前端 api.types 三处一致；severity/status 枚举值前后端一致；EventService 构造（sessions_root 可选）测试与实现一致
- **关键依赖链**：Task2 依赖 Task1 的 done session_dir 字段；Task3 前端依赖 Task2 的响应形状；Task4 依赖全部
