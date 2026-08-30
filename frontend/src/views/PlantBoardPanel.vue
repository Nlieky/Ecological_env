<template>
  <div class="board" v-if="store.dashboard">
    <!-- 顶部：厂名 + 窗口 + 刷新状态 -->
    <div class="head">
      <div>
        <h2>{{ plantId }}</h2>
        <span class="sub">
          <span class="live-dot" :class="{ on: replaying || !store.dashboardLoading }" />
          <template v-if="replaying">
            <b>流式输出</b> · {{ simTime }}
            <span class="mono">({{ Math.min(cursor, WINDOW_PTS) }}/{{ WINDOW_PTS }} 窗口 · 第 {{ cursor }}/{{ totalPts }} 点)</span>
            <template v-if="anchorDate"> · 段 {{ anchorDate }} 起</template>
            <span v-if="lastJump" class="jump">· ⤴ 已跳转至异常 {{ lastJump.slice(5, 16) }}</span>
          </template>
          <template v-else>
            {{ store.dashboardLoading ? '刷新中…' : '实时监测中' }} ·
            数据截至 {{ store.dashboard.latest_time || '—' }} ·
            进水 {{ store.dashboard.influent_points }} 点 · 出水 {{ store.dashboard.effluent_points }} 点
          </template>
        </span>
      </div>
      <div class="wins">
        <!-- 任意时间点开播:选日期 → 该日 00:00 起流式播放,播完自动续下一段 -->
        <span class="date-pick">
          <span class="dp-lbl">开播</span>
          <input type="date" v-model="anchorDate" :min="DATA_MIN" :max="DATA_MAX" @change="onAnchorPick" />
        </span>
        <button v-if="anchorDate" class="live-btn" @click="backToLive">● 实时</button>
        <button v-for="w in WINDOWS" :key="w.v" :class="{ on: hours === w.v && !anchorDate }" @click="setWindow(w.v)">{{ w.t }}</button>
        <!-- 流式回放控制 -->
        <button v-if="!replaying" class="replay" @click="startReplay()">▶ 流式回放</button>
        <template v-else>
          <span class="speeds">
            <button v-for="(s, i) in SPEEDS" :key="s.t" :class="{ on: speedIdx === i }" @click="setSpeed(i)">{{ s.t }}</button>
          </span>
          <button class="replay stop" @click="stopReplay()">⏹ 停止</button>
        </template>
      </div>
    </div>

    <!-- 全指标一页（Grafana 式）：每个指标一格，进水vs出水双曲线，同屏联动推进 -->
    <!-- visibleFields: AI set_view 指令可过滤只看指定指标面板 -->
    <div class="grid" :class="{ filtered: visibleFields.length < FIELDS.length }">
      <div v-for="field in visibleFields" :key="field" class="panel"
        :class="{ warn: panelStatus(field) === 'warning', marked: hasAnnotations(field) }">
        <div class="p-hd">
          <div class="p-title">
            <span class="p-name">{{ store.dashboard.indicators[field].label }}<span v-if="store.dashboard.indicators[field].unit" class="u">（{{ store.dashboard.indicators[field].unit }}）</span></span>
            <span class="pill st" :class="panelStatus(field)">{{ statusText(panelStatus(field)) }}</span>
            <span v-if="hasAnnotations(field)" class="pill ai">AI 标注 {{ annCount(field) }}</span>
          </div>
          <!-- stat 大字:出水当前值为面板主数值,超限红/正常绿;进水为次级(该厂无进水数据则隐藏) -->
          <div class="p-stats">
            <div v-if="sideFilter !== 'effluent' && hasSide(field, 'influent')" class="stat sub">
              <span class="s-k">进水</span>
              <span class="s-v">{{ cardVal(field, 'influent') ?? '—' }}</span>
            </div>
            <div v-if="sideFilter !== 'influent'" class="stat main" :class="panelStatus(field)">
              <span class="s-k">出水</span>
              <span class="s-v">{{ cardVal(field, 'effluent') ?? '—' }}</span>
              <span v-if="limitText(field)" class="s-lim">{{ limitText(field) }}</span>
            </div>
          </div>
        </div>
        <div :ref="(el) => setChartRef(field, el)" class="p-chart" />
      </div>
    </div>

    <!-- 底部：数据质量 -->
    <div class="quality-card">
      <div class="ch-hd">数据质量</div>
      <div class="q-grid">
        <div class="q-item"><span class="q-k">{{ anchorDate ? '播放段' : '数据窗口' }}</span><span class="q-v">{{ anchorDate ? `${store.dashboard.segment_start || anchorDate} ~ ${store.dashboard.segment_end || '—'}` : (store.dashboard.window_hours >= 10000 ? '全部' : store.dashboard.window_hours + 'h') }}</span></div>
        <div class="q-item"><span class="q-k">进水点数</span><span class="q-v">{{ store.dashboard.influent_points }}</span></div>
        <div class="q-item"><span class="q-k">出水点数</span><span class="q-v">{{ store.dashboard.effluent_points }}</span></div>
        <div class="q-item"><span class="q-k">最后刷新</span><span class="q-v">{{ lastRefresh }}</span></div>
      </div>
    </div>
  </div>

  <div v-else class="board loading">
    {{ store.dashboardLoading ? '加载看板数据…' : '该厂暂无数据' }}
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import echarts from '@/lib/echarts'
import { usePlantsStore } from '@/stores/plants'
import { useActionStore } from '@/stores/action'
import { usePolling } from '@/composables/usePolling'

