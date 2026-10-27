import { ref } from 'vue'
import type { ConversationDetail, SessionTrace } from '@/api/types/api.types'

interface AuditDetailApi {
  detail: (id: string) => Promise<{ success?: boolean; data: ConversationDetail | null }>
  trace: (id: string) => Promise<SessionTrace>
}

export function useAuditDetail(api: AuditDetailApi) {
  const selectedId = ref('')
  const detail = ref<ConversationDetail | null>(null)
  const trace = ref<SessionTrace | null>(null)
  const detailError = ref<string | null>(null)
  const traceError = ref<string | null>(null)
  const loadingDetail = ref(false)
  const loadingTrace = ref(false)
  let generation = 0
  let disposed = false

  async function select(id: string) {
    if (disposed) return
    const request = ++generation
    selectedId.value = id
    detail.value = null
    trace.value = null
    detailError.value = null
    traceError.value = null
    loadingDetail.value = true
    loadingTrace.value = true
    // Independent settlement: a slow or failed trace must not hide the conversation.
    async function loadConversation() {
      try {
        const result = await api.detail(id)
        if (result.success === false || !result.data) throw new Error('Conversation unavailable')
        if (request === generation) detail.value = result.data
      } catch {
        if (request === generation) detailError.value = '会话加载失败，请重试'
      } finally {
        if (request === generation) loadingDetail.value = false
      }
    }
    async function loadTrace() {
      try {
        const result = await api.trace(id)
        if (request !== generation) return
        const recorded = result.api_call || result.master_decision || result.subagent_executions.length
          || result.operator_calls.length || result.llm_calls.length
        trace.value = recorded ? result : null
      } catch {
        if (request === generation) traceError.value = '追溯加载失败，请重试'
      } finally {
        if (request === generation) loadingTrace.value = false
      }
    }
    await Promise.all([loadConversation(), loadTrace()])
  }

  function dispose() { disposed = true; generation++ }
  return { selectedId, detail, trace, detailError, traceError, loadingDetail, loadingTrace, select, dispose }
}
