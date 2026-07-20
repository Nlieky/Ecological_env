<template>
  <div class="card">
    <div class="lbl">证据链 <router-link class="more" :to="`/logs/trace/${trace.session_id}`">查看完整追溯 ▸</router-link></div>
    <div class="evi">
      <div class="e"><div class="h">意图</div><div class="v">{{ md?.intent || '—' }}</div></div>
      <div class="e"><div class="h">耗时</div><div class="v">{{ md?.total_latency_ms != null ? Math.round(md.total_latency_ms) + 'ms' : '—' }}</div></div>
      <div class="e"><div class="h">推理摘要</div><div class="v sm">{{ md?.reasoning_summary || '—' }}</div></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SessionTrace } from '@/api/types/api.types'
const props = defineProps<{ trace: SessionTrace }>()
const md = computed(() => props.trace.master_decision)
</script>

<style scoped>
.card { background: #fafbff; border: 1px solid #e6e9ff; border-radius: 9px; padding: 10px 12px }
.lbl { font-size: 11px; color: var(--primary); font-weight: 600; margin-bottom: 7px; display: flex; justify-content: space-between }
.more { color: var(--primary); text-decoration: none; font-weight: 400 }
.evi { display: flex; gap: 8px }
.e { flex: 1; padding: 6px 8px; border: 1px solid var(--brd); border-radius: 7px; background: #fff }
.h { color: var(--text-muted); font-size: 9.5px; letter-spacing: .5px }
.v { color: var(--text-primary); font-weight: 600; margin-top: 2px; font-size: 11px }
.v.sm { font-weight: 400; font-size: 10.5px; color: var(--text-secondary) }
</style>
