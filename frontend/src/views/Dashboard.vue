<template>
  <div class="dashboard">
    <!-- Hero Section -->
    <section class="hero panel">
      <div>
        <p class="eyebrow">Monitoring Dashboard</p>
        <h2>废水监测大屏</h2>
        <p class="subtitle">4×4 厂区框架 · 实时水质数据 · 异常告警</p>
      </div>
      <div class="hero-actions">
        <el-tag type="success" v-if="onlineCount > 0">
          {{ onlineCount }} 个在线
        </el-tag>
        <el-tag type="info">{{ lastUpdate }}</el-tag>
        <el-button @click="loadPlants" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </section>

    <!-- Stats Grid -->
    <section class="stats-grid">
      <div class="stat-card warm">
        <span>在线厂区</span>
        <strong>{{ onlineCount }} / 16</strong>
      </div>
      <div class="stat-card cool">
        <span>异常指标</span>
        <strong>{{ abnormalCount }}</strong>
      </div>
      <div class="stat-card accent">
        <span>平均 pH</span>
        <strong>{{ averagePh }}</strong>
      </div>
      <div class="stat-card neutral">
        <span>总流量</span>
        <strong>{{ totalFlow }} m³/h</strong>
      </div>
    </section>

    <!-- Plant Grid -->
    <section class="plant-grid-section">
      <div class="plant-grid">
        <div
          v-for="plant in plants"
          :key="plant.id"
          class="plant-card"
          :class="{ 'offline': plant.status !== 'online', 'has-alert': hasAlert(plant) }"
          @click="showPlantDetail(plant)"
        >
          <div class="plant-header">
            <div class="plant-icon">
              <el-icon v-if="plant.status === 'online'"><CircleCheck /></el-icon>
              <el-icon v-else><Warning /></el-icon>
            </div>
            <div class="plant-info">
              <span class="plant-name">{{ plant.name }}</span>
              <el-tag :type="plant.status === 'online' ? 'success' : 'info'" size="small">
                {{ plant.status === 'online' ? '在线' : '离线' }}
              </el-tag>
            </div>
          </div>

          <div v-if="plant.status === 'online' && plant.metrics" class="metrics-grid">
            <div class="metric-item">
              <span class="metric-label">pH</span>
              <span class="metric-value" :class="getStatusClass(plant.metricStatus?.pH)">
                {{ plant.metrics.pH.toFixed(1) }}
              </span>
            </div>
            <div class="metric-item">
              <span class="metric-label">COD</span>
              <span class="metric-value" :class="getStatusClass(plant.metricStatus?.cod)">
                {{ plant.metrics.cod.toFixed(0) }}
              </span>
            </div>
            <div class="metric-item">
              <span class="metric-label">氨氮</span>
              <span class="metric-value" :class="getStatusClass(plant.metricStatus?.ammoniaNitrogen)">
                {{ plant.metrics.ammoniaNitrogen.toFixed(1) }}
              </span>
            </div>
            <div class="metric-item">
              <span class="metric-label">总氮</span>
              <span class="metric-value" :class="getStatusClass(plant.metricStatus?.totalNitrogen)">
                {{ plant.metrics.totalNitrogen.toFixed(1) }}
              </span>
            </div>
            <div class="metric-item">
              <span class="metric-label">总磷</span>
              <span class="metric-value" :class="getStatusClass(plant.metricStatus?.totalPhosphorus)">
                {{ plant.metrics.totalPhosphorus.toFixed(2) }}
              </span>
            </div>
            <div class="metric-item">
              <span class="metric-label">流量</span>
              <span class="metric-value" :class="getStatusClass(plant.metricStatus?.flow)">
                {{ plant.metrics.flow.toFixed(0) }}
              </span>
            </div>
          </div>

          <div v-else class="offline-message">
            <el-icon><WarningFilled /></el-icon>
            <span>待接入厂区</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Plant Detail Dialog -->
    <el-dialog
      v-model="detailVisible"
      :title="selectedPlant?.name"
      width="600px"
    >
      <div v-if="selectedPlant && selectedPlant.status === 'online' && selectedPlant.metrics" class="plant-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="状态">
            <el-tag type="success">在线运行</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="最后更新">
            {{ formatTime(selectedPlant.lastUpdate) }}
          </el-descriptions-item>
          <el-descriptions-item label="pH值">
            <span :class="getStatusClass(selectedPlant.metricStatus?.pH)">
              {{ selectedPlant.metrics.pH.toFixed(2) }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="COD (mg/L)">
            <span :class="getStatusClass(selectedPlant.metricStatus?.cod)">
              {{ selectedPlant.metrics.cod.toFixed(2) }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="氨氮 (mg/L)">
            <span :class="getStatusClass(selectedPlant.metricStatus?.ammoniaNitrogen)">
              {{ selectedPlant.metrics.ammoniaNitrogen.toFixed(2) }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="总氮 (mg/L)">
            <span :class="getStatusClass(selectedPlant.metricStatus?.totalNitrogen)">
              {{ selectedPlant.metrics.totalNitrogen.toFixed(2) }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="总磷 (mg/L)">
            <span :class="getStatusClass(selectedPlant.metricStatus?.totalPhosphorus)">
              {{ selectedPlant.metrics.totalPhosphorus.toFixed(2) }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="流量 (m³/h)">
            <span :class="getStatusClass(selectedPlant.metricStatus?.flow)">
              {{ selectedPlant.metrics.flow.toFixed(2) }}
            </span>
          </el-descriptions-item>
        </el-descriptions>
      </div>
      <div v-else class="plant-detail-offline">
        <el-empty description="厂区离线或暂无数据" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { realtimeApi } from '@/api/realtime'
import type { PlantData } from '@/types'
import { Warning, CircleCheck, WarningFilled, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const plants = ref<PlantData[]>([])
const detailVisible = ref(false)
const selectedPlant = ref<PlantData | null>(null)
const loading = ref(false)

const onlineCount = computed(() => plants.value.filter(p => p.status === 'online').length)

const abnormalCount = computed(() => {
  return plants.value.reduce((count, plant) => {
    if (plant.status !== 'online' || !plant.metricStatus) return count
    return count + Object.values(plant.metricStatus).filter(s => s === 'abnormal').length
  }, 0)
})

const averagePh = computed(() => {
  const online = plants.value.filter(p => p.status === 'online' && p.metrics)
  if (!online.length) return '--'
  const sum = online.reduce((acc, p) => acc + (p.metrics?.pH || 0), 0)
  return (sum / online.length).toFixed(1)
})

const totalFlow = computed(() => {
  return plants.value.reduce((sum, p) => sum + (p.metrics?.flow || 0), 0).toFixed(0)
})

const lastUpdate = computed(() => {
  if (plants.value.length === 0) return '--'
  const latest = plants.value
    .filter(p => p.lastUpdate)
    .map(p => new Date(p.lastUpdate))
    .sort((a, b) => b.getTime() - a.getTime())[0]
  return latest ? formatTime(latest.toISOString()) : '--'
})

const hasAlert = (plant: PlantData): boolean => {
  if (plant.status !== 'online' || !plant.metricStatus) return false
  return Object.values(plant.metricStatus).some(s => s === 'abnormal')
}

const getStatusClass = (status?: string) => {
  switch (status) {
    case 'normal': return 'status-normal'
    case 'abnormal': return 'status-abnormal'
    default: return 'status-unknown'
  }
}

const formatTime = (iso: string) => {
  return new Date(iso).toLocaleString('zh-CN')
}

const showPlantDetail = (plant: PlantData) => {
  selectedPlant.value = plant
  detailVisible.value = true
}

const loadPlants = async () => {
  loading.value = true
  try {
    const data = await realtimeApi.getAllPlants()
    plants.value = data
  } catch (error) {
    console.error('Failed to load plants:', error)
    ElMessage.error('加载厂区数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadPlants()
  // Auto refresh every 10 seconds
  setInterval(loadPlants, 10000)
})
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

/* Panel Base Style */
.panel {
  background: linear-gradient(180deg, #ffffff 0%, #fffdf8 100%);
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 20px;
  padding: 22px;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
}

/* Hero Section */
.hero {
  align-items: center;
  background:
    radial-gradient(circle at top left, rgba(251, 191, 36, 0.18), transparent 32%),
    radial-gradient(circle at bottom right, rgba(37, 99, 235, 0.15), transparent 28%),
    linear-gradient(135deg, #fff7ed 0%, #f8fbff 100%);
  display: flex;
  gap: 16px;
  justify-content: space-between;
}

.eyebrow {
  color: #9a3412;
  font-size: 12px;
  letter-spacing: 0.16em;
  margin: 0 0 8px;
  text-transform: uppercase;
}

.hero h2 {
  color: #0f172a;
  font-size: 23px;
  margin: 0;
}

.subtitle {
  color: #475569;
  line-height: 1.45;
  margin: 8px 0 0;
  max-width: 620px;
}

.hero-actions {
  align-items: center;
  display: flex;
  gap: 12px;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(4, 1fr);
}

.stat-card {
  border-radius: 22px;
  color: #0f172a;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 116px;
  padding: 18px;
}

.stat-card span {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.stat-card strong {
  font-size: 28px;
  line-height: 1.1;
}

.stat-card.warm {
  background: linear-gradient(135deg, #fef3c7 0%, #fed7aa 100%);
}

.stat-card.cool {
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
}

.stat-card.accent {
  background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
}

.stat-card.neutral {
  background: linear-gradient(135deg, #e2e8f0 0%, #cbd5e1 100%);
}

/* Plant Grid */
.plant-grid-section {
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 20px;
  padding: 22px;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
}

.plant-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.plant-card {
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  border: 1.5px solid #e2e8f0;
  border-radius: 16px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.plant-card:hover {
  border-color: #3b82f6;
  box-shadow: 0 12px 28px rgba(59, 130, 246, 0.12);
  transform: translateY(-2px);
}

.plant-card.offline {
  opacity: 0.6;
  background: linear-gradient(180deg, #f1f5f9 0%, #e2e8f0 100%);
}

.plant-card.has-alert {
  border-color: #f59e0b;
  box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.1);
}

.plant-card.has-alert:hover {
  border-color: #ef4444;
  box-shadow: 0 12px 28px rgba(239, 68, 68, 0.18);
}

.plant-header {
  align-items: center;
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e2e8f0;
}

.plant-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.plant-card:not(.offline) .plant-icon {
  background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
  color: #059669;
}

.plant-card.offline .plant-icon {
  background: #f1f5f9;
  color: #94a3b8;
}

.plant-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.plant-name {
  font-weight: 700;
  color: #1e293b;
  font-size: 14px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.metric-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #f8fafc;
  border-radius: 10px;
}

.metric-label {
  font-size: 12px;
  color: #64748b;
}

.metric-value {
  font-weight: 700;
  font-size: 14px;
  color: #1e293b;
}

.metric-value.status-normal {
  color: #059669;
}

.metric-value.status-abnormal {
  color: #ef4444;
}

.metric-value.status-unknown {
  color: #94a3b8;
}

.offline-message {
  align-items: center;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 24px;
  color: #94a3b8;
  font-size: 13px;
}

.plant-detail {
  color: #1e293b;
}

.plant-detail-offline {
  color: #64748b;
}

/* Responsive */
@media (max-width: 1400px) {
  .plant-grid,
  .stats-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 1000px) {
  .plant-grid,
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .hero {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 600px) {
  .plant-grid,
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .metrics-grid {
    grid-template-columns: 1fr;
  }
}
</style>
