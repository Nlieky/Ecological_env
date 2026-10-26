<template>
  <section class="event-card" aria-label="单事件状态确认">
    <strong>单事件状态变更</strong>
    <p>事件 {{ proposal?.event_id || message?.eventOperation?.eventId || target }} · 厂站 {{ proposal?.plant_id || context.plant || '未选择' }}</p>
    <template v-if="!proposal && !message?.eventOperation">
      <label>事件 ID<input v-model="target" :disabled="busy" maxlength="50" placeholder="输入明确的单事件 ID" /></label>
      <label>目标状态<select v-model="newStatus" :disabled="busy"><option value="processing">处理中</option><option value="resolved">已解决</option><option value="ignored">忽略</option><option value="pending">待处理</option></select></label>
      <label>变更理由<textarea v-model="reason" :disabled="busy" maxlength="1000" rows="2" /></label>
      <button :disabled="busy || !target || !reason.trim()" @click="prepare">核验并准备确认</button>
    </template>
    <template v-else-if="proposal">
      <p>{{ proposal.old_status }} → {{ proposal.new_status }}</p><p>理由：{{ proposal.reason }}</p><p>有效期至 {{ proposal.expires_at }}</p><p>{{ proposal.identity }}</p>
      <button v-if="state === 'prepared'" :disabled="busy" @click="confirm">确认修改此事件</button>
      <button v-if="state === 'prepared'" :disabled="busy" @click="cancel">取消变更</button>
      <button v-if="state === 'unknown'" :disabled="busy" @click="verify">查询操作结果</button>
      <button v-if="state === 'failed'" @click="reset">重新准备</button>
    </template>
    <template v-if="message?.eventOperation"><p>{{ message.eventOperation.feedback }}</p><button v-if="message.eventOperation.state === 'unknown'" :disabled="busy" @click="verify">查询操作结果</button></template>
    <p v-if="feedback" role="status">{{ feedback }}</p>
  </section>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { assistantService, type AssistantContext, type EventProposal } from '@/api/modules/assistant'
import { useAssistantStore } from '@/stores/assistant'
import type { AssistantMessage } from '@/stores/assistant'
import { useAssistantContextStore } from '@/stores/assistantContext'
import { eventsService } from '@/api/modules/events'
const props = defineProps<{ context: AssistantContext; parameters?: Record<string, unknown>; message?: AssistantMessage }>()
const assistant = useAssistantStore(), current = useAssistantContextStore()
const target = ref(String(props.parameters?.event_id || props.parameters?.eventId || props.context.objectId || ''))
const newStatus = ref(String(props.parameters?.new_status || 'processing')), reason = ref(String(props.parameters?.reason || ''))
const proposal = ref<EventProposal>(), busy = ref(false), state = ref<'prepared' | 'unknown' | 'failed' | 'completed'>('prepared'), feedback = ref(''), operationId = ref('')
let idempotencyKey = ''
let operationMessage = props.message
function sameContext() { return current.current?.revision === props.context.revision && current.current?.objectId === props.context.objectId && current.current?.route === props.context.route }
function errorText(error: unknown) { const e = error as { response?: { data?: { detail?: unknown } }; message?: string }; return typeof e.response?.data?.detail === 'string' ? e.response.data.detail : e.message || '操作失败' }
async function prepare() {
  if (busy.value) return
  if (!sameContext()) { feedback.value = '页面或对象已变化，请基于当前事件重新准备'; return }
  const request = { session_id: assistant.sessionId, event_id: target.value, new_status: newStatus.value, reason: reason.value.trim() }
  busy.value = true
  try { const event = await eventsService.detail(request.event_id); if (!sameContext()) throw new Error('页面或对象已变化，请重新准备'); proposal.value = await assistantService.proposeEvent({ ...request, expected_status: event.status, expected_updated_at: event.updatedAt }); idempotencyKey = crypto.randomUUID(); state.value = 'prepared'; feedback.value = '' }
  catch (error) { feedback.value = errorText(error) }
  finally { busy.value = false }
}
async function confirm() {
  if (!proposal.value || state.value !== 'prepared' || busy.value) return
  if (!sameContext() || new Date(proposal.value.expires_at).getTime() <= Date.now()) { state.value = 'failed'; feedback.value = '对象已变化或提议过期，请重新准备'; return }
  const eventId = proposal.value.event_id
  busy.value = true
  if (!operationMessage) { assistant.messages.push({ id: crypto.randomUUID(), role: 'assistant', content: `事件 ${eventId} 状态变更操作`, context: JSON.parse(JSON.stringify(props.context)), status: 'complete' }); operationMessage = assistant.messages[assistant.messages.length - 1] }
  operationMessage!.eventOperation = { key: idempotencyKey, eventId, state: 'unknown', feedback: '提交中，结果待核验。' }
  try { const result = await assistantService.confirmEvent(proposal.value.proposal_id, { session_id: assistant.sessionId, idempotency_key: idempotencyKey }); operationId.value = result.operation_id; const checked = await assistantService.eventOperation(result.operation_id, assistant.sessionId); state.value = 'completed'; feedback.value = `已核验：${checked.event_id} → ${checked.new_status}；${checked.identity}` }
  catch (error) { const status = (error as { response?: { status?: number } }).response?.status; state.value = !operationId.value && status && status < 500 ? 'failed' : 'unknown'; feedback.value = state.value === 'unknown' ? '结果待核验，请查询操作结果；不会自动重复写入。' : errorText(error) }
  finally { busy.value = false; if (operationMessage) { operationMessage.eventOperation = state.value === 'failed' ? undefined : { key: idempotencyKey, eventId, operationId: operationId.value || undefined, state: state.value === 'completed' ? 'completed' : 'unknown', feedback: feedback.value }; if (state.value === 'failed') operationMessage.content += `\n${feedback.value}` } }
}
async function verify() {
  busy.value = true
  try { const op = operationId.value || props.message?.eventOperation?.operationId; const key = props.message?.eventOperation?.key || idempotencyKey; const result = op ? await assistantService.eventOperation(op, assistant.sessionId) : await assistantService.eventOperationByKey(key, assistant.sessionId); operationId.value = result.operation_id; state.value = 'completed'; feedback.value = `已核验：${result.event_id} → ${result.new_status}` }
  catch (error) { feedback.value = errorText(error) }
  finally { busy.value = false; if (props.message?.eventOperation) { props.message.eventOperation.state = state.value === 'completed' ? 'completed' : 'unknown'; props.message.eventOperation.feedback = feedback.value; props.message.eventOperation.operationId = operationId.value || undefined } }
}
function reset() { proposal.value = undefined; feedback.value = ''; state.value = 'prepared' }
function cancel() {
  if (busy.value || state.value !== 'prepared') return
  proposal.value = undefined
  idempotencyKey = ''
  feedback.value = '已取消，未提交事件变更。'
}
</script>
<style scoped>
.event-card { margin-top:10px; padding:12px; border:1px solid #93c5fd; border-radius:10px; background:#eff6ff; font-size:13px; overflow-wrap:anywhere } p { line-height:1.5 } label { display:block; margin:8px 0 } select,textarea { display:block; box-sizing:border-box; width:100%; margin-top:5px; border:1px solid #bfdbfe; border-radius:6px; padding:7px; color:#1e293b; background:white; font:inherit } button { border:1px solid #93c5fd; border-radius:7px; padding:7px 10px; background:white; color:#2563eb; cursor:pointer } button:disabled { opacity:.5 }
</style>
