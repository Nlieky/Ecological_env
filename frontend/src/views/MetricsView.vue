<template>
  <PageShell title="指标查询" subtitle="按采样窗口比较进水与出水指标" class="metrics">
    <template #toolbar>
    <!-- 筛选条 -->
    <div class="bar">
      <div class="grp"><label class="lbl" for="metrics-plant">厂站</label><select id="metrics-plant" :value="plants.activePlant" @change="plants.selectPlant(($event.target as HTMLSelectElement).value)"><option value="" disabled>选择厂站</option><option v-for="p in plantOptions" :key="p" :value="p">{{ p }}</option></select><span v-if="plants.treeError">{{ plants.treeError }}</span></div>
      <div class="grp">
        <span class="lbl">指标</span>
        <button v-for="i in INDICATORS" :key="i.key" class="chip" :class="{ on: indicator === i.key }" @click="indicator = i.key">
          {{ i.label }}<span class="chip-d">{{ i.desc }}</span>
        </button>
      </div>
      <div class="grp">
        <span class="lbl">时间窗口</span>
        <button v-for="w in WINDOWS" :key="w.v" class="chip sm" :class="{ on: timeWindow === w.v && !customRange.start }" @click="pickWindow(w.v)">{{ w.t }}</button>
        <!-- 自定义日期范围(长时段堆叠查询,大屏流式看板不管这个) -->
        <span class="range-box">
          <span class="lbl">自定义</span>
          <input type="date" v-model="customRange.start" @change="loadCustom" />
          <span class="dash">~</span>
          <input type="date" v-model="customRange.end" @change="loadCustom" />
          <button v-if="customRange.start" class="chip sm clear" @click="clearRange">✕ 清除</button>
          <span class="lbl">含结束当天；未填结束日期时查询开始当天</span>
        </span>
      </div>
    </div>
    <p v-if="rangeError" role="alert" class="range-error">{{ rangeError }}</p>
    </template>
    <PageState :state="viewState" :preserve-content="!!dashboard" :message="error ? (dashboard ? '刷新失败，保留上次加载的数据。' : '指标数据加载失败，请重试。') : undefined" @retry="load">
    <p v-if="error" role="alert">{{ error }}</p>
    <p v-if="missingSide" role="status">{{ missingSide }}</p>
    <button v-if="viewState === 'empty'" type="button" @click="load">重新加载</button>
    <div v-if="dashboard" class="lbl">{{ contextLabel(dashboard.data_context) }} · 数据库 {{ dashboard.data_context?.bucket || '未核验' }} · 时效 {{ plantStatusLabel(dashboard.data_context?.freshness || 'unverified') }} · 最新采样 {{ formatSamplingTime(dashboard.data_context?.latest_sample_at, dashboard.data_context?.timezone) }} · 数据截至 {{ formatSamplingTime(dashboard.latest_time, dashboard.data_context?.timezone) }} · 窗口 {{ formatSamplingTime(dashboard.segment_start, dashboard.data_context?.timezone) }} ~ {{ formatSamplingTime(dashboard.segment_end, dashboard.data_context?.timezone) }} <span v-if="dashboard.data_context?.warning">· {{ dashboard.data_context.warning }}</span></div>

    <!-- 统计卡片 -->
    <div class="stats" v-if="cur">
      <div class="stat"><div class="k">当前(进水)</div><div class="v">{{ fmt(cur.influent) }} <span class="u">{{ curUnit }}</span></div></div>
      <div class="stat"><div class="k">当前(出水)</div><div class="v">{{ fmt(cur.effluent) }} <span class="u">{{ curUnit }}</span></div></div>
      <div class="stat"><div class="k">进水 均值/极值</div><div class="v sm">{{ fmt(stat.influent.mean) }} / {{ fmt(stat.influent.min) }}~{{ fmt(stat.influent.max) }}</div></div>
      <div class="stat"><div class="k">出水 均值/极值</div><div class="v sm">{{ fmt(stat.effluent.mean) }} / {{ fmt(stat.effluent.min) }}~{{ fmt(stat.effluent.max) }}</div></div>
    </div>

    <!-- 趋势图 -->
    <div class="chart-card">
      <div class="chart-head">
        <span class="ct">{{ curMeta.label }}（{{ curMeta.desc }}）趋势 · 进水 vs 出水</span>
        <span class="cs">{{ customRange.start ? `自定义 ${customRange.start} ~ ${customRange.end || customRange.start}` : `${records.length} 个采样点` }}</span>
      </div>
      <div class="chart-wrap">
        <div ref="chartEl" class="chart"></div>
      </div>
    </div>
    </PageState>
  </PageShell>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import echarts from '@/lib/echarts'
