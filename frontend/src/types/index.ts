// Water quality metrics
export interface WaterMetrics {
  pH: number
  cod: number
  ammoniaNitrogen: number
  totalNitrogen: number
  totalPhosphorus: number
  flow: number
}

// Metric status
export type MetricStatus = 'normal' | 'abnormal' | 'offline'

// Plant data
export interface PlantData {
  id: string
  name: string
  status: 'online' | 'offline'
  metrics: WaterMetrics | null
  metricStatus: Record<keyof WaterMetrics, MetricStatus>
  lastUpdate: string
}

// AI message
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  evidence?: any[]
  chartData?: any
}

// Alert event
export interface AlertEvent {
  id: string
  timestamp: string
  type: string
  plantId: string
  severity: 'low' | 'medium' | 'high'
  status: 'pending' | 'processing' | 'resolved' | 'ignored'
  evidence: {
    dataSnapshot: WaterMetrics
    operators: Array<{
      name: string
      result: any
    }>
    rules: Array<{
      name: string
      matched: boolean
    }>
    llmReasoning: string
  }
}

// Page context
export interface PageContext {
  page: string
  plantId?: string
  timeRange?: [string, string]
  suggestedQuestions?: string[]
}
