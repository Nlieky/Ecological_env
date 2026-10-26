"""Saved settings are read at documented runtime boundaries; no live services."""
import asyncio
import ast
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def test_classifier_reads_timeout_each_call(monkeypatch):
    spec = importlib.util.spec_from_file_location('effect_classifier', ROOT / 'skills/action-command-core/scripts/action_classifier.py')
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='NOT_ACTION'))])
    monkeypatch.setattr(mod, '_get_client', lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    values = iter([7, 11])
    monkeypatch.setattr('backend.services.agent_strategy.get_strategy', lambda *a, **k: next(values))
    assert not mod.classify_action('hello').is_action
    assert not mod.classify_action('hello').is_action
    assert [c.get('timeout') for c in calls] == [7, 11]
    mod.classify_action('hello', timeout_s=3)
    assert calls[-1]['timeout'] == 3


def test_empty_strategy_does_not_request_restart(monkeypatch):
    from backend.api.v1.agents.config import routes
    persisted = []
    monkeypatch.setattr('backend.services.agent_strategy.set_strategy', lambda *a: persisted.append(a))
    result = asyncio.run(routes.put_strategy(routes.StrategyBody(items={'default_llm_provider': ''})))
    assert result['restart_needed'] is False
    assert result['applied_keys'] == []
    assert result['effects'] == {}
    assert persisted == []


def test_status_distinguishes_reachable_and_ready(monkeypatch):
    from backend.services import agent_service_control as svc
    monkeypatch.setattr(svc, '_pids_by_port', lambda p: [])
    monkeypatch.setattr('backend.services.agent_params.get_param', lambda *a, **k: 'saved-model')
    monkeypatch.setattr('httpx.get', lambda *a, **k: SimpleNamespace(status_code=200, json=lambda: {'agent_initialized': False}))
    result = svc.get_status()
    assert result['alive'] is True
    assert result['ready'] is False
    assert result['saved_model'] == 'saved-model'


def test_restart_waits_for_initialized_agent(monkeypatch):
    from backend.services import agent_service_control as svc
    monkeypatch.setattr(svc, '_pids_by_port', lambda p: [])
    monkeypatch.setattr(svc.time, 'sleep', lambda n: None)
    launches = []
    monkeypatch.setattr(svc.subprocess, 'Popen', lambda *a, **k: launches.append(k))
    monkeypatch.setattr('httpx.get', lambda *a, **k: SimpleNamespace(status_code=200, json=lambda: {'agent_initialized': False}))
    result = svc.restart_agent(True)
    assert result['ok'] is False
    assert result['new_alive'] is True
    assert result['new_ready'] is False
    if svc.os.name == 'nt':
        assert launches[0]['creationflags'] == 0x08000000


@pytest.mark.parametrize('kind', ['params', 'strategy'])
@pytest.mark.parametrize('invalid', [0, True, 1.5, '1.0'])
def test_positive_integer_validation(kind, invalid, monkeypatch):
    from fastapi import HTTPException
    from backend.api.v1.agents.config import routes
    if kind == 'params':
        monkeypatch.setattr('backend.services.agent_params.set_param', lambda *a: None)
        call = routes.put_params(routes.ParamsBody(params={'agent_timeout': invalid}))
    else:
        monkeypatch.setattr('backend.services.agent_strategy.set_strategy', lambda *a: None)
        call = routes.put_strategy(routes.StrategyBody(items={'action_shortcircuit_timeout': invalid}))
    with pytest.raises(HTTPException):
        asyncio.run(call)


def test_view_context_toggle_controls_detector_and_message():
    tree = ast.parse((ROOT / 'scripts/start_agent.py').read_text(encoding='utf-8'))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_query_view_context')
    namespace = {'_gst': lambda *a: False, 'json': __import__('json')}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), 'start_agent.py', 'exec'), namespace)
    request = SimpleNamespace(query='question', view_context='{"anchor":"2026-10-01"}')
    assert namespace['_query_view_context'](request) == ({}, 'question')
    namespace['_gst'] = lambda *a: True
    context, message = namespace['_query_view_context'](request)
    assert context == {'anchor': '2026-10-01'}
    assert '2026-10-01' in message


