"""Single event proposals with compare-and-update and transactional audit."""
import os
import uuid
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from backend.database.session import SessionLocal
from backend.models.alert_event import AlertEvent, EventStatus
from backend.models.assistant_event import AssistantEventProposal, AssistantEventOperation
from backend.services.event_service import EventService


def enabled():
    return os.getenv('ASSISTANT_EVENT_WRITES_ENABLED', 'false').lower() == 'true'


def require_enabled():
    if not enabled():
        raise HTTPException(403, '助手事件写入未启用，请使用事件页面。')


def propose(req):
    require_enabled()
    with SessionLocal() as db:
        ev = db.get(AlertEvent, req.event_id)
        if ev is None:
            raise HTTPException(404, '事件不存在')
        old = ev.status.value
        if (req.expected_status is not None and old != req.expected_status) or (req.expected_updated_at is not None and ev.updated_at != req.expected_updated_at):
            raise HTTPException(409, '事件已变化，请重新读取')
        if (old, req.new_status) not in EventService.VALID_TRANSITIONS:
            raise HTTPException(400, '非法状态流转')
        p = AssistantEventProposal(id=uuid.uuid4().hex, session_id=req.session_id, event_id=ev.id,
            old_status=old, new_status=req.new_status, expected_updated_at=ev.updated_at,
            reason=req.reason, plant_id=ev.plant_id, expires_at=datetime.now() + timedelta(minutes=5))
        db.add(p)
        db.commit()
        return dict(proposal_id=p.id, event_id=p.event_id, plant_id=p.plant_id, old_status=p.old_status,
                    new_status=p.new_status, reason=p.reason, expected_updated_at=p.expected_updated_at.isoformat(),
                    expires_at=p.expires_at.isoformat(), identity='本地操作会话，身份未认证')


def operation(operation_id, session_id):
    with SessionLocal() as db:
        op = db.get(AssistantEventOperation, operation_id)
        if op is None or op.session_id != session_id:
            raise HTTPException(404, '操作不存在')
        return op.result


def operation_by_key(idempotency_key, session_id):
    with SessionLocal() as db:
        op = db.query(AssistantEventOperation).filter_by(session_id=session_id, idempotency_key=idempotency_key).first()
        if op is None:
            raise HTTPException(404, '操作不存在或结果尚未提交；请稍后核验')
        return op.result


def confirm(proposal_id, req):
    with SessionLocal() as db:
        existing = db.query(AssistantEventOperation).filter_by(session_id=req.session_id, idempotency_key=req.idempotency_key).first()
        if existing:
            if existing.proposal_id != proposal_id:
                raise HTTPException(409, '幂等键已用于其他提议')
            return existing.result
        require_enabled()
        p = db.get(AssistantEventProposal, proposal_id)
        if p is None or p.session_id != req.session_id:
            raise HTTPException(404, '提议不存在')
        now = datetime.now()
        if p.expires_at <= now or p.consumed_at is not None:
            raise HTTPException(409, '提议过期或已使用，请重新确认')
        # Both claims and the event update roll back if audit insertion fails.
        claimed = db.execute(update(AssistantEventProposal).where(
            AssistantEventProposal.id == p.id, AssistantEventProposal.consumed_at.is_(None),
            AssistantEventProposal.expires_at > now).values(consumed_at=now)).rowcount
        changed = db.execute(update(AlertEvent).where(AlertEvent.id == p.event_id,
            AlertEvent.status == EventStatus(p.old_status), AlertEvent.updated_at == p.expected_updated_at
            ).values(status=EventStatus(p.new_status), updated_at=now)).rowcount
        if claimed != 1 or changed != 1:
            db.rollback()
            raise HTTPException(409, '事件或提议已变化，请重新确认')
        op_id = uuid.uuid4().hex
        result = dict(operation_id=op_id, proposal_id=p.id, event_id=p.event_id, old_status=p.old_status,
            new_status=p.new_status, reason=p.reason, status='completed', updated_at=now.isoformat(),
            source='global-assistant', identity='本地操作会话，身份未认证')
        db.add(AssistantEventOperation(id=op_id, proposal_id=p.id, session_id=req.session_id,
            idempotency_key=req.idempotency_key, result=result, created_at=now))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            original = db.query(AssistantEventOperation).filter_by(session_id=req.session_id, idempotency_key=req.idempotency_key, proposal_id=proposal_id).first()
            if original:
                return original.result
            raise HTTPException(409, '提议已提交，请查询操作结果')
        return result
