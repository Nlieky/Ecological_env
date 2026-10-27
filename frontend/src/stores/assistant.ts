import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { assistantService, type AssistantAction, type AssistantContext, type AssistantHandoff, type AssistantPending } from '@/api/modules/assistant'
import { CONTRACT_VERSION, validateAssistantAction } from '@/assistant/capabilities'
import type { AssistantExecutionResult } from '@/assistant/executor'
export interface CandidateState { state: 'prepared' | 'running' | 'succeeded' | 'empty' | 'failed' | 'stale'; receipt?: AssistantExecutionResult }

export interface AssistantMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  context: AssistantContext
  status: 'complete' | 'running' | 'failed' | 'interrupted'
  error?: string
  query?: string
  actions?: AssistantAction[]
  candidates?: CandidateState[]
  pending?: AssistantPending
  handoff?: AssistantHandoff
  eventDraft?: { eventId: string; new_status: string; reason: string }
  eventOperation?: { key: string; eventId: string; operationId?: string; state: 'unknown' | 'completed'; feedback: string }
}
const STORAGE_KEY = 'ecological.assistant.v1'
const uid = () => globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`
// Never age out the only lookup key for a write whose outcome is still unknown.
function retainedMessages(items: AssistantMessage[]) {
  const recentIds = new Set(items.slice(-100).map(message => message.id))
  return items.filter(message => recentIds.has(message.id) || message.eventOperation?.state === 'unknown')
}
// Context is intentionally allowlisted; credentials and raw request/log bodies never enter this channel.
export function snapshotAssistantContext(context: AssistantContext): AssistantContext {
  const allowed = ['route', 'pageId', 'pageTitle', 'objectId', 'range', 'actions', 'revision', 'selectedObject', 'selectedObjectId', 'selectedId', 'plant', 'plantId', 'indicator', 'timeRange', 'dataSource', 'freshness', 'filters', 'loading', 'error', 'availableActions', 'source', 'selection', 'status']
  const clean = (value: unknown): unknown => {
    if (Array.isArray(value)) return value.slice(0, 100).map(clean)
    if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).filter(([key]) => !/key|token|password|secret|credential|body|raw/i.test(key)).map(([key, item]) => [key, clean(item)]))
    return typeof value === 'string' ? value.slice(0, 4000) : value
  }
  return JSON.parse(JSON.stringify(Object.fromEntries(Object.entries(context).filter(([key]) => allowed.includes(key)).map(([key, value]) => [key, clean(value)]))))
}
export const useAssistantStore = defineStore('assistant', () => {
  const open = ref(false), expanded = ref(false), loading = ref(false), draft = ref('')
  const sessionId = ref<string>(uid()), messages = ref<AssistantMessage[]>([])
  const pending = ref<AssistantPending>()
  try {
    const saved = JSON.parse(globalThis.sessionStorage?.getItem(STORAGE_KEY) || 'null')
    if (saved?.version === 1 && Array.isArray(saved.messages)) {
      sessionId.value = typeof saved.sessionId === 'string' ? saved.sessionId : uid()
      messages.value = retainedMessages(saved.messages.filter((m: AssistantMessage) => m && typeof m.id === 'string' && ['user', 'assistant'].includes(m.role) && typeof m.content === 'string')).map((m: AssistantMessage) => ({ ...m, context: snapshotAssistantContext(m.context || {}), status: m.status === 'running' ? 'interrupted' : m.status, actions: undefined, handoff: undefined, pending: undefined, eventDraft: undefined, candidates: m.candidates?.filter(c => c.receipt).map(c => ({ ...c, state: c.state === 'running' ? 'failed' : c.state })) }))
    }
  } catch { /* Disabled storage or malformed saved data must not prevent help. */ }
  watch([messages, sessionId], () => {
    try {
      // Persist only conversational text and sanitized context, never live action/proposal tokens.
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ version: 1, sessionId: sessionId.value, messages: retainedMessages(messages.value).map(({ id, role, content, context, status, error, query, eventOperation, candidates }) => ({ id, role, content, context, status, error, query, eventOperation, candidates: candidates?.filter(c => c.receipt) })) }))
    } catch { /* Storage quota/privacy mode: retain the in-memory session. */ }
  }, { deep: true, flush: 'sync' })
  async function submit(query: string, context: AssistantContext, addQuestion: boolean) {
    if (loading.value || !query.trim()) return
    loading.value = true
    let frozen = snapshotAssistantContext(context)
    if (pending.value) {
      const binding = (value: AssistantContext) => JSON.stringify(Object.fromEntries(['route', 'pageId', 'objectId', 'plant', 'source', 'range', 'indicator', 'filters'].map(key => [key, value[key]])))
      if (binding(frozen) !== binding(pending.value.context)) { clearPending(); }
      else { frozen = { ...pending.value.context, status: frozen.status }; pending.value = { ...pending.value, context: frozen } }
    }
    const history = messages.value.filter(m => m.status === 'complete').slice(-20).map(({ role, content }) => ({ role, content: content.slice(0, 4000) }))
    if (addQuestion) messages.value.push({ id: uid(), role: 'user', content: query, context: frozen, status: 'complete' })
    const responseId = uid()
    messages.value.push({ id: responseId, role: 'assistant', content: '', context: frozen, status: 'running', query })
    try {
      const response = await assistantService.respond({ query, session_id: sessionId.value, context: frozen, history, ...(pending.value ? { pending: pending.value } : {}) })
      const message = messages.value.find(m => m.id === responseId)!
      message.content = response.message; message.actions = []; message.handoff = response.handoff; message.status = 'complete'
      if ((response.actions?.length || response.pending) && response.contract_version !== CONTRACT_VERSION) { message.error = '操作协议不一致，请基于当前页面重新准备操作'; clearPending() }
      else {
        messages.value.forEach(item => { item.pending = undefined })
        const offered = Array.isArray(response.actions) ? response.actions : []
        message.actions = offered.filter(action => validateAssistantAction(action).success).map(action => ({ capability: action.capability, parameters: { ...action.parameters }, id: action.id, label: action.label, parameter_sources: action.parameter_sources, contract_version: CONTRACT_VERSION }))
        if (message.actions.length !== offered.length) message.error = '部分操作参数无效，已停用，请重新准备操作'
        message.candidates = message.actions.map(() => ({ state: 'prepared' }))
        const next = response.pending
        pending.value = next && next.contract_version === CONTRACT_VERSION && typeof next.capability === 'string' && Array.isArray(next.missing) && next.missing.every(key => typeof key === 'string') && next.parameters && typeof next.parameters === 'object' && !Array.isArray(next.parameters) ? { ...next, context: frozen } : undefined
        message.pending = pending.value
      }
      if (response.session_id) sessionId.value = response.session_id
    } catch (error) {
      const message = messages.value.find(m => m.id === responseId)!
      const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      message.status = 'failed'; message.error = typeof detail === 'string' ? detail : error instanceof Error ? error.message : '请求失败，请重试'
    } finally { loading.value = false }
  }
  const sendQuery = (query: string, context: AssistantContext = {}) => submit(query, context, true)
  function clearPending() { pending.value = undefined; messages.value.forEach(message => { message.pending = undefined }) }
  async function reprepare(id: string, context: AssistantContext) { const message = messages.value.find(m => m.id === id); if (message?.query) { clearPending(); await submit(message.query, context, true) } }
  async function retry(id: string) {
    const message = messages.value.find(m => m.id === id)
    if (message?.query && ['failed', 'interrupted'].includes(message.status)) await submit(message.query, message.context, false)
  }
  return { open, expanded, loading, draft, sessionId, messages, pending, sendQuery, retry, clearPending, reprepare }
})