const props = defineProps<{ plantId: string }>()
const store = usePlantsStore()
const actionStore = useActionStore()

const WINDOWS = [
  { t: '24h', v: 24 }, { t: '72h', v: 72 }, { t: '168h', v: 168 }, { t: '全部', v: 10000 },
] as const

const hours = ref(24)
const lastRefresh = ref('')
const lastJump = ref('')   // 标注跳转提示(异常点在视野外时自动跳转后显示)

// ── 任意时间点开播(锚点日期模式) ─────────────────────────────
// 选日期后 fetchDashboard 带 anchor=该日,取[该日00:00起7天]一段;
// 回放播完该段 → 自动加载下一段(锚点+7天)继续播,永续直到"回到实时"。
const anchorDate = ref('')          // '' = 实时模式(锚定最新点)
const DATA_MIN = '2026-01-01'
const DATA_MAX = '2026-12-31'
const SEG_DAYS = 7

/** 下一段锚点 = 当前段锚点 + 7 天;超出数据末尾返回 ''(停播回实时) */
function nextSegmentAnchor(): string {
  const a = new Date(anchorDate.value + 'T00:00:00')
  a.setDate(a.getDate() + SEG_DAYS)
  const ymd = a.toISOString().slice(0, 10)
  // 数据末尾判断:segment_end 接近 latest_time 就没有下一段了
  const seg = store.dashboard?.segment_end || ''
  const latest = store.dashboard?.latest_time || ''
  if (seg && latest && seg.slice(0, 10) >= latest.slice(0, 10)) return ''
  return ymd
}

async function onAnchorPick() {
  if (!anchorDate.value) { backToLive(); return }
  await store.fetchDashboard(props.plantId, hours.value, anchorDate.value)
  startReplay()
}
function setWindow(v: number) {
  hours.value = v
  anchorDate.value = ''   // 选时间窗 = 回实时模式
  void store.fetchDashboard(props.plantId, hours.value)
}
function backToLive() {
  anchorDate.value = ''
  void store.fetchDashboard(props.plantId, hours.value).then(() => {
    // 实时模式不自动回放,显示最新窗口全量
    stopReplay()
  })
}

// ══ 全指标图表网格 ════════════════════════════════════════════════
const chartRefs = new Map<string, HTMLDivElement>()
const charts = new Map<string, ReturnType<typeof echarts.init>>()

