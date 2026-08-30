<template>
  <div class="metrics">
    <!-- 筛选条 -->
    <div class="bar">
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
        </span>
      </div>
    </div>

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
        <span class="cs">{{ customRange.start ? `自定义 ${customRange.start} ~ ${customRange.end || '今'}` : `${records.length} 个采样点` }}</span>
      </div>
      <div class="chart-wrap">
        <div ref="chartEl" class="chart"></div>
        <div v-if="loading" class="loading">加载中…</div>
        <div v-else-if="!records.length" class="loading">该时间窗口无数据</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import echarts from '@/lib/echarts'
import { monitoringService } from '@/api/modules/monitoring'
import { plantsService } from '@/api/modules/plants'
import { useActionStore } from '@/stores/action'
import type { HistoryRecord } from '@/api/types/api.types'

const actionStore = useActionStore()

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
const records = ref<HistoryRecord[]>([])
const loading = ref(false)

// 自定义日期范围(长时段查询;归本页,大屏流式看板保持固定滑窗)
const customRange = ref<{ start: string; end: string }>({ start: '', end: '' })
function pickWindow(v: '1h' | '6h' | '24h') {
  customRange.value = { start: '', end: '' }
  timeWindow.value = v
}
function clearRange() {
  customRange.value = { start: '', end: '' }
  void load()
}
async function loadCustom() {
  const { start, end } = customRange.value
  if (!start) return
  // 复用 dashboard 段查询:起止日期(堆叠全量展示,自适应点距)
  try {
    const r = await plantsService.dashboard(PLANT, 24, start)
    const d = r.data
    // dashboard anchor 模式=该日起7天;不足/超出由 end 截断
    const inRange = (t: string) => (!end || t.slice(0, 10) <= end)
    const rs: HistoryRecord[] = (d.indicators?.pH?.series?.effluent ?? [])
      .filter((p) => inRange(p.time))
      .map((p) => ({ timestamp: p.time.replace(' ', 'T'),
        influent: {}, effluent: {} } as unknown as HistoryRecord))
    // 把全部指标塞进对应时间戳
    for (const [field, ind] of Object.entries(d.indicators ?? {})) {
      const key = field === 'suspended_solids' ? 'SS' : field
      for (const side of ['influent', 'effluent'] as const) {
        for (const p of ind.series[side]) {
          if (!inRange(p.time)) continue
          const rec = rs.find((x) => x.timestamp === p.time.replace(' ', 'T'))
          if (rec) (rec[side] as any)[key] = p.value
        }
      }
    }
    records.value = rs
  } catch { records.value = [] }
  await nextTick()
  renderChart()
}
const PLANT = '当阳市金桥污水处理厂一期'

const curMeta = computed(() => INDICATORS.find((i) => i.key === indicator.value)!)
const curUnit = computed(() => curMeta.value.unit)

const cur = computed(() => {
  const last = records.value[records.value.length - 1]
  if (!last) return null
  return {
    influent: last.influent?.[indicator.value] ?? null,
    effluent: last.effluent?.[indicator.value] ?? null,
  }
})
const stat = computed(() => stats(indicator.value))

function stats(key: IndKey) {
  const calc = (side: 'influent' | 'effluent') => {
    const vs = records.value.map((r) => r[side]?.[key]).filter((v): v is number => typeof v === 'number')
    if (!vs.length) return { mean: null, min: null, max: null } as const
    const mean = vs.reduce((a, b) => a + b, 0) / vs.length
    return { mean, min: Math.min(...vs), max: Math.max(...vs) } as const
  }
  return { influent: calc('influent'), effluent: calc('effluent') }
}
function fmt(v: number | null | undefined) { return v == null ? '—' : v.toFixed(2) }

const chartEl = ref<HTMLDivElement>()
let chart: ReturnType<typeof echarts.init> | null = null

function renderChart() {
  if (!chart || !records.value.length) return
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
  loading.value = true
  try {
    const r = await monitoringService.history({ time_range: timeWindow.value, page_size: 500 })
    records.value = r.records
  } catch { records.value = [] }
  finally { loading.value = false }
  await nextTick()
  renderChart()
}

watch(indicator, renderChart)
watch(timeWindow, load)

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
  if (v === '1h' || v === '6h' || v === '24h') timeWindow.value = v
  else console.info('[MetricsView] 时间范围', v, '超出本视图窗口(1h/6h/24h)，忽略')
})

// 算法标注：run_detector 结果 → 曲线上 markPoint 高亮异常点
watch(() => actionStore.annotations, () => renderChart(), { deep: true })

onMounted(async () => {
  if (chartEl.value) chart = echarts.init(chartEl.value)
  await load()
})
onBeforeUnmount(() => { chart?.dispose(); chart = null })
</script>

<style scoped>
.metrics { display: flex; flex-direction: column; gap: 14px; max-width: 1100px }
.bar { display: flex; flex-wrap: wrap; gap: 18px; align-items: center; background: var(--card-bg);
  border: 1px solid var(--brd); border-radius: 13px; padding: 11px 14px }
.grp { display: flex; align-items: center; gap: 7px; flex-wrap: wrap }
.lbl { font-size: 11px; color: var(--text-muted); letter-spacing: .5px }
.range-box { display: inline-flex; align-items: center; gap: 6px; padding: 3px 8px;
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
