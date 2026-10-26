// ========== Query Interface ==========
export interface QueryRequest {
  query: string
  session_id?: string
  context?: PageContext
}

export interface QueryResponse {
  content: string
  session_id: string
  timestamp: string
  chartData?: any
  decision_path: DecisionPath[]
  reasoning?: string
  metadata?: Record<string, any>
}

export interface DecisionPath {
  step_number: number
  step_name: string
  decision: string
  action: string
}

// ========== Agent Capabilities (/api/query/capabilities) ==========
export interface MasterAgentInfo {
  name: string
  role: string
  location: string
}
export interface ImplementationInfo {
  method: string
  description: string
  identity_files_loaded: string[]
}
export interface DecisionTreeNode {
  step: number
  question: string
  condition?: string
  yes_action?: string
  no_action?: string
  action?: string
}
export interface SubAgentInfo {
  name: string
  role: string
  location: string
}
export interface CapabilitiesResponse {
  master_agent: MasterAgentInfo
  implementation: ImplementationInfo
  decision_tree: DecisionTreeNode[]
  sub_agents: SubAgentInfo[]
}

// ========== Observability / Tracing DataSources ==========
export interface TracingDataSource {
  id: string
  name: string
  provider: string
  config: { url: string } & Record<string, unknown>
  enabled: boolean
  created_at: string
  updated_at: string
}
export interface DataSourceInput {
  name: string
  provider: string
  config: Record<string, unknown>
  enabled: boolean
}
export interface TestConnectionResult {
  status: string
  message: string
  latency_ms: number
}

// ========== Tracing catalog / search / trace detail ==========
export interface CatalogService { name: string; operations: string[] }
export interface CatalogResponse { services: CatalogService[] }
export interface TraceSearchResult {
  traceID: string
  rootSpanName: string
  rootServiceName: string
  startTime: number   // 微秒
  duration: number    // 微秒
  spanCount: number
}
export interface TraceSpanLog { timestamp: number; fields: Record<string, unknown> }
export interface TraceSpan {
  spanID: string
  operationName: string
  duration: number    // 微秒
  startTime: number   // 微秒
  tags: Record<string, unknown>
  logs: TraceSpanLog[]
  processID: string
  references: { refType: string; traceID: string; spanID: string }[]
}
export interface TraceProcess { serviceName: string; tags: Record<string, unknown> }
export interface TraceDetail {
  traceID: string
  spans: TraceSpan[]
  processes: Record<string, TraceProcess>
}

// ========== Realtime Data Interface ==========
// 字段名与后端 /api/realtime/plants 实际返回对齐（驼峰）；离线厂 metrics/metricStatus 为 null。
export interface PlantData {
  id: string
  name: string
  status: 'online' | 'offline'
  metrics: WaterMetrics | null
  metricStatus: MetricStatus | null
  lastUpdate: string
}

export interface WaterMetrics {
  pH: number
  cod: number
  ammoniaNitrogen: number
  totalNitrogen: number
  totalPhosphorus: number
  flow: number
}

export interface MetricStatus {
  pH: 'normal' | 'abnormal' | 'offline'
  cod: 'normal' | 'abnormal' | 'offline'
  ammoniaNitrogen: 'normal' | 'abnormal' | 'offline'
  totalNitrogen: 'normal' | 'abnormal' | 'offline'
  totalPhosphorus: 'normal' | 'abnormal' | 'offline'
  flow: 'normal' | 'abnormal' | 'offline'
}

// ========== Events Interface ==========
export interface EventListRequest {
  type?: string
  plantId?: string
  severity?: string
  status?: string
  startTime?: string
  endTime?: string
  page?: number
  pageSize?: number
}

