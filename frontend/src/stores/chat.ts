import { defineStore } from 'pinia'
import { ref } from 'vue'
import { conversationsService } from '@/api/modules/conversations'
import { queryService } from '@/api/modules/query'
import type { ConversationListItem, ConversationDetail, SessionTrace } from '@/api/types/api.types'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  trace?: SessionTrace | null
  streaming?: boolean
  progress?: string
  chartData?: { charts: any[] } | null
}

let _seq = 0
const nextId = () => `m${Date.now()}_${++_seq}`

const SUBAGENT_NAMES: Record<string, string> = {
  'multi-dimensional-data-perception': '数据感知',
  'anomaly-detection': '异常检测',
  'rule-reasoning': '规则推理',
  'disposition-execution': '研判处置',
}

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
    loading.value = true
    try {
      const r = await conversationsService.detail(id)
      current.value = r.data
      sessionId.value = id
      // 还原该会话的历史消息到聊天区(过滤 tool 中间步骤,只留 user/assistant 对话)
      messages.value = (r.data?.messages || [])
        .filter((m) => m.role === 'user' || m.role === 'assistant')
        .map((m) => ({
          id: nextId(),
          role: m.role as 'user' | 'assistant',
          content: m.content || '',
          timestamp: m.timestamp || new Date().toISOString(),
        }))
    } catch { /* 拦截器已弹错 */ }
    finally { loading.value = false }
  }

  async function sendQuery(query: string) {
    if (!query.trim() || loading.value) return
    loading.value = true; error.value = null
    messages.value.push({ id: nextId(), role: 'user', content: query, timestamp: new Date().toISOString() })
    // 先放一个空的 assistant 消息，流式过程中就地更新（进度 + 逐字内容）
    const aid = nextId()
    messages.value.push({ id: aid, role: 'assistant', content: '', timestamp: new Date().toISOString(), streaming: true, progress: '' })
    const patch = (p: Partial<ChatMessage>) => {
      const i = messages.value.findIndex((m) => m.id === aid)
      if (i >= 0) messages.value[i] = { ...messages.value[i], ...p }
    }
    const calls: { key: string; name: string; summary?: string }[] = []
    let collectedChart: any = null
    try {
      await new Promise<void>((resolve, reject) => {
        queryService.executeStream(
          { query, session_id: sessionId.value },
          {
            onProgress: (e) => {
              const name = SUBAGENT_NAMES[e.subagent] || e.subagent
              if (e.stage === 'done') {
                calls.push({ key: e.subagent, name, summary: e.summary })
                // 收集 chartData（异常检测优先带标注，否则数据感知）
                if (e.chartData) collectedChart = e.chartData
              }
              patch({ progress: e.stage === 'start' ? `正在调用「${name}」子智能体…` : `「${name}」完成${e.summary ? '（' + e.summary + '）' : ''}` })
            },
            onDelta: (t) => patch({ content: (messages.value.find((m) => m.id === aid)?.content || '') + t }),
            onDone: (content, sid) => {
              sessionId.value = sid
              patch({
                content: content || '(空回答)',
                streaming: false,
                progress: '',
                chartData: collectedChart ? { charts: Array.isArray(collectedChart) ? collectedChart : (collectedChart.charts || []) } : null,
              })
              resolve()
            },
            onError: (msg) => {
              patch({ content: '⚠ 查询失败: ' + msg, streaming: false, progress: '' })
              reject(new Error(msg))
            },
          },
        )
      })
      // 用流式过程中收集的子智能体调用记录构建 trace（DB 里没有，就地构建填决策路径面板）
      if (calls.length) {
        const trace: SessionTrace = {
          session_id: sessionId.value || '',
          api_call: null,
          master_decision: { decision_path: calls.map((c) => c.name) },
          subagent_executions: calls.map((c) => ({ subagent_name: c.key, status: 'completed', result_summary: c.summary || '' })),
          operator_calls: [],
          llm_calls: [],
        }
        const i = messages.value.findIndex((m) => m.id === aid)
        if (i >= 0) messages.value[i] = { ...messages.value[i], trace }
      }
    } catch (e: any) {
      error.value = e?.message || '查询失败'
    } finally {
      loading.value = false
    }
  }

  function clearMessages() { messages.value = []; sessionId.value = undefined }

  return { conversations, current, messages, sessionId, loading, error, fetchConversations, openConversation, sendQuery, clearMessages }
})
