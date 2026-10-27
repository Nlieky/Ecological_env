import api from '../client'
import type { RealtimeData, DataQuality, HistoryData } from '../types/api.types'

interface Envelope<T> { success: boolean; data: T; error: unknown; metadata: unknown }

const unwrap = <T>(p: Promise<Envelope<T>>) => p.then((r) => r.data)

export const monitoringService = {
  realtime: (plantId: string) => unwrap(api.get<unknown, Envelope<RealtimeData>>('/v1/monitoring/realtime', { params: { plant_id: plantId } })),
  quality: (plantId: string, timeRange = '24h') =>
    unwrap(api.get<unknown, Envelope<DataQuality>>('/v1/monitoring/quality', { params: { plant_id: plantId, time_range: timeRange } })),
  history: (params: { plant_id: string; time_range?: string; page?: number; page_size?: number; aggregation?: string }) =>
    unwrap(api.get<unknown, Envelope<HistoryData>>('/v1/data/history', { params })),
  aggregated: (params: { plant_id: string; period?: string; metrics?: string }) =>
    unwrap(api.get<unknown, Envelope<any>>('/v1/data/aggregated', { params })),
}
