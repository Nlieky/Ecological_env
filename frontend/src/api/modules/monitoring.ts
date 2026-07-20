import api from '../client'
import type { RealtimeData, DataQuality, HistoryData } from '../types/api.types'

export const monitoringService = {
  realtime: () => api.get<unknown, RealtimeData>('/v1/monitoring/realtime'),
  quality: (timeRange = '24h') =>
    api.get<unknown, DataQuality>('/v1/monitoring/quality', { params: { time_range: timeRange } }),
  history: (params: { time_range?: string; page?: number; page_size?: number; aggregation?: string }) =>
    api.get<unknown, HistoryData>('/v1/data/history', { params }),
  aggregated: (params: { period?: string; metrics?: string }) =>
    api.get<unknown, any>('/v1/data/aggregated', { params }),
}