function setChartRef(field: string, el: unknown) {
  if (el) chartRefs.set(field, el as HTMLDivElement)
}

function ensureCharts() {
  for (const [field, el] of chartRefs) {
    if (!charts.has(field) && el) charts.set(field, echarts.init(el))
  }
}

const FIELDS = computed(() => Object.keys(store.dashboard?.indicators ?? {}))

// ══ 流式回放（固定窗口滑动,仿 Grafana）════════════════════════════
// 窗口长度固定(WINDOW_PTS),曲线到达右端后旧点从左侧流走,不无限堆叠——
// 真流式输出的视觉;长时段堆叠查询归 /metrics 指标查询页。
const replaying = ref(false)
const cursor = ref(0)
const SPEEDS = [{ t: '×0.5', ms: 1600 }, { t: '×1', ms: 800 }, { t: '×2', ms: 400 }, { t: '×4', ms: 200 }] as const
const speedIdx = ref(0)
const WINDOW_PTS = 24   // 固定窗口=24个点(约一天),左右恒定,数据流过
let replayTimer: ReturnType<typeof setInterval> | null = null

const totalPts = computed(() => {
  let n = 0
  for (const f of FIELDS.value) {
    const ind = store.dashboard?.indicators?.[f]
    if (!ind) continue
    n = Math.max(n, ind.series.effluent.length, ind.series.influent.length)
  }
  return n
})

const simTime = computed(() => {
  if (!replaying.value) return ''
  for (const f of FIELDS.value) {
    const ind = store.dashboard?.indicators?.[f]
    if (!ind) continue
    const s = ind.series.effluent.length ? ind.series.effluent : ind.series.influent
    const i = Math.min(cursor.value, s.length) - 1
    if (i >= 0) return s[i].time
  }
  return ''
})

function clearReplayTimer() {
  if (replayTimer) { clearInterval(replayTimer); replayTimer = null }
}

function startReplay(fromCurrent = false) {
  clearReplayTimer()
  replaying.value = true
  if (!fromCurrent) cursor.value = 0
  replayTimer = setInterval(async () => {
    if (cursor.value < totalPts.value) { cursor.value++; renderAll() }
    else if (anchorDate.value) {
      // 锚点模式播完本段:自动加载下一段继续播(永续)
      const next = nextSegmentAnchor()
      if (next) {
        anchorDate.value = next
        cursor.value = 0
        await store.fetchDashboard(props.plantId, hours.value, next)
        // startReplay 不重置 cursor,继续跑(此时 cursor 已是 0)
      } else {
        backToLive()  // 到数据末尾了,回实时
      }
    }
    else stopReplay()  // 实时窗口模式:播完即停
  }, SPEEDS[speedIdx.value].ms)
  renderAll()
}

function stopReplay() {
  clearReplayTimer()
  replaying.value = false
  renderAll()
}

function setSpeed(i: number) {
  if (speedIdx.value === i) return
  speedIdx.value = i
  if (replaying.value) startReplay(true)
}

