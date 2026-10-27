import { computed, ref } from 'vue'

type Value = string | boolean | number
interface Item { key: string; value: Value; type?: string }
export interface SaveAcknowledgement { success: boolean; applied_keys: string[]; restart_needed: boolean }
export function requireSuccess(result: { success?: boolean }) {
  if (result.success !== true) throw new Error('服务器未确认保存成功')
}
export function useConfigDraft() {
  const draft = ref<Record<string, Value>>({})
  const baseline = ref<Record<string, Value>>({})
  const secrets = new Set<string>()
  const restartHint = ref(false)
  function initialize(items: Item[]) {
    secrets.clear(); draft.value = {}; baseline.value = {}
    items.forEach(item => {
      if (item.type === 'secret') secrets.add(item.key)
      draft.value[item.key] = baseline.value[item.key] = item.type === 'secret' ? '' : item.value
    })
  }
  function payload() {
    return Object.fromEntries(Object.entries(draft.value).filter(([key, value]) =>
      secrets.has(key) ? String(value).trim() !== '' : value !== baseline.value[key]))
  }
  const dirty = computed(() => Object.entries(draft.value).some(([key, value]) => value !== baseline.value[key]))
  function acknowledge(sent: Record<string, Value>, result: SaveAcknowledgement) {
    requireSuccess(result)
    result.applied_keys.forEach(key => {
      if (!(key in sent)) return
      if (secrets.has(key)) {
        baseline.value[key] = ''
        if (draft.value[key] === sent[key]) draft.value[key] = ''
      } else baseline.value[key] = sent[key]
    })
    restartHint.value ||= result.restart_needed
  }
  return { draft, baseline, dirty, restartHint, initialize, payload, acknowledge }
}
