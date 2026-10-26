import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface AssistantContext {
  route: string
  pageId: string
  objectId: string | null
  plant: string | null
  indicator: string | null
  range: string | { start: string; end: string } | null
  source: string
  freshness: string | null
  filters: Record<string, string | number | boolean | null>
  status: 'loading' | 'ready' | 'empty' | 'error' | 'stale'
  actions: string[]
  revision: number
}
export type ContextInput = Pick<AssistantContext, 'route' | 'pageId'> & Partial<Omit<AssistantContext, 'route' | 'pageId' | 'revision'>>
const allowedFilters = new Set(['status', 'severity', 'page', 'module', 'tab', 'entity', 'side', 'search', 'dirty'])
export const useAssistantContextStore = defineStore('assistantContext', () => {
  const current = ref<AssistantContext | null>(null)
  let owner: string | null = null
  let revision = 0
  function register(key: string, input: ContextInput) {
    const next = {
      route: input.route.split('?')[0]!, pageId: input.pageId,
      objectId: input.objectId ?? null, plant: input.plant ?? null, indicator: input.indicator ?? null,
      range: input.range ?? null, source: input.source ?? '未核验', freshness: input.freshness ?? null,
      filters: Object.fromEntries(Object.entries(input.filters ?? {}).filter(([k, v]) => allowedFilters.has(k) && (v === null || ['string', 'number', 'boolean'].includes(typeof v)))),
      status: input.status ?? 'ready', actions: [...(input.actions ?? [])],
    }
    const old = current.value && { ...current.value, revision: undefined }
    if (owner === key && JSON.stringify(old) === JSON.stringify({ ...next, revision: undefined })) return
    owner = key
    current.value = { ...next, revision: ++revision }
  }
  function clear(key: string) { if (owner === key) { current.value = null; owner = null; revision++ } }
  function snapshot(): AssistantContext | null {
    if (!current.value) return null
    const copy = JSON.parse(JSON.stringify(current.value)) as AssistantContext
    Object.freeze(copy.filters); Object.freeze(copy.actions)
    if (typeof copy.range === 'object' && copy.range) Object.freeze(copy.range)
    return Object.freeze(copy)
  }
  return { current, register, clear, snapshot }
})
