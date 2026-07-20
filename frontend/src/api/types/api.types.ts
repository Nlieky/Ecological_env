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

export interface AlertEvent {
  id: string
  timestamp: string
  type: string
  plant_id: string
  severity: 'low' | 'medium' | 'high'
  status: 'pending' | 'processing' | 'resolved' | 'ignored'
  evidence?: any
}

export interface EventListResponse {
  items: AlertEvent[]
  total: number
  page: number
  pageSize: number
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
export type LogType = 'api' | 'master' | 'subagent' | 'operator' | 'llm' | 'error'
export interface LogEntryV1 {
  id: string
  timestamp: string
  module: string
  content: string
  details?: any
  latency_ms?: number | null
}
export interface SessionTrace {
  session_id: string
  api_call: any
  master_decision: Record<string, any> | null
  subagent_executions: Record<string, any>[]
  operator_calls: Record<string, any>[]
  llm_calls: Record<string, any>[]
}
