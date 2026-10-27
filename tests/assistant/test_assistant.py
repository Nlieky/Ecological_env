from datetime import datetime
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def client(tmp_path, monkeypatch):
    from backend.api.routes import assistant
    from backend.database.base import Base
    from backend.models.alert_event import AlertEvent, EventSeverity
    from backend.services import assistant_events
    engine = create_engine(f"sqlite:///{tmp_path / 'assistant.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(assistant_events, "SessionLocal", factory)
    monkeypatch.delenv("ASSISTANT_EVENT_WRITES_ENABLED", raising=False)
    with factory() as db:
        db.add(AlertEvent(id="evt_test", timestamp=datetime.now(), plant_id="test", severity=EventSeverity.low))
        db.commit()
    app = FastAPI()
    app.include_router(assistant.router, prefix="/api")
    return TestClient(app), factory


def test_help_and_strict_context(client, monkeypatch):
    c, _ = client
    from backend.services import assistant_service
    async def help_turn(req):
        return {'message':'事件中心使用帮助', 'actions':[], 'session_id':req.session_id}
    monkeypatch.setattr(assistant_service, 'respond', help_turn)
    r = c.post('/api/assistant/respond', json={"query":"这里是什么", "session_id":"s", "context":{"pageId":"events"}})
    assert r.status_code == 200
    assert "事件" in r.json()['message']
    assert r.json()['actions'] == []
    assert c.post('/api/assistant/respond', json={"query":"x", "session_id":"s", "context":{"api_key":"secret"}}).status_code == 422


def proposal(c):
    return c.post('/api/assistant/event-proposals', json={"session_id":"s", "event_id":"evt_test", "new_status":"processing", "reason":"人工核验"})


def test_write_disabled(client):
    c, _ = client
    assert proposal(c).status_code == 403


def test_confirm_bound_idempotent_and_audited(client, monkeypatch):
    c, factory = client
    monkeypatch.setenv('ASSISTANT_EVENT_WRITES_ENABLED', 'true')
    p = proposal(c).json()
    url = f"/api/assistant/event-proposals/{p['proposal_id']}/confirm"
    assert c.post(url, json={"session_id":"other", "idempotency_key":"k"}).status_code == 404
    body = {"session_id":"s", "idempotency_key":"k"}
    r = c.post(url, json=body)
    assert r.status_code == 200, r.text
    assert r.json()['status'] == 'completed'
    assert c.post(url, json=body).json() == r.json()
    assert c.get(f"/api/assistant/operations/{r.json()['operation_id']}?session_id=s").json() == r.json()
    monkeypatch.setenv('ASSISTANT_EVENT_WRITES_ENABLED', 'false')
    assert c.post(url, json=body).json() == r.json()
    assert c.get('/api/assistant/operations/by-key/k?session_id=s').json() == r.json()
    assert c.get('/api/assistant/operations/by-key/k?session_id=other').status_code == 404
    from backend.models.assistant_event import AssistantEventOperation
    with factory() as db:
        assert db.query(AssistantEventOperation).count() == 1


def test_concurrent_change_expiry_and_disable(client, monkeypatch):
    c, factory = client
    monkeypatch.setenv('ASSISTANT_EVENT_WRITES_ENABLED', 'true')
    p = proposal(c).json()
    from backend.models.alert_event import AlertEvent, EventStatus
    with factory() as db:
        event = db.get(AlertEvent, 'evt_test')
        event.status = EventStatus.resolved
        db.commit()
    url = f"/api/assistant/event-proposals/{p['proposal_id']}/confirm"
    assert c.post(url, json={"session_id":"s", "idempotency_key":"k"}).status_code == 409
    monkeypatch.setenv('ASSISTANT_EVENT_WRITES_ENABLED', 'false')
    assert c.post(url, json={"session_id":"s", "idempotency_key":"k"}).status_code == 403


def test_expired_proposal_and_version_mismatch(client, monkeypatch):
    c, factory = client
    monkeypatch.setenv('ASSISTANT_EVENT_WRITES_ENABLED', 'true')
    payload = {"session_id":"s", "event_id":"evt_test", "new_status":"processing", "reason":"核验", "expected_status":"resolved"}
    assert c.post('/api/assistant/event-proposals', json=payload).status_code == 409
    p = proposal(c).json()
    from backend.models.assistant_event import AssistantEventProposal
    with factory() as db:
        db.get(AssistantEventProposal, p['proposal_id']).expires_at = datetime(2000, 1, 1)
        db.commit()
    assert c.post(f"/api/assistant/event-proposals/{p['proposal_id']}/confirm", json={"session_id":"s", "idempotency_key":"k"}).status_code == 409


def test_action_allowlist():
    from backend.services.assistant_service import validate_actions
    assert validate_actions([{'capability':'navigate', 'parameters':{'pageId':'events'}}])
    for action in [{'capability':'delete', 'parameters':{}}, {'capability':'strategy.draft', 'parameters':{'api_key':'secret'}}, {'capability':'navigate', 'parameters':{'pageId':'fake'}}]:
        with pytest.raises(ValueError):
            validate_actions([action])
    assert validate_actions([{'capability':'dashboard.detect', 'parameters':{'algorithm':'constant', 'indicator':'COD', 'side':'effluent'}}])
    with pytest.raises(ValueError):
        validate_actions([{'capability':'dashboard.detect', 'parameters':{'algorithm':'constant'}}])
    assert validate_actions([{'capability':'event.propose', 'parameters':{'eventId':'evt_test', 'new_status':'processing', 'reason':'人工核验'}}])
    for parameters in [{'eventId':'evt_test', 'new_status':'delete', 'reason':'核验'}, {'new_status':'processing', 'reason':'核验'}, {'eventId':'evt_test', 'new_status':'processing', 'reason':'核验', 'confirmed':True}]:
        with pytest.raises(ValueError):
            validate_actions([{'capability':'event.propose', 'parameters':parameters}])


@pytest.mark.parametrize('raw', [
    '{"message":"partial",',
    '```json\n{"message":"partial",\n```',
    '{"message":"x","actions":[{"capability":"delete","parameters":{"id":"one"}}]}',
    '{"message":"x","actions":[{"capability":"event.propose","parameters":{"confirmed":true}}]}',
    '[{"message":"x"}]', '',
])
def test_model_compatibility_never_relaxes_action_validation(raw):
    from backend.services.assistant_service import parse_model_answer
    with pytest.raises(ValueError):
        parse_model_answer(raw)


def test_model_unavailable_is_explicit_and_private(client, monkeypatch):
    c, _ = client
    from backend.services import assistant_service
    class Offline:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs):
            raise assistant_service.httpx.ConnectError('api_key=secret')
    monkeypatch.setattr(assistant_service.httpx, 'AsyncClient', Offline)
    r = c.post('/api/assistant/respond', json={'query':'请解释这个问题', 'session_id':'s'})
    assert r.status_code == 503
    assert 'secret' not in r.text


