<template>
  <div class="bar">
    <div class="grp"><span class="lbl">分类</span>
      <span v-for="c in cats" :key="c.v" class="chip" :class="{ on: app.dashboardFilters.category === c.v }" @click="set('category', c.v)">{{ c.t }}</span>
    </div>
    <div class="grp"><span class="lbl">时间窗口</span>
      <span v-for="w in wins" :key="w.v" class="chip" :class="{ on: app.dashboardFilters.timeWindow === w.v }" @click="set('timeWindow', w.v)">{{ w.t }}</span>
    </div>
    <div class="grp"><span class="lbl">排序</span>
      <span v-for="s in sorts" :key="s.v" class="chip" :class="{ on: app.dashboardFilters.sort === s.v }" @click="set('sort', s.v)">{{ s.t }}</span>
    </div>
    <span class="ts" v-if="lastUpdate">数据更新 {{ lastUpdate }}</span>
  </div>
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores/app'
defineProps<{ lastUpdate?: string }>()
const app = useAppStore()
const cats = [{ t: '全部', v: 'all' as const }, { t: '进水', v: 'influent' as const }, { t: '出水', v: 'effluent' as const }]
const wins = [{ t: '1H', v: '1h' as const }, { t: '6H', v: '6h' as const }, { t: '24H', v: '24h' as const }]
const sorts = [{ t: '异常优先', v: 'anomaly' as const }, { t: '当前值', v: 'value' as const }, { t: '涨跌幅', v: 'delta' as const }]
function set(k: 'category' | 'timeWindow' | 'sort', v: string) {
  ;(app.dashboardFilters as any)[k] = v
}
</script>

<style scoped>
.bar { display: flex; gap: 14px; align-items: center; flex-wrap: wrap; padding: 11px 14px; border-radius: 13px; background: var(--card-bg); border: 1px solid var(--brd); backdrop-filter: blur(6px); }
.grp { display: flex; align-items: center; gap: 7px; }
.lbl { font-size: 11px; color: var(--text-muted); letter-spacing: 1px; }
.chip { font-size: 12px; padding: 5px 11px; border-radius: 8px; color: var(--text-secondary); cursor: pointer; background: var(--surface-1); border: 1px solid var(--brd); }
.chip.on { color: #04121a; background: linear-gradient(135deg, var(--cyan), #5fb9ff); border-color: transparent; font-weight: 600; box-shadow: 0 0 14px rgba(34,211,238,.4); }
.ts { margin-left: auto; font-size: 12px; color: var(--text-secondary); font-variant-numeric: tabular-nums; }
</style>
