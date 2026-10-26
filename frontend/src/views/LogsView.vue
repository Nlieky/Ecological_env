<template>
  <PageShell class="logs" title="日志中心" subtitle="按异常、模块和会话快速定位运行问题" scroll="contained">
    <template #actions><el-button :loading="loading" @click="load">刷新</el-button></template>
    <template #toolbar>
    <div class="head">
      <div class="bar">
        <el-radio-group v-model="logType" @change="onTypeChange">
          <el-radio-button v-for="t in TYPES" :key="t.v" :label="t.v">{{ t.t }}</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <div class="summary-row">
      <button :class="{ on: logType === 'all' }" @click="setType('all')"><b>{{ total }}</b><span>全部日志</span></button>
      <button :class="{ on: logType === 'error' }" @click="setType('error')"><b class="danger">错误</b><span>优先处理</span></button>
      <button @click="setType('master')"><b>主智能体</b><span>决策过程</span></button>
      <button @click="setType('subagent')"><b>子智能体</b><span>执行过程</span></button>
    </div>
    </template>
    <PageState :state="error ? 'error' : loading ? (rows.length ? 'refreshing' : 'initial-loading') : rows.length ? 'ready' : 'empty'" :preserve-content="!!rows.length" :message="error ? `日志加载失败：${error}` : undefined" @retry="load">
    <div class="log-list">
      <article v-for="row in rows" :key="`${row.module}-${row.id}`" class="log-row" :class="row.level || 'info'">
        <div class="log-meta"><span class="level">{{ levelLabel(row) }}</span><span class="ts">{{ formatDateTime(row.timestamp) }}</span></div>
        <div class="log-main"><div class="log-title">{{ row.content || '—' }}</div><div class="tags"><span>{{ moduleLabel(row.module) }}</span><span v-if="row.latency_ms != null">{{ formatDuration(row.latency_ms) }}</span><RouterLink v-if="sessionId(row)" :to="`/logs/trace/${encodeURIComponent(sessionId(row))}`">查看追溯</RouterLink></div>
          <details><summary>查看上下文</summary><div class="detail">
            <div v-for="(v, k) in row.details || {}" :key="k" class="kv">
              <span class="dk">{{ k }}</span>
              <span class="dv">{{ fmtVal(v) }}</span>
            </div>
            <div v-if="!row.details || !Object.keys(row.details).length" class="empty">无详细信息</div>
          </div></details></div>
      </article>
    </div>
    </PageState>
    <template #footer>
    <div class="pager">
      <span class="total">共 {{ total }} 条</span>
      <el-pagination background layout="prev, pager, next" :total="total" :page-size="PAGE" :current-page="page"
        @current-change="onPage" />
    </div>
    </template>
  </PageShell>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { RouterLink } from 'vue-router'
import PageShell from '@/components/common/PageShell.vue'
import PageState from '@/components/common/PageState.vue'
import { formatDateTime, formatDuration } from '@/utils/displayFormat'
import { logsService } from '@/api/modules/logs'
import type { LogEntryV1, LogType } from '@/api/types/api.types'
import { useAssistantContext } from '@/composables/useAssistantContext'

const TYPES: { v: LogType; t: string }[] = [
  { v: 'all', t: '全部' },
  { v: 'api', t: 'API' },
  { v: 'master', t: '主智能体' },
  { v: 'subagent', t: '子智能体' },
  { v: 'operator', t: '算子' },
  { v: 'llm', t: 'LLM' },
  { v: 'error', t: '错误' },
]
const PAGE = 20

