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

# === 废水监测指标（供 Prometheus 抓取 + Grafana 可视化）===
# 指标名严格对齐 grafana/dashboards/stream_01.json，不加 label（dashboard 按裸指标名查询）。
# 数据由 backend/metrics/updater.py 后台线程从 MonitoringDataset 推进游标实时填充。
_INFLUENT_KEYS = ["ph", "cod", "tn", "an", "tp", "flow_rate", "discharge_volume"]
_EFFLUENT_KEYS = ["ph", "cod", "tn", "an", "tp", "flow_rate", "discharge_volume", "suspended_solids"]

wastewater_influent = {k: Gauge(f"wastewater_influent_{k}", f"进水 {k}") for k in _INFLUENT_KEYS}
wastewater_effluent = {k: Gauge(f"wastewater_effluent_{k}", f"出水 {k}") for k in _EFFLUENT_KEYS}

wastewater_data_processed_total = Counter(
    "wastewater_data_processed_total", "已处理的监测数据点总数"
)
wastewater_anomaly_detected_total = Counter(
    "wastewater_anomaly_detected_total", "检测到的异常总数"
)

