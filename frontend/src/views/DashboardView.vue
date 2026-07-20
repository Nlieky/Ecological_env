<template>
  <div>
    <div class="top-row">
      <div class="seg">
        <button :class="{ on: mode === 'plant' }" @click="mode = 'plant'">单厂 · 全指标</button>
        <button :class="{ on: mode === 'overview' }" @click="mode = 'overview'">全厂总览</button>
      </div>
      <button v-if="!app.fullscreen" class="fs-btn" @click="app.setFullscreen(true)">⛶ 全屏大屏</button>
    </div>
    <template v-if="mode === 'plant'">
      <CockpitFilterBar :last-update="realtime.lastUpdate" />
      <div v-if="groups" class="matrix-wrap">
        <IndicatorMatrix :groups="groups" />
        <AnomalyList :groups="groups" />
      </div>
      <div v-else class="loading">加载中…</div>
    </template>
    <PlantOverviewGrid v-else :plants="plants" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRealtimeStore } from '@/stores/realtime'
import { useAppStore } from '@/stores/app'
import { monitoringService } from '@/api/modules/monitoring'
import { plantsService } from '@/api/modules/plants'
import { buildIndicatorCells, type IndicatorGroups } from '@/composables/useIndicatorMatrix'
import { usePolling } from '@/composables/usePolling'
import CockpitFilterBar from '@/components/cockpit/CockpitFilterBar.vue'
import IndicatorMatrix from '@/components/cockpit/IndicatorMatrix.vue'
import AnomalyList from '@/components/cockpit/AnomalyList.vue'
import PlantOverviewGrid from '@/components/cockpit/PlantOverviewGrid.vue'
import type { HistoryData, PlantData } from '@/api/types/api.types'

const realtime = useRealtimeStore()
const app = useAppStore()
const mode = ref<'plant' | 'overview'>('plant')
const history = ref<HistoryData | null>(null)
const plants = ref<PlantData[]>([])
// 统一单壳后，CockpitShell 不再挂载；大屏自行轮询实时数据（默认 30s）
const { start: startPolling, stop: stopPolling } = usePolling(() => realtime.fetchRealtime(), 30000)

const groups = computed<IndicatorGroups | null>(() =>
  realtime.realtime && history.value ? buildIndicatorCells(realtime.realtime, history.value) : null,
)

async function loadHistory() {
  try {
    history.value = await monitoringService.history({ time_range: app.dashboardFilters.timeWindow, page_size: 100 })
  } catch {
    history.value = null
  }
}
async function loadPlants() {
  try { plants.value = await plantsService.list() } catch { plants.value = [] }
}

onMounted(() => {
  void realtime.fetchRealtime()
  void loadHistory()
  void loadPlants()
  startPolling()
})
onBeforeUnmount(() => stopPolling())
watch(() => app.dashboardFilters.timeWindow, () => void loadHistory())
</script>

<style scoped>
.top-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; gap: 12px; }
.seg { display: inline-flex; background: var(--card-bg); border: 1px solid var(--brd); border-radius: 11px; padding: 4px; }
.seg button { background: transparent; border: 0; color: var(--text-secondary); font-size: 13px; padding: 7px 16px; border-radius: 8px; cursor: pointer; font-family: inherit; }
.seg button.on { color: #04121a; background: linear-gradient(135deg, var(--cyan), #5fb9ff); font-weight: 600; }
.fs-btn { flex-shrink: 0; background: var(--card-bg); border: 1px solid var(--brd); color: var(--text-secondary);
  font-size: 12.5px; padding: 8px 14px; border-radius: 9px; cursor: pointer; font-family: inherit; transition: all .15s }
.fs-btn:hover { color: var(--primary); border-color: var(--primary) }
.matrix-wrap { margin-top: 14px; }
.loading { color: var(--text-muted); font-size: 13px; padding: 20px; }
</style>
