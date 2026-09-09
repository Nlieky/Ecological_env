# tests/events/test_event_service.py
"""事件采集器测试：各等级入库/none 不入/幂等/损坏文件/厂名解析。"""
import json
from pathlib import Path

import pytest

from backend.services.event_service import EventService, _parse_plant_id


@pytest.fixture
def svc(tmp_path, monkeypatch):
    """采集器指向临时 sessions 根 + 临时库。"""
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
    assert ev["plantId"] == "当阳市金桥污水处理厂一期"


def test_plant_id_alias(svc, tmp_path):
    make_session(tmp_path, "session_t4", "low", plant="金桥")
    ev = svc.collect_from_session("session_t4")
    assert ev["plantId"] == "当阳市金桥污水处理厂一期"  # 别名经 plant_aliases 归一


def test_parse_plant_id_unknown():
    # 厂名解析读真实 shared/data/plant-hierarchy.yaml（与运行时同源）——
    # "unknown" 兜底不依赖 yaml 内容，故此用例对 yaml 变更稳健。
    assert _parse_plant_id("今天天气怎么样") == "unknown"


def test_incomplete_status_skipped(svc, tmp_path):
    sd = make_session(tmp_path, "session_t5", "high")
    d = json.loads((sd / "disposition_result.json").read_text(encoding="utf-8"))
    d["status"] = "failed"
    (sd / "disposition_result.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    assert svc.collect_from_session("session_t5") is None
