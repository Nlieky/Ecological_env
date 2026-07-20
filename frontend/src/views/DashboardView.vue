<template>
  <div class="ph">
    <h2>监测大屏(Phase 1 实现)</h2>
    <p>当前出水指标(实时): {{ realtime.realtime?.effluent }}</p>
    <p class="hint">Phase 0 地基占位 — 矩阵大屏在 Phase 1 实现。</p>
  </div>
</template>

<script setup lang="ts">
import { useRealtimeStore } from '@/stores/realtime'
const realtime = useRealtimeStore()
realtime.fetchRealtime()
</script>
<style scoped>
.ph{padding:10px}
.ph h2{color:var(--text-primary);margin-bottom:8px}
.hint{color:var(--text-muted);font-size:13px}
</style>
