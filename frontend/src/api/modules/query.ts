import api from '../client'
import type { QueryRequest, QueryResponse } from '../types/api.types'

export const queryService = {
  execute: (req: QueryRequest) => api.post<unknown, QueryResponse>('/query', req),
  capabilities: () => api.get<unknown, any>('/query/capabilities'),
}
