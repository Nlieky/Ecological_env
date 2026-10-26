<template><FloatingAssistant :docked="docked" :current-context="currentContext" @action="execute" @handoff="handoff" /></template>
<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import FloatingAssistant from '@/components/aiops/FloatingAssistant.vue'
import { useAssistantStore, type AssistantMessage } from '@/stores/assistant'
import { useAssistantContextStore, type AssistantContext as PageContext } from '@/stores/assistantContext'
import type { AssistantAction, AssistantHandoff } from '@/api/modules/assistant'
import { executeAssistantAction } from '@/assistant/executor'
import { handoffToMainAssistant } from '@/assistant/handoff'
import { assistantService } from '@/api/modules/assistant'
import { runCandidate } from '@/assistant/execution'
import { validateAssistantAction } from '@/assistant/capabilities'
const assistant = useAssistantStore(), context = useAssistantContextStore(), route = useRoute(), router = useRouter()
const availableWidth = ref(0)
const width = computed(() => assistant.expanded ? 560 : 420)
const docked = computed(() => assistant.open && availableWidth.value - width.value >= 900)
const currentContext = computed(() => context.current ? { ...context.current } : { route: route.path, pageId: String(route.name || route.path) })
let observer: ResizeObserver | undefined, drawerObserver: MutationObserver | undefined, frame = 0
function measure() {
  const admin = document.querySelector('.admin'), sidebar = admin?.firstElementChild
  availableWidth.value = (admin?.getBoundingClientRect().width || 0) - (sidebar?.getBoundingClientRect().width || 0)
}
function resizeCharts() { cancelAnimationFrame(frame); frame = requestAnimationFrame(() => window.dispatchEvent(new Event('resize'))) }
function coordinateDrawers() {
  if (assistant.open && Array.from(document.querySelectorAll<HTMLElement>('.el-drawer')).some(el => el.getClientRects().length > 0 && getComputedStyle(el).visibility !== 'hidden')) assistant.open = false
}
onMounted(() => {
  measure(); observer = new ResizeObserver(() => { measure(); resizeCharts() })
  const admin = document.querySelector('.admin')
  if (admin) { observer.observe(admin); if (admin.firstElementChild) observer.observe(admin.firstElementChild) }
  drawerObserver = new MutationObserver(coordinateDrawers)
  drawerObserver.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'style', 'aria-hidden'] })
})
watch([() => assistant.open, width, docked], async () => { coordinateDrawers(); await nextTick(); resizeCharts() })
onBeforeUnmount(() => { observer?.disconnect(); drawerObserver?.disconnect(); cancelAnimationFrame(frame) })
async function execute(action: AssistantAction, message: AssistantMessage) {
  const index = message.actions?.indexOf(action) ?? -1
  if (index < 0) return
  message.candidates ||= message.actions!.map(() => ({ state: 'prepared' }))
  await runCandidate(message.candidates[index]!, async () => {
  const valid = validateAssistantAction(action)
  if (!valid.success) return valid
  if (action.capability === 'event.propose') {
    try {
      const capabilities = await assistantService.capabilities()
      if (!capabilities.event_writes_enabled) return { success: false, message: '助手事件写入未启用，请使用事件页面。' }
      const p = action.parameters
      if (Object.keys(p).some(key => !['eventId', 'new_status', 'reason'].includes(key)) || typeof p.eventId !== 'string' || !p.eventId.trim() || p.eventId.length > 50 || !['pending', 'processing', 'resolved', 'ignored'].includes(String(p.new_status)) || typeof p.reason !== 'string' || !p.reason.trim() || p.reason.length > 1000) return { success: false, message: '事件变更缺少明确事件、状态或理由，或参数超出允许范围，请重新准备。' }
      message.eventDraft = { eventId: p.eventId, new_status: String(p.new_status), reason: p.reason }
      return { success: true, message: '已打开事件变更确认卡，请核对后确认。' }
    } catch { return { success: false, message: '无法核验事件写入是否启用，请稍后重试。' } }
  }
  return executeAssistantAction(action, message.context as unknown as PageContext, router)
  })
}
async function handoff(value: AssistantHandoff, message: AssistantMessage) {
  try { await handoffToMainAssistant(value.query, message.context as unknown as PageContext, router, message.id); assistant.open = false }
  catch (error) { ElMessage.error(error instanceof Error ? error.message : '交接失败') }
}
</script>
