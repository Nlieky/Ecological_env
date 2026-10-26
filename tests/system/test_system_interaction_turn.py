import json
import threading
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from shared.assistant.master_turn import SystemInteractionRuntime, parse_turn, restrict_agent

SKILL = Path('skills/system-interaction-core/SKILL.md')
sys.path.insert(0, str(Path('shared/framework/hermes-agent').resolve()))


def payload(session='s'):
    return {'query': '帮助', 'session_id': session, 'context': {'pageId': 'events'}}


def test_two_sessions_overlap_and_same_session_busy(monkeypatch):
    from scripts.start_agent import AgentService
    barrier = threading.Barrier(3)
    release = threading.Event()
    calls = []
    class Agent:
        def run_conversation(self, **kwargs):
            calls.append(kwargs)
            barrier.wait(3)
            release.wait(3)
            return {'final_response': '{"message":"帮助","actions":[]}'}
    service = AgentService()
    service.master_agent = object()
    monkeypatch.setattr(service, '_create_main_agent', lambda **kwargs: Agent())
    runtime = service.system_interaction
    professional_lock = service._agent_lock
    professional_lock.acquire()
    with ThreadPoolExecutor(2) as pool:
        a = pool.submit(runtime.respond, payload('a'))
        b = pool.submit(runtime.respond, payload('b'))
        barrier.wait(3)
        with pytest.raises(HTTPException) as error:
            runtime.respond(payload('a'))
        assert error.value.status_code == 409
        assert professional_lock.locked()
        release.set()
        assert a.result()['session_id'] == 'a'
        assert b.result()['session_id'] == 'b'
    professional_lock.release()
    assert len({c['task_id'] for c in calls}) == 2
    assert all(c['task_id'].startswith('system-assistant:') for c in calls)


def test_timeout_quarantines_only_worker_and_retains_capacity():
    release = threading.Event()
    made = []
    class Agent:
        def run_conversation(self, **kwargs):
            release.wait(3)
            return {'final_response': '{"message":"ok"}'}
    def factory(sid):
        made.append(sid)
        return Agent()
    runtime = SystemInteractionRuntime(factory, SKILL, capacity=1, timeout=.02)
    with pytest.raises(HTTPException) as error:
        runtime.respond(payload())
    assert error.value.status_code == 504
    with pytest.raises(HTTPException) as error:
        runtime.respond(payload('other'))
    assert error.value.status_code == 409
    release.set()
    for entry in runtime._sessions.values():
        while entry['busy']:
            threading.Event().wait(.001)
    assert runtime.respond(payload())['message'] == 'ok'
    assert len(made) == 2


def test_dispatch_denied_even_if_model_requests_hidden_tool():
    agent = restrict_agent(SimpleNamespace())
    assert agent.tools == [] and agent.valid_tool_names == set()
    for name in ('_invoke_tool', '_execute_tool_calls', '_execute_tool_calls_concurrent', '_execute_tool_calls_sequential'):
        with pytest.raises(PermissionError):
            getattr(agent, name)('terminal', {})


def test_restriction_disables_snapshot_trajectory_and_error_debug_persistence():
    writes = []
    agent = SimpleNamespace(_session_json_enabled=True, save_trajectories=True,
                            _save_session_log=lambda *a, **k: writes.append('session'),
                            _save_trajectory=lambda *a, **k: writes.append('trajectory'),
                            _dump_api_request_debug=lambda *a, **k: writes.append('debug'))
    restrict_agent(agent)
    assert agent._session_json_enabled is False
    assert agent.save_trajectories is False
    agent._save_session_log([{'content':'private'}])
    agent._save_trajectory([], 'private', False)
    agent._dump_api_request_debug({'messages':['private']}, reason='failure')
    assert writes == []