// 回放时面板头部数值 = 模拟时间点的瞬时值
function cardVal(field: string, side: 'influent' | 'effluent'): number | null {
  const ind = store.dashboard?.indicators?.[field]
  if (!ind) return null
  if (!replaying.value) return ind[side]
  const s = ind.series[side]
  const i = Math.min(cursor.value, s.length) - 1
  return i >= 0 ? (s[i]?.value ?? null) : null
}
function panelStatus(field: string): 'normal' | 'warning' | 'nodata' {
  const ind = store.dashboard?.indicators?.[field]
  if (!ind) return 'nodata'
  if (!replaying.value) return ind.status
  const eff = cardVal(field, 'effluent')
  if (eff == null) return 'nodata'
  const lim = ind.limit as number | [number, number] | null | undefined
  if (lim == null) return 'normal'
  const lo = Array.isArray(lim) ? lim[0] : null
  const hi = Array.isArray(lim) ? lim[1] : lim
  return (lo != null && eff < lo) || (hi != null && eff > hi) ? 'warning' : 'normal'
}
function statusText(s: string) {
  return s === 'normal' ? '正常' : s === 'warning' ? '⚠ 超限' : '无数据'
}
/** 限值说明文字,如 "≤100" / "6~9" */
function limitText(field: string): string {
  const ind = store.dashboard?.indicators?.[field]
  const lim = ind?.limit as number | [number, number] | null | undefined
  if (lim == null) return ''
  if (Array.isArray(lim)) return `${lim[0]}~${lim[1]}`
  return `≤${lim}`
}
/** 出水阈值着色:超限区 markArea 红色半透明带 + 曲线本身按当前状态着色 */
function thresholdAreas(field: string): any[] | undefined {
  const ind = store.dashboard?.indicators?.[field]
  const lim = ind?.limit as number | [number, number] | null | undefined
  if (lim == null) return undefined
  // markArea 在 y 轴上画超限带(视觉:越过这条带=超标)
  const data: any[] = []
  if (Array.isArray(lim)) {
    data.push([{ yAxis: lim[1], itemStyle: { color: 'rgba(239,68,68,.06)' } }, { yAxis: 'max' }])
    data.push([{ yAxis: 'min' }, { yAxis: lim[0], itemStyle: { color: 'rgba(239,68,68,.06)' } }])
  } else {
    data.push([{ yAxis: lim, itemStyle: { color: 'rgba(239,68,68,.06)' } }, { yAxis: 'max' }])
  }
  return data
}

// ── 真实数据轮询（10s;锚点播放模式下暂停,避免把段数据覆盖回实时） ──
const POLL_MS = 10_000
const { start: startPoll, stop: stopPoll } = usePolling(
  async () => {
    if (anchorDate.value) return  // 播放历史段时不轮询
    await store.fetchDashboard(props.plantId, hours.value)
    lastRefresh.value = new Date().toLocaleTimeString()
  },
  POLL_MS,
)

/** 该厂该指标是否有某侧数据(洗舱站无进水→隐藏进水线/stat,多厂通用) */
function hasSide(field: string, side: 'influent' | 'effluent'): boolean {
  const ind = store.dashboard?.indicators?.[field]
  return !!ind && (ind.series?.[side]?.length ?? 0) > 0
}

// ── AI 动作标注:按指标取本面板的异常点(markPoint 红点) ──
function hasAnnotations(field: string): boolean {
  if (!actionStore.annotations.length) return false
  return !actionStore.annotationIndicator || actionStore.annotationIndicator === field
}
function annCount(field: string): number {
  if (!hasAnnotations(field)) return 0
  return actionStore.annotations.length
}
function markPointsFor(field: string, effl: { time: string; value: number }[], infl: { time: string; value: number }[]) {
  if (!actionStore.annotations.length) return undefined
  if (actionStore.annotationIndicator && actionStore.annotationIndicator !== field) return undefined
  const xs = (effl.length ? effl : infl).map((p) => p.time.slice(5))
  const idxByTime = new Map(xs.map((t, i) => [t, i]))
  const pts = actionStore.annotations
    .map((a) => ({ idx: idxByTime.get(a.timestamp.slice(5)), a }))
    .filter(({ idx }) => idx !== undefined)
    .map(({ idx, a }) => ({ coord: [idx, a.value], value: a.type, itemStyle: { color: '#ef4444' } }))
  if (!pts.length) return undefined
  return {
    symbol: 'circle', symbolSize: 7,
    itemStyle: { color: '#ef4444', borderColor: '#fff', borderWidth: 1 },
    label: { show: false },
    data: pts,
  } as any
}

