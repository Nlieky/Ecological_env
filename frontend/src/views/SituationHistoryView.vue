<template>
  <div class="sh">
    <div class="hd">
      <div class="wins">
        <button v-for="w in WINDOWS" :key="w.v" :class="{ on: days === w.v }" @click="days = w.v">{{ w.t }}</button>
      </div>
    </div>

    <PageState :state="viewState" :preserve-content="loaded" :message="error ? (loaded ? '刷新失败，保留上次加载的数据。' : '历史态势加载失败，请重试。') : undefined" @retry="load">
    <p v-if="error" role="alert">{{ error }}</p>
    <button v-if="viewState === 'empty'" type="button" @click="load">重新加载</button>
    <template v-if="rows.length">
      <div class="grid">
        <!-- 每日监测点数 -->
        <div class="card">
          <div class="c-ttl">每日监测点数</div>
          <div ref="ptsEl" class="chart" />
        </div>
        <!-- 每日出水超标次数 -->
        <div class="card">
          <div class="c-ttl">每日出水超标次数</div>
          <div ref="exceedEl" class="chart" />
        </div>
        <!-- 出水均值趋势 -->
        <div class="card wide">
          <div class="c-ttl">出水指标日均趋势</div>
          <div ref="trendEl" class="chart" />
        </div>
        <!-- 明细表 -->
        <div class="card wide">
          <div class="c-ttl">每日明细</div>
          <div class="tbl">
            <div class="tr th"><span>日期</span><span>点数</span><span>进水</span><span>出水</span><span>超标</span>
              <span>pH</span><span>COD</span><span>氨氮</span><span>TP</span></div>
            <div v-for="r in [...rows].reverse()" :key="r.day" class="tr" :class="{ bad: r.exceed > 0 }">
              <span>{{ r.day }}</span><span>{{ r.points }}</span>
              <span>{{ r.influent_points }}</span><span>{{ r.effluent_points }}</span>
              <span :class="{ ex: r.exceed > 0 }">{{ r.exceed }}</span>
              <span>{{ m(r, 'pH') }}</span><span>{{ m(r, 'COD') }}</span><span>{{ m(r, 'AN') }}</span><span>{{ m(r, 'TP') }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>
    </PageState>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import echarts from '@/lib/echarts'
import api from '@/api/client'
import { usePolling } from '@/composables/usePolling'
import { requestGate } from '@/composables/dashboardData'
import PageState from '@/components/common/PageState.vue'

interface DayRow {
  day: string; points: number; influent_points: number; effluent_points: number; exceed: number
  metrics: { influent?: Record<string, number>; effluent?: Record<string, number> }
}

const WINDOWS = [
  { t: '近7天', v: 7 }, { t: '近30天', v: 30 }, { t: '近90天', v: 90 }, { t: '全部', v: 365 },
] as const
const days = ref(30)
const rows = ref<DayRow[]>([])
const loading = ref(false)
const error = ref('')
const loaded = ref(false)
let loadedDays: number | null = null
const gate = requestGate()
const viewState = computed(() => loading.value ? (loaded.value ? 'refreshing' : 'initial-loading') : error.value ? 'error' : rows.value.length ? 'ready' : 'empty')

const ptsEl = ref<HTMLDivElement>()
const exceedEl = ref<HTMLDivElement>()
const trendEl = ref<HTMLDivElement>()
let c1: ReturnType<typeof echarts.init> | null = null
let c2: ReturnType<typeof echarts.init> | null = null
let c3: ReturnType<typeof echarts.init> | null = null

const m = (r: DayRow, f: string) => r.metrics?.effluent?.[f] ?? '—'

async function load() {
  const request = gate.begin()
  if (request === null) return
  const requestedDays = days.value
  if (loadedDays !== requestedDays) { rows.value = []; loaded.value = false }
  loading.value = true
  error.value = ''
  try {
    const r = await api.get<unknown, { data: DayRow[] }>('/v1/system/history', { params: { days: requestedDays } })
    if (!gate.current(request)) return
    rows.value = r.data
    loadedDays = requestedDays
    loaded.value = true
    await nextTick()
    if (gate.current(request)) render()
  } catch (e) { if (gate.current(request)) error.value = e instanceof Error ? e.message : '历史态势加载失败' } finally { if (gate.current(request)) loading.value = false }
}

function render() {
  if (!rows.value.length) return
  const xs = rows.value.map((r) => r.day.slice(5))
  // 1) 点数
  c1?.setOption({
    tooltip: { trigger: 'axis' }, legend: { top: 0, textStyle: { fontSize: 10 } },
    grid: { left: 44, right: 10, top: 26, bottom: 24 },
    xAxis: { type: 'category', data: xs, axisLabel: { fontSize: 9.5 } },
    yAxis: { type: 'value' },
    series: [
      { name: '进水', type: 'bar', stack: 'p', data: rows.value.map((r) => r.influent_points), itemStyle: { color: '#6366f1', borderRadius: [0,0,0,0] } },
      { name: '出水', type: 'bar', stack: 'p', data: rows.value.map((r) => r.effluent_points), itemStyle: { color: '#10b981', borderRadius: [3,3,0,0] } },
    ],
  }, true)
  // 2) 超标
  c2?.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 36, right: 10, top: 18, bottom: 24 },
    xAxis: { type: 'category', data: xs, axisLabel: { fontSize: 9.5 } },
    yAxis: { type: 'value', minInterval: 1 },
    series: [{ type: 'bar', data: rows.value.map((r) => r.exceed),
      itemStyle: { color: '#ef4444', borderRadius: [3,3,0,0] } }],
  }, true)
  // 3) 出水均值
  const fields = [['pH', '#6366f1'], ['COD', '#f59e0b'], ['TN', '#10b981'], ['AN', '#ef4444'], ['TP', '#8b5cf6']]
  c3?.setOption({
    tooltip: { trigger: 'axis' }, legend: { top: 0, textStyle: { fontSize: 10 } },
    grid: { left: 44, right: 20, top: 26, bottom: 24 },
    xAxis: { type: 'category', data: xs, axisLabel: { fontSize: 9.5 } },
    yAxis: [{ type: 'value', name: 'mg/L' }, { type: 'value', name: 'pH', min: 6, max: 9 }],
    series: fields.map(([f, c]) => ({
      name: f === 'AN' ? '氨氮' : f, type: 'line', smooth: true, symbol: 'circle', symbolSize: 4,
      yAxisIndex: f === 'pH' ? 1 : 0,
      data: rows.value.map((r) => r.metrics?.effluent?.[f] ?? null),
      lineStyle: { width: 1.6, color: c }, itemStyle: { color: c },
    })),
  }, true)
}