def test_registry_describes_actual_read_boundaries():
    from backend.services.agent_params import PARAM_REGISTRY
    from backend.services.agent_strategy import STRATEGY_REGISTRY
    assert PARAM_REGISTRY['subagent_timeout']['effect'] == 'immediate'
    assert PARAM_REGISTRY['subagent_max_iterations']['effect'] == 'immediate'
    assert '新子智能体' in PARAM_REGISTRY['subagent_max_iterations']['read_timing']
    assert '重启' in PARAM_REGISTRY['hermes_total_timeout']['read_timing']
    assert STRATEGY_REGISTRY['action_shortcircuit_timeout']['effect'] == 'immediate'
    assert '每次分类' in STRATEGY_REGISTRY['action_shortcircuit_timeout']['read_timing']


def test_params_report_only_persisted_keys(monkeypatch):
    from backend.api.v1.agents.config import routes
    persisted = []
    monkeypatch.setattr('backend.services.agent_params.set_param', lambda *a: persisted.append(a))
    result = asyncio.run(routes.put_params(routes.ParamsBody(params={'llm_api_key': '', 'agent_timeout': 100})))
    assert result['applied_keys'] == ['agent_timeout']
    assert result['effects'] == {'agent_timeout': 'immediate'}
    assert result['restart_needed'] is False
    assert persisted == [('agent_timeout', '100')]


def test_restart_succeeds_only_after_ready(monkeypatch):
    from backend.services import agent_service_control as svc
    monkeypatch.setattr(svc, '_pids_by_port', lambda p: [])
    monkeypatch.setattr(svc.time, 'sleep', lambda n: None)
    monkeypatch.setattr(svc.subprocess, 'Popen', lambda *a, **k: None)
    statuses = iter([False, True])
    def health(*a, **k):
        ready = next(statuses)
        return SimpleNamespace(status_code=200, json=lambda: {'agent_initialized': ready})
    monkeypatch.setattr('httpx.get', health)
    assert svc.restart_agent(True) == {'ok': True, 'old_pids': [], 'new_alive': True, 'new_ready': True}


@pytest.mark.parametrize('kind', ['params', 'strategy'])
def test_integral_float_is_persisted_as_canonical_integer(kind, monkeypatch):
    from backend.api.v1.agents.config import routes
    persisted = []
    if kind == 'params':
        from backend.services.agent_params import _convert
        monkeypatch.setattr('backend.services.agent_params.set_param', lambda *a: persisted.append(a))
        result = asyncio.run(routes.put_params(routes.ParamsBody(params={'agent_timeout': 1.0})))
        key = 'agent_timeout'
        convert = lambda raw: _convert(raw, 'int')
    else:
        from backend.services.agent_strategy import _convert, STRATEGY_REGISTRY
        monkeypatch.setattr('backend.services.agent_strategy.set_strategy', lambda *a: persisted.append(a))
        result = asyncio.run(routes.put_strategy(routes.StrategyBody(items={'action_shortcircuit_timeout': 1.0})))
        key = 'action_shortcircuit_timeout'
        convert = lambda raw: _convert(raw, STRATEGY_REGISTRY[key])
    assert result['success'] is True
    assert persisted == [(key, '1')]
    assert convert(persisted[0][1]) == 1


@pytest.mark.parametrize('kind', ['params', 'strategy'])
def test_infinite_integer_input_is_a_validation_error(kind, monkeypatch):
    from fastapi import HTTPException
    from backend.api.v1.agents.config import routes
    persisted = []
    if kind == 'params':
        monkeypatch.setattr('backend.services.agent_params.set_param', lambda *a: persisted.append(a))
        call = routes.put_params(routes.ParamsBody(params={'agent_timeout': float('inf')}))
    else:
        monkeypatch.setattr('backend.services.agent_strategy.set_strategy', lambda *a: persisted.append(a))
        call = routes.put_strategy(routes.StrategyBody(items={'action_shortcircuit_timeout': float('inf')}))
    with pytest.raises(HTTPException) as error:
        asyncio.run(call)
    assert error.value.status_code == 400
    assert persisted == []
