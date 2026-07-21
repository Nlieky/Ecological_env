<template>
  <div class="anomaly">
    <h3>趋势异常清单 <span class="badge">{{ items.length }} 条</span></h3>
    <div v-if="items.length" class="list">
      <div v-for="it in items" :key="it.key" class="item">
        <span class="ico" :class="it.tone">{{ it.icon }}</span>
        <div><div class="t">{{ it.name }} · {{ it.kind }}</div><div class="d">{{ it.detail }}</div></div>
      </div>
    </div>
    <div v-else class="empty">暂无趋势异常</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { IndicatorGroups } from '@/composables/useIndicatorMatrix'
const props = defineProps<{ groups: IndicatorGroups }>()
const items = computed(() => {
  const out: { key: string; name: string; kind: string; detail: string; tone: string; icon: string }[] = []
  for (const c of [...props.groups.influent, ...props.groups.effluent]) {
    if (c.trend === 'volatile') out.push({ key: c.key, name: c.name, kind: '波动过大', detail: `当前 ${c.value ?? '—'} ${c.unit}`, tone: 'vol', icon: '∿' })
    else if (c.trend === 'down' && (c.deltaPct ?? 0) <= -10) out.push({ key: c.key, name: c.name, kind: '突然下跌', detail: `${c.deltaPct}%`, tone: 'down', icon: '▼' })
  }
  return out
})
</script>

<style scoped>
.anomaly { margin-top: 16px; padding: 13px 16px; border-radius: 14px; background: var(--card-bg); border: 1px solid var(--brd); }
h3 { font-size: 13px; display: flex; gap: 8px; align-items: center; margin-bottom: 10px; color: var(--text-primary); }
.badge { font-size: 11px; padding: 2px 8px; border-radius: 6px; background: rgba(251,90,106,.15); color: var(--danger); border: 1px solid rgba(251,90,106,.3); }
.list { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.item { display: flex; gap: 10px; align-items: center; padding: 9px 11px; border-radius: 10px; background: var(--surface-1); border: 1px solid var(--brd); }
.ico { width: 28px; height: 28px; border-radius: 8px; display: grid; place-items: center; font-size: 13px; }
.ico.down { background: rgba(251,90,106,.12); color: var(--danger); } .ico.vol { background: rgba(139,155,255,.12); color: var(--violet); }
.t { font-size: 12px; color: var(--text-primary); } .d { font-size: 11px; color: var(--text-muted); margin-top: 1px; }
.empty { color: var(--text-muted); font-size: 12px; }
</style>
