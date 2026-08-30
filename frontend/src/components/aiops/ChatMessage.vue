<template>
  <div class="msg" :class="msg.role">
    <div class="role">{{ roleLabel }}</div>
    <div v-if="msg.role === 'user'" class="bubble user">{{ msg.content }}</div>
    <div v-else class="bubble assistant">
      <div v-if="msg.streaming && msg.progress" class="prog">⏳ {{ msg.progress }}</div>
      <MarkdownRenderer v-if="!msg.streaming && msg.content" :content="msg.content" />
      <div v-else-if="msg.content" class="stream-text">{{ msg.content }}<span class="cur">▋</span></div>
      <div v-else-if="msg.streaming" class="stream-text muted">{{ msg.progress ? '' : '思考中…' }}</div>
      <!-- 数据曲线(chartData) -->
      <div v-if="charts.length" class="charts">
        <div v-for="(c, i) in charts" :key="i" :ref="el => setChartRef(el, i)" class="chart-item"></div>
      </div>
      <div v-if="msg.trace" class="cards">
        <DecisionFlow :trace="msg.trace" />
        <SubAgentChips :trace="msg.trace" />
        <EvidenceChain :trace="msg.trace" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, watch } from 'vue'
import echarts from '@/lib/echarts'
import MarkdownRenderer from '@/components/markdown/MarkdownRenderer.vue'
import DecisionFlow from './DecisionFlow.vue'
import SubAgentChips from './SubAgentChips.vue'
import EvidenceChain from './EvidenceChain.vue'
import type { ChatMessage } from '@/stores/chat'
const props = defineProps<{ msg: ChatMessage }>()

// 角色标签:动作通道(AI 助手,短路器秒回)与研判通道(主智能体)区分显示
const roleLabel = computed(() => {
  if (props.msg.role === 'user') return '👤 运维员'
  // 首行是 actionData JSON(短路器输出)或会话在动作助手上下文 → 动作助手
  return props.msg.channel === 'action' ? '⚡ 动作助手' : '🤖 主智能体'
})

// chartData 渲染
const charts = computed(() => props.msg?.chartData?.charts || [])
const chartRefs: HTMLElement[] = []
/** 幂等渲染:echarts.getInstanceByDom 取已有实例,没有才 init。
 *  只在微任务(nextTick 后)调用——ref 回调发生在 Vue patch 主过程中,
 *  里面直接 setOption 会触发 ECharts "main process" 告警并引发 vnode 崩溃。 */
function renderChartAt(i: number) {
  const el = chartRefs[i]
  const opt = charts.value[i]?.option
  if (!el || !opt) return
  const inst = echarts.getInstanceByDom(el as any) || echarts.init(el)
  inst.setOption(opt)
}
const setChartRef = (el: any, i: number) => {
  // ref 回调仅登记 DOM(卸载时 el=null 清位),渲染交给 watch 的 nextTick
  if (el) {
    chartRefs[i] = el
    queueMicrotask(() => renderChartAt(i))  // 微任务:patch 主流程外执行
  }
}
watch(charts, async () => {
  await nextTick()
  await nextTick()  // 双 nextTick:v-for 的 ref 回调在 patch 后异步执行
  charts.value.forEach((_, i) => renderChartAt(i))
}, { immediate: true })
</script>

<style scoped>
.msg { margin-bottom: 18px; max-width: 820px }
.role { font-size: 11px; color: var(--text-muted); margin-bottom: 5px }
.bubble { padding: 13px 16px; border-radius: 12px; font-size: 13.5px; line-height: 1.7 }
.user { background: var(--primary); color: #fff; border-radius: 12px 12px 4px 12px }
.assistant { background: #fff; border: 1px solid var(--brd); border-radius: 12px 12px 12px 4px; box-shadow: 0 1px 3px rgba(0,0,0,.04) }
.cards { margin-top: 12px; border-left: 3px solid var(--primary); padding-left: 12px; display: flex; flex-direction: column; gap: 8px }
.prog { font-size: 12.5px; color: var(--primary); background: var(--primary-soft, #eef2ff); border-radius: 8px; padding: 7px 11px; margin-bottom: 9px }
.stream-text { white-space: pre-wrap; word-break: break-word; font-size: 13.5px; line-height: 1.7 }
.stream-text.muted { color: var(--text-muted) }
.cur { animation: blink 1s step-start infinite; color: var(--primary); margin-left: 1px }
@keyframes blink { 50% { opacity: 0 } }
.charts { margin-top: 12px; display: flex; flex-direction: column; gap: 10px }
.chart-item { width: 100%; height: 280px; border: 1px solid var(--brd); border-radius: 10px; overflow: hidden }
</style>