// ── 渲染：每个指标一格进/出双线 ──
function renderAll() {
  const inds = store.dashboard?.indicators
  if (!inds) return
  for (const field of FIELDS.value) {
    const ch = charts.get(field)
    const ind = inds[field]
    if (!ch || !ind) continue
    let infl = ind.series.influent
    let effl = ind.series.effluent
    if (replaying.value) {
      // 固定滑窗:已播的 WINDOW_PTS 个点;超出窗口左端的流走(不堆叠)
      infl = infl.slice(Math.max(0, cursor.value - WINDOW_PTS), cursor.value)
      effl = effl.slice(Math.max(0, cursor.value - WINDOW_PTS), cursor.value)
    }
    const xs = (effl.length ? effl : infl).map((p) => p.time.slice(5))
    // 限值参考线
    const lim = ind.limit as number | [number, number] | null | undefined
    const markLine: any = { silent: true, symbol: 'none', data: [] as any[], lineStyle: { color: '#f59e0b', type: 'dashed', opacity: .7 }, label: { fontSize: 9, formatter: '{b}: {c}' } }
    if (typeof lim === 'number') markLine.data.push({ yAxis: lim, name: '限值' })
    else if (Array.isArray(lim)) {
      if (lim[0] != null) markLine.data.push({ yAxis: lim[0], name: '下限' })
      if (lim[1] != null) markLine.data.push({ yAxis: lim[1], name: '上限' })
    }
    const mp = markPointsFor(field, effl, infl)
    const showIn = sideFilter.value !== 'effluent' && infl.length > 0   // 无进水数据的厂不画进水线
    const showOut = sideFilter.value !== 'influent' && effl.length > 0
    const overLimit = panelStatus(field) === 'warning'
    const outColor = overLimit ? '#ef4444' : '#10b981'
    const areas = thresholdAreas(field)
    const series: any[] = []
    if (showIn) series.push(
      { name: '进水', type: 'line', smooth: true, symbol: 'none',
        data: infl.map((p) => p.value), lineStyle: { width: 1.6 }, itemStyle: { color: '#6366f1' },
        areaStyle: { color: 'rgba(99,102,241,.05)' } })
    if (showOut) series.push(
      { name: '出水', type: 'line', smooth: true, symbol: 'none',
        data: effl.map((p) => p.value), lineStyle: { width: 1.8 },
        itemStyle: { color: outColor },
        areaStyle: { color: overLimit ? 'rgba(239,68,68,.07)' : 'rgba(16,185,129,.05)' },
        markLine: markLine.data.length ? markLine : undefined,
        markArea: areas ? { silent: true, data: areas } : undefined,
        markPoint: mp })
    ch.setOption({
      animation: true, animationDurationUpdate: 260, animationEasingUpdate: 'linear',
      tooltip: { trigger: 'axis', textStyle: { fontSize: 11 } },
      legend: { show: false },
      grid: { left: 46, right: 10, top: 8, bottom: 20 },
      xAxis: { type: 'category', data: xs, axisLabel: { fontSize: 9, formatter: (v: string) => v.slice(5) } },
      yAxis: { type: 'value', scale: true, axisLabel: { fontSize: 9 },
        splitLine: { lineStyle: { color: 'rgba(148,163,184,.15)' } } },
      series,
    }, true)
  }
}

watch(() => store.dashboard, (d) => {
  // 上报观看窗口上下文:AI 检测动作按"正在看的时段"取数
  if (d) actionStore.setViewContext({
    plant: props.plantId,
    anchor: anchorDate.value || undefined,
    segmentStart: d.segment_start,
    segmentEnd: d.segment_end,
  })
  nextTick(() => {
    ensureCharts()   // 数据到达后 DOM 才在,init 在这兜底(修过 v-if 时序坑)
    renderAll()
  })
}, { deep: true })

// AI 动作:新标注到达 → 重画(红点);异常点不在当前滑窗内 → 自动跳转游标保证可见
watch(() => actionStore.annotationSeq, () => {
  ensureAnnotationVisible()
  renderAll()
})

/** 标注落地保证可见:回放中若首个异常点在滑窗外(更早),把游标跳到它后面一点。
 *  数据流快、检测有延迟,异常点常已流出视野——不跳转用户根本看不到红点。 */
