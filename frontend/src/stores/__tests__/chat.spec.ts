import { beforeEach, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { queryService } from '@/api/modules/query'
import { conversationsService } from '@/api/modules/conversations'
import { useChatStore } from '../chat'

beforeEach(() => { setActivePinia(createPinia()); vi.restoreAllMocks(); vi.spyOn(conversationsService, 'list').mockResolvedValue({ data: { conversations: [] } } as never) })
it('retains partial output with separate error and measured timing', async () => {
  let callbacks: any
  vi.spyOn(queryService, 'executeStream').mockImplementation((_q, c) => { callbacks = c; return new AbortController() })
  const store = useChatStore()
  const pending = store.sendQuery('q')
  callbacks.onProgress({ subagent: 'anomaly-detection', stage: 'start' })
  callbacks.onProgress({ subagent: 'anomaly-detection', stage: 'done' })
  callbacks.onDelta('partial'); callbacks.onError('lost')
  await pending
  expect(store.messages[1].content).toBe('partial')
  expect((store.messages[1] as any).error).toBe('lost')
  expect((store.messages[1] as any).elapsedMs).toBeGreaterThanOrEqual(0)
  expect((store.messages[1] as any).stageDurations[0].elapsedMs).toBeGreaterThanOrEqual(0)
  expect(store.loading).toBe(false)
})
it('invalidates old stream callbacks when cleared and settles the old send', async () => {
  let callbacks: any
  const ctrl = new AbortController()
  vi.spyOn(queryService, 'executeStream').mockImplementation((_q, c) => { callbacks = c; return ctrl })
  const store = useChatStore(), pending = store.sendQuery('q')
  store.clearMessages()
  callbacks.onDone('old', 'old-session')
  await pending
  expect(ctrl.signal.aborted).toBe(true)
  expect(store.sessionId).toBeUndefined()
  expect(store.loading).toBe(false)
})
it('ignores a deferred detail after a new selection', async () => {
  let finish: any
  vi.spyOn(conversationsService, 'detail').mockImplementation(() => new Promise((r) => { finish = r }))
  const store = useChatStore(), pending = store.openConversation('old')
  store.clearMessages()
  finish({ data: { id: 'old', messages: [] } }); await pending
  expect(store.sessionId).toBeUndefined()
})
it('keeps server queue and turn measurements on the completed message', async () => {
  let callbacks: any
  vi.spyOn(queryService, 'executeStream').mockImplementation((_q, c) => { callbacks = c; return new AbortController() })
  const store = useChatStore(), pending = store.sendQuery('q')
  callbacks.onDone('answer', 's', { queueElapsedMs: 10, turnElapsedMs: 20 })
  await pending
  expect((store.messages[1] as any).queueElapsedMs).toBe(10)
  expect((store.messages[1] as any).turnElapsedMs).toBe(20)
})
it('blocks sending while conversation creation is pending', async () => {
  let finish: any
  vi.spyOn(conversationsService, 'create').mockImplementation(() => new Promise((r) => { finish = r }))
  const execute = vi.spyOn(queryService, 'executeStream')
  const store = useChatStore(), pending = store.startNewConversation()
  expect(store.loading).toBe(true)
  await store.sendQuery('too early')
  expect(execute).not.toHaveBeenCalled()
  finish({ data: { id: 'new' } }); await pending
  expect(store.sessionId).toBe('new')
  expect(store.loading).toBe(false)
})
it('unlocks after failed creation', async () => {
  vi.spyOn(conversationsService, 'create').mockRejectedValue(new Error('failed'))
  const store = useChatStore()
  await store.startNewConversation()
  expect(store.loading).toBe(false)
  expect(store.sessionId).toBeUndefined()
})
it('an older creation cannot replace a newer selection or unlock its loading', async () => {
  let finishCreate: any, finishDetail: any
  vi.spyOn(conversationsService, 'create').mockImplementation(() => new Promise((r) => { finishCreate = r }))
  vi.spyOn(conversationsService, 'detail').mockImplementation(() => new Promise((r) => { finishDetail = r }))
  const store = useChatStore(), creating = store.startNewConversation()
  const selecting = store.openConversation('selected')
  finishCreate({ data: { id: 'old-create' } }); await creating
  expect(store.sessionId).toBeUndefined()
  expect(store.loading).toBe(true)
  finishDetail({ data: { id: 'selected', messages: [] } }); await selecting
  expect(store.sessionId).toBe('selected')
  expect(store.loading).toBe(false)
})

it('keeps a conversation stream alive when another conversation is opened', async () => {
  let callbacks: any
  const ctrl = new AbortController()
  vi.spyOn(queryService, 'executeStream').mockImplementation((_q, c) => { callbacks = c; return ctrl })
  vi.spyOn(conversationsService, 'detail').mockImplementation(async (id) => ({
    data: { id, title: id, message_count: 0, messages: [] },
  } as never))
  const store = useChatStore()
  await store.openConversation('a')
  const pending = store.sendQuery('question-a')
  await store.openConversation('b')

  expect(ctrl.signal.aborted).toBe(false)
  expect(store.conversationStatus('a')).toBe('running')
  callbacks.onDelta('answer-a')
  callbacks.onDone('answer-a', 'a')
  await pending

  await store.openConversation('a')
  expect(store.messages[store.messages.length - 1]?.content).toBe('answer-a')
  expect(store.conversationStatus('a')).toBe('completed')
})

it('keeps simultaneous conversation streams and messages isolated', async () => {
  const streams: Record<string, any> = {}
  vi.spyOn(queryService, 'executeStream').mockImplementation((q, c) => {
    streams[q.session_id || ''] = c
    return new AbortController()
  })
  vi.spyOn(conversationsService, 'detail').mockImplementation(async (id) => ({
    data: { id, title: id, message_count: 0, messages: [] },
  } as never))
  const store = useChatStore()
  await store.openConversation('a')
  const a = store.sendQuery('question-a')
  await store.openConversation('b')
  const b = store.sendQuery('question-b')

  streams.a.onDelta('A')
  streams.b.onDelta('B')
  expect(store.conversationStatus('a')).toBe('running')
  expect(store.conversationStatus('b')).toBe('running')
  expect(store.messages[store.messages.length - 1]?.content).toBe('B')

  streams.a.onDone('A done', 'a')
  streams.b.onDone('B done', 'b')
  await Promise.all([a, b])
  await store.openConversation('a')
  expect(store.messages[store.messages.length - 1]?.content).toBe('A done')
  await store.openConversation('b')
  expect(store.messages[store.messages.length - 1]?.content).toBe('B done')
})