@pytest.mark.parametrize('content', [
    '当前页面是监测大屏，可切换厂站和时间范围。',
    '```json\n{"message":"当前页面是监测大屏","actions":[]}\n```',
])
def test_model_text_and_fenced_json_are_safe_answers(client, monkeypatch, content):
    c, _ = client
    from backend.services import assistant_service
    from shared.assistant.master_turn import parse_turn
    calls = []
    class ModelClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return assistant_service.httpx.Response(200, request=assistant_service.httpx.Request('POST', url), json=parse_turn(content, 's', {}))
    monkeypatch.setattr(assistant_service.httpx, 'AsyncClient', ModelClient)
    r = c.post('/api/assistant/respond', json={'query':'解释当前页面','session_id':'s','context':{'pageId':'dashboard'},'history':[{'role':'user','content':'打开事件中心'}]})
    assert r.status_code == 200, r.text
    assert '监测大屏' in r.json()['message']
    assert r.json()['actions'] == []
    from backend.core.config import settings
    assert calls[0][0] == settings.AGENT_SERVICE_URL.rstrip('/') + '/system-assistant/respond'
    assert calls[0][1]['json']['history'][0]['content'] == '打开事件中心'


def test_audit_failure_rolls_back_event(client, monkeypatch):
    c, factory = client
    monkeypatch.setenv('ASSISTANT_EVENT_WRITES_ENABLED', 'true')
    p = proposal(c).json()
    from sqlalchemy import event
    from backend.models.assistant_event import AssistantEventOperation, AssistantEventProposal
    from backend.models.alert_event import AlertEvent
    def fail(*args):
        raise RuntimeError('simulated audit failure')
    event.listen(AssistantEventOperation, 'before_insert', fail)
    try:
        with pytest.raises(RuntimeError, match='simulated audit failure'):
            c.post(f"/api/assistant/event-proposals/{p['proposal_id']}/confirm", json={'session_id':'s', 'idempotency_key':'k'})
    finally:
        event.remove(AssistantEventOperation, 'before_insert', fail)
    with factory() as db:
        assert db.get(AlertEvent, 'evt_test').status.value == 'pending'
        assert db.get(AssistantEventProposal, p['proposal_id']).consumed_at is None


