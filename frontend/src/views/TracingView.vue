<template>
  <div class="trc">
    <!-- 筛选 -->
    <div class="bar">
      <el-select v-model="service" placeholder="服务" clearable style="width: 200px" @change="onServiceChange">
        <el-option v-for="s in services" :key="s.name" :label="s.name" :value="s.name" />
      </el-select>
      <el-select v-model="operation" placeholder="操作" clearable filterable style="width: 260px">
        <el-option v-for="op in operationOptions" :key="op" :label="op" :value="op" />
      </el-select>
      <el-input-number v-model="minDurationMs" :min="0" :step="100" placeholder="最小耗时(ms)" controls-position="right" style="width: 150px" />
      <el-button type="primary" @click="search"><el-icon><Search/></el-icon>&nbsp;搜索</el-button>
    </div>

    <!-- trace 列表 -->
    <el-table :data="traces" v-loading="loading" stripe style="width: 100%" @row-click="openDetail" highlight-current-row>
      <el-table-column label="Trace ID" min-width="120">
        <template #default="{ row }"><span class="tid">{{ row.traceID }}</span></template>
      </el-table-column>
      <el-table-column label="根操作" min-width="220" prop="rootSpanName" />
      <el-table-column label="服务" width="170" prop="rootServiceName" />
      <el-table-column label="开始时间" width="180">
        <template #default="{ row }">{{ fmtTime(row.startTime) }}</template>
      </el-table-column>
      <el-table-column label="耗时" width="110">
        <template #default="{ row }">
          <el-tag size="small" :type="durType(row.duration)" effect="plain">{{ fmtDur(row.duration) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Span 数" width="90" prop="spanCount" />
    </el-table>
    <div v-if="!loading && !traces.length" class="empty">无匹配链路</div>

    <!-- 详情抽屉 -->
    <el-drawer v-model="drawerVisible" :title="`链路详情 · ${currentTraceId}`" direction="rtl" size="640px">
      <div v-loading="detailLoading">
        <template v-if="detail">
          <div class="d-summary">
            <div><span class="k">根操作</span>{{ rootOp }}</div>
            <div><span class="k">总耗时</span>{{ fmtDur(totalDur) }}</div>
            <div><span class="k">Span 数</span>{{ detail.spans.length }}</div>
          </div>
          <div class="spans">
            <div v-for="s in spansSorted" :key="s.spanID" class="span">
              <div class="span-head">
                <span class="span-op">{{ s.operationName }}</span>
                <span class="span-svc">{{ svcOf(s) }}</span>
                <span class="span-dur">{{ fmtDur(s.duration) }}</span>
              </div>
              <div class="waterfall">
                <i :style="{ left: leftPct(s) + '%', width: widthPct(s) + '%' }"></i>
              </div>
              <details v-if="Object.keys(s.tags || {}).length || (s.logs && s.logs.length)" class="meta">
                <summary>标签 / 日志（{{ Object.keys(s.tags||{}).length + (s.logs?.length||0) }}）</summary>
                <div class="kv"><span v-for="(v, k) in s.tags" :key="k"><b>{{ k }}</b>: {{ v }}</span></div>
                <div v-for="(lg, i) in s.logs" :key="i" class="log">▸ {{ lg.fields?.event || '' }} {{ fmtFields(lg.fields) }}</div>
              </details>
            </div>
          </div>
        </template>
        <div v-else-if="!detailLoading" class="empty">无详情</div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { observabilityService } from '@/api/modules/observability'
import type { CatalogService, TraceSearchResult, TraceDetail, TraceSpan } from '@/api/types/api.types'

const services = ref<CatalogService[]>([])
const service = ref('')
const operation = ref('')
const minDurationMs = ref<number | undefined>(undefined)
const traces = ref<TraceSearchResult[]>([])
const loading = ref(false)

const operationOptions = computed(() => {
  if (!service.value) return services.value.flatMap((s) => s.operations)
  return services.value.find((s) => s.name === service.value)?.operations ?? []
})

function onServiceChange() { operation.value = '' }

async function loadCatalog() {
  try { const c = await observabilityService.catalog(); services.value = c.services }
  catch { services.value = [] }
}
async function search() {
  loading.value = true
  try {
    traces.value = await observabilityService.search({
      service: service.value || undefined,
      operation: operation.value || undefined,
      durationMin: minDurationMs.value ? minDurationMs.value * 1000 : undefined,
      limit: 50,
    })
  } catch { traces.value = [] }
  finally { loading.value = false }
}

// 详情
const drawerVisible = ref(false)
const currentTraceId = ref('')
const detail = ref<TraceDetail | null>(null)
const detailLoading = ref(false)
async function openDetail(row: TraceSearchResult) {
  currentTraceId.value = row.traceID
  drawerVisible.value = true
  detail.value = null
  detailLoading.value = true
  try { detail.value = await observabilityService.trace(row.traceID) }
  catch { detail.value = null }
  finally { detailLoading.value = false }
}

const rootOp = computed(() => detail.value?.spans.find((s) => !s.references.length)?.operationName || '—')
const totalDur = computed(() => {
  if (!detail.value?.spans.length) return 0
  const start = Math.min(...detail.value.spans.map((s) => s.startTime))
  const end = Math.max(...detail.value.spans.map((s) => s.startTime + s.duration))
  return end - start
})
const spansSorted = computed(() => {
  if (!detail.value) return []
  return [...detail.value.spans].sort((a, b) => a.startTime - b.startTime)
})
function svcOf(s: TraceSpan) {
  return detail.value?.processes?.[s.processID]?.serviceName || s.processID
}
function leftPct(s: TraceSpan) {
  if (!detail.value || !totalDur.value) return 0
  const start = Math.min(...detail.value.spans.map((x) => x.startTime))
  return ((s.startTime - start) / totalDur.value) * 100
}
function widthPct(s: TraceSpan) {
  if (!totalDur.value) return 0
  return Math.max((s.duration / totalDur.value) * 100, 1)
}

// 格式化（µs 单位）
function fmtTime(us: number) { return new Date(us / 1000).toLocaleString('zh-CN', { hour12: false }) }
function fmtDur(us: number) {
  if (us >= 1e6) return (us / 1e6).toFixed(2) + ' s'
  if (us >= 1000) return (us / 1000).toFixed(1) + ' ms'
  return us + ' µs'
}
function durType(us: number) {
  if (us >= 3e6) return 'danger'
  if (us >= 1e6) return 'warning'
  return 'success'
}
function fmtFields(f?: Record<string, unknown>) {
  if (!f) return ''
  return Object.entries(f).filter(([k]) => k !== 'event').map(([k, v]) => `${k}=${v}`).join(' ')
}

onMounted(async () => { await loadCatalog(); await search() })
</script>

<style scoped>
.trc { display: flex; flex-direction: column; gap: 14px }
.bar { display: flex; gap: 10px; align-items: center; flex-wrap: wrap }
.tid { font-family: ui-monospace, monospace; font-size: 12px; color: var(--primary) }
.empty { color: var(--text-muted); font-size: 13px; padding: 24px; text-align: center }

.d-summary { display: flex; flex-direction: column; gap: 6px; background: #f8fafc; border: 1px solid var(--brd);
  border-radius: 10px; padding: 12px 14px; margin-bottom: 14px }
.d-summary .k { display: inline-block; width: 64px; color: var(--text-muted); font-size: 11px }
.spans { display: flex; flex-direction: column; gap: 10px }
.span { border: 1px solid var(--brd); border-radius: 9px; padding: 9px 11px }
.span-head { display: flex; align-items: center; gap: 10px }
.span-op { font-size: 12.5px; font-weight: 600; color: var(--text-primary); flex: 1; min-width: 0;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap }
.span-svc { font-size: 11px; color: var(--text-muted); background: #f1f5f9; padding: 2px 7px; border-radius: 5px }
.span-dur { font-size: 11.5px; color: var(--primary); font-weight: 600; font-variant-numeric: tabular-nums }
.waterfall { position: relative; height: 6px; background: #f1f5f9; border-radius: 3px; margin-top: 7px; overflow: hidden }
.waterfall i { position: absolute; top: 0; bottom: 0; background: var(--brand-gradient); border-radius: 3px; min-width: 2px }
.meta { margin-top: 6px }
.meta summary { cursor: pointer; font-size: 11px; color: var(--text-muted); user-select: none }
.kv { display: flex; flex-direction: column; gap: 2px; margin-top: 5px }
.kv span { font-size: 11px; color: var(--text-secondary); font-family: ui-monospace, monospace }
.kv b { color: var(--text-primary); font-weight: 600 }
.log { font-size: 11px; color: var(--text-muted); font-family: ui-monospace, monospace; margin-top: 2px }
</style>
