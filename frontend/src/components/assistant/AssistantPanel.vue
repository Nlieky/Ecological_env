<template>
  <section class="assistant-panel" aria-label="全系统助手" tabindex="-1" @keydown.esc.stop="assistant.open = false">
    <header><strong>全系统助手</strong><div><button :aria-label="assistant.expanded ? '恢复默认宽度' : '展开宽度'" @click="assistant.expanded = !assistant.expanded">{{ assistant.expanded ? '收窄' : '展开' }}</button><button aria-label="收起助手" @click="assistant.open = false">✕</button></div></header>
    <div class="current-context">当前页面：{{ currentContext.pageTitle || currentContext.pageId || '系统' }}</div>
    <div ref="scrollBody" class="messages" role="log" aria-live="polite" aria-relevant="additions text">
      <p v-if="!assistant.messages.length" class="empty">可以问页面用途、字段含义，或请我帮你找到功能。<br>专业研判与报告可交给主 AI 助手。</p>
      <article v-for="message in assistant.messages" :key="message.id" :class="['message', message.role]">
        <small>{{ message.role === 'user' ? '你' : '系统助手' }} · {{ message.context.pageTitle || message.context.pageId || '系统' }}</small>
        <div class="message-content">{{ message.content }}</div>
        <p v-if="message.status === 'running'" role="status">正在解释…</p>
        <p v-if="message.status === 'interrupted'" class="error">接收已停止，可重新提问。</p>
        <p v-if="message.error" class="error">{{ message.error }}</p>
        <button v-if="['failed', 'interrupted'].includes(message.status)" :disabled="assistant.loading" @click="assistant.retry(message.id)">重试原问题</button>
        <slot name="actions" :message="message">
          <div v-for="(action, index) in message.actions" :key="action.id || index" class="candidate">
            <button class="action-card" :disabled="!['prepared', 'failed'].includes(message.candidates?.[index]?.state || 'prepared')" @click="emit('action', action, message)">{{ capabilityDescriptor(action.capability)?.title || action.label || action.capability }} · {{ stateLabel(message.candidates?.[index]?.state) }}</button>
            <small>来源厂站：{{ message.context.plant || '未选择' }} · 时间：{{ formatValue(message.context.range) }}</small>
            <div v-for="(value, key) in action.parameters" :key="key" class="parameter">{{ fieldLabel(action.capability, String(key)) }}：{{ formatValue(value) }}（{{ origin(action.parameter_sources?.[key]) }}）</div>
            <p v-if="Object.values(action.parameter_sources || {}).includes('default')" class="parameter">{{ capabilityDescriptor(action.capability)?.defaults.explanation || '已按你的授权采用默认参数' }}</p>
            <div v-if="message.candidates?.[index]?.receipt" class="receipt" role="status"><p>{{ message.candidates[index]!.receipt!.message }}</p><div v-for="(value, key) in message.candidates[index]!.receipt!.details" :key="key" class="parameter">{{ fieldLabel(action.capability, String(key)) }}：{{ formatValue(value) }}</div></div>
          </div>
        </slot>
        <div v-if="message.pending" class="pending-card"><p>请补充：{{ message.pending.missing.map(key => missingPrompt(message.pending!.capability, key)).join('；') }}</p><button @click="assistant.clearPending()">取消 / 清除待补充操作</button></div>
        <p v-for="(candidate, index) in !message.actions?.length ? message.candidates : []" :key="index" class="receipt">{{ candidate.receipt?.message }}</p>
        <button v-if="message.query && (message.actions?.length || message.pending || message.error)" :disabled="assistant.loading" @click="assistant.reprepare(message.id, currentContext)">基于当前页面重新准备</button>
        <AssistantEventCard v-if="message.eventDraft || message.eventOperation" :context="message.context" :parameters="message.eventDraft" :message="message" />
        <button v-if="message.handoff" class="action-card" @click="emit('handoff', message.handoff, message)">交给主 AI 助手 · 查看交接</button>
      </article>
    </div>
    <details v-if="eventWritesEnabled && currentContext.pageId === 'events'" class="event-tools"><summary>修改单事件状态（需确认）</summary><AssistantEventCard :key="String(currentContext.revision)" :context="currentContext" /></details>
    <form @submit.prevent="send"><label for="assistant-query">向系统助手提问</label><textarea id="assistant-query" ref="input" v-model="assistant.draft" rows="3" placeholder="解释当前页面，或帮我找到功能…" @keydown.enter.exact.prevent="send" /><div class="composer-bottom"><small>Enter 发送 · Shift+Enter 换行</small><button type="submit" :disabled="assistant.loading || !assistant.draft.trim()">{{ assistant.loading ? '解释中…' : '发送' }}</button></div></form>
  </section>
