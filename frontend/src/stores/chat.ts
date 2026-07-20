import { defineStore } from 'pinia'
import { ref } from 'vue'
import { conversationsService } from '@/api/modules/conversations'
import { queryService } from '@/api/modules/query'
import { logsService } from '@/api/modules/logs'
import type { ConversationListItem, ConversationDetail, SessionTrace, QueryResponse } from '@/api/types/api.types'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  trace?: SessionTrace | null
}

let _seq = 0
const nextId = () => `m${Date.now()}_${++_seq}`

export const useChatStore = defineStore('chat', () => {
  const conversations = ref<ConversationListItem[]>([])
  const current = ref<ConversationDetail | null>(null)
  const messages = ref<ChatMessage[]>([])
  const sessionId = ref<string | undefined>(undefined)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchConversations(page = 1) {
    try { const r = await conversationsService.list(page); conversations.value = r.data.conversations } catch {}
  }
  async function openConversation(id: string) {
    try { const r = await conversationsService.detail(id); current.value = r.data } catch {}
  }

  async function sendQuery(query: string) {
    if (!query.trim() || loading.value) return
    loading.value = true; error.value = null
    messages.value.push({ id: nextId(), role: 'user', content: query, timestamp: new Date().toISOString() })
    try {
      const res: QueryResponse = await queryService.execute({ query, session_id: sessionId.value })
      sessionId.value = res.session_id
      let trace: SessionTrace | null = null
      try { trace = await logsService.trace(res.session_id) } catch { trace = null }
      messages.value.push({
        id: nextId(), role: 'assistant',
        content: res.content || '(空回答)',
        timestamp: res.timestamp || new Date().toISOString(),
        trace,
      })
    } catch (e: any) {
      error.value = e?.message || '查询失败'
      messages.value.push({ id: nextId(), role: 'assistant', content: '⚠ 查询失败,请稍后重试。', timestamp: new Date().toISOString() })
    } finally {
      loading.value = false
    }
  }

  function clearMessages() { messages.value = []; sessionId.value = undefined }

  return { conversations, current, messages, sessionId, loading, error, fetchConversations, openConversation, sendQuery, clearMessages }
})