import PageShell from '@/components/common/PageShell.vue'
import PageState from '@/components/common/PageState.vue'
import { plantsService } from '@/api/modules/plants'
import { usePlantsStore } from '@/stores/plants'
import { dashboardSnapshot, latestValues, finiteStats, dateRange, requestGate, formatSamplingTime, plantStatusLabel, initializeMetrics } from '@/composables/dashboardData'
import { formatDataContext as contextLabel } from '@/utils/displayFormat'
import { useActionStore } from '@/stores/action'
import type { PlantDashboard } from '@/api/types/api.types'
import type { DashboardRecord } from '@/composables/dashboardData'
import { useAssistantContext } from '@/composables/useAssistantContext'
import { useAssistantContextStore } from '@/stores/assistantContext'
import { contextPolicy } from '@/assistant/contextPolicy'

const actionStore = useActionStore()
const plants = usePlantsStore()
const route = useRoute()
const assistantContext = useAssistantContextStore()
const plantOptions = computed(() => [...new Set([...(plants.tree?.cities.flatMap(c => c.districts.flatMap(d => d.plants.map(p => p.plant_id))) ?? []), ...(plants.tree?.ungrouped.map(p => p.plant_id) ?? [])])])
const dashboard = ref<PlantDashboard | null>(null)
const error = ref('')
const rangeError = ref('')
let loadedQuery = ''
const gate = requestGate()

const INDICATORS = [
  { key: 'pH', label: 'pH', desc: '酸碱度', unit: '' },
  { key: 'COD', label: 'COD', desc: '化学需氧量', unit: 'mg/L' },
  { key: 'TN', label: 'TN', desc: '总氮', unit: 'mg/L' },
  { key: 'AN', label: 'AN', desc: '氨氮', unit: 'mg/L' },
  { key: 'TP', label: 'TP', desc: '总磷', unit: 'mg/L' },
] as const
const WINDOWS = [{ t: '1H', v: '1h' }, { t: '6H', v: '6h' }, { t: '24H', v: '24h' }] as const

type IndKey = typeof INDICATORS[number]['key']
const indicator = ref<IndKey>('COD')
const timeWindow = ref<'1h' | '6h' | '24h'>('24h')
const records = ref<DashboardRecord[]>([])
const loading = ref(false)
const missingSide = computed(() => {
  if (!records.value.length) return ''
  const has = (side: 'influent' | 'effluent') => records.value.some(r => typeof r[side]?.[indicator.value] === 'number')
  return !has('influent') ? '当前指标缺少进水数据' : !has('effluent') ? '当前指标缺少出水数据' : ''
})
const viewState = computed(() => {
  if (loading.value) return dashboard.value ? 'refreshing' : 'initial-loading'
  if (error.value) return 'error'
  if (!records.value.length) return 'empty'
  return missingSide.value ? 'partial' : dashboard.value?.data_context?.freshness === 'stale' ? 'stale' : 'ready'
})

// 自定义日期范围(长时段查询;归本页,大屏流式看板保持固定滑窗)
const customRange = ref<{ start: string; end: string }>({ start: '', end: '' })
useAssistantContext(() => ({ pageId: 'metrics', plant: plants.activePlant || null, indicator: indicator.value, range: customRange.value.start ? { ...customRange.value } : timeWindow.value, source: dashboard.value?.data_context?.bucket || '指标查询接口（来源未核验）', freshness: dashboard.value?.data_context?.freshness || null, status: loading.value ? 'loading' : error.value ? 'error' : records.value.length ? 'ready' : 'empty', actions: ['navigate', 'metrics.filter'] }), async action => {
  if (action.capability !== 'metrics.filter') return { success: false, message: '指标页不支持该操作' }
  const p = action.parameters
  if (typeof p.plant === 'string') {
    const lease = assistantContext.snapshot()
    const plant = plants.activePlant
    await plants.fetchTree()
    const changed = contextPolicy(action, lease as unknown as Record<string, unknown>, assistantContext.current as unknown as Record<string, unknown>)
    if (!gate.alive() || route.path !== '/metrics' || changed || plants.activePlant !== plant) return { success: false, code: 'stale_context', message: changed || '页面或厂站已变化，未应用旧操作' }
    if (!plantOptions.value.includes(p.plant)) return { success: false, message: '厂站不在已加载目录中' }
    plants.selectPlant(p.plant)
  }
  if (p.indicator) indicator.value = p.indicator as IndKey
  if (p.range) { customRange.value = { start: '', end: '' }; timeWindow.value = p.range as '1h' | '6h' | '24h' }
  await load()
  return { success: !error.value && !!dashboard.value, message: error.value || (dashboard.value ? '指标查询已加载' : '未获得指标数据') }
})
function pickWindow(v: '1h' | '6h' | '24h') {
  customRange.value = { start: '', end: '' }
  timeWindow.value = v
  void load()
}
function clearRange() {
  customRange.value = { start: '', end: '' }
  void load()
}
async function loadCustom() {
  await load()
}

