<template>
  <PageShell title="会话审计" subtitle="主智能体决策与执行审计" scroll="contained">
  <template #actions><button class="search-btn" :disabled="loadingList || loadingDetail" @click="refresh">刷新</button></template>
  <div class="audit">
    <!-- 左：会话列表（每个会话 = 一次主智能体执行） -->
    <aside class="list">
      <div class="list-head">
        <span class="list-ttl">会话审计</span>
        <span class="list-cnt">{{ total }} 条</span>
      </div>
      <form class="list-search" @submit.prevent="setSearch(searchInput)">
        <span class="search-icon">⌕</span>
        <input v-model="searchInput" @input="scheduleSearch(searchInput)" aria-label="搜索标题或会话ID" placeholder="标题片段 / 会话 ID" maxlength="200" />
        <button v-if="searchInput" class="clear-search" type="button" aria-label="清除搜索" @click="searchInput = ''; setSearch('')">×</button>
        <button class="search-btn" type="submit">{{ loadingList ? '搜索中' : '搜索' }}</button>
      </form>
      <div v-if="selectedOutsideList" class="selection-note">当前查看：{{ detail?.title || selectedId }}（不在本页列表）</div>
      <div class="list-body">
        <PageState :state="listError ? 'error' : loadingList ? (conversations.length ? 'refreshing' : 'initial-loading') : conversations.length ? 'ready' : 'empty'" :preserve-content="!!conversations.length" :message="listError || undefined" @retry="loadList">
        <div v-for="c in conversations" :key="c.id" class="item" :class="{ on: c.id === selectedId }" @click="select(c.id)">
          <div class="it-t">{{ c.title || '(无标题)' }}</div>
          <div class="it-m">
            <span>{{ fmt(c.started_at) }}</span>
            <span>{{ c.message_count }} 条消息</span>
          </div>
        </div>
        </PageState>
      </div>
      <div class="list-pager">
        <button :disabled="page <= 1" @click="setPage(page - 1)">上一页</button>
        <span>{{ page }} / {{ Math.max(1, Math.ceil(total / pageSize)) }} · 共 {{ total }} 条</span>
        <button :disabled="page * pageSize >= total" @click="setPage(page + 1)">下一页</button>
      </div>
    </aside>

    <!-- 右：审计详情 -->
    <section class="detail">
      <PageState :state="detailError ? 'error' : loadingDetail ? (detail ? 'refreshing' : 'initial-loading') : detail ? 'ready' : 'idle'" :preserve-content="!!detail" :message="detailError || undefined" @retry="select(selectedId)">
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

        <!-- 当前接口提供最近一轮决策；不是逐条消息的全轮次追溯。 -->
        <div v-if="trace && traceError" class="trace-empty error" role="alert">{{ traceError }} <button @click="select(selectedId)">重试</button></div>
        <div v-if="trace" class="trace-cards">
          <div class="tc-ttl">{{ trace.master_decision ? '最近一轮已记录决策' : '追溯记录（未记录主智能体决策）' }} · 追溯记录不代表结论已核验</div>
          <div class="trace-scope">子智能体记录对应最近一轮；算子与模型调用记录为会话级汇总。</div>
          <DecisionFlow :trace="trace" />
          <SubAgentChips :trace="trace" />
          <EvidenceChain :trace="trace" />
        </div>
        <div v-else-if="loadingTrace" class="trace-empty" role="status">正在加载追溯记录…</div>
        <div v-else-if="traceError" class="trace-empty error" role="alert">
          {{ traceError }} <button @click="select(selectedId)">重试</button>
        </div>
        <div v-else class="trace-empty">该会话暂无已记录的追溯数据</div>
      </template>

      <div v-else-if="loadingDetail" class="placeholder" role="status">加载会话详情中…</div>
      <div v-else-if="detailError" class="placeholder error" role="alert">
        <span>{{ detailError }} <button @click="select(selectedId)">重试</button></span>
      </div>
      <div v-else class="placeholder">← 选择左侧会话，查看主智能体决策与执行审计</div>
      </PageState>
    </section>
  </div>
  </PageShell>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import PageShell from '@/components/common/PageShell.vue'
import PageState from '@/components/common/PageState.vue'
import { formatDateTime } from '@/utils/displayFormat'
import { useRoute } from 'vue-router'
import { conversationsService } from '@/api/modules/conversations'
import { logsService } from '@/api/modules/logs'
import MarkdownRenderer from '@/components/markdown/MarkdownRenderer.vue'
import DecisionFlow from '@/components/aiops/DecisionFlow.vue'
import SubAgentChips from '@/components/aiops/SubAgentChips.vue'
import EvidenceChain from '@/components/aiops/EvidenceChain.vue'
import { useAuditDetail } from '@/composables/useAuditDetail'
import { useAuditList } from '@/composables/useAuditList'
import { useAssistantContext } from '@/composables/useAssistantContext'

