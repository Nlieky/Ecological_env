import json
from pathlib import Path
import pytest

READY = {'pageId': 'dashboard', 'plant': 'fixture', 'source': 'fixture-source', 'range': {'start': '2026-01-01T00:00:00Z', 'end': '2026-01-01T01:00:00Z'}}


def test_registry_and_generated_contract():
    from shared.assistant.contract import contract_document, CAPABILITIES
    from shared.assistant.protocol import SCHEMAS
    document = contract_document()
    assert set(CAPABILITIES) == set(SCHEMAS)
    assert CAPABILITIES['audit.focus']['target_path'] == '/agents/audit'
    assert CAPABILITIES['graph.focus']['target_path'] == '/agents/knowledge'
    assert CAPABILITIES['strategy.draft']['target_path'] == '/agents/config'
    for item in document['capabilities']:
        assert {'id', 'target_page', 'target_path', 'title', 'parameters', 'required', 'inheritance', 'defaults', 'readiness', 'invalidation', 'level'} <= set(item)
    assert json.loads(Path('frontend/src/assistant/contract.generated.json').read_text(encoding='utf-8')) == document


def test_redundant_navigation_is_removed_using_registered_target_not_user_phrases():
    from shared.assistant.master_turn import parse_turn
    raw = {'message': '准备筛选', 'actions': [
        {'capability': 'navigate', 'parameters': {'pageId': 'logs'}},
        {'capability': 'logs.filter', 'parameters': {'module': 'api'}}]}
    result = parse_turn(json.dumps(raw), 's', {})
    assert [action['capability'] for action in result['actions']] == ['logs.filter']


def test_operation_message_reflects_validated_preparation_not_model_claims():
    from shared.assistant.master_turn import parse_turn
    incomplete = parse_turn(json.dumps({'message': '已经执行完毕', 'intent': {'capability': 'logs.filter', 'parameters': {}}}), 's', {})
    assert '补充' in incomplete['message'] and '执行完毕' not in incomplete['message']
    complete = parse_turn(json.dumps({'message': '已经执行完毕', 'intent': {'capability': 'logs.filter', 'parameters': {'module': 'api'}}}), 's', {})
    assert '准备' in complete['message'] and '执行完毕' not in complete['message']


def test_runtime_retries_one_invalid_protocol_without_executing_anything():
    from shared.assistant.master_turn import SystemInteractionRuntime
    messages = []
    class Agent:
        def run_conversation(self, **kwargs):
            messages.append(json.loads(kwargs['user_message']))
            if len(messages) == 1:
                return {'final_response': json.dumps({'message': 'bad', 'intent': {'capability': 'logs.filter', 'parameters': {'private': 'not-allowed'}}})}
            return {'final_response': json.dumps({'message': 'prepared', 'intent': {'capability': 'logs.filter', 'parameters': {'module': 'error'}}})}
    runtime = SystemInteractionRuntime(lambda key: Agent(), Path('skills/system-interaction-core/SKILL.md'))
    result = runtime.respond({'query': '只准备日志筛选', 'session_id': 'repair'})
    assert len(messages) == 2
    assert messages[0]['context'] == messages[1]['context']
    assert messages[1]['protocol_feedback']['code'] == 'invalid_parameters'
    assert [action['capability'] for action in result['actions']] == ['logs.filter']


def turn(intent, context=None, pending=None):
    from shared.assistant.master_turn import parse_turn
    return parse_turn(json.dumps({'message': '准备候选', 'actions': [], 'intent': intent}), 's', context or {}, pending)


def test_inheritance_defaults_and_pending_completion():
    context = {**READY, 'indicator': 'TN', 'filters': {'side': 'influent'}, 'revision': 2}
    first = turn({'capability': 'dashboard.detect', 'parameters': {}}, context)
    assert first['actions'] == []
    assert first['pending']['missing'] == ['algorithm']
    done = turn({'capability': 'dashboard.detect', 'parameters': {}, 'use_defaults': True}, context, first['pending'])
    action = done['actions'][0]
    assert action['parameters'] == {'indicator': 'TN', 'side': 'influent', 'algorithm': 'iforest'}
    assert action['parameter_sources'] == {'indicator': 'context', 'side': 'context', 'algorithm': 'default'}
    assert 'contract_version' in action
    assert turn({'capability': 'dashboard.detect', 'parameters': {}}, {'pageId': 'dashboard', 'filters': {'side': 'all'}})['pending']['missing'] == ['algorithm', 'indicator', 'side']