const curMeta = computed(() => INDICATORS.find((i) => i.key === indicator.value)!)
const curUnit = computed(() => curMeta.value.unit)

const cur = computed(() => records.value.length ? latestValues(records.value, indicator.value) : null)
const stat = computed(() => stats(indicator.value))

function stats(key: IndKey) {
  const calc = (side: 'influent' | 'effluent') => {
    return finiteStats(records.value.map((r) => r[side]?.[key]))
  }
  return { influent: calc('influent'), effluent: calc('effluent') }
}
function fmt(v: number | null | undefined) { return v == null ? '—' : v.toFixed(2) }

const chartEl = ref<HTMLDivElement>()
let chart: ReturnType<typeof echarts.init> | null = null

function renderChart() {
  if (!chart) return
  if (!records.value.length) { chart.clear(); return }
  const xs = records.value.map((r) => r.timestamp.replace('T', ' ').slice(5, 16)) // MM-DD HH:mm
  const infl = records.value.map((r) => r.influent?.[indicator.value] ?? null)
  const effl = records.value.map((r) => r.effluent?.[indicator.value] ?? null)

  // AI 动作标注：run_detector 的异常点 → 出水曲线 markPoint（值+类型标签）
  const ann = actionStore.annotations.filter((a) => a.value != null)
  const markPointData = ann.map((a) => ({
    coord: [a.timestamp.slice(5, 16), a.value],
    value: a.type,
    symbolSize: 42,
    itemStyle: { color: '#ef4444' },
    label: { show: true, formatter: a.type, fontSize: 10, color: '#fff' },
  }))

  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['进水', '出水'], top: 4, textStyle: { color: '#64748b', fontSize: 12 } },
    grid: { left: 48, right: 20, top: 36, bottom: 48 },
    xAxis: { type: 'category', data: xs, axisLabel: { color: '#94a3b8', fontSize: 11 }, axisLine: { lineStyle: { color: '#e2e8f0' } } },
    yAxis: { type: 'value', name: curUnit.value, nameTextStyle: { color: '#94a3b8', fontSize: 11 },
      axisLabel: { color: '#94a3b8', fontSize: 11 }, splitLine: { lineStyle: { color: '#f1f5f9' } } },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 16, bottom: 8 }],
    series: [
      { name: '进水', type: 'line', smooth: true, symbol: 'none', data: infl, lineStyle: { width: 2 },
        itemStyle: { color: '#6366f1' }, areaStyle: { color: 'rgba(99,102,241,.08)' } },
      { name: '出水', type: 'line', smooth: true, symbol: 'none', data: effl, lineStyle: { width: 2 },
        itemStyle: { color: '#10b981' },
        ...(markPointData.length ? [{ markPoint: { data: markPointData, symbol: 'circle' } }] : []) },
    ],
  })
}

async function load() {
  let range: ReturnType<typeof dateRange> | undefined
  rangeError.value = ''
  try { range = customRange.value.start ? dateRange(customRange.value.start, customRange.value.end) : undefined }
  catch (e) { rangeError.value = e instanceof Error ? e.message : '请输入有效日期'; gate.begin(); loading.value = false; return }
  const request = gate.begin()
  if (request === null) return
  loading.value = true
  const query = JSON.stringify([plants.activePlant, timeWindow.value, range])
  error.value = ''
  if (query !== loadedQuery) { records.value = []; dashboard.value = null; renderChart() }
  try {
    if (!plants.activePlant) { loading.value = false; return }
    const r = await plantsService.dashboard(plants.activePlant, parseInt(timeWindow.value), range?.anchor, range?.endDate)
    if (!gate.current(request)) return
    const snapshot = dashboardSnapshot(r.data)
    dashboard.value = snapshot.dashboard
    records.value = snapshot.records
    loadedQuery = query
  } catch (e: unknown) {
    if (!gate.current(request)) return
    error.value = e instanceof Error ? e.message : '指标数据加载失败'
  } finally { if (gate.current(request)) loading.value = false }
  await nextTick()
  if (gate.current(request)) renderChart()
}

watch(indicator, renderChart)
watch(() => plants.activePlant, load)

// ── AI 助手动作指令响应 ──────────────────────────────────────
// action store 的状态由 chat store 的 onAction 回调 dispatch（AI 助手说话 → 大屏变化）

