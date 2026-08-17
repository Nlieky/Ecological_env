<template>
  <div class="pdash">
    <!-- 左：厂区目录树 -->
    <div class="side">
      <div class="side-ttl">厂区目录</div>
      <PlantTree :active-id="plantId" @select="goPlant" />
    </div>

    <!-- 右：单厂监控大屏 -->
    <div class="main" v-if="store.dashboard">
      <!-- 顶部：厂名 + 窗口 + 刷新状态 -->
      <div class="head">
        <div>
          <h2>{{ plantId }}</h2>
          <span class="sub">
            <span class="live-dot" :class="{ on: !store.dashboardLoading }" />
            {{ store.dashboardLoading ? '刷新中…' : '实时监测中' }} ·
            进水 {{ store.dashboard.influent_points }} 点 · 出水 {{ store.dashboard.effluent_points }} 点
          </span>
        </div>
        <div class="wins">
          <button v-for="w in WINDOWS" :key="w.v" :class="{ on: hours === w.v }" @click="hours = w.v">{{ w.t }}</button>
          <button class="pause" :class="{ on: !polling }" @click="togglePolling">{{ polling ? '⏸ 暂停' : '▶ 恢复' }}</button>
        </div>
      </div>

      <!-- 第一行：指标卡片（点击选中联动趋势） -->
      <div class="cards">
        <div v-for="(ind, field) in store.dashboard.indicators" :key="field" class="card"
          :class="[ind.status, { sel: curField === field }]" @click="curField = String(field)">
          <div class="c-hd">{{ ind.label }}<span v-if="ind.unit" class="u">{{ ind.unit }}</span></div>
          <div class="c-vals">
            <div class="v"><span class="k">进</span>{{ ind.influent ?? '—' }}</div>
            <div class="v"><span class="k">出</span>{{ ind.effluent ?? '—' }}</div>
          </div>
          <div class="c-st" :class="ind.status">
            {{ ind.status === 'normal' ? '正常' : ind.status === 'warning' ? '⚠ 超限' : '无数据' }}
          </div>
        </div>
      </div>

      <!-- 第二行：双趋势图（主指标大图 + 次指标小图） -->
      <div class="charts-row">
        <div class="chart-card main-chart">
          <div class="ch-hd">{{ curLabel }} 趋势 · 进水 vs 出水</div>
          <div ref="chartEl" class="chart" />
        </div>
        <div class="chart-card mini-chart">
          <div class="ch-hd">全指标缩略</div>
          <div ref="miniChartEl" class="chart mini" />
        </div>
      </div>

      <!-- 第三行：数据质量 -->
      <div class="quality-card">
        <div class="ch-hd">数据质量</div>
        <div class="q-grid">
          <div class="q-item"><span class="q-k">数据窗口</span><span class="q-v">{{ store.dashboard.window_hours }}h</span></div>
          <div class="q-item"><span class="q-k">进水点数</span><span class="q-v">{{ store.dashboard.influent_points }}</span></div>
          <div class="q-item"><span class="q-k">出水点数</span><span class="q-v">{{ store.dashboard.effluent_points }}</span></div>
          <div class="q-item"><span class="q-k">最后刷新</span><span class="q-v">{{ lastRefresh }}</span></div>
        </div>
      </div>
    </div>

    <div v-else class="main loading">
      {{ store.dashboardLoading ? '加载看板数据…' : '该厂暂无数据' }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import echarts from '@/lib/echarts'
import PlantTree from '@/components/cockpit/PlantTree.vue'
import { usePlantsStore } from '@/stores/plants'
import { usePolling } from '@/composables/usePolling'

const route = useRoute()
const router = useRouter()
const store = usePlantsStore()

const WINDOWS = [
  { t: '24h', v: 24 }, { t: '72h', v: 72 }, { t: '168h', v: 168 }, { t: '全部', v: 10000 },
] as const

const plantId = computed(() => decodeURIComponent(String(route.params.plantId || '')))
const hours = ref(10000) // 默认全部（现有数据是历史批次）
const curField = ref('COD')
const lastRefresh = ref('')

const curLabel = computed(() => store.dashboard?.indicators?.[curField.value]?.label || curField.value)

const chartEl = ref<HTMLDivElement>()
const miniChartEl = ref<HTMLDivElement>()
let chart: ReturnType<typeof echarts.init> | null = null
let miniChart: ReturnType<typeof echarts.init> | null = null

function goPlant(id: string) {
  router.push(`/plants/${encodeURIComponent(id)}`)
}

// ── 轮询刷新（数据流式推进）──
const POLL_MS = 10_000 // 10 秒一刷，模拟实时
const { start: startPoll, stop: stopPoll } = usePolling(
  async () => { await store.fetchDashboard(plantId.value, hours.value); lastRefresh.value = new Date().toLocaleTimeString() },
  POLL_MS,
)
const polling = ref(true)
function togglePolling() {
  if (polling.value) { stopPoll(); polling.value = false } else { startPoll(); polling.value = true }
}

// ── 主趋势图 ──
function renderChart() {
  const ind = store.dashboard?.indicators?.[curField.value]
  if (!chart || !ind) return
  const infl = ind.series.influent.map((p) => [p.time.slice(5), p.value])
  const effl = ind.series.effluent.map((p) => [p.time.slice(5), p.value])
  const xs = effl.length ? effl.map((p) => p[0]) : infl.map((p) => p[0])
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['进水', '出水'], top: 4 },
    grid: { left: 52, right: 20, top: 34, bottom: 44 },
    xAxis: { type: 'category', data: xs, axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value', name: ind.unit },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 16, bottom: 8 }],
    series: [
      { name: '进水', type: 'line', smooth: true, symbol: 'none', data: infl,
        lineStyle: { width: 2 }, itemStyle: { color: '#6366f1' }, areaStyle: { color: 'rgba(99,102,241,.06)' } },
      { name: '出水', type: 'line', smooth: true, symbol: 'none', data: effl,
        lineStyle: { width: 2 }, itemStyle: { color: '#10b981' } },
    ],
  }, true)
}

