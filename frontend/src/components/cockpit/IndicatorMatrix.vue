<template>
  <div class="matrix">
    <IndicatorGroup v-if="show('influent')" label="进水指标 INFLUENT" :cells="groups.influent" @drill="$emit('drill', $event)" />
    <IndicatorGroup v-if="show('effluent')" label="出水指标 EFFLUENT" :cells="groups.effluent" @drill="$emit('drill', $event)" />
    <IndicatorGroup label="衍生指标 DERIVED" :cells="groups.derived" @drill="$emit('drill', $event)" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import IndicatorGroup from './IndicatorGroup.vue'
import type { IndicatorGroups, IndicatorCell } from '@/composables/useIndicatorMatrix'
import { useAppStore } from '@/stores/app'

const props = defineProps<{ groups: IndicatorGroups }>()
defineEmits<{ (e: 'drill', key: string): void }>()
const app = useAppStore()

function show(side: 'influent' | 'effluent') {
  return app.dashboardFilters.category === 'all' || app.dashboardFilters.category === side
}
const rank = (t: string) => (t === 'volatile' ? 0 : t === 'down' ? 1 : t === 'up' ? 2 : 3)
const sortFn = (a: IndicatorCell, b: IndicatorCell) => rank(a.trend) - rank(b.trend)
const groups = computed(() => ({
  influent: [...props.groups.influent].sort(sortFn),
  effluent: [...props.groups.effluent].sort(sortFn),
  derived: props.groups.derived,
}))
</script>

<style scoped>
.matrix { display: flex; flex-direction: column; gap: 4px; }
</style>
