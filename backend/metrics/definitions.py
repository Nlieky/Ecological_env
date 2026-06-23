"""
Prometheus 监控指标定义 - Hermes 决策树监控
"""
from prometheus_client import Counter, Histogram, Gauge

# === API 请求指标 ===
api_requests_total = Counter(
    'api_requests_total',
    'API 请求总数',
    ['method', 'endpoint', 'status']
)

api_request_duration_seconds = Histogram(
    'api_request_duration_seconds',
    'API 请求耗时（秒）',
    ['endpoint']
)

# === Hermes 查询指标 ===
hermes_query_total = Counter(
    'hermes_query_total',
    'Hermes 查询总数'
)

hermes_query_duration_seconds = Histogram(
    'hermes_query_duration_seconds',
    'Hermes 查询耗时（秒）',
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

# === 决策树分支指标 ===
decision_tree_branch_taken = Counter(
    'decision_tree_branch_taken_total',
    '决策树分支执行次数',
    ['step', 'decision']  # step: 1-5, decision: YES/NO
)

# === 子智能体调用指标 ===
sub_agent_called = Counter(
    'sub_agent_called_total',
    '子智能体调用次数',
    ['agent_name', 'status']
)

sub_agent_duration = Histogram(
    'sub_agent_duration_seconds',
    '子智能体调用耗时（秒）',
    ['agent_name'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# === 会话管理指标 ===
active_sessions = Gauge(
    'active_sessions',
    '当前活跃会话数'
)
