<template>
  <div>
    <div class="grp-label">{{ label }}</div>
    <div class="grid">
      <SparklineCell v-for="c in cells" :key="c.key" :cell="c" @drill="$emit('drill', $event)" />
    </div>
  </div>
</template>

<script setup lang="ts">
import SparklineCell from './SparklineCell.vue'
import type { IndicatorCell } from '@/composables/useIndicatorMatrix'
defineProps<{ label: string; cells: IndicatorCell[] }>()
defineEmits<{ (e: 'drill', key: string): void }>()
</script>

<style scoped>
.grp-label { display: flex; align-items: center; gap: 8px; font-size: 11px; color: var(--cyan); letter-spacing: 1px; margin: 10px 0 8px; text-transform: uppercase; }
.grp-label::after { content: ''; flex: 1; height: 1px; background: linear-gradient(90deg, rgba(34,211,238,.25), transparent); }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(188px, 1fr)); gap: 11px; }
</style>
