"""Shared allowlisted system-interaction response protocol."""
import json
import re
from .contract import SCHEMAS, PAGES

SAFE_ERROR_DETAILS = {
    'missing_parameters': '系统助手参数缺失，未执行任何操作。',
    'unsupported_capability': '系统助手能力不支持，未执行任何操作。',
    'invalid_parameters': '系统助手参数无效，未执行任何操作。',
    'stale_context': '页面对象或采样窗口已变化，请重新准备。',
    'not_ready': '页面数据或采样窗口尚未就绪，请等待后重新准备。',
    'contract_version': '操作契约版本已变化，请刷新后重新准备。',
    'invalid_response': '系统助手响应格式错误，未执行任何操作。',
}


class ProtocolError(ValueError):
    """Only allowlisted codes/paths are safe to show in logs and responses."""
    def __init__(self, code='invalid_response', path='response', capability=None):
        codes = {'invalid_response', 'unsupported_capability', 'invalid_parameters', 'missing_parameters', 'invalid_metadata', 'contract_version', 'stale_context', 'not_ready', 'invalid_json'}
        self.code = code if code in codes else 'invalid_response'
        self.capability = capability if isinstance(capability, str) and capability in SCHEMAS else 'unknown'
        safe_paths = {'response', 'intent', 'actions', 'pending', 'context', 'contract_version', 'parameters', 'parameter_sources', 'message', 'handoff'}
        safe_paths.update('parameters.' + key for schema in SCHEMAS.values() for key in schema)
        self.path = path if path in safe_paths else 'response'
        super().__init__(self.code + ':' + self.path)

def parse_model_answer(raw):
    if not isinstance(raw, str) or not raw.strip() or len(raw) > 12000:
        raise ValueError('Invalid model content')
    text = raw.strip()
    fence = re.fullmatch(r'```(?:json)?\s*\n?(.*?)\n?```', text, flags=re.DOTALL | re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    try:
        content = json.loads(text)
    except json.JSONDecodeError:
        # Prose is display-only. Never infer actions or salvage malformed JSON.
        if fence or text.startswith(('{', '[', '```')) or len(text) > 6000:
            raise
        return {'message': text + '\n（仅文字说明，未执行任何操作。）', 'actions': []}
    if not isinstance(content, dict) or set(content) - {'message', 'actions'} or not isinstance(content.get('message'), str) or not 0 < len(content['message']) <= 6000:
        raise ValueError('Invalid response schema')
    return {'message': content['message'], 'actions': validate_actions(content.get('actions', []))}

def validate_actions(actions):
    if not isinstance(actions, list) or len(actions) > 5:
        raise ProtocolError('invalid_response', 'actions')
    for action in actions:
        if not isinstance(action, dict) or set(action) - {'capability', 'parameters', 'label', 'id'}:
            raise ProtocolError('invalid_response', 'actions')
        capability = action.get('capability')
        schema = SCHEMAS.get(capability) if isinstance(capability, str) else None
        params = action.get('parameters')
        if schema is None or not isinstance(params, dict) or not params or set(params) - set(schema):
            raise ProtocolError('invalid_parameters' if schema else 'unsupported_capability', 'parameters', action.get('capability'))
        if action['capability'] in {'dashboard.detect', 'event.propose'} and set(params) != set(schema):
            raise ProtocolError('missing_parameters', 'parameters', action['capability'])
        for key, value in params.items():
            rule = schema[key]
            valid = (isinstance(value, str) and 0 < len(value.strip()) <= 256) if rule == 'text' else (type(value) is bool) if rule == 'bool' else (isinstance(value, str) and value in rule)
            if not valid:
                raise ProtocolError('invalid_parameters', 'parameters.' + key, action['capability'])
        for field in ('id', 'label'):
            if field in action and (not isinstance(action[field], str) or len(action[field]) > 200):
                raise ProtocolError('invalid_metadata', 'actions', action['capability'])
    return actions