const logType = ref<LogType>('api')
const rows = ref<LogEntryV1[]>([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)
const error = ref<string | null>(null)
let generation = 0
let disposed = false
let loadedKey = ''
function sessionId(row: LogEntryV1) {
  const value = row.details?.session_id
  return typeof value === 'string' && value.trim() ? value : ''
}

async function load() {
  const current = ++generation
  loading.value = true
  error.value = null
  const key = `${logType.value}:${page.value}`
  if (key !== loadedKey) { rows.value = []; total.value = 0 }
  try {
    const r = await logsService.list({ log_type: logType.value, page: page.value, page_size: PAGE })
    if (disposed || current !== generation) return
    rows.value = r.data
    total.value = r.total
    loadedKey = key
  } catch (e: any) { if (!disposed && current === generation) error.value = e?.message || '请求失败' }
  finally { if (!disposed && current === generation) loading.value = false }
}
function onTypeChange() { page.value = 1; void load() }
function setType(value: LogType) { logType.value = value; onTypeChange() }
function onPage(p: number) { page.value = p; void load() }
function fmtVal(v: unknown) {
  if (v == null || v === '') return '—'
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}
function moduleLabel(value: string) { return TYPES.find(t => t.v === value)?.t || value }
function levelLabel(row: LogEntryV1) { return row.level === 'error' ? '错误' : row.level === 'warning' ? '警告' : row.slow ? '慢调用' : '信息' }

useAssistantContext(() => ({ pageId: 'logs', source: '日志查询接口', filters: { module: logType.value, page: page.value }, status: loading.value ? 'loading' : error.value ? 'error' : rows.value.length ? 'ready' : 'empty', actions: ['navigate', 'logs.filter'] }), async action => {
  if (action.capability !== 'logs.filter') return { success: false, message: '日志页不支持该操作' }
  logType.value = action.parameters.module as LogType
  page.value = 1
  await load()
  return { success: !error.value, message: error.value || `已按 ${logType.value} 查询 ${total.value} 条日志` }
})
onMounted(load)
onBeforeUnmount(() => { disposed = true; ++generation })
</script>

<style scoped>
.logs { height: 100%; min-height: 0 }
.head { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px }
.ttl { font-size: 16px; font-weight: 700 }
.sub { margin-top: 3px; font-size: 11px; color: var(--text-muted) }
.summary-row { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 10px }
.summary-row button { display: flex; flex-direction: column; gap: 4px; text-align: left; padding: 11px 13px; border: 1px solid var(--brd); border-radius: 10px; background: var(--card-bg); cursor: pointer }
.summary-row button.on { border-color: var(--primary); background: #eef2ff }.summary-row b { color: var(--text-primary) }.summary-row span { font-size: 11px; color: var(--text-muted) }.summary-row .danger { color: #dc2626 }
.log-list { flex: 1; min-height: 0; overflow-y: auto; border: 1px solid var(--brd); border-radius: 12px; background: var(--card-bg) }
.log-main { min-width: 0; overflow-wrap: anywhere }.tags { flex-wrap: wrap }.summary-row { margin-top: 12px }
.log-row { display: grid; grid-template-columns: 150px 1fr; gap: 14px; padding: 13px 15px; border-bottom: 1px solid var(--brd) }.log-row:last-child { border-bottom: 0 }
.log-meta { display: flex; flex-direction: column; gap: 6px }.level { width: fit-content; font-size: 11px; font-weight: 600 }.error .level { color: #dc2626 }.warning .level { color: #d97706 }
.log-title { font-size: 13px; color: var(--text-primary) }.tags { display: flex; gap: 12px; margin-top: 5px; font-size: 11px; color: var(--text-muted) }.tags a { color: var(--primary) }
details summary { margin-top: 8px; color: var(--primary); font-size: 11px; cursor: pointer }
.ts { font-size: 12px; color: var(--text-secondary); font-variant-numeric: tabular-nums }
.content { font-size: 12px; color: var(--text-muted); font-family: ui-monospace, monospace;
  display: inline-block; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; vertical-align: bottom }
.pager { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-top: 4px; padding-right: 130px; box-sizing: border-box }
.total { font-size: 12px; color: var(--text-muted) }
.detail { padding: 6px 16px 10px; display: grid; grid-template-columns: 1fr 1fr; gap: 4px 20px }
@media (max-width: 760px) { .summary-row { grid-template-columns: 1fr 1fr }.log-row { grid-template-columns: 1fr }.log-meta { flex-direction: row } }
.kv { display: flex; gap: 8px; min-width: 0; font-size: 12px }
.dk { color: var(--text-muted); flex-shrink: 0; font-family: ui-monospace, monospace }
.dv { color: var(--text-primary); word-break: break-all; font-family: ui-monospace, monospace }
.detail .empty { padding: 4px 0; grid-column: 1 / -1 }
</style>
