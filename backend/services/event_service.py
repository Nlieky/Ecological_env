"""事件服务：从 session 目录采集处置研判结果入库（查询/状态方法 Task2 补）。

采集时机：backend 落库 conversations 的同一位置调 collect_from_session。
幂等靠 session_id 唯一索引。none 不入（留审计链路）。
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database.session import SessionLocal
from backend.models.alert_event import AlertEvent, EventSeverity, EventStatus

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SEVERITY_CN = {"high": "高风险", "medium": "中风险", "low": "低风险"}
# 研判写回的图谱 DB（可 patch，测试指向临时图/不存在路径）。
# graph 模块只在 _writeback_case_to_graph 内延迟 import——顶部无条件 import
# 会让事件测试环境连带加载图谱链路（子项目3 约定）。
_graph_db_path = _PROJECT_ROOT / "shared" / "data" / "knowledge_graph.db"


def _plant_lookup() -> tuple[set, dict]:
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
    """从 task 文本解析厂全称：先全称包含匹配（取最长防子串），再别名表。"""
    if not text:
        return "unknown"
    plants, aliases = _plant_lookup()
    hits = [p for p in plants if p in text]
    if hits:
        return max(hits, key=len)
    for alias, full in sorted(aliases.items(), key=lambda x: -len(x[0])):
        if alias in text:
            return full
    return "unknown"


def _parse_ts(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return datetime.now()


def _to_local_naive(s: str) -> datetime:
    """解析时间串并归一化到本地 naive（I2）。

    存储是 naive 本地时间（datetime.now()），SQLite TIMESTAMP 绑定会静默丢
    tzinfo——aware 输入（前端 toISOString 产 Z 后缀）若不先转本地，按字面
    UTC 数值比本地会错窗 8 小时。aware→本地 naive；naive 原样返回；非法→None。
    """
    try:
        dt = datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)
    return dt


def _writeback_case_to_graph(ev: dict, db_path) -> None:
    """研判结论写回图谱（子项目3 阶段B）：case 节点 + involves(厂) + cites(模式)。

    幂等（upsert）；图缺失静默跳过；厂/模式节点不存在跳过对应边（防悬挂边）。
    图损坏（GraphStore 构造抛"file is not a database"）由调用方 try/except 兜住。
    """
    db_path = Path(db_path)
    if not db_path.exists():
        logger.info(f"[events] 图谱不存在({db_path.name})，写回跳过")
        return
    from shared.knowledge_graph.graph_store import GraphStore
    from shared.knowledge_graph.graph_query import GraphKnowledgeSource
    g = GraphStore(db_path)
    try:
        case_id = f"case:{ev['id']}"
        ts = ev.get("timestamp", "")[:10] or "案例"
        g.upsert_node(case_id, "case", f"研判案例 {ts}",
                      {"timestamp": ev.get("timestamp", ""),
                       "plant_id": ev.get("plantId", ""),
                       "severity": ev.get("severity", ""),
                       "violation_types": ev.get("violationTypes", []),
                       "confidence": ev.get("confidence"),
                       "action": ev.get("action", ""),
                       "source_event": ev.get("id", ""),
                       "source": "研判写回(子项目3)"})
        # involves → 厂（先查存在防悬挂；plant 节点 id=plant:<中文全称>）
        plant_id = ev.get("plantId", "")
        if plant_id and g.get_node(f"plant:{plant_id}") is not None:
            g.upsert_edge(case_id, f"plant:{plant_id}", "involves",
                          {"note": "研判涉及"})
        elif plant_id:
            logger.info(f"[events] 厂节点不存在({plant_id})，involves 跳过")
        # cites → 模式（中文类型名反查 slug；图不可用时反查 None 跳过）
        src = GraphKnowledgeSource(db_path=db_path)
        for vt in ev.get("violationTypes", []) or []:
            pid = src.pattern_id_by_label(str(vt))
            if pid:
                g.upsert_edge(case_id, pid, "cites", {"note": "研判认定"})
            else:
                logger.info(f"[events] 模式反查失败({vt})，cites 跳过")
        logger.info(f"[events] 图谱写回完成: {case_id}")
    finally:
        g.close()


class EventService:
    def __init__(self, sessions_root: Optional[Path] = None):
        self.sessions_root = Path(sessions_root) if sessions_root else _PROJECT_ROOT / "sessions"

    def collect_from_session(self, session_dir_name: str,
                             conversation_id: Optional[str] = None) -> Optional[dict]:
        """读 <sessions_root>/<name>/disposition_result.json 入库。

        入库条件：status=completed 且 suspicion_level in {high,medium,low}。
        幂等：session 已有事件 → 跳过返回 None。文件缺失/损坏 → None。
        """
        f = self.sessions_root / session_dir_name / "disposition_result.json"
        if not f.exists():
            return None
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"[events] disposition_result 解析失败({session_dir_name}): {e}")
            return None
        result = data.get("result") or {}
        if data.get("status") != "completed":
            return None
        level = result.get("suspicion_level")
        if level not in _SEVERITY_CN:
            return None

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
                    task_text = (json.loads(tj.read_text(encoding="utf-8")).get("task", ""))
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
            )
            db.add(ev)
            db.commit()
            ev_dict = self._to_dict(ev)
            # 研判写回图谱（子项目3 阶段B）：案例节点+involves厂+cites模式。
            # 独立 try/except——图谱写失败只记日志，事件已入库不受影响。
            try:
                _writeback_case_to_graph(ev_dict, db_path=_graph_db_path)
            except Exception as wb_err:
                logger.warning(f"[events] 图谱写回失败(不影响事件): {wb_err}")
            return ev_dict
        except IntegrityError:
            # 并发竞态：另一个采集者已插入同 session_id 的行。保持"已采集→None"契约。
            db.rollback()
            return None
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # ---------- 查询/状态（Task2）----------
    VALID_TRANSITIONS = {
        ("pending", "pending"), ("pending", "processing"),
        ("pending", "resolved"), ("pending", "ignored"),
        ("processing", "processing"), ("processing", "resolved"),
        ("processing", "ignored"),
        ("resolved", "resolved"), ("ignored", "ignored"),
    }

    def list_events(self, start_time=None, end_time=None, type_q=None,
                    plant_id=None, severity=None, status=None,
                    page=1, page_size=20) -> dict:
        """分页筛选查询（timestamp 倒序）。枚举值非法→空结果（不炸）。"""
        if severity is not None and severity not in EventSeverity._value2member_map_:
            return {"data": [], "total": 0}
        if status is not None and status not in EventStatus._value2member_map_:
            return {"data": [], "total": 0}

        conds = []
        if start_time:
            dt = _to_local_naive(start_time)
            if dt is not None:
                conds.append(AlertEvent.timestamp >= dt)
        if end_time:
            dt = _to_local_naive(end_time)
            if dt is not None:
                conds.append(AlertEvent.timestamp <= dt)
        if type_q:
            # JSON 列做包含匹配。SQLite 的 JSON 序列化会把非 ASCII 转义成 \uXXXX，
            # 直接 cast 成文本 LIKE 匹配不到中文——用 json_each 解码后再 LIKE。
            # M5: 表名用 __tablename__ 拼，模型改表名时同步
            conds.append(text(
                f"exists (select 1 from json_each({AlertEvent.__tablename__}.violation_types) "
                "where json_each.value like :type_q)"
            ).bindparams(type_q=f"%{type_q}%"))
        if plant_id:
            conds.append(AlertEvent.plant_id == plant_id)
        if severity is not None:
            conds.append(AlertEvent.severity == EventSeverity(severity))
        if status is not None:
            conds.append(AlertEvent.status == EventStatus(status))

        db: Session = SessionLocal()
        try:
            q = db.query(AlertEvent)
            for c in conds:
                q = q.filter(c)
            total = q.count()
            rows = (q.order_by(AlertEvent.timestamp.desc())
                     .offset((page - 1) * page_size).limit(page_size).all())
            return {"data": [self._to_dict(r) for r in rows], "total": total}
        finally:
            db.close()

    def get_event(self, event_id: str) -> Optional[dict]:
        db: Session = SessionLocal()
        try:
            ev = db.query(AlertEvent).filter(AlertEvent.id == event_id).first()
            return self._to_dict(ev) if ev else None
        finally:
            db.close()

    def update_status(self, event_id: str, new_status: str) -> Optional[dict]:
        """状态机：非法流转 raise ValueError（路由转 400）；事件不存在 None。"""
        if new_status not in EventStatus._value2member_map_:
            raise ValueError(f"非法状态值: {new_status}")
        db: Session = SessionLocal()
        try:
            ev = db.query(AlertEvent).filter(AlertEvent.id == event_id).first()
            if not ev:
                return None
            cur = ev.status.value if ev.status else "pending"
            if (cur, new_status) not in self.VALID_TRANSITIONS:
                raise ValueError(f"非法状态流转: {cur} → {new_status}")
            ev.status = EventStatus(new_status)
            db.commit()
            db.refresh(ev)
            return self._to_dict(ev)
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
