"""Declarative, JSON-only authority for assistant page operations."""
from copy import deepcopy

CONTRACT_VERSION = '1.0.0'
PAGES = ['dashboard', 'metrics', 'events', 'audit', 'graph', 'logs', 'config', 'chat']
INDICATORS = ['pH', 'COD', 'TN', 'AN', 'TP', 'suspended_solids']
SCHEMAS = {
    'navigate': {'pageId': PAGES},
    'dashboard.view': {'plant': 'text', 'indicator': INDICATORS, 'side': ['influent', 'effluent', 'all']},
    'dashboard.range': {'range': ['1h', '6h', '24h', '7d', '30d']},
    'dashboard.detect': {'algorithm': ['constant', 'changepoint', 'iforest'], 'indicator': INDICATORS, 'side': ['influent', 'effluent']},
    'metrics.filter': {'plant': 'text', 'indicator': INDICATORS[:-1], 'range': ['1h', '6h', '24h']},
    'events.filter': {'status': ['', 'pending', 'processing', 'resolved', 'ignored'], 'severity': ['', 'low', 'medium', 'high']},
    'events.detail': {'eventId': 'text'}, 'audit.focus': {'sessionId': 'text'}, 'graph.focus': {'nodeId': 'text'},
    'event.propose': {'eventId': 'text', 'new_status': ['pending', 'processing', 'resolved', 'ignored'], 'reason': 'text'},
    'logs.filter': {'module': ['all', 'api', 'master', 'subagent', 'operator', 'llm', 'error']},
    'strategy.draft': {'language_constraint': ['zh', 'en', 'none'], 'conclusion_first': 'bool', 'confidence_labeling': 'bool'},
}
_TARGETS = {
    'navigate': (None, '打开页面'), 'dashboard.view': ('dashboard', '调整大屏视图'),
    'dashboard.range': ('dashboard', '切换采样窗口'), 'dashboard.detect': ('dashboard', '准备统计检测'),
    'metrics.filter': ('metrics', '筛选指标'), 'events.filter': ('events', '筛选事件'),
    'events.detail': ('events', '查看事件'), 'audit.focus': ('audit', '定位审计会话'),
    'graph.focus': ('graph', '定位图谱节点'), 'event.propose': ('events', '准备事件状态变更'),
    'logs.filter': ('logs', '筛选日志'), 'strategy.draft': ('config', '准备策略草稿'),
}
_INHERIT = {
    'dashboard.view': {'plant': 'plant', 'indicator': 'indicator', 'side': 'filters.side'},
    'dashboard.range': {'range': 'range'},
    'dashboard.detect': {'indicator': 'indicator', 'side': 'filters.side'},
    'metrics.filter': {'plant': 'plant', 'indicator': 'indicator', 'range': 'range'},
    'events.filter': {'status': 'filters.status', 'severity': 'filters.severity'},
    'events.detail': {'eventId': 'objectId'}, 'audit.focus': {'sessionId': 'objectId'},
    'graph.focus': {'nodeId': 'objectId'}, 'event.propose': {'eventId': 'objectId'},
    'logs.filter': {'module': 'filters.module'},
}
_PATHS = {'audit': '/agents/audit', 'graph': '/agents/knowledge', 'config': '/agents/config'}
_LABELS = {'pageId': '目标页面', 'plant': '厂站', 'indicator': '指标', 'side': '进水或出水侧别', 'range': '采样时段', 'algorithm': '检测算法', 'status': '处理状态', 'severity': '严重程度', 'eventId': '事件编号', 'sessionId': '会话编号', 'nodeId': '节点编号', 'new_status': '目标状态', 'reason': '变更理由', 'module': '日志模块', 'language_constraint': '语言约束', 'conclusion_first': '是否结论优先', 'confidence_labeling': '是否标明置信度'}
_DESTINATION = {'navigate', 'events.filter', 'events.detail', 'audit.focus', 'graph.focus', 'logs.filter'}
_RELOAD = {'dashboard.view', 'dashboard.range', 'metrics.filter'}
CAPABILITIES = {}
for _id, _schema in SCHEMAS.items():
    _page, _title = _TARGETS[_id]
    _required = list(_schema) if _id in {'navigate', 'dashboard.range', 'dashboard.detect', 'events.detail', 'audit.focus', 'graph.focus', 'event.propose', 'logs.filter'} else []
    CAPABILITIES[_id] = {
        'id': _id, 'target_page': _page, 'target_path': _PATHS.get(_page, '/' + _page) if _page else None,
        'title': _title, 'parameters': deepcopy(_schema), 'required': _required,
        'minimum_parameters': 1, 'missing_prompts': {key: '请明确' + _LABELS[key] for key in _schema},
        'inheritance': _INHERIT.get(_id, {}),
        'defaults': {'requires_delegation': True, 'values': {'algorithm': 'iforest'} if _id == 'dashboard.detect' else {},
                     'explanation': '探索性离群统计候选，不代表超限或违规。' if _id == 'dashboard.detect' else ''},
        'readiness': {'status': [] if _id in _DESTINATION | _RELOAD else ['ready'], 'required_context': ['pageId', 'plant', 'source', 'range'] if _id == 'dashboard.detect' else [], 'range_requires_bounds': _id == 'dashboard.detect'},
        'invalidation': {'mode': 'destination' if _id in _DESTINATION else 'window' if _id == 'dashboard.detect' else 'proposal' if _id == 'event.propose' else 'relative', 'fields': [] if _id in _DESTINATION else ['pageId', 'route', 'plant', 'source', 'range', 'indicator', 'filters.side'] if _id == 'dashboard.detect' else ['pageId', 'route', 'objectId', 'plant', 'source', 'range'], 'revision_only': False},
        'level': 'proposal' if _id == 'event.propose' else 'draft' if _id == 'strategy.draft' else 'read',
        'requires_confirmation': _id in {'event.propose', 'strategy.draft'},
    }


def contract_document():
    return {'contract_version': CONTRACT_VERSION, 'capabilities': deepcopy(list(CAPABILITIES.values()))}
