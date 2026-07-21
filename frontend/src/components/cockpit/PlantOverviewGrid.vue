<template>
  <div>
    <div class="grp-label">全厂总览 · OVERVIEW</div>
    <div class="plants">
      <div v-for="p in plants" :key="p.id" class="plant" :class="health(p)" @click="$emit('select', p.id)">
        <div class="pname">{{ p.name }}</div>
        <div class="pstat">COD {{ p.metrics?.cod ?? '—' }} mg/L · {{ p.status === 'online' ? '在线' : '离线' }}</div>
        <div class="prow"><span class="pkey">健康度</span><span class="pval">{{ healthScore(p) }}</span></div>
        <div class="pbar"><i :style="{ width: healthScore(p) + '%' }"></i></div>
      </div>
    </div>
    <div v-if="!plants.length" class="empty">暂无厂数据</div>
  </div>
</template>

<script setup lang="ts">
import type { PlantData } from '@/api/types/api.types'
defineProps<{ plants: PlantData[] }>()
defineEmits<{ (e: 'select', id: string): void }>()

function healthScore(p: PlantData): number {
  // 离线厂 metricStatus 为 null；在线厂才有指标状态。空则健康度 0。
  if (!p.metricStatus) return 0
  const entries = Object.values(p.metricStatus) as string[]
  if (!entries.length) return 0
  const normal = entries.filter((s) => s === 'normal').length
  return Math.round((normal / entries.length) * 100)
}
function health(p: PlantData) {
  const s = healthScore(p)
  return s >= 80 ? 'ok' : s >= 50 ? 'warn' : 'err'
}
</script>

<style scoped>
.grp-label { display: flex; align-items: center; gap: 8px; font-size: 11px; color: var(--cyan); letter-spacing: 1px; margin: 10px 0 12px; text-transform: uppercase; }
.grp-label::after { content: ''; flex: 1; height: 1px; background: linear-gradient(90deg, rgba(34,211,238,.25), transparent); }
.plants { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 10px; }
.plant { padding: 11px 12px; border-radius: 11px; background: var(--card-bg); border: 1px solid var(--brd); cursor: pointer; transition: border-color .15s; }
.plant:hover { border-color: rgba(120,180,255,.3); }
.pname { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.pstat { font-size: 11px; color: var(--text-muted); margin: 2px 0 7px; }
.prow { display: flex; justify-content: space-between; font-size: 11px; }
.pkey { color: var(--text-secondary); } .pval { color: var(--text-primary); font-weight: 600; }
.pbar { height: 4px; border-radius: 3px; margin-top: 8px; background: var(--surface-2); overflow: hidden; }
.pbar i { display: block; height: 100%; }
.ok .pbar i { background: var(--emerald); } .warn .pbar i { background: var(--warning); } .err .pbar i { background: var(--danger); }
.plant.err { border-color: rgba(251,90,106,.35); }
.empty { color: var(--text-muted); font-size: 12px; padding: 20px; }
</style>
