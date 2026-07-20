<template>
  <div class="audit">
    <!-- 左：会话列表（每个会话 = 一次主智能体执行） -->
    <aside class="list">
      <div class="list-head">
        <span class="list-ttl">会话审计</span>
        <span class="list-cnt">{{ total }} 条</span>
      </div>
      <div class="list-body">
        <div v-for="c in conversations" :key="c.id" class="item" :class="{ on: c.id === selectedId }" @click="select(c.id)">
          <div class="it-t">{{ c.title || '(无标题)' }}</div>
          <div class="it-m">
            <span>{{ fmt(c.started_at) }}</span>
            <span>{{ c.message_count }} 条消息</span>
          </div>
        </div>
        <div v-if="!conversations.length && !loadingList" class="empty">暂无会话记录</div>
      </div>
    </aside>

    <!-- 右：审计详情 -->
    <section class="detail">
      <template v-if="detail">
        <div class="d-head">
          <span class="d-ttl">{{ detail.title }}</span>
          <span class="d-meta">{{ detail.message_count }} 条消息 · {{ selectedId }}</span>
        </div>

        <div class="msgs">
          <div v-for="(m, i) in detail.messages" :key="i" class="msg" :class="m.role">
            <div class="m-role">{{ roleLabel(m.role) }}</div>
            <div v-if="m.role === 'assistant'" class="m-body"><MarkdownRenderer :content="m.content || ''" /></div>
            <div v-else-if="m.role === 'tool'" class="m-tool">🔧 {{ m.tool_call_info ? JSON.stringify(m.tool_call_info) : (m.content || '工具调用') }}</div>
            <div v-else class="m-body plain">{{ m.content }}</div>
          </div>
          <div v-if="loadingDetail" class="ld">加载详情中…</div>
        </div>

        <!-- 推理追溯卡片（复用 Phase 2） -->
        <div v-if="trace" class="trace-cards">
          <div class="tc-ttl">推理追溯</div>
          <DecisionFlow :trace="trace" />
          <SubAgentChips :trace="trace" />
          <EvidenceChain :trace="trace" />
        </div>
        <div v-else-if="!loadingDetail" class="trace-empty">该会话无追溯数据（trace 未记录）</div>
      </template>

      <div v-else class="placeholder">← 选择左侧会话，查看主智能体决策与执行审计</div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { conversationsService } from '@/api/modules/conversations'
import { logsService } from '@/api/modules/logs'
import MarkdownRenderer from '@/components/markdown/MarkdownRenderer.vue'
import DecisionFlow from '@/components/aiops/DecisionFlow.vue'
import SubAgentChips from '@/components/aiops/SubAgentChips.vue'
import EvidenceChain from '@/components/aiops/EvidenceChain.vue'
import type { ConversationListItem, ConversationDetail, SessionTrace } from '@/api/types/api.types'

const conversations = ref<ConversationListItem[]>([])
const total = ref(0)
const selectedId = ref<string>('')
const detail = ref<ConversationDetail | null>(null)
const trace = ref<SessionTrace | null>(null)
const loadingList = ref(true)
const loadingDetail = ref(false)

function roleLabel(r: string) {
  return r === 'user' ? '👤 提问' : r === 'assistant' ? '🤖 主智能体' : '🔧 工具'
}
function fmt(t: string | null) { return t ? t.replace('T', ' ').slice(0, 16) : '—' }

async function loadList() {
  loadingList.value = true
  try {
    const r = await conversationsService.list(1, 50)
    conversations.value = r.data.conversations
    total.value = r.data.total_count
    if (conversations.value.length) await select(conversations.value[0].id)
  } catch { conversations.value = [] }
  finally { loadingList.value = false }
}

async function select(id: string) {
  selectedId.value = id
  detail.value = null
  trace.value = null
  loadingDetail.value = true
  try {
    const [d, t] = await Promise.all([
      conversationsService.detail(id),
      logsService.trace(id).catch(() => null),
    ])
    detail.value = d.data
    trace.value = t
  } catch { detail.value = null }
  finally { loadingDetail.value = false }
}

onMounted(loadList)
</script>

<style scoped>
.audit { display: flex; gap: 14px; height: calc(100vh - var(--header-height) - 40px); min-height: 0 }
.list { width: 280px; flex-shrink: 0; background: var(--card-bg); border: 1px solid var(--brd); border-radius: 13px;
  display: flex; flex-direction: column; overflow: hidden }
.list-head { display: flex; justify-content: space-between; align-items: center; padding: 12px 14px; border-bottom: 1px solid var(--brd) }
.list-ttl { font-size: 13px; font-weight: 700 }
.list-cnt { font-size: 11px; color: var(--text-muted) }
.list-body { flex: 1; overflow-y: auto; padding: 6px }
.item { padding: 9px 11px; border-radius: 8px; cursor: pointer; margin-bottom: 3px }
.item:hover { background: #f8fafc }
.item.on { background: #eef2ff; border: 1px solid #c7d2fe }
.it-t { font-size: 12.5px; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 500 }
.it-m { display: flex; justify-content: space-between; font-size: 10.5px; color: var(--text-muted); margin-top: 3px }
.empty { color: var(--text-muted); font-size: 12px; padding: 16px; text-align: center }

.detail { flex: 1; min-width: 0; background: var(--card-bg); border: 1px solid var(--brd); border-radius: 13px;
  display: flex; flex-direction: column; overflow: hidden }
.d-head { display: flex; justify-content: space-between; align-items: baseline; padding: 12px 16px; border-bottom: 1px solid var(--brd) }
.d-ttl { font-size: 14px; font-weight: 700 }
.d-meta { font-size: 11px; color: var(--text-muted); font-family: ui-monospace, monospace }
.msgs { flex: 1; overflow-y: auto; padding: 14px 16px; display: flex; flex-direction: column; gap: 12px }
.msg { max-width: 760px }
.m-role { font-size: 11px; color: var(--text-muted); margin-bottom: 4px }
.m-body { font-size: 13px; line-height: 1.7; color: var(--text-primary); background: #f8fafc; border: 1px solid var(--brd);
  border-radius: 10px; padding: 10px 13px }
.m-body.plain { white-space: pre-wrap }
.msg.user .m-body { background: #eef2ff; border-color: #c7d2fe }
.m-tool { font-size: 11px; color: var(--text-muted); font-family: ui-monospace, monospace; background: #fffbeb;
  border: 1px solid #fde68a; border-radius: 8px; padding: 7px 10px; word-break: break-all }
.ld { color: var(--text-muted); font-size: 13px; padding: 10px 0 }

.trace-cards { border-top: 1px solid var(--brd); padding: 14px 16px; display: flex; flex-direction: column; gap: 10px;
  max-height: 40%; overflow-y: auto; background: #fafbff }
.tc-ttl { font-size: 12px; font-weight: 700; color: var(--primary); margin-bottom: 2px }
.trace-empty { padding: 12px 16px; font-size: 12px; color: var(--text-muted); border-top: 1px solid var(--brd) }

.placeholder { flex: 1; display: grid; place-items: center; color: var(--text-muted); font-size: 14px }
</style>