</template>
<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import { useAssistantStore, type AssistantMessage } from '@/stores/assistant'
import type { AssistantAction, AssistantContext, AssistantHandoff } from '@/api/modules/assistant'
import { assistantService } from '@/api/modules/assistant'
import AssistantEventCard from './AssistantEventCard.vue'
import { capabilityDescriptor } from '@/assistant/capabilities'
const valueLabels: Record<string, string> = { influent: '进水', effluent: '出水', all: '全部', constant: '恒值检测', changepoint: '突变检测', iforest: '离群检测', dashboard: '监测大屏', events: '事件中心', metrics: '指标查询', audit: '智能体审计', graph: '知识图谱', config: '智能体配置', chat: 'AI助手', logs: '日志中心' }
const formatValue = (value: unknown): string => {
  if (value == null) return '未指定'
  if (typeof value !== 'object') return valueLabels[String(value)] || String(value)
  if ('start' in value && 'end' in value) return `${value.start} ~ ${value.end}`
  return Object.values(value).map(formatValue).join('、')
}
const detailLabels: Record<string, string> = { plant: '厂站', source: '数据来源', start: '开始时间', end: '结束时间', anomaly_count: '检出数量', visible_count: '可见标记数量' }
const fieldLabel = (capability: string, key: string) => detailLabels[key] || (capabilityDescriptor(capability)?.missing_prompts as Record<string, string> | undefined)?.[key]?.replace(/^请明确/, '') || key
const stateLabel = (state?: string) => ({ prepared: '执行操作', running: '执行中…', succeeded: '已完成', empty: '完成 · 无匹配结果', failed: '失败 · 重试操作', stale: '已失效 · 请重新准备' }[state || 'prepared'] || '执行操作')
const origin = (value: unknown) => value === 'context' ? '页面继承' : value === 'default' ? '服务端默认' : '请求解析'
const missingPrompt = (capability: string, key: string) => (capabilityDescriptor(capability)?.missing_prompts as Record<string, string> | undefined)?.[key] || key
const props = defineProps<{ currentContext: AssistantContext }>()
const emit = defineEmits<{ action: [action: AssistantAction, message: AssistantMessage]; handoff: [handoff: AssistantHandoff, message: AssistantMessage] }>()
const assistant = useAssistantStore(), input = ref<HTMLTextAreaElement>(), scrollBody = ref<HTMLElement>()
const eventWritesEnabled = ref(false)
function send() { if (assistant.loading || !assistant.draft.trim()) return; const query = assistant.draft.trim(); assistant.draft = ''; void assistant.sendQuery(query, props.currentContext) }
onMounted(() => { input.value?.focus(); void assistantService.capabilities().then(value => { eventWritesEnabled.value = value.event_writes_enabled === true }).catch(() => {}) })
watch(() => assistant.messages, async () => { await nextTick(); if (scrollBody.value) scrollBody.value.scrollTop = scrollBody.value.scrollHeight }, { deep: true })
watch(() => assistant.open, async value => { if (value) { await nextTick(); input.value?.focus() } })
</script>
<style scoped>
.assistant-panel { height:100%; min-height:0; display:flex; flex-direction:column; color:#1e293b; outline:none; }
.event-tools { padding:10px 14px; max-height:40%; overflow:auto; font-size:13px; background:rgba(239,246,255,.95) } summary { cursor:pointer }
header { display:flex; justify-content:space-between; align-items:center; padding:14px; border-bottom:1px solid rgba(96,165,250,.25) } header strong { color:#2563eb } header div { display:flex; gap:6px }
button { font:inherit; cursor:pointer; border:1px solid rgba(96,165,250,.4); background:rgba(255,255,255,.85); color:#2563eb; border-radius:8px; padding:6px 10px } button:disabled { opacity:.55; cursor:default } button:focus-visible, textarea:focus-visible { outline:2px solid #2563eb; outline-offset:2px }
.current-context { font-size:12px; padding:10px 14px; color:#475569; background:rgba(239,246,255,.9) }.messages { flex:1; min-height:0; overflow:auto; padding:14px; background:rgba(255,255,255,.88) }.empty { font-size:14px; line-height:1.9; color:#64748b; padding:24px 0 }.message { margin:0 0 16px; padding:12px; border-radius:12px; background:#f1f5f9; overflow-wrap:anywhere }.message.user { background:#eff6ff }.message small { font-size:11px; color:#64748b }.message-content { white-space:pre-wrap; line-height:1.7; font-size:14px; margin-top:5px }.error { color:#b45309; font-size:13px }.action-card { display:block; margin-top:8px; width:100%; text-align:left }
form { padding:12px 14px; border-top:1px solid rgba(96,165,250,.25); background:rgba(239,246,255,.95) } label { display:block; font-size:12px; margin-bottom:7px } textarea { box-sizing:border-box; resize:vertical; width:100%; max-height:180px; border:1px solid #bfdbfe; border-radius:10px; padding:10px; font:inherit; background:rgba(255,255,255,.95); color:#1e293b }.composer-bottom { display:flex; align-items:center; justify-content:space-between; gap:8px; margin-top:8px }.composer-bottom small { color:#64748b; font-size:11px }
</style>
