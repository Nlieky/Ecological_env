<template>
  <div class="card">
    <div class="lbl">子智能体调用 <span class="more">{{ executed.length }}/{{ ALL.length }}</span></div>
    <div class="chips">
      <span v-for="a in ALL" :key="a.key" class="chip" :class="{ on: isActive(a.key) }">
        <span class="dot"></span>{{ a.name }}<span class="lat">{{ isActive(a.key) ? '已调用' : '未调用' }}</span>
      </span>
    </div>
    <div v-if="!executed.length" class="empty">暂无子智能体调用记录(agent 服务未回传)</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SessionTrace } from '@/api/types/api.types'
const props = defineProps<{ trace: SessionTrace }>()
const ALL = [
  { key: 'multi-dimensional-data-perception', name: '多维数据感知' },
  { key: 'anomaly-detection', name: '异常检测' },
  { key: 'rule-reasoning', name: '规则推理' },
  { key: 'disposition-execution', name: '研判处置' },
]
const executed = computed(() => props.trace.subagent_executions || [])
function isActive(key: string) {
  return executed.value.some((e) => String(e.subagent_name || '').includes(key))
}
</script>

<style scoped>
.card { background: #fafbff; border: 1px solid #e6e9ff; border-radius: 9px; padding: 10px 12px }
.lbl { font-size: 11px; color: var(--primary); font-weight: 600; margin-bottom: 7px; display: flex; justify-content: space-between }
.more { color: var(--text-muted) }
.chips { display: flex; flex-wrap: wrap; gap: 6px }
.chip { font-size: 11px; padding: 5px 9px; border-radius: 7px; background: #fff; border: 1px solid var(--brd); display: flex; align-items: center; gap: 6px; opacity: .5 }
.chip.on { opacity: 1; border-color: #bbf7d0; background: #f0fdf4 }
.dot { width: 6px; height: 6px; border-radius: 50%; background: var(--text-muted) }
.on .dot { background: var(--success) }
.lat { color: var(--text-muted); font-size: 10px }
.empty { font-size: 11px; color: var(--text-muted); margin-top: 6px }
</style>
