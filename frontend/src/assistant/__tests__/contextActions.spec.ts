import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAssistantContextStore } from '@/stores/assistantContext'
import { validateAssistantAction } from '@/assistant/capabilities'
import { executeAssistantAction, registerAssistantExecutor, waitForAssistantExecutor } from '@/assistant/executor'
import { createRouter, createMemoryHistory } from 'vue-router'

describe('assistant context and capability boundary', () => {
  beforeEach(() => setActivePinia(createPinia()))
  it('waits for delayed target registration and cancels on route leave or timeout', async () => {
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/events', component: {} }, { path: '/logs', component: {} }] })
    await router.push('/events')
    const waiting = waitForAssistantExecutor('events', '/events', router, 100)
    const handler = async () => ({ success: true, message: 'done' })
    const cleanup = registerAssistantExecutor('events', handler)
    expect(await waiting).toBe(handler); cleanup()
    const leaving = waitForAssistantExecutor('events', '/events', router, 100)
    await router.push('/logs'); expect(await leaving).toBeNull()
    await router.push('/events'); vi.useFakeTimers()
    const timeout = waitForAssistantExecutor('events', '/events', router, 10)
    await vi.advanceTimersByTimeAsync(10); expect(await timeout).toBeNull(); vi.useRealTimers()
  })
  it.each(['plant', 'range', 'source'])('rejects changed window %s and original unready snapshots', async field => {
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/dashboard', component: {} }] }); await router.push('/dashboard')
    const store = useAssistantContextStore(), context = { route: '/dashboard', pageId: 'dashboard', plant: 'a', source: 'real', range: { start: '2026-01-01', end: '2026-01-02' }, status: 'ready' as const }
    store.register('one', context); const frozen = store.snapshot()
    store.register('one', { ...context, [field]: field === 'range' ? { start: '2026-02-01', end: '2026-02-02' } : 'changed' })
    const action = { capability: 'dashboard.detect', parameters: { algorithm: 'constant', indicator: 'COD', side: 'effluent' } }
    expect((await executeAssistantAction(action, frozen, router)).success).toBe(false)
    store.register('one', { ...context, status: 'loading' }); const unready = store.snapshot(); store.register('one', context)
    expect((await executeAssistantAction(action, unready, router)).message).toContain('就绪')
  })
  it('freezes a sanitized snapshot and clears only the owning page', () => {
    const store = useAssistantContextStore()
    store.register('one', { route: '/events', pageId: 'events', objectId: 'e1', filters: { status: 'pending', api_key: 'secret' } })
    const snapshot = store.snapshot()!
    store.register('two', { route: '/logs', pageId: 'logs' })
    store.clear('one')
    expect(store.current?.pageId).toBe('logs')
    expect(snapshot.pageId).toBe('events')
    expect(snapshot.filters).toEqual({ status: 'pending' })
    expect(Object.isFrozen(snapshot.filters)).toBe(true)
  })
  it('rejects unknown capabilities and sensitive draft fields', () => {
    expect(validateAssistantAction({ capability: 'restart', parameters: {} }).success).toBe(false)
    expect(validateAssistantAction({ capability: 'strategy.draft', parameters: { api_key: 'x' } }).success).toBe(false)
    expect(validateAssistantAction({ capability: 'strategy.draft', parameters: { language_constraint: 'zh', conclusion_first: true } }).success).toBe(true)
    expect(validateAssistantAction({ capability: 'logs.filter', parameters: { module: 'frontend' } }).success).toBe(false)
    expect(validateAssistantAction({ capability: 'navigate', parameters: { pageId: '__proto__' } }).success).toBe(false)
    expect(validateAssistantAction({ capability: 'dashboard.detect', parameters: { algorithm: 'constant', indicator: 'pH', side: 'effluent' } }).success).toBe(true)
    expect(validateAssistantAction({ capability: 'dashboard.detect', parameters: { algorithm: 'shell', indicator: 'pH', side: 'effluent' } }).success).toBe(false)
  })
  it('rejects responses prepared for a previous object', async () => {
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/dashboard', component: {} }] })
    await router.push('/dashboard')
    const store = useAssistantContextStore()
    store.register('one', { route: '/dashboard', pageId: 'dashboard', objectId: 'e1' })
    const frozen = store.snapshot()
    store.register('one', { route: '/dashboard', pageId: 'dashboard', objectId: 'e2' })
    let called = false
    const cleanup = registerAssistantExecutor('dashboard', async () => { called = true; return { success: true, message: 'ok' } })
    const result = await executeAssistantAction({ capability: 'dashboard.range', parameters: { range: '6h' } }, frozen, router)
    expect(result.success).toBe(false)
    expect(called).toBe(false)
    cleanup()
  })
  it('navigates to an explicit destination after the source page refreshes', async () => {
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/dashboard', component: {} }, { path: '/events', component: {} }] })
    await router.push('/dashboard')
    const store = useAssistantContextStore()
    store.register('one', { route: '/dashboard', pageId: 'dashboard', status: 'loading' })
    const frozen = store.snapshot()
    store.register('one', { route: '/dashboard', pageId: 'dashboard', status: 'ready', plant: 'loaded plant' })
    const result = await executeAssistantAction({ capability: 'navigate', parameters: { pageId: 'events' } }, frozen, router)
    expect(result.success).toBe(true)
    expect(router.currentRoute.value.path).toBe('/events')
  })
  it('allows window detection after an unrelated source status refresh', async () => {
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/dashboard', component: {} }] })
    await router.push('/dashboard')
    const store = useAssistantContextStore()
    const context = { route: '/dashboard', pageId: 'dashboard', plant: 'plant-a', source: 'real', range: { start: '2026-07-01 00:00:00', end: '2026-07-02 00:00:00' }, status: 'ready' as const }
    store.register('one', context)
    const frozen = store.snapshot()
    store.register('one', { ...context, freshness: 'historical' })
    const handler = registerAssistantExecutor('dashboard', async () => ({ success: true, message: 'done' }))
    try {
      const result = await executeAssistantAction({ capability: 'dashboard.detect', parameters: { algorithm: 'iforest', indicator: 'TN', side: 'influent' } }, frozen, router)
      expect(result.success).toBe(true)
    } finally { handler() }
  })
  it('explains which bound field changed rather than rejecting every revision', async () => {
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/dashboard', component: {} }] })
    await router.push('/dashboard')
    const store = useAssistantContextStore()
    const context = { route: '/dashboard', pageId: 'dashboard', plant: 'plant-a', source: 'real', range: { start: '2026-07-01', end: '2026-07-02' }, status: 'ready' as const }
    store.register('one', context)
    const frozen = store.snapshot()
    store.register('one', { ...context, source: 'simulated' })
    const result = await executeAssistantAction({ capability: 'dashboard.detect', parameters: { algorithm: 'iforest', indicator: 'COD', side: 'effluent' } }, frozen, router)
    expect(result.success).toBe(false)
    expect(result.message).toContain('来源')
  })
  it('allows explicit filters after the source selection changes', async () => {
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/events', component: {} }] })
    await router.push('/events')
    const store = useAssistantContextStore()
    store.register('one', { route: '/events', pageId: 'events', objectId: 'old' })
    const frozen = store.snapshot()
    store.register('one', { route: '/events', pageId: 'events', objectId: 'new' })
    const handler = registerAssistantExecutor('events', async () => ({ success: true, message: 'filtered' }))
    try {
      const result = await executeAssistantAction({ capability: 'events.filter', parameters: { status: 'processing' } }, frozen, router)
      expect(result.success).toBe(true)
    } finally { handler() }
  })
})
