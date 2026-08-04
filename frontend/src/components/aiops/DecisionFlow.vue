<template>
  <div class="card">
    <div class="lbl">决策路径 <span class="more">master_decision</span></div>
    <div class="flow">
      <span v-for="(s, i) in steps" :key="i" class="step" :class="s.done ? 'done' : 'skip'">
        <span class="n">{{ i + 1 }}</span>{{ s.name }}
      </span>
    </div>
    <div class="path" v-if="rawPath?.length">原始:{{ rawPath.join(' → ') }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SessionTrace } from '@/api/types/api.types'
const props = defineProps<{ trace: SessionTrace }>()
const md = computed(() => props.trace.master_decision)
const rawPath = computed(() => (md.value?.decision_path as string[] | undefined) ?? [])
const STEPS = ['数据感知', '异常检测', '规则推理', '研判处置']
// decision_path 存的是英文 key（multi-dimensional-data-perception 等），映射到中文模板
// 名后再判定高亮——避免按数组长度误高亮前 N 个固定模板（旧逻辑 length=3 就高亮
// "感知/异常/规则"，哪怕第3个实际是"异常检测"）。
const KEY_CN: Record<string, string> = {
  'multi-dimensional-data-perception': '数据感知',
  'anomaly-detection': '异常检测',
  'rule-reasoning': '规则推理',
  'disposition-execution': '研判处置',
}
const calledSet = computed(() => new Set((rawPath.value || []).map((p) => KEY_CN[p] ?? p)))
const steps = computed(() => STEPS.map((name) => ({ name, done: calledSet.value.has(name) })))
</script>

<style scoped>
.card { background: #fafbff; border: 1px solid #e6e9ff; border-radius: 9px; padding: 10px 12px }
.lbl { font-size: 11px; color: var(--primary); font-weight: 600; margin-bottom: 7px; display: flex; justify-content: space-between }
.more { color: var(--text-muted); font-weight: 400 }
.flow { display: flex; gap: 6px; flex-wrap: wrap }
.step { display: flex; align-items: center; gap: 5px; font-size: 11.5px; padding: 4px 9px; border-radius: 7px; background: #fff; border: 1px solid var(--brd) }
.step.done { border-color: #bbf7d0; background: #f0fdf4 }
.step.skip { opacity: .5 }
.n { width: 16px; height: 16px; border-radius: 50%; display: grid; place-items: center; font-size: 9px; font-weight: 700; background: var(--success); color: #fff }
.skip .n { background: var(--text-muted) }
.path { margin-top: 6px; font-size: 11px; color: var(--text-secondary) }
</style>
