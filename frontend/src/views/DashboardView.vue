<template>
  <div class="dash-layout">
    <!-- 左：厂区目录树(真实数据,点击进单厂看板) -->
    <div class="dash-side">
      <div class="dash-side-ttl">厂区目录</div>
      <PlantTree @select="goPlant" />
    </div>
    <!-- 右：原有内容 -->
    <div class="dash-main">
      <div class="seg">
        <button :class="{ on: mode === 'plant' }" @click="mode = 'plant'">单厂 · 全指标</button>
        <button :class="{ on: mode === 'overview' }" @click="mode = 'overview'">全厂总览</button>
      </div>
      <template v-if="mode === 'plant'">
        <CockpitFilterBar :last-update="realtime.lastUpdate" />
        <div v-if="groups" class="matrix-wrap">
          <IndicatorMatrix :groups="groups" />
          <AnomalyList :groups="groups" />
        </div>
        <div v-else-if="realtime.loading || isLoadingHistory" class="loading">加载中…</div>
        <div v-else class="error">
          ⚠ 数据加载失败（后端 / InfluxDB 可能未连接）
          <button class="retry-btn" @click="retry">重试</button>
        </div>
      </template>
      <PlantOverviewGrid v-else :plants="plants" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
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
import PlantTree from '@/components/cockpit/PlantTree.vue'
import type { HistoryData, PlantData } from '@/api/types/api.types'

const router = useRouter()
function goPlant(id: string) {
  router.push(`/plants/${encodeURIComponent(id)}`)
}

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

const isLoadingHistory = ref(false)
async function loadHistory() {
  isLoadingHistory.value = true
  try {
    history.value = await monitoringService.history({ time_range: app.dashboardFilters.timeWindow, page_size: 100 })
  } catch {
    history.value = null
  } finally {
    isLoadingHistory.value = false
  }
}
function retry() {
  void realtime.fetchRealtime()
  void loadHistory()
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
.dash-layout { display: flex; gap: 16px; align-items: flex-start }
.dash-side { width: 230px; flex-shrink: 0; background: var(--card-bg, #fff);
  border: 1px solid var(--brd, #e2e8f0); border-radius: 13px; padding: 10px 8px }
.dash-side-ttl { font-size: 11px; color: var(--text-muted, #94a3b8); letter-spacing: .5px;
  padding: 2px 6px 8px }
.dash-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 14px }
.seg { display: inline-flex; background: var(--card-bg); border: 1px solid var(--brd); border-radius: 11px; padding: 4px; margin-bottom: 14px; }
.seg button { background: transparent; border: 0; color: var(--text-secondary); font-size: 13px; padding: 7px 16px; border-radius: 8px; cursor: pointer; font-family: inherit; }
.seg button.on { color: #04121a; background: linear-gradient(135deg, var(--cyan), #5fb9ff); font-weight: 600; }
.matrix-wrap { margin-top: 14px; }
.loading { color: var(--text-muted); font-size: 13px; padding: 20px; }
.error { color: var(--el-color-danger, #f56c6c); font-size: 13px; padding: 20px; display: flex; align-items: center; gap: 12px; }
.retry-btn { padding: 6px 14px; border-radius: 8px; border: 1px solid var(--brd); background: var(--card-bg); color: var(--primary); font-size: 12px; cursor: pointer; font-family: inherit; }
.retry-btn:hover { border-color: var(--primary); }
</style>
