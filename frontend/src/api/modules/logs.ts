import api from '../client'
import type { LogType, LogEntryV1, SessionTrace } from '../types/api.types'

export interface LogsResponse { data: LogEntryV1[]; total: number }

export const logsService = {
  list: (params: { log_type: LogType; page?: number; page_size?: number; start_time?: string; end_time?: string; search?: string; level?: string }) =>
    api.get<unknown, LogsResponse>('/logs', { params }),
  trace: (sessionId: string) => api.get<unknown, SessionTrace>(`/logs/trace/${encodeURIComponent(sessionId)}`),
}
