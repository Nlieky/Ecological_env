import { getCurrentScope, onScopeDispose, ref, shallowRef } from 'vue'
import { requestGate } from './dashboardData'

export type AsyncViewState = 'idle' | 'initial-loading' | 'refreshing' | 'ready' | 'empty' | 'error' | 'stale'

/** Latest request wins. Failures are consumed and exposed as safe presentation text. */
export function useAsyncView<T>(loader: () => Promise<T>, options: { initialData?: T; isEmpty?: (data: T) => boolean } = {}) {
  const data = shallowRef<T | undefined>(options.initialData)
  const state = ref<AsyncViewState>('idle')
  const error = ref<string | null>(null)
  const gate = requestGate()
  async function run() {
    const id = gate.begin()
    if (id === null) return
    state.value = data.value === undefined ? 'initial-loading' : 'refreshing'
    error.value = null
    try {
      const result = await loader()
      if (!gate.current(id)) return
      data.value = result
      state.value = options.isEmpty?.(result) ? 'empty' : 'ready'
    } catch {
      if (!gate.current(id)) return
      error.value = '数据加载失败，请稍后重试。'
      state.value = 'error'
    }
  }
  function dispose() { gate.dispose() }
  if (getCurrentScope()) onScopeDispose(dispose)
  return { data, state, error, run, refresh: run, retry: run, dispose }
}
