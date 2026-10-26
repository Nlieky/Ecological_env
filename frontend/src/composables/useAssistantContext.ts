import { onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAssistantContextStore, type ContextInput } from '@/stores/assistantContext'
import { registerAssistantExecutor, type AssistantPageExecutor } from '@/assistant/executor'

let ownerSequence = 0
/** Each page supplies only structured, explicitly selected display state. */
export function useAssistantContext(getContext: () => Omit<ContextInput, 'route'>, executor?: AssistantPageExecutor) {
  const route = useRoute()
  const store = useAssistantContextStore()
  const owner = `page-${++ownerSequence}`
  const stop = watch(() => ({ ...getContext(), route: route.path }), value => store.register(owner, value), { deep: true, immediate: true })
  const clearExecutor = executor ? registerAssistantExecutor(getContext().pageId, executor) : undefined
  onBeforeUnmount(() => { stop(); clearExecutor?.(); store.clear(owner) })
}
