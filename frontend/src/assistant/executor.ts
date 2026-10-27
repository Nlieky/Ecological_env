import { nextTick, watch } from 'vue'
import type { Router } from 'vue-router'
import { useAssistantContextStore, type AssistantContext } from '@/stores/assistantContext'
import { ASSISTANT_PAGES, capabilityDescriptor, validateAssistantAction, type AssistantAction } from './capabilities'
import { contextPolicy } from './contextPolicy'

export interface AssistantExecutionResult { success: boolean; message: string; target?: string; code?: string; details?: Record<string, unknown> }
export type AssistantPageExecutor = (action: AssistantAction) => Promise<AssistantExecutionResult>
const handlers = new Map<string, AssistantPageExecutor>()
const registrations = new Set<() => void>()
export function registerAssistantExecutor(pageId: string, handler: AssistantPageExecutor) {
  handlers.set(pageId, handler)
  registrations.forEach(notify => notify())
  return () => { if (handlers.get(pageId) === handler) handlers.delete(pageId) }
}
export function waitForAssistantExecutor(pageId: string, target: string, router: Router, timeoutMs = 2500): Promise<AssistantPageExecutor | null> {
  return new Promise(resolve => {
    let finished = false
    const finish = (handler: AssistantPageExecutor | null) => { if (finished) return; finished = true; clearTimeout(timer); registrations.delete(check); stop(); resolve(handler) }
    const check = () => { if (router.currentRoute.value.path !== target) finish(null); else if (handlers.has(pageId)) finish(handlers.get(pageId)!) }
    const stop = watch(() => router.currentRoute.value.path, check, { flush: 'sync' })
    const timer = setTimeout(() => finish(null), timeoutMs)
    registrations.add(check); check()
  })
}
export async function executeAssistantAction(action: AssistantAction, context: AssistantContext | null, router: Router): Promise<AssistantExecutionResult> {
  const valid = validateAssistantAction(action)
  if (!valid.success) return valid
  const current = useAssistantContextStore().current
  const descriptor = capabilityDescriptor(action.capability)
  if (descriptor?.invalidation.mode !== 'destination' && context?.route !== router.currentRoute.value.path) return { success: false, code: 'stale_context', message: '来源页面已变化，请重新准备操作' }
  // Explicit navigation depends only on its allowlisted destination, not on a
  // source snapshot that polling/loading may have refreshed while we answered.
  const invalid = contextPolicy(action, context as unknown as Record<string, unknown>, current as unknown as Record<string, unknown>)
  if (invalid) return { success: false, code: 'stale_context', message: invalid }
  try {
    if (action.capability === 'navigate') {
      const target = ASSISTANT_PAGES[action.parameters.pageId as keyof typeof ASSISTANT_PAGES]
      if (router.currentRoute.value.path !== target && await router.push(target)) return { success: false, message: '导航被页面取消' }
      return { success: router.currentRoute.value.path === target, message: `已打开 ${target}`, target }
    }
    const descriptor = capabilityDescriptor(action.capability)
    const pageId = descriptor?.target_page, target = descriptor?.target_path
    if (!pageId || !target || descriptor.level === 'proposal') return { success: false, message: '该能力未开放' }
    if (router.currentRoute.value.path !== target) {
      if (await router.push(target)) return { success: false, message: '导航被页面取消' }
      await nextTick()
    }
    const handler = handlers.get(pageId) || await waitForAssistantExecutor(pageId, target, router)
    if (router.currentRoute.value.path !== target) return { success: false, code: 'stale_context', message: '已离开目标页面，请重新准备操作', target }
    if (!handler) return { success: false, code: 'target_not_ready', message: '目标页面尚未就绪，请稍后重试或重新准备', target }
    const changed = context?.route === target ? contextPolicy(action, context as unknown as Record<string, unknown>, useAssistantContextStore().current as unknown as Record<string, unknown>) : null
    if (changed) return { success: false, code: 'stale_context', message: changed, target }
    const result = await handler(action)
    if (router.currentRoute.value.path !== target) return { success: false, code: 'stale_context', message: '执行期间已离开目标页面，结果请返回目标页核验', target }
    return { ...result, target }
  } catch (e) { return { success: false, message: e instanceof Error ? e.message : '页面操作失败' } }
}
