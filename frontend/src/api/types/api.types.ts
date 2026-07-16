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

// ========== Realtime Data Interface ==========
export interface PlantData {
  id: string
  name: string
  status: 'online' | 'offline'
  metrics: WaterMetrics
  metric_status: MetricStatus
  last_update: string
}

export interface WaterMetrics {
  ph: number
  cod: number
  ammonia_nitrogen: number
  total_nitrogen: number
  total_phosphorus: number
  flow: number
}

export interface MetricStatus {
  ph: 'normal' | 'abnormal' | 'offline'
  cod: 'normal' | 'abnormal' | 'offline'
  ammonia_nitrogen: 'normal' | 'abnormal' | 'offline'
  total_nitrogen: 'normal' | 'abnormal' | 'offline'
  total_phosphorus: 'normal' | 'abnormal' | 'offline'
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