def test_pending_explicit_merge_reset_and_version():
    first = turn({'capability': 'dashboard.detect', 'parameters': {'indicator': 'COD'}}, READY)
    done = turn({'capability': 'dashboard.detect', 'parameters': {'side': 'effluent', 'algorithm': 'constant'}}, READY, pending=first['pending'])
    assert done['actions'][0]['parameters']['indicator'] == 'COD'
    assert turn({'capability': 'dashboard.detect', 'parameters': {}, 'reset': True}, pending=first['pending'])['pending']['parameters'] == {}
    first['pending']['contract_version'] = 'obsolete'
    with pytest.raises(ValueError):
        turn({'capability': 'dashboard.detect', 'parameters': {}}, pending=first['pending'])


@pytest.mark.parametrize('intent', [
    {'capability': 'delete', 'parameters': {}},
    {'capability': 'dashboard.detect', 'parameters': {'algorithm': 'magic'}},
    {'capability': 'navigate', 'parameters': {'pageId': 'events'}, 'parameter_sources': {}},
    {'capability': 'navigate', 'parameters': {'pageId': 'events'}, 'use_defaults': 'yes'},
])
def test_safe_structured_errors(intent):
    from shared.assistant.protocol import ProtocolError
    with pytest.raises(ProtocolError) as error:
        turn(intent)
    assert error.value.code and error.value.path
    assert 'magic' not in str(error.value)


def test_proxy_validation_preserves_server_sources():
    from shared.assistant.master_turn import validate_response
    prepared = turn({'capability': 'dashboard.detect', 'parameters': {'indicator': 'TP', 'side': 'influent'}, 'use_defaults': True}, READY)
    assert validate_response(prepared, 's', {}) == prepared
    prepared['actions'][0]['parameter_sources']['algorithm'] = 'forged'
    with pytest.raises(ValueError):
        validate_response(prepared, 's', {})


def test_pending_binding_and_untrusted_metadata():
    from copy import deepcopy
    from backend.models.assistant import RespondRequest
    first = turn({'capability': 'dashboard.detect', 'parameters': {}}, {'pageId': 'dashboard', 'indicator': 'TN', 'source': 'one'})
    with pytest.raises(ValueError, match='stale_context'):
        turn({'capability': 'dashboard.detect', 'parameters': {}}, {'pageId': 'dashboard', 'indicator': 'TN', 'source': 'two'}, first['pending'])
    for mutation in ({'missing': []}, {'parameter_sources': {'indicator': 'default'}}, {'parameters': {'indicator': 'bogus'}}):
        pending = {**deepcopy(first['pending']), **mutation}
        with pytest.raises(ValueError):
            RespondRequest(query='x', session_id='s', pending=pending)
    from shared.assistant.master_turn import parse_turn
    for metadata in ({'contract_version': '1.0.0'}, {'parameter_sources': {}}, {'context': {}}):
        raw = {'message': 'x', 'actions': [{'capability': 'navigate', 'parameters': {'pageId': 'events'}, **metadata}]}
        with pytest.raises(ValueError):
            parse_turn(json.dumps(raw), 's', {})


def test_runtime_safe_protocol_diagnostics(caplog):
    from shared.assistant.master_turn import SystemInteractionRuntime
    from fastapi import HTTPException
    class Agent:
        def run_conversation(self, **kwargs):
            return {'final_response': json.dumps({'message': 'secret-model', 'intent': {'capability': 'dashboard.detect', 'parameters': {'algorithm': 'private-algorithm'}}})}
    runtime = SystemInteractionRuntime(lambda key: Agent(), Path('skills/system-interaction-core/SKILL.md'))
    with pytest.raises(HTTPException) as error:
        runtime.respond({'query': 'secret-user', 'session_id': 'secret-session'})
    assert error.value.status_code == 502
    assert '参数无效' in error.value.detail
    assert 'capability=dashboard.detect path=parameters.algorithm code=invalid_parameters' in caplog.text
    assert not any(secret in caplog.text + error.value.detail for secret in ('secret-model', 'private-algorithm', 'secret-user', 'secret-session'))


