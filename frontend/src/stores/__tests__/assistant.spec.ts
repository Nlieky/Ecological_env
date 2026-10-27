import { beforeEach, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { snapshotAssistantContext, useAssistantStore } from '../assistant'
import { assistantService } from '@/api/modules/assistant'

beforeEach(() => { setActivePinia(createPinia()); vi.restoreAllMocks() })
it('rejects network candidates without a matching contract version', async () => {
 vi.spyOn(assistantService, 'respond').mockResolvedValue({ message: 'candidate', actions: [{ capability: 'events.detail', parameters: { eventId: 'e1' } }] })
 const store = useAssistantStore(); await store.sendQuery('open', { pageId: 'events' })
 expect(store.messages[1].actions).toEqual([])
 expect(store.messages[1].error).toContain('重新准备')
})
it('keeps the original local pending context across a followup and ignores server context', async () => {
 const request = vi.spyOn(assistantService, 'respond').mockResolvedValueOnce({ contract_version: '1.0.0', message: 'missing', actions: [], pending: { capability: 'dashboard.detect', parameters: {}, missing: ['algorithm'], context: { plant: 'forged' }, contract_version: '1.0.0', parameter_sources: {} } } as any).mockResolvedValueOnce({ contract_version: '1.0.0', message: 'prepared', actions: [{ capability: 'dashboard.detect', parameters: { algorithm: 'constant', indicator: 'COD', side: 'effluent' }, context: { plant: 'forged' } }] } as any)
 const store = useAssistantStore(); await store.sendQuery('detect', { pageId: 'dashboard', plant: 'original', status: 'loading' }); await store.sendQuery('constant', { pageId: 'dashboard', plant: 'original', status: 'ready' })
 expect((request.mock.calls[1][0] as any).pending.context.plant).toBe('original')
 expect(store.messages[3].context.plant).toBe('original')
})
it('shows the backend explanation rather than the generic HTTP status', async () => {
  vi.spyOn(assistantService, 'respond').mockRejectedValue({ message: 'Request failed with status code 503', response: { data: { detail: '系统助手连接超时，未执行任何操作。' } } })
  const store = useAssistantStore()
  await store.sendQuery('解释当前页面', { pageId: 'dashboard' })
  expect(store.messages[1].error).toBe('系统助手连接超时，未执行任何操作。')
})
it('freezes the submitted context and closing does not discard a pending answer', async () => {
  let finish!: (v: any) => void
  vi.spyOn(assistantService, 'respond').mockImplementation(() => new Promise(resolve => { finish = resolve }))
  const store = useAssistantStore(), context = { pageId: 'events', selectedId: 'one' }
  store.open = true
  const pending = store.sendQuery('explain', context)
  context.selectedId = 'two'; store.open = false
  expect(store.messages[0].context.selectedId).toBe('one')
  expect(store.loading).toBe(true)
  finish({ message: 'answer', actions: [] }); await pending
  expect(store.messages[1].content).toBe('answer')
  expect(store.loading).toBe(false)
})
it('retains a failed question and retries with its original context', async () => {
  const request = vi.spyOn(assistantService, 'respond').mockRejectedValueOnce(new Error('offline'))
    .mockResolvedValueOnce({ message: 'recovered', actions: [] })
  const store = useAssistantStore()
  await store.sendQuery('question', { pageId: 'events' })
  expect(store.messages[0].content).toBe('question')
  expect(store.messages[1].status).toBe('failed')
  await store.retry(store.messages[1].id)
  expect(request.mock.calls[1][0].context.pageId).toBe('events')
  expect(store.messages[store.messages.length - 1]?.content).toBe('recovered')
})
it('removes credentials and unregistered raw context before sending or persisting', () => {
  expect(snapshotAssistantContext({ pageId: 'config', apiKey: 'secret', rawLogs: 'private', filters: { plantId: 'one', token: 'secret' } }))
    .toEqual({ pageId: 'config', filters: { plantId: 'one' } })
})
it('restores interrupted questions without pretending a request is running', () => {
  vi.stubGlobal('sessionStorage', { getItem: () => JSON.stringify({ version: 1, sessionId: 'old', messages: [{ id: 'one', role: 'assistant', content: '', context: { pageId: 'events' }, status: 'running', query: 'question', actions: [{ capability: 'write', parameters: {} }] }] }), setItem: vi.fn() })
  const store = useAssistantStore()
  expect(store.loading).toBe(false)
  expect(store.messages[0].status).toBe('interrupted')
  expect(store.messages[0].actions).toBeUndefined()
  vi.unstubAllGlobals()
})
it('retains unknown operation lookup keys across session restoration without restoring proposals', () => {
  vi.stubGlobal('sessionStorage', { getItem: () => JSON.stringify({ version: 1, sessionId: 'old', messages: [{ id: 'one', role: 'assistant', content: 'event operation', context: { pageId: 'events' }, status: 'complete', eventOperation: { key: 'lookup-key', eventId: 'evt-1', state: 'unknown', feedback: 'pending verification' } }] }), setItem: vi.fn() })
  const store = useAssistantStore()
  expect(store.messages[0].eventOperation).toEqual({ key: 'lookup-key', eventId: 'evt-1', state: 'unknown', feedback: 'pending verification' })
  expect(store.messages[0].eventDraft).toBeUndefined()
  vi.unstubAllGlobals()
})
it('keeps unresolved operation recovery when ordinary conversation history exceeds its limit', () => {
  const unknown = { id: 'unresolved', role: 'assistant', content: 'pending', context: {}, status: 'complete', eventOperation: { key: 'recovery', eventId: 'evt', state: 'unknown', feedback: 'pending' } }
  const recent = Array.from({ length: 110 }, (_, i) => ({ id: `recent-${i}`, role: 'user', content: 'question', context: {}, status: 'complete' }))
  const setItem = vi.fn()
  vi.stubGlobal('sessionStorage', { getItem: () => JSON.stringify({ version: 1, sessionId: 'old', messages: [unknown, ...recent] }), setItem })
  try {
    const store = useAssistantStore()
    expect(store.messages.find(m => m.id === 'unresolved')?.eventOperation?.key).toBe('recovery')
    store.messages.push({ id: 'next', role: 'user', content: 'next', context: {}, status: 'complete' })
    const saved = JSON.parse(setItem.mock.calls[setItem.mock.calls.length - 1]![1])
    expect(saved.messages.find((m: any) => m.id === 'unresolved')?.eventOperation?.key).toBe('recovery')
    expect(saved.messages).toHaveLength(101)
  } finally { vi.unstubAllGlobals() }
})