def test_restricted_identity_reads_same_workspace_identity_without_private_files(tmp_path):
    for name, text in {'IDENTITY.md':'main identity', 'SOUL.md':'main soul',
                       'MEMORY.md':'private memory', 'USER.md':'private user',
                       'AGENTS.md':'professional tool instructions'}.items():
        (tmp_path / name).write_text(text, encoding='utf-8')
    agent = restrict_agent(SimpleNamespace(_identity_path=tmp_path))
    from shared.framework.hermes_agent.agent.identity_loader import load_identity_files_from_path
    filenames = getattr(agent, '_identity_filenames', None)
    # Match the real framework loader, including its default full-identity behavior.
    prompt = (load_identity_files_from_path(agent._identity_path, filenames=filenames)
              if filenames is not None else load_identity_files_from_path(agent._identity_path))
    assert 'main identity' in prompt and 'main soul' in prompt
    assert 'private memory' not in prompt and 'private user' not in prompt
    assert 'professional tool instructions' not in prompt


def test_parser_handoff_context_bound_and_no_action_inference():
    result = parse_turn('```json\n{"message":"专业问题","handoff":{"query":"任意专业请求"}}\n```', 's', {'pageId':'events'})
    assert result['handoff'] == {'query':'任意专业请求', 'context':{'pageId':'events'}}
    assert parse_turn('打开事件中心', 's', {})['actions'] == []
    for raw in ('{"message":"partial",', '{"message":"x","actions":[{"capability":"delete","parameters":{}}]}'):
        with pytest.raises(ValueError):
            parse_turn(raw, 's', {})


def test_handoff_is_one_draft_operation_not_an_extra_navigation_sequence():
    raw = json.dumps({'message':'请查看交接草稿', 'actions':[{'capability':'navigate','parameters':{'pageId':'chat'}}],
                      'handoff':{'query':'专业报告'}})
    result = parse_turn(raw, 's', {'pageId':'dashboard'})
    assert result['handoff']['query'] == '专业报告'
    assert result['actions'] == []


def test_offline_and_invalid_output_do_not_fallback():
    runtime = SystemInteractionRuntime(lambda sid: None, SKILL, ready=lambda: False)
    with pytest.raises(HTTPException) as error:
        runtime.respond(payload())
    assert error.value.status_code == 503


def test_invalid_model_output_is_502_and_evicts_failed_instance():
    made = []
    class Agent:
        def run_conversation(self, **kwargs):
            return {'final_response': '{"message":"partial",'}
        def release_clients(self):
            made.append('released')
    runtime = SystemInteractionRuntime(lambda sid: Agent(), SKILL)
    for _ in range(2):
        with pytest.raises(HTTPException) as error:
            runtime.respond(payload())
        assert error.value.status_code == 502
    assert made == ['released']


def test_cache_bound_releases_idle_clients_and_history_comes_only_from_client():
    calls, released = [], []
    class Agent:
        def run_conversation(self, **kwargs):
            calls.append(kwargs)
            return {'final_response': '{"message":"ok"}', 'messages': [{'role':'assistant','content':'private prior response'}]}
        def release_clients(self):
            released.append(True)
    runtime = SystemInteractionRuntime(lambda sid: Agent(), SKILL, max_sessions=1)
    runtime.respond(payload('a'))
    req = payload('b')
    req['history'] = [{'role':'user','content':'client history'}]
    runtime.respond(req)
    assert len(runtime._sessions) == 1 and released == [True]
    assert calls[0]['conversation_history'] == []
    assert calls[1]['conversation_history'] == req['history']


def test_professional_http_callers_cannot_use_reserved_namespace():
    from scripts.start_agent import _reject_reserved_session
    with pytest.raises(HTTPException) as error:
        _reject_reserved_session('system-assistant:abc')
    assert error.value.status_code == 409
    _reject_reserved_session('normal')


def test_chat_completion_sidebar_requests_json_without_changing_professional_mode(monkeypatch):
    from scripts import start_agent
    monkeypatch.setattr(start_agent._lp, 'seed_defaults', lambda: None)
    monkeypatch.setattr(start_agent._lp, 'resolve_default', lambda: {'model':'fixture','base_url':'https://fixture.invalid','api_key':'private'})
    monkeypatch.setattr(start_agent, 'AIAgent', lambda **kwargs: SimpleNamespace(api_mode='chat_completions', request_overrides={}))
    service = start_agent.AgentService()
    main = service._create_main_agent()
    sidebar = service._create_main_agent(system_interaction=True, session_id='side')
    assert main.request_overrides == {}
    assert sidebar.request_overrides.get('response_format') == {'type':'json_object'}