@pytest.mark.parametrize('context', [{}, {**READY, 'status': 'loading'}, {**READY, 'source': '未核验'}, {**READY, 'range': '24h'}, {**READY, 'range': {'start': '', 'end': ''}}])
def test_detection_binding_must_be_ready(context):
    with pytest.raises(ValueError, match='not_ready'):
        turn({'capability': 'dashboard.detect', 'parameters': {'indicator': 'TN', 'side': 'influent', 'algorithm': 'constant'}}, context)


@pytest.mark.parametrize('detail,expected', [('系统助手参数无效，未执行任何操作。', '参数无效'), ('secret upstream body', '返回无效')])
def test_proxy_relays_only_allowlisted_safe_diagnostics(monkeypatch, detail, expected):
    import asyncio
    from backend.services import assistant_service
    from backend.models.assistant import RespondRequest
    from fastapi import HTTPException
    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs):
            return assistant_service.httpx.Response(502, json={'detail': detail})
    monkeypatch.setattr(assistant_service.httpx, 'AsyncClient', Client)
    with pytest.raises(HTTPException) as error:
        asyncio.run(assistant_service.respond(RespondRequest(query='x', session_id='s')))
    assert expected in error.value.detail
    assert 'secret' not in error.value.detail


def test_non_string_capability_uses_structured_error():
    from shared.assistant.protocol import validate_actions, ProtocolError
    with pytest.raises(ProtocolError):
        validate_actions([{'capability': [], 'parameters': {}}])


@pytest.mark.parametrize('sources', [[], None, 'explicit', 1])
def test_malformed_prepared_sources_are_protocol_errors(sources):
    from shared.assistant.master_turn import validate_response
    from shared.assistant.protocol import ProtocolError
    prepared = turn({'capability': 'navigate', 'parameters': {'pageId': 'events'}})
    prepared['actions'][0]['parameter_sources'] = sources
    with pytest.raises(ProtocolError):
        validate_response(prepared, 's', {})


def test_pending_known_loading_binding_can_finish_when_ready():
    first = turn({'capability': 'dashboard.detect', 'parameters': {'indicator': 'TN'}}, {**READY, 'status': 'loading', 'revision': 1})
    done = turn({'capability': 'dashboard.detect', 'parameters': {'algorithm': 'constant', 'side': 'influent'}}, {**READY, 'status': 'ready', 'revision': 2}, first['pending'])
    action = done['actions'][0]
    assert action['context']['range'] == READY['range']
    assert action['context']['plant'] == READY['plant']
    assert action['context']['revision'] == 1
    assert action['context']['status'] == 'ready'


@pytest.mark.parametrize('capability,parameters,page', [('strategy.draft', {'conclusion_first': True}, 'config')])
def test_relative_target_readiness_but_not_source_readiness(capability, parameters, page):
    with pytest.raises(ValueError, match='not_ready'):
        turn({'capability': capability, 'parameters': parameters}, {'pageId': page, 'status': 'loading'})
    assert turn({'capability': capability, 'parameters': parameters}, {'pageId': 'events', 'status': 'error'})['actions']


@pytest.mark.parametrize('status', ['empty', 'loading'])
@pytest.mark.parametrize('capability,parameters,page', [('dashboard.view', {'plant': 'fixture'}, 'dashboard'), ('dashboard.range', {'range': '6h'}, 'dashboard'), ('metrics.filter', {'indicator': 'TN'}, 'metrics')])
def test_reload_operations_can_recover_unready_data(capability, parameters, page, status):
    assert turn({'capability': capability, 'parameters': parameters}, {'pageId': page, 'status': status})['actions']
