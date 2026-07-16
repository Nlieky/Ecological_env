import type { QueryResponse, DecisionPath, PlantData, AlertEvent } from '@/api/types/api.types'

// ========== Chat Message ==========
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  chartData?: any
  evidence?: DecisionPath[]
}

// ========== Session Info ==========
export interface Session {
  id: string
  createdAt: string
  messageCount: number
}

// ========== Page Context ==========
export interface PageContext {
  page?: string
  plantId?: string
  timeRange?: string
  suggestedQuestions?: string[]
}

// Re-export API types
export type { QueryResponse, DecisionPath, PlantData, AlertEvent }