// 指标切换："只看pH" → indicator 变 pH（支持中文名→key 映射）
const CN_TO_KEY: Record<string, IndKey> = { 'pH': 'pH', '酸碱度': 'pH', 'COD': 'COD', '化学需氧量': 'COD',
  'TN': 'TN', '总氮': 'TN', 'AN': 'AN', '氨氮': 'AN', 'NH3-N': 'AN', 'TP': 'TP', '总磷': 'TP' }
watch(() => actionStore.indicators, (v) => {
  if (v && v.length) {
    const key = CN_TO_KEY[v[0]] ?? (v[0] as IndKey)
    if (INDICATORS.some((i) => i.key === key)) indicator.value = key
  }
}, { immediate: true })

// 时间范围切换："看最近一周" → timeWindow 变化（7d/30d 超出本视图窗口，映射提示）
watch(() => actionStore.timeRange, (v) => {
  if (!v) return
  if (v === '1h' || v === '6h' || v === '24h') pickWindow(v)
  else console.info('[MetricsView] 时间范围', v, '超出本视图窗口(1h/6h/24h)，忽略')
})

// 算法标注：run_detector 结果 → 曲线上 markPoint 高亮异常点
watch(() => actionStore.annotations, () => renderChart(), { deep: true })

let resizeObserver: ResizeObserver | undefined
function resizeChart() { chart?.resize() }
watch(chartEl, (el, previous) => {
  if (!gate.alive()) return
  if (previous) resizeObserver?.unobserve(previous)
  chart?.dispose()
  chart = el ? echarts.init(el) : null
  if (el) resizeObserver?.observe(el)
  renderChart()
}, { flush: 'post' })
onMounted(async () => {
  window.addEventListener('resize', resizeChart)
  if (typeof ResizeObserver !== 'undefined') resizeObserver = new ResizeObserver(resizeChart)
  await initializeMetrics(() => plants.fetchTree(), gate, () => {
    if (!plants.activePlant && plantOptions.value.length) plants.selectPlant(plantOptions.value[0])
  }, load)
})
onBeforeUnmount(() => { gate.dispose(); window.removeEventListener('resize', resizeChart); resizeObserver?.disconnect(); chart?.dispose(); chart = null })
</script>

<style scoped>
.metrics { width: 100%; min-width: 0 }
.range-error { color: #dc2626; font-size: 13px; margin: 8px 0 0 }
.range-box { flex-wrap: wrap; max-width: 100% }
.bar { display: flex; flex-wrap: wrap; gap: 18px; align-items: center; background: var(--card-bg);
  border: 1px solid var(--brd); border-radius: 13px; padding: 11px 14px }
.grp { display: flex; align-items: center; gap: 7px; flex-wrap: wrap }
.lbl { font-size: 11px; color: var(--text-muted); letter-spacing: .5px }
.range-box { display: inline-flex; align-items: center; gap: 6px; padding: 3px 8px; flex-wrap: wrap;
  border: 1px solid var(--brd); border-radius: 8px; background: #fff }
.range-box input { border: 0; outline: none; font-size: 12px; color: var(--text-primary);
  font-family: inherit; cursor: pointer }
.range-box .dash { color: var(--text-muted) }
.chip.clear { border-style: dashed; color: #ef4444 }
.chip { background: #fff; border: 1px solid var(--brd); color: var(--text-secondary); font-size: 12.5px;
  padding: 6px 12px; border-radius: 8px; cursor: pointer; font-family: inherit; display: inline-flex; align-items: center; gap: 6px }
.chip.sm { padding: 6px 11px; font-size: 12px }
.chip:hover { border-color: var(--primary) }
.chip.on { color: var(--primary); border-color: var(--primary); background: #eef2ff; font-weight: 600 }
.chip-d { font-size: 10.5px; color: var(--text-muted); font-weight: 400 }
.chip.on .chip-d { color: var(--primary) }

.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px }
.stat { background: var(--card-bg); border: 1px solid var(--brd); border-radius: 11px; padding: 12px 14px }
.stat .k { font-size: 11px; color: var(--text-muted) }
.stat .v { font-size: 19px; font-weight: 700; color: var(--text-primary); margin-top: 4px }
.stat .v.sm { font-size: 14px }
.stat .u { font-size: 11px; color: var(--text-muted); font-weight: 400 }

.chart-card { background: var(--card-bg); border: 1px solid var(--brd); border-radius: 13px; padding: 14px 16px;
  position: relative }
.chart-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px }
.ct { font-size: 13px; font-weight: 700 }
.cs { font-size: 11px; color: var(--text-muted) }
.chart-wrap { position: relative; width: 100%; height: 400px }
.chart { width: 100%; height: 100% }
.loading { position: absolute; inset: 0; display: grid; place-items: center; color: var(--text-muted); font-size: 13px }
</style>