function ensureAnnotationVisible() {
  const anns = actionStore.annotations
  if (!anns.length || !replaying.value) return
  const ind = store.dashboard?.indicators?.[actionStore.annotationIndicator || '']
  if (!ind) return
  const s = ind.series.effluent.length ? ind.series.effluent : ind.series.influent
  const firstTs = anns.map((a) => a.timestamp).sort()[0]
  // 找首个异常点在序列里的下标
  const idx = s.findIndex((p) => p.time === firstTs)
  if (idx < 0) return                      // 不在本段数据里,无从跳转
  const windowStart = cursor.value - WINDOW_PTS
  if (idx >= windowStart && idx < cursor.value) return  // 已在窗内
  // 跳转:游标 = 异常点下标 + 半窗,让红点落在窗口中部
  cursor.value = Math.min(idx + Math.floor(WINDOW_PTS / 2), totalPts.value)
  lastJump.value = firstTs
}
const visibleFields = computed(() => {
  const all = FIELDS.value
  const want = actionStore.indicators?.map((n) => actionStore.normalizeIndicator(n)) ?? null
  if (!want) return all
  const filtered = all.filter((f) => want.includes(f))
  return filtered.length ? filtered : all
})
// AI set_side 过滤(side=influent 只看进水线)
const sideFilter = computed(() => actionStore.side)

// 切时间窗 / 切厂：拉新数据后从头回放
watch(hours, async () => { await store.fetchDashboard(props.plantId, hours.value); startReplay() })
watch(() => props.plantId, async () => {
  hours.value = 24
  anchorDate.value = ''   // 切厂回实时模式
  stopReplay()
  await store.fetchDashboard(props.plantId, hours.value)
  startReplay()
})

function resize() { charts.forEach((c) => c.resize()) }

onMounted(async () => {
  window.addEventListener('resize', resize)
  await store.fetchDashboard(props.plantId, hours.value)
  startPoll()
  startReplay()
})
onBeforeUnmount(() => {
  clearReplayTimer()
  stopPoll()
  window.removeEventListener('resize', resize)
  charts.forEach((c) => c.dispose())
  charts.clear(); chartRefs.clear()
})
</script>

<style scoped>
.board { display: flex; flex-direction: column; gap: 14px }
.board.loading { padding: 60px; text-align: center; color: var(--text-muted) }