@pytest.mark.parametrize('selected_provider', [False, True])
def test_model_uses_runtime_provider_fallback_without_tools(client, monkeypatch, selected_provider):
    from scripts import start_agent
    calls = []
    selected = {'base_url':'https://selected.invalid/v1', 'model':'selected-model', 'api_key':'fixture-only'}
    monkeypatch.setattr(start_agent._lp, 'seed_defaults', lambda: None)
    monkeypatch.setattr(start_agent._lp, 'resolve_default', lambda: selected if selected_provider else None)
    values = {'llm_base_url':'https://runtime.invalid/v1', 'llm_model':'runtime-model', 'llm_api_key':'fixture-only'}
    monkeypatch.setattr(start_agent, '_gp', lambda key, **kwargs: values.get(key, kwargs.get('default')))
    monkeypatch.setattr(start_agent, 'AIAgent', lambda **kwargs: calls.append(kwargs) or object())
    service = start_agent.AgentService()
    service._create_main_agent()
    service._create_main_agent(system_interaction=True, session_id='system-assistant:test')
    for key in ('identity_path', 'load_soul_identity', 'model', 'base_url', 'api_key'):
        assert calls[0][key] == calls[1][key]
    assert calls[1]['model'] == ('selected-model' if selected_provider else 'runtime-model')
    assert calls[1]['enabled_toolsets'] == []
    assert calls[1]['skip_memory'] and calls[1]['skip_context_files']
    assert calls[1]['session_db'] is None


def test_version_only_change_is_conflict_and_does_not_consume(client, monkeypatch):
    from datetime import timedelta
    from backend.models.alert_event import AlertEvent
    from backend.models.assistant_event import AssistantEventProposal, AssistantEventOperation
    c, factory = client
    monkeypatch.setenv('ASSISTANT_EVENT_WRITES_ENABLED', 'true')
    p = proposal(c).json()
    with factory() as db:
        ev = db.get(AlertEvent, 'evt_test')
        ev.updated_at += timedelta(seconds=1)
        db.commit()
    response = c.post(f"/api/assistant/event-proposals/{p['proposal_id']}/confirm", json={'session_id': 's', 'idempotency_key': 'version'})
    assert response.status_code == 409
    with factory() as db:
        assert db.get(AlertEvent, 'evt_test').status.value == 'pending'
        assert db.get(AssistantEventProposal, p['proposal_id']).consumed_at is None
        assert db.query(AssistantEventOperation).count() == 0


def test_proposal_replay_new_key_and_key_reuse_other_proposal(client, monkeypatch):
    c, _ = client
    monkeypatch.setenv('ASSISTANT_EVENT_WRITES_ENABLED', 'true')
    first, second = proposal(c).json(), proposal(c).json()
    url = f"/api/assistant/event-proposals/{first['proposal_id']}/confirm"
    assert c.post(url, json={'session_id': 's', 'idempotency_key': 'one'}).status_code == 200
    assert c.post(url, json={'session_id': 's', 'idempotency_key': 'two'}).status_code == 409
    assert c.post(f"/api/assistant/event-proposals/{second['proposal_id']}/confirm", json={'session_id': 's', 'idempotency_key': 'one'}).status_code == 409


def test_terminal_transition_and_blank_reason_rejected(client, monkeypatch):
    from backend.models.alert_event import AlertEvent, EventStatus
    c, factory = client
    monkeypatch.setenv('ASSISTANT_EVENT_WRITES_ENABLED', 'true')
    with factory() as db:
        db.get(AlertEvent, 'evt_test').status = EventStatus.resolved
        db.commit()
    assert proposal(c).status_code == 400
    assert c.post('/api/assistant/event-proposals', json={'session_id': 's', 'event_id': 'evt_test', 'new_status': 'processing', 'reason': '   '}).status_code == 422
