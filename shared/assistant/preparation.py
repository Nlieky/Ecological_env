"""Deterministic preparation; model proposals never supply execution metadata."""
from copy import deepcopy
import json
from datetime import datetime
from .contract import CAPABILITIES, CONTRACT_VERSION
from .protocol import ProtocolError, validate_actions


def get_path(context, path):
    value = context
    for part in path.split('.'):
        value = value.get(part) if isinstance(value, dict) else None
    return value


def clean_context(context):
    from backend.models.assistant import AssistantContext
    try:
        return AssistantContext.model_validate(context or {}).model_dump()
    except (ValueError, TypeError):
        raise ProtocolError('invalid_metadata', 'context') from None


def validate_parameters(capability, parameters):
    if not isinstance(capability, str) or capability not in CAPABILITIES:
        raise ProtocolError('unsupported_capability', 'intent')
    if not isinstance(parameters, dict):
        raise ProtocolError('invalid_parameters', 'parameters', capability)
    # Validate each supplied field without pretending absent fields were supplied.
    schema = CAPABILITIES[capability]['parameters']
    for key, value in parameters.items():
        if key not in schema:
            raise ProtocolError('invalid_parameters', 'parameters', capability)
        rule = schema[key]
        valid = (isinstance(value, str) and 0 < len(value.strip()) <= 256) if rule == 'text' else (type(value) is bool) if rule == 'bool' else (isinstance(value, str) and value in rule)
        if not valid:
            raise ProtocolError('invalid_parameters', 'parameters.' + key, capability)


def validate_pending(pending):
    if not isinstance(pending, dict) or set(pending) != {'capability', 'parameters', 'missing', 'parameter_sources', 'context', 'contract_version', 'use_defaults'} or len(json.dumps(pending, ensure_ascii=False)) > 12000:
        raise ProtocolError('invalid_metadata', 'pending')
    capability = pending['capability']
    validate_parameters(capability, pending['parameters'])
    if pending['contract_version'] != CONTRACT_VERSION:
        raise ProtocolError('contract_version', 'contract_version', capability)
    if type(pending['use_defaults']) is not bool:
        raise ProtocolError('invalid_metadata', 'pending', capability)
    sources = pending['parameter_sources']
    if not isinstance(sources, dict) or set(sources) != set(pending['parameters']) or any(v not in ('explicit', 'context', 'default') for v in sources.values()):
        raise ProtocolError('invalid_metadata', 'parameter_sources', capability)
    context = clean_context(pending['context'])
    descriptor = CAPABILITIES[capability]
    for key, source in sources.items():
        if source == 'context' and (context['pageId'] != descriptor['target_page'] or key not in descriptor['inheritance'] or get_path(context, descriptor['inheritance'][key]) != pending['parameters'][key]):
            raise ProtocolError('invalid_metadata', 'parameter_sources', capability)
        if source == 'default' and (not pending['use_defaults'] or descriptor['defaults']['values'].get(key) != pending['parameters'][key]):
            raise ProtocolError('invalid_metadata', 'parameter_sources', capability)
    missing = missing_parameters(capability, pending['parameters'])
    if pending['missing'] != missing:
        raise ProtocolError('invalid_metadata', 'pending', capability)
    return {**deepcopy(pending), 'context': context}


def missing_parameters(capability, parameters):
    descriptor = CAPABILITIES[capability]
    return [key for key in descriptor['required'] if key not in parameters] or (list(descriptor['parameters']) if not parameters else [])