// ── 全指标缩略图（所有出水指标归一化叠画） ──
function renderMini() {
  const inds = store.dashboard?.indicators
  if (!miniChart || !inds) return
  const palette = ['#6366f1', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6', '#06b6d4']
  const series: any[] = []
  const xs: string[] = []
  Object.values(inds).forEach((ind, i) => {
    const pts = ind.series.effluent.map((p) => p.value)
    if (!pts.length) return
    const mx = Math.max(...pts), mn = Math.min(...pts)
    const norm = (v: number) => mx === mn ? 0.5 : (v - mn) / (mx - mn)
    if (!xs.length) xs.push(...ind.series.effluent.map((p) => p.time.slice(5, 10)))
    series.push({
      name: ind.label, type: 'line', smooth: true, symbol: 'none',
      data: pts.map(norm), lineStyle: { width: 1.5, opacity: .8 },
      itemStyle: { color: palette[i % palette.length] },
    })
  })
  miniChart.setOption({
    tooltip: { trigger: 'axis', formatter: (ps: any) =>
      ps.map((p: any) => `${p.marker}${p.seriesId ? '' : ''}${p.name}: ${inds[p.name]?.effluent ?? '—'}`).join('<br/>') },
    legend: { top: 2, textStyle: { fontSize: 9 }, itemWidth: 12 },
    grid: { left: 8, right: 8, top: 42, bottom: 20 },
    xAxis: { type: 'category', data: xs, show: false },
    yAxis: { type: 'value', show: false, min: 0, max: 1 },
    series,
  }, true)
}

watch(hours, () => store.fetchDashboard(plantId.value, hours.value))
watch(() => store.dashboard, () => { nextTick(() => { renderChart(); renderMini() }) }, { deep: true })
watch(curField, renderChart)
watch(plantId, () => store.fetchDashboard(plantId.value, hours.value))

function resize() { chart?.resize(); miniChart?.resize() }

onMounted(async () => {
  if (chartEl.value) chart = echarts.init(chartEl.value)
  if (miniChartEl.value) miniChart = echarts.init(miniChartEl.value)
  window.addEventListener('resize', resize)
  await store.fetchTree()
  await store.fetchDashboard(plantId.value, hours.value)
  startPoll()
})
onBeforeUnmount(() => {
  stopPoll()
  window.removeEventListener('resize', resize)
  chart?.dispose(); chart = null
  miniChart?.dispose(); miniChart = null
})
</script>

<style scoped>
.pdash { display: flex; gap: 16px; align-items: flex-start }
.side { width: 240px; flex-shrink: 0; background: var(--card-bg, #fff);
  border: 1px solid var(--brd, #e2e8f0); border-radius: 13px; padding: 10px 8px }
.side-ttl { font-size: 11px; color: var(--text-muted, #94a3b8); letter-spacing: .5px; padding: 2px 6px 8px }
.main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 14px }
.main.loading { padding: 60px; text-align: center; color: var(--text-muted) }

.head { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px }
.head h2 { margin: 0; font-size: 18px }
.sub { font-size: 12px; color: var(--text-muted); display: inline-flex; align-items: center; gap: 5px }
.live-dot { width: 8px; height: 8px; border-radius: 50%; background: #cbd5e1 }
.live-dot.on { background: #10b981; animation: pulse 2s infinite }
@keyframes pulse { 0%,100% { box-shadow: 0 0 0 0 rgba(16,185,129,.4) } 50% { box-shadow: 0 0 0 5px rgba(16,185,129,0) } }
.wins { display: flex; gap: 6px }
.wins button { background: #fff; border: 1px solid var(--brd, #e2e8f0); border-radius: 7px;
  padding: 5px 12px; cursor: pointer; font-size: 12px; color: var(--text-secondary, #475569) }
.wins button.on { border-color: var(--primary, #4f46e5); color: var(--primary, #4f46e5); font-weight: 600 }
.wins button.pause { border-style: dashed }

.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px }
.card { background: var(--card-bg, #fff); border: 1px solid var(--brd, #e2e8f0);
  border-radius: 12px; padding: 10px 12px; cursor: pointer; transition: border-color .15s }
.card:hover { border-color: var(--primary, #4f46e5) }
.card.sel { border-color: var(--primary, #4f46e5); box-shadow: 0 0 0 1px var(--primary, #4f46e5) inset }
.card.warning { border-color: #fca5a5; background: rgba(239, 68, 68, .04) }
.c-hd { font-size: 12.5px; font-weight: 600; margin-bottom: 6px }
.c-hd .u { font-weight: 400; font-size: 10.5px; color: var(--text-muted); margin-left: 3px }
.c-vals { display: flex; gap: 10px }
.v { font-size: 16px; font-weight: 700 }
.v .k { font-size: 10px; font-weight: 400; color: var(--text-muted); margin-right: 3px }
.c-st { margin-top: 5px; font-size: 10.5px }
.c-st.normal { color: #10b981 }
.c-st.warning { color: #ef4444; font-weight: 600 }
.c-st.nodata { color: #94a3b8 }

.charts-row { display: grid; grid-template-columns: 1fr 280px; gap: 10px }
.chart-card { background: var(--card-bg, #fff); border: 1px solid var(--brd, #e2e8f0);
  border-radius: 13px; padding: 12px }
.ch-hd { font-size: 13px; font-weight: 600; margin-bottom: 8px }
.chart { height: 300px }
.chart.mini { height: 252px }

.quality-card { background: var(--card-bg, #fff); border: 1px solid var(--brd, #e2e8f0);
  border-radius: 13px; padding: 12px }
.q-grid { display: flex; gap: 28px; flex-wrap: wrap }
.q-item { display: flex; flex-direction: column; gap: 3px }
.q-k { font-size: 10.5px; color: var(--text-muted) }
.q-v { font-size: 15px; font-weight: 700 }
@media (max-width: 1100px) { .charts-row { grid-template-columns: 1fr } }
</style>