// evidence_points 混合数组（anomaly / expert_pattern / regulation / process_mechanism / similar_case），结构见 @/views/eventEvidence
export interface AlertEvent {
  id: string
  timestamp: string
  sessionId: string
  conversationId: string | null
  plantId: string
  violationTypes: string[]
  severity: 'low' | 'medium' | 'high'
  status: 'pending' | 'processing' | 'resolved' | 'ignored'
  action: string
  confidence: number | null
  evidence: Record<string, unknown>[]
  workOrder?: Record<string, unknown> | null
  createdAt: string
  updatedAt: string
}

export interface EventListResponse {
  data: AlertEvent[]
  total: number
}

// ========== Logs Interface ==========
export interface LogsRequest {
  type?: string
  startTime?: string
  endTime?: string
  page?: number
  pageSize?: number
}

export interface LogEntry {
  id: string
  timestamp: string
  type: string
  level: string
  message: string
  details?: any
}

// ========== Common Types ==========
export interface PageContext {
  page?: string
  plant_id?: string
  time_range?: string
}

// ========== Monitoring (v1) ==========
export interface RealtimeData {
  timestamp: string
  influent: Record<string, number | null>
  effluent: Record<string, number | null>
  flow_rate: number
  quality_score: number
}
export interface DataQuality {
  completeness_rate: number
  missing_data_count: number
  anomaly_count: number
  last_update: string
}
export interface HistoryRecord {
  timestamp: string
  influent: Record<string, number | null>
  effluent: Record<string, number | null>
}
export interface HistoryData {
  records: HistoryRecord[]
  summary: Record<string, number>
  total_count: number
  page: number
  page_size: number
}

// ========== Conversations (v1) ==========
export interface ConversationListItem {
  id: string
  title: string
  started_at: string | null
  message_count: number
  status: string
}
export interface ConversationMessage {
  role: 'user' | 'assistant' | 'tool'
  content: string | null
  tool_call_info?: any
  timestamp: string | null
}
export interface ConversationDetail {
  id: string
  title: string
  message_count: number
  messages: ConversationMessage[]
}
export interface ConversationListResponse {
  conversations: ConversationListItem[]
  total_count: number
  page: number
  page_size: number
}

// ========== Logs / Trace ==========
export type LogType = 'all' | 'api' | 'master' | 'subagent' | 'operator' | 'llm' | 'error'
export interface LogEntryV1 {
  id: string
  timestamp: string
  module: string
  content: string
  details?: any
  latency_ms?: number | null
  level?: 'info' | 'warning' | 'error'
  slow?: boolean
  session_id?: string | null
}
export interface SessionTrace {
  session_id: string
  api_call: any
  master_decision: Record<string, any> | null
  subagent_executions: Record<string, any>[]
  operator_calls: Record<string, any>[]
  llm_calls: Record<string, any>[]
}

// ── 多厂区仪表盘 ──
export interface PlantNode {
  plant_id: string
  status: 'online' | 'offline'
  data_types: string[]
  latest_time: string
  point_count: number
}
export interface PlantDistrict { name: string; plants: PlantNode[] }
export interface PlantCity { name: string; districts: PlantDistrict[] }
export interface PlantTree { cities: PlantCity[]; ungrouped: PlantNode[] }

export interface DataContext {
  origin: 'real' | 'simulated' | 'unverified'
  mode: 'historical' | 'simulation' | 'live' | 'unverified'
  bucket: string
  timezone: string
  latest_sample_at: string | null
  freshness: string
  warning: string | null
}
export interface IndicatorTrendPoint { time: string; value: number | null }
export interface PlantIndicator {
  label: string
  unit: string
  limit: number | [number, number] | null
  influent: number | null
  effluent: number | null
  status: 'normal' | 'warning' | 'nodata'
  series: { influent: IndicatorTrendPoint[]; effluent: IndicatorTrendPoint[] }
}
export interface PlantDashboard {
  data_context?: DataContext
  plant_id: string
  window_hours: number
  latest_time?: string
  anchor?: string
  segment_start?: string
  segment_end?: string
  indicators: Record<string, PlantIndicator>
  influent_points: number
  effluent_points: number
}