def validate_readiness(capability, context):
    descriptor = CAPABILITIES[capability]
    policy = descriptor['readiness']
    if context['pageId'] == descriptor['target_page'] and policy['status'] and context['status'] not in policy['status']:
        raise ProtocolError('not_ready', 'context', capability)
    if not policy['required_context']:
        return
    ready = context['pageId'] == descriptor['target_page'] and context['status'] in policy['status']
    ready = ready and all(context.get(key) for key in policy['required_context']) and context['source'] != '未核验'
    bounds = context.get('range')
    try:
        ready = ready and isinstance(bounds, dict) and bool(bounds.get('start')) and bool(bounds.get('end'))
        if ready:
            ready = datetime.fromisoformat(bounds['start'].replace('Z', '+00:00')) < datetime.fromisoformat(bounds['end'].replace('Z', '+00:00'))
    except (ValueError, TypeError):
        ready = False
    if not ready:
        raise ProtocolError('not_ready', 'context', capability)


def prepare_intent(intent, context, pending=None):
    if not isinstance(intent, dict) or set(intent) - {'capability', 'parameters', 'use_defaults', 'reset'} or not {'capability', 'parameters'} <= set(intent):
        raise ProtocolError('invalid_response', 'intent')
    capability, explicit = intent['capability'], intent['parameters']
    validate_parameters(capability, explicit)
    if any(type(intent[key]) is not bool for key in ('use_defaults', 'reset') if key in intent):
        raise ProtocolError('invalid_metadata', 'intent', capability)
    descriptor = CAPABILITIES[capability]
    context = clean_context(context)
    params, sources = {}, {}
    delegated = intent.get('use_defaults', False)
    if pending is not None and not intent.get('reset'):
        pending = validate_pending(pending)
        if pending['capability'] == capability:
            if any(get_path(pending['context'], key) != get_path(context, key) for key in descriptor['invalidation']['fields']):
                raise ProtocolError('stale_context', 'context', capability)
            # Readiness can progress without changing any semantic binding.
            # Preserve the original object/window and diagnostic revision.
            context = {**pending['context'], 'status': context['status']}
            params, sources = pending['parameters'].copy(), pending['parameter_sources'].copy()
            delegated = intent.get('use_defaults', pending['use_defaults'])
    if not delegated:
        for key in list(params):
            if sources[key] == 'default':
                del params[key]
                del sources[key]
    params.update(explicit)
    sources.update({key: 'explicit' for key in explicit})
    if context['pageId'] == descriptor['target_page']:
        for key, path in descriptor['inheritance'].items():
            if key in params:
                continue
            value = get_path(context, path)
            try:
                validate_parameters(capability, {key: value})
            except ProtocolError:
                continue
            params[key], sources[key] = value, 'context'
    if delegated:
        for key, value in descriptor['defaults']['values'].items():
            if key not in params:
                params[key], sources[key] = value, 'default'
    missing = missing_parameters(capability, params)
    prepared = {'capability': capability, 'parameters': params, 'parameter_sources': sources, 'context': context, 'contract_version': CONTRACT_VERSION}
    if missing:
        return {'actions': [], 'pending': {**prepared, 'missing': missing, 'use_defaults': delegated}}
    validate_readiness(capability, context)
    validate_actions([{'capability': capability, 'parameters': params}])
    return {'actions': [prepared]}


def validate_prepared_actions(actions):
    if not isinstance(actions, list) or len(actions) > 5:
        raise ProtocolError('invalid_response', 'actions')
    for action in actions:
        if not isinstance(action, dict):
            raise ProtocolError('invalid_response', 'actions')
        base = {key: value for key, value in action.items() if key not in {'contract_version', 'parameter_sources', 'context'}}
        validate_actions([base])
        metadata = set(action) & {'contract_version', 'parameter_sources', 'context'}
        if metadata:
            if len(metadata) != 3:
                raise ProtocolError('invalid_metadata', 'actions')
            if not isinstance(action['parameter_sources'], dict):
                raise ProtocolError('invalid_metadata', 'parameter_sources', action['capability'])
            validate_pending({**{key: action[key] for key in ('capability', 'parameters', 'parameter_sources', 'context', 'contract_version')}, 'missing': [], 'use_defaults': any(v == 'default' for v in action['parameter_sources'].values())})
            validate_readiness(action['capability'], clean_context(action['context']))
    return actions
