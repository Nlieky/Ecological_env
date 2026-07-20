import api from '../client'
import type { QueryRequest, QueryResponse, CapabilitiesResponse } from '../types/api.types'

export const queryService = {
  execute: (req: QueryRequest) => api.post<unknown, QueryResponse>('/query', req),
  capabilities: () => api.get<unknown, CapabilitiesResponse>('/query/capabilities'),
}
