import { defineStore } from 'pinia'
import { ref } from 'vue'
import { conversationsService } from '@/api/modules/conversations'
import { queryService } from '@/api/modules/query'
import { useActionStore } from './action'
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
  /** 消息来源通道:'action'=动作助手(右下角,短路器),'chat'=主智能体研判 */
  channel?: 'action' | 'chat'
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
        .map((m) => {
          const msg: ChatMessage = {
            id: nextId(),
            role: m.role as 'user' | 'assistant',
            content: m.content || '',
            timestamp: m.timestamp || new Date().toISOString(),
          }
          const ti = m.tool_call_info as any
          if (ti?.chartData) {
            const cd = ti.chartData
            msg.chartData = Array.isArray(cd) ? { charts: cd } : (cd.charts ? cd : { charts: [] })
          }
          return msg
        })
    } catch { /* 拦截器已弹错 */ }
    finally { loading.value = false }
  }

  /**
   * 发送查询。
   * mode='floating' → AI 助手(右下角)·动作通道:请求带 mode=action,后端只走动作短路,
   *   非动作直接回引导语,绝不进子智能体管线(与 /chat 研判通道分离,两个创新点)。
   * mode='chat' → 智能体问答·研判通道:全管线(主智能体→子智能体→报告)。
   */
  async function sendQuery(query: string, mode: 'chat' | 'floating' = 'chat') {
    if (!query.trim() || loading.value) return
    loading.value = true; error.value = null
    const ch: 'action' | 'chat' = mode === 'floating' ? 'action' : 'chat'
    messages.value.push({ id: nextId(), role: 'user', content: query, timestamp: new Date().toISOString(), channel: ch })
    // 先放一个空的 assistant 消息，流式过程中就地更新（进度 + 逐字内容）
    const aid = nextId()
    messages.value.push({ id: aid, role: 'assistant', content: '', timestamp: new Date().toISOString(), streaming: true, progress: '', channel: ch })
    const patch = (p: Partial<ChatMessage>) => {
      const i = messages.value.findIndex((m) => m.id === aid)
      if (i >= 0) messages.value[i] = { ...messages.value[i], ...p }
    }
    const calls: { key: string; name: string; summary?: string }[] = []
    // 多厂/多次调用:chartData 按厂累积(每次①调用一组图,后到不覆盖先到)
    const collectedCharts: any[] = []
    // 大屏当前观看窗口随请求带给后端:AI 检测动作对齐"正在看的时段"
    const vc = useActionStore().viewContext
    const viewCtx = (vc && typeof vc === 'object' && Object.keys(vc).length)
      ? JSON.stringify(vc) : ''
    try {
      await new Promise<void>((resolve, reject) => {
        queryService.executeStream(
          { query, session_id: sessionId.value, view_context: viewCtx,
            ...(mode === 'floating' ? { mode: 'action' } : {}) },
          {
            onProgress: (e) => {
              const name = SUBAGENT_NAMES[e.subagent] || e.subagent
              if (e.stage === 'done') {
                calls.push({ key: e.subagent, name, summary: e.summary })
                // 收集 chartData（异常检测优先带标注，否则数据感知）;多厂累积不覆盖
                if (e.chartData) {
                  const arr = Array.isArray(e.chartData) ? e.chartData : (e.chartData.charts || [e.chartData])
                  collectedCharts.push(...arr)
                }
              }
              patch({ progress: e.stage === 'start' ? `正在调用「${name}」子智能体…` : `「${name}」完成${e.summary ? '（' + e.summary + '）' : ''}` })
            },
            onAction: (actionData) => {
              if (actionData) useActionStore().dispatch(actionData)
            },
            onDelta: (t) => patch({ content: (messages.value.find((m) => m.id === aid)?.content || '') + t }),
            onDone: (content, sid) => {
              sessionId.value = sid
              patch({
                content: content || '(空回答)',
                streaming: false,
                progress: '',
                // 多厂累积的全部图(两厂对话=两组图都显示,不互相覆盖)
                chartData: collectedCharts.length ? { charts: collectedCharts } : null,
              })
              // 非流式兼容：回复第一行是 actionData JSON 时也 dispatch（UI 动作没走 SSE action 事件）
              const m = (content || '').match(/^\s*(\{[\s\S]*?\})\s*\n/)
              if (m) { try { const a = JSON.parse(m[1]); if (a.cmd) useActionStore().dispatch(a) } catch { /* 非 JSON 忽略 */ } }
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

  /** 新建对话：在后端先落一条记录（列表立即可见），并把返回的 id 设为当前
   *  sessionId——这样首次提问时后端 record_exchange 按 session_id 能命中
   *  这条对话（追加而非另建），问答与"新对话"归到同一条。 */
  async function startNewConversation() {
    messages.value = []
    current.value = null
    try {
      const r: any = await conversationsService.create('新对话')
      const d = r.data ?? r
      if (d?.id) sessionId.value = d.id
      await fetchConversations()
    } catch {
      sessionId.value = undefined   // 创建失败退回旧行为：空白对话,首问时由后端建
    }
  }

  return { conversations, current, messages, sessionId, loading, error, fetchConversations, openConversation, sendQuery, clearMessages, startNewConversation }
})