const { selectedId, detail, trace, detailError, traceError, loadingDetail, loadingTrace, select: fetchDetail, dispose } = useAuditDetail({
  detail: conversationsService.detail,
  trace: logsService.trace,
})
async function select(id: string) {
  const same = id === selectedId.value
  const previousDetail = detail.value
  const previousTrace = trace.value
  const request = fetchDetail(id)
  if (same) { detail.value = previousDetail; trace.value = previousTrace }
  await request
}
function refresh() { void loadList(); if (selectedId.value) void select(selectedId.value) }
const route = useRoute()
const searchInput = ref('')
const { conversations, total, page, search, pageSize, setSearch: applySearch, setPage: applyPage, loading: loadingList, error: listError, load: loadList, dispose: disposeList } = useAuditList(conversationsService.list, select, { selectedId: () => selectedId.value })
let searchTimer: ReturnType<typeof setTimeout> | undefined
function setSearch(value: string) {
  if (searchTimer) clearTimeout(searchTimer)
  if (value.trim().replace(/\s+/g, ' ') !== search.value || page.value !== 1) { conversations.value = []; total.value = 0 }
  return applySearch(value)
}
function scheduleSearch(value: string) {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { void setSearch(value) }, 300)
}
function setPage(value: number) {
  if (value !== page.value) { conversations.value = []; total.value = 0 }
  return applyPage(value)
}
const selectedOutsideList = computed(() => selectedId.value && !conversations.value.some(c => c.id === selectedId.value))
useAssistantContext(() => ({ pageId: 'audit', objectId: selectedId.value || null, source: '会话审计接口', filters: { search: search.value, page: page.value }, status: loadingList.value || loadingDetail.value ? 'loading' : listError.value || detailError.value ? 'error' : conversations.value.length ? 'ready' : 'empty', actions: ['navigate', 'audit.focus'] }), async action => {
  if (action.capability !== 'audit.focus') return { success: false, message: '审计页不支持该操作' }
  const id = String(action.parameters.sessionId)
  await select(id)
  const success = selectedId.value === id && detail.value?.id === id && !detailError.value
  return { success, message: detailError.value || (success ? `已加载会话 ${id}` : '会话不存在或响应对象不一致') }
})
watch(() => route.query.session, session => {
  const id = Array.isArray(session) ? session[0] : session
  if (id) void select(id)
}, { immediate: true })

function roleLabel(r: string) {
  return r === 'user' ? '👤 提问' : r === 'assistant' ? '🤖 主智能体' : '🔧 工具'
}
const fmt = formatDateTime

onMounted(loadList)
onBeforeUnmount(() => { if (searchTimer) clearTimeout(searchTimer); disposeList(); dispose() })
</script>

<style scoped>
.audit { display: flex; gap: 14px; height: 100%; min-height: 0; overflow: hidden }
.list, .detail, .list-body, .msgs { min-height: 0 }
.list-head, .list-search, .list-pager, .d-head, .selection-note { flex-shrink: 0 }
.list { width: 280px; flex-shrink: 0; background: var(--card-bg); border: 1px solid var(--brd); border-radius: 13px;
  display: flex; flex-direction: column; overflow: hidden }
.list-head { display: flex; justify-content: space-between; align-items: center; padding: 12px 14px; border-bottom: 1px solid var(--brd) }
.list-ttl { font-size: 13px; font-weight: 700 }
.list-cnt { font-size: 11px; color: var(--text-muted) }
.list-body { flex: 1; overflow-y: auto; padding: 6px }
.list-search { display: flex; align-items: center; gap: 6px; margin: 9px; padding: 4px 5px 4px 9px; border: 1px solid var(--brd); border-radius: 9px; background: #f8fafc }
.list-search:focus-within { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(79,70,229,.09) }
.search-icon { color: var(--text-muted); font-size: 16px }
.list-search input { min-width: 0; width: 100%; font-size: 12px; border: 0; outline: 0; background: transparent; color: var(--text-primary) }
.list-search button { border: 0; border-radius: 6px; cursor: pointer }
.clear-search { background: transparent; color: var(--text-muted); font-size: 16px }
.search-btn { padding: 5px 9px; background: var(--primary); color: #fff; font-size: 11px }
.list-pager { display: flex; justify-content: space-between; align-items: center; padding: 8px; font-size: 10px; border-top: 1px solid var(--brd) }
.selection-note { padding: 6px 12px; font-size: 11px; color: var(--text-muted); overflow-wrap: anywhere }
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
.trace-scope { font-size: 11px; color: var(--text-muted) }
.trace-empty { padding: 12px 16px; font-size: 12px; color: var(--text-muted); border-top: 1px solid var(--brd) }
.error { color: #b91c1c }
.error button { margin-left: 8px; color: var(--primary); background: transparent; border: 1px solid var(--brd); border-radius: 5px; padding: 3px 8px; cursor: pointer }

.placeholder { flex: 1; display: grid; place-items: center; color: var(--text-muted); font-size: 14px }
</style>
