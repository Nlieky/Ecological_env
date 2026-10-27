import api, { SILENT } from '../client'

export type AssistantContext = Record<string, unknown>
export interface AssistantAction {
  id?: string
  capability: string
  parameters: Record<string, unknown>
  label?: string
  contract_version?: string
  parameter_sources?: Record<string, string>
  [key: string]: unknown
}
export interface AssistantHandoff { query: string; context: AssistantContext }
export interface AssistantPending { capability: string; parameters: Record<string, unknown>; missing: string[]; parameter_sources: Record<string, string>; context: AssistantContext; contract_version: string; use_defaults?: boolean }
export interface AssistantRequest {
  query: string
  session_id: string
  context: AssistantContext
  history: { role: 'user' | 'assistant'; content: string }[]
  pending?: AssistantPending
}
export interface AssistantResponse {
  contract_version?: string
  pending?: AssistantPending
  message: string
  actions: AssistantAction[]
  handoff?: AssistantHandoff
  session_id?: string
}
export interface EventProposal { proposal_id: string; event_id: string; plant_id: string; old_status: string; new_status: string; reason: string; expires_at: string; expected_updated_at: string; identity: string }
export interface EventOperation { operation_id: string; event_id: string; new_status: string; status: string; identity: string }
export const assistantService = {
  respond: (body: AssistantRequest) => api.post<unknown, AssistantResponse>('/assistant/respond', body, SILENT),
  capabilities: () => api.get<unknown, { capabilities: unknown[]; event_writes_enabled: boolean }>('/assistant/capabilities', SILENT),
  proposeEvent: (body: { session_id: string; event_id: string; new_status: string; reason: string; expected_status?: string; expected_updated_at?: string }) => api.post<unknown, EventProposal>('/assistant/event-proposals', body, SILENT),
  confirmEvent: (id: string, body: { session_id: string; idempotency_key: string }) => api.post<unknown, EventOperation>(`/assistant/event-proposals/${encodeURIComponent(id)}/confirm`, body, SILENT),
  eventOperation: (id: string, sessionId: string) => api.get<unknown, EventOperation>(`/assistant/operations/${encodeURIComponent(id)}`, { ...SILENT, params: { session_id: sessionId } }),
  eventOperationByKey: (key: string, sessionId: string) => api.get<unknown, EventOperation>(`/assistant/operations/by-key/${encodeURIComponent(key)}`, { ...SILENT, params: { session_id: sessionId } }),
}
