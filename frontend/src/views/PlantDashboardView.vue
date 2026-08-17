<template>
  <div class="pdash">
    <!-- 布局：左目录树 + 右看板 -->
    <div class="side">
      <div class="side-ttl">厂区目录</div>
      <PlantTree :active-id="plantId" @select="goPlant" />
    </div>

    <div class="main" v-if="store.dashboard">
      <div class="head">
        <div>
          <h2>{{ plantId }}</h2>
          <span class="sub">数据窗口 {{ store.dashboard.window_hours }}h ·
            进水 {{ store.dashboard.influent_points }} 点 · 出水 {{ store.dashboard.effluent_points }} 点</span>
        </div>
        <div class="wins">
          <button v-for="w in [24, 72, 168, 10000]" :key="w" :class="{ on: hours === w }" @click="hours = w">{{ w === 10000 ? '全部' : w + 'h' }}</button>
        </div>
      </div>

      <!-- 指标卡片：点击切趋势 -->
      <div class="cards">
        <div v-for="(ind, field) in store.dashboard.indicators" :key="field" class="card"
          :class="[ind.status, { sel: curField === field }]" @click="curField = String(field)">
          <div class="c-hd">{{ ind.label }}<span v-if="ind.unit" class="u">{{ ind.unit }}</span></div>
          <div class="c-vals">
            <div class="v"><span class="k">进水</span>{{ ind.influent ?? '—' }}</div>
            <div class="v"><span class="k">出水</span>{{ ind.effluent ?? '—' }}</div>
          </div>
          <div class="c-st" :class="ind.status">
            {{ ind.status === 'normal' ? '正常' : ind.status === 'warning' ? '⚠ 超限' : '无数据' }}
          </div>
        </div>
      </div>

      <!-- 趋势图 -->
      <div class="chart-card">
        <div class="ch-hd">{{ curLabel }} 趋势 · 进水 vs 出水</div>
        <div ref="chartEl" class="chart" />
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

const route = useRoute()
const router = useRouter()
const store = usePlantsStore()

const plantId = computed(() => decodeURIComponent(String(route.params.plantId || '')))
const hours = ref(10000) // 默认"全部"（现有数据是历史批次，24h 窗口常无数据）
const curField = ref('COD')

const curLabel = computed(() => store.dashboard?.indicators?.[curField.value]?.label || curField.value)

const chartEl = ref<HTMLDivElement>()
let chart: ReturnType<typeof echarts.init> | null = null

function goPlant(id: string) {
  router.push(`/plants/${encodeURIComponent(id)}`)
}

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
        lineStyle: { width: 2 }, itemStyle: { color: '#6366f1' } },
      { name: '出水', type: 'line', smooth: true, symbol: 'none', data: effl,
        lineStyle: { width: 2 }, itemStyle: { color: '#10b981' } },
    ],
  }, true)
}

watch(hours, () => store.fetchDashboard(plantId.value, hours.value))
watch(() => store.dashboard, () => nextTick(renderChart), { deep: true })
watch(curField, renderChart)
watch(plantId, () => store.fetchDashboard(plantId.value, hours.value))

onMounted(async () => {
  if (chartEl.value) chart = echarts.init(chartEl.value)
  await store.fetchTree()
  await store.fetchDashboard(plantId.value, hours.value)
})
onBeforeUnmount(() => { chart?.dispose(); chart = null })
</script>

<style scoped>
.pdash { display: flex; gap: 16px; align-items: flex-start }
.side { width: 240px; flex-shrink: 0; background: var(--card-bg, #fff);
  border: 1px solid var(--brd, #e2e8f0); border-radius: 13px; padding: 10px 8px }
.side-ttl { font-size: 11px; color: var(--text-muted, #94a3b8); letter-spacing: .5px;
  padding: 2px 6px 8px }
.main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 14px }
.main.loading { padding: 60px; text-align: center; color: var(--text-muted) }
.head { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px }
.head h2 { margin: 0; font-size: 18px }
.sub { font-size: 12px; color: var(--text-muted) }
.wins { display: flex; gap: 6px }
.wins button { background: #fff; border: 1px solid var(--brd, #e2e8f0); border-radius: 7px;
  padding: 5px 12px; cursor: pointer; font-size: 12px; color: var(--text-secondary, #475569) }
.wins button.on { border-color: var(--primary, #4f46e5); color: var(--primary, #4f46e5); font-weight: 600 }
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px }
.card { background: var(--card-bg, #fff); border: 1px solid var(--brd, #e2e8f0);
  border-radius: 12px; padding: 12px 14px; cursor: pointer; transition: border-color .15s }
.card:hover { border-color: var(--primary, #4f46e5) }
.card.sel { border-color: var(--primary, #4f46e5); box-shadow: 0 0 0 1px var(--primary, #4f46e5) inset }
.card.warning { border-color: #fca5a5; background: rgba(239, 68, 68, .04) }
.c-hd { font-size: 13px; font-weight: 600; margin-bottom: 8px }
.c-hd .u { font-weight: 400; font-size: 11px; color: var(--text-muted); margin-left: 4px }
.c-vals { display: flex; gap: 14px }
.v { font-size: 17px; font-weight: 700 }
.v .k { font-size: 10.5px; font-weight: 400; color: var(--text-muted); margin-right: 4px }
.c-st { margin-top: 7px; font-size: 11px }
.c-st.normal { color: #10b981 }
.c-st.warning { color: #ef4444; font-weight: 600 }
.c-st.nodata { color: #94a3b8 }
.chart-card { background: var(--card-bg, #fff); border: 1px solid var(--brd, #e2e8f0);
  border-radius: 13px; padding: 12px }
.ch-hd { font-size: 13px; font-weight: 600; margin-bottom: 8px }
.chart { height: 320px }
</style>