function resize() { c1?.resize(); c2?.resize(); c3?.resize() }
watch(days, load)
let resizeObserver: ResizeObserver | undefined
const elements: (HTMLDivElement | undefined)[] = []
function syncCharts() {
  if (!gate.alive()) return
  const current = [ptsEl.value, exceedEl.value, trendEl.value]
  const charts = [c1, c2, c3]
  current.forEach((el, i) => {
    if (el === elements[i]) return
    if (elements[i]) resizeObserver?.unobserve(elements[i]!)
    charts[i]?.dispose()
    elements[i] = el
    charts[i] = el ? echarts.init(el) : null
    if (el) resizeObserver?.observe(el)
  })
  ;[c1, c2, c3] = charts
  render()
}
watch([ptsEl, exceedEl, trendEl], syncCharts, { flush: 'post' })
const { start, stop } = usePolling(load, 60_000)
onMounted(() => {
  if (typeof ResizeObserver !== 'undefined') resizeObserver = new ResizeObserver(resize)
  window.addEventListener('resize', resize)
  start()
})
onBeforeUnmount(() => {
  gate.dispose()
  stop()
  window.removeEventListener('resize', resize)
  elements.forEach(el => { if (el) resizeObserver?.unobserve(el) })
  resizeObserver?.disconnect()
  c1?.dispose(); c2?.dispose(); c3?.dispose()
  c1 = null; c2 = null; c3 = null
})
</script>

<style scoped>
.sh { display: flex; flex-direction: column; gap: 14px }
.hd { display: flex; align-items: center; gap: 14px }
.hd h2 { margin: 0; font-size: 18px }
.wins { display: flex; gap: 6px }
.wins button { background: #fff; border: 1px solid var(--brd, #e2e8f0); border-radius: 7px;
  padding: 5px 12px; cursor: pointer; font-size: 12px; color: var(--text-secondary, #475569) }
.wins button.on { border-color: var(--primary, #4f46e5); color: var(--primary, #4f46e5); font-weight: 600 }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px }
.card { background: var(--card-bg, #fff); border: 1px solid var(--brd, #e2e8f0); border-radius: 13px; padding: 12px }
.card.wide { grid-column: 1 / -1 }
.c-ttl { font-size: 13px; font-weight: 600; margin-bottom: 8px }
.chart { height: 220px }
.tbl { font-size: 12.5px }
.tr { display: grid; grid-template-columns: 1.2fr .7fr .7fr .7fr .7fr .7fr .7fr .7fr .7fr; gap: 6px;
  padding: 7px 10px; border-top: 1px solid #eef2f7; align-items: center }
.tr.th { border-top: 0; color: var(--text-muted); font-size: 11px; font-weight: 600; background: #f8fafc; position: sticky; top: 0 }
.tr.bad { background: rgba(239,68,68,.04) }
.ex { color: #ef4444; font-weight: 700 }
.loading { padding: 60px; text-align: center; color: var(--text-muted); font-size: 13px }
@media (max-width: 1100px) { .grid { grid-template-columns: 1fr } }
</style>
