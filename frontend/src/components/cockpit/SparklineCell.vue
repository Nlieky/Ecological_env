<template>
  <div class="cell" :class="`t-${cell.trend}`" @click="$emit('drill', cell.key)">
    <span class="glowbar"></span>
    <div class="head">
      <span class="name">{{ cell.name }}</span>
      <span class="dot"></span>
    </div>
    <div class="value">{{ cell.value == null ? '—' : cell.value }}<span class="unit">{{ cell.unit }}</span></div>
    <div class="foot">
      <svg class="spark" viewBox="0 0 92 28" preserveAspectRatio="none">
        <polygon :points="areaPts" :fill="color" opacity="0.12" />
        <polyline :points="linePts" fill="none" :stroke="color" stroke-width="1.5" stroke-linejoin="round" />
      </svg>
      <span class="delta">{{ arrow }} {{ cell.deltaPct == null ? '—' : Math.abs(cell.deltaPct) + '%' }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { sparklinePoints, type Trend } from '@/composables/useSparkline'
import type { IndicatorCell } from '@/composables/useIndicatorMatrix'

const props = defineProps<{ cell: IndicatorCell }>()
defineEmits<{ (e: 'drill', key: string): void }>()

const linePts = computed(() => sparklinePoints(props.cell.series, 92, 28))
const areaPts = computed(() => {
  const p = linePts.value
  return p ? `${p} 92,28 0,28` : ''
})
const colorMap: Record<Trend, string> = { up: 'var(--emerald)', down: 'var(--danger)', volatile: 'var(--warning)', flat: 'var(--text-muted)' }
const color = computed(() => colorMap[props.cell.trend])
const arrowMap: Record<Trend, string> = { up: '▲', down: '▼', volatile: '∿', flat: '–' }
const arrow = computed(() => arrowMap[props.cell.trend])
</script>

<style scoped>
.cell { position: relative; padding: 11px 12px 9px; border-radius: 12px; cursor: pointer; overflow: hidden;
  background: var(--card-bg); border: 1px solid var(--brd); transition: transform .15s, border-color .15s; }
.cell:hover { transform: translateY(-2px); border-color: rgba(120,180,255,.3); }
.glowbar { position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: linear-gradient(currentColor, transparent); }
.head { display: flex; justify-content: space-between; align-items: center; }
.name { font-size: 11px; color: var(--text-secondary); }
.dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; box-shadow: 0 0 8px currentColor; }
.value { font-size: 20px; font-weight: 700; margin: 4px 0 1px; font-variant-numeric: tabular-nums; color: var(--text-primary); }
.unit { font-size: 10.5px; color: var(--text-muted); font-weight: 500; margin-left: 3px; }
.foot { display: flex; align-items: flex-end; justify-content: space-between; height: 28px; }
.spark { width: 92px; height: 28px; }
.delta { font-size: 11px; font-weight: 600; color: currentColor; }
.t-up { color: var(--emerald) } .t-down { color: var(--danger) } .t-volatile { color: var(--warning) } .t-flat { color: var(--text-muted) }
</style>