.head { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px }
.head h2 { margin: 0; font-size: 18px }
.sub { font-size: 12px; color: var(--text-muted); display: inline-flex; align-items: center; gap: 5px; flex-wrap: wrap }
.sub b { color: var(--primary, #4f46e5) }
.sub .mono { font-variant-numeric: tabular-nums; opacity: .85 }
.sub .jump { color: #ef4444; font-weight: 600 }
.live-dot { width: 8px; height: 8px; border-radius: 50%; background: #cbd5e1 }
.live-dot.on { background: #10b981; animation: pulse 2s infinite }
@keyframes pulse { 0%,100% { box-shadow: 0 0 0 0 rgba(16,185,129,.4) } 50% { box-shadow: 0 0 0 5px rgba(16,185,129,0) } }
.wins { display: flex; gap: 6px; align-items: center }
.date-pick { display: inline-flex; align-items: center; gap: 5px; border: 1px solid var(--brd, #e2e8f0);
  border-radius: 7px; padding: 3px 8px; background: #fff }
.dp-lbl { font-size: 11px; color: var(--text-muted, #94a3b8) }
.date-pick input { border: 0; outline: none; font-size: 12px; color: var(--text-primary, #0f172a);
  font-family: inherit; cursor: pointer; background: transparent }
.live-btn { background: rgba(16,185,129,.08)!important; border-color: rgba(16,185,129,.45)!important;
  color: #059669!important; font-weight: 700 }
.wins button { background: #fff; border: 1px solid var(--brd, #e2e8f0); border-radius: 7px;
  padding: 5px 12px; cursor: pointer; font-size: 12px; color: var(--text-secondary, #475569) }
.wins button.on { border-color: var(--primary, #4f46e5); color: var(--primary, #4f46e5); font-weight: 600 }
.wins button.replay { border-color: var(--primary, #4f46e5); color: var(--primary, #4f46e5); font-weight: 700 }
.wins button.replay.stop { border-style: dashed; color: #ef4444; border-color: #fca5a5 }
.speeds { display: inline-flex; border: 1px solid var(--brd, #e2e8f0); border-radius: 7px; overflow: hidden }
.speeds button { border: 0; border-radius: 0; padding: 5px 9px; background: #fff }
.speeds button.on { background: var(--primary, #4f46e5); color: #fff }

/* Grafana 式网格:2列(宽屏3列),每格一个指标 */
.grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px }
@media (min-width: 1500px) { .grid { grid-template-columns: repeat(3, 1fr) } }
.panel { background: var(--card-bg, #fff); border: 1px solid var(--brd, #e2e8f0);
  border-radius: 13px; padding: 12px 14px 10px; transition: box-shadow .15s }
.panel:hover { box-shadow: 0 2px 10px rgba(15,23,42,.05) }
.panel.warn { border-color: #fca5a5; background: rgba(239, 68, 68, .025) }
.panel.marked { border-color: #ef4444; box-shadow: 0 0 0 1px rgba(239,68,68,.35), 0 0 18px rgba(239,68,68,.12) }
.grid.filtered .panel { min-width: 0 }

.p-hd { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; margin-bottom: 6px }
.p-title { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; padding-top: 2px }
.p-name { font-size: 13.5px; font-weight: 700; color: var(--text-primary, #0f172a) }
.p-name .u { font-weight: 400; font-size: 10.5px; color: var(--text-muted, #94a3b8) }

/* stat 区:出水主数值大字 + 进水次级,带状态色 */
.p-stats { display: flex; gap: 14px; align-items: baseline }
.stat { display: flex; align-items: baseline; gap: 5px }
.stat .s-k { font-size: 10px; color: var(--text-muted, #94a3b8); font-weight: 500 }
.stat .s-v { font-variant-numeric: tabular-nums; font-weight: 800; line-height: 1 }
.stat.main .s-v { font-size: 24px; color: #10b981 }
.stat.main.warning .s-v { color: #ef4444 }
.stat.main.nodata .s-v { color: #94a3b8; font-size: 18px }
.stat.main .s-lim { font-size: 9.5px; color: #f59e0b; background: rgba(245,158,11,.09);
  border: 1px solid rgba(245,158,11,.3); border-radius: 5px; padding: 0 5px; font-weight: 600 }
.stat.sub .s-v { font-size: 14px; color: #6366f1; font-weight: 700 }
.stat.sub .s-k { font-size: 9.5px }

.pill { font-size: 10.5px; padding: 1px 7px; border-radius: 6px; border: 1px solid var(--brd, #e2e8f0);
  color: var(--text-secondary); font-variant-numeric: tabular-nums }
.pill.st { color: #10b981; border-color: rgba(16,185,129,.3) }
.pill.st.warning { color: #ef4444; border-color: rgba(239,68,68,.4); background: rgba(239,68,68,.07); font-weight: 700 }
.pill.st.nodata { color: #94a3b8 }
.pill.ai { color: #ef4444; border-color: rgba(239,68,68,.45); background: rgba(239,68,68,.08); font-weight: 700 }
.p-chart { height: 148px }

.quality-card { background: var(--card-bg, #fff); border: 1px solid var(--brd, #e2e8f0);
  border-radius: 13px; padding: 12px }
.ch-hd { font-size: 13px; font-weight: 600; margin-bottom: 8px }
.q-grid { display: flex; gap: 28px; flex-wrap: wrap }
.q-item { display: flex; flex-direction: column; gap: 3px }
.q-k { font-size: 10.5px; color: var(--text-muted) }
.q-v { font-size: 15px; font-weight: 700 }
</style>
