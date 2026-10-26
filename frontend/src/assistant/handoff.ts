import { ref } from 'vue'
import type { Router } from 'vue-router'
import type { AssistantContext } from '@/stores/assistantContext'

export interface AssistantHandoff { query: string; context: AssistantContext | null; operationId: string }
export const mainAssistantDraft = ref<AssistantHandoff | null>(null)
export async function handoffToMainAssistant(query: string, context: AssistantContext | null, router: Router, operationId: string = crypto.randomUUID()) {
  if (!query.trim()) throw new Error('交接问题不能为空')
  const draft = { query: query.trim(), context: context ? JSON.parse(JSON.stringify(context)) : null, operationId }
  const failure = router.currentRoute.value.path === '/chat' ? undefined : await router.push('/chat')
  if (failure) throw new Error('主助手导航未完成')
  mainAssistantDraft.value = draft
}
export function formatHandoffDraft(draft: AssistantHandoff) {
  const c = draft.context
  return `${draft.query}\n\n[来源：系统助手；操作 ${draft.operationId}${c ? `；页面 ${c.route}；厂站 ${c.plant || '未选择'}；指标 ${c.indicator || '未选择'}；范围 ${typeof c.range === 'object' ? JSON.stringify(c.range) : c.range || '未指定'}；数据来源 ${c.source}；时效 ${c.freshness || '未核验'}` : ''}]`
}
