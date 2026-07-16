import api from '../client'
import type { LogsRequest, LogEntry } from '../types/api.types'

export class LogsService {
  async getLogs(params?: LogsRequest): Promise<{
    items: LogEntry[]
    total: number
    page: number
    pageSize: number
  }> {
    return api.get('/logs', { params })
  }

  async getSessionTrace(sessionId: string): Promise<any> {
    return api.get(`/logs/trace/${sessionId}`)
  }
}

export const logsService = new LogsService()
