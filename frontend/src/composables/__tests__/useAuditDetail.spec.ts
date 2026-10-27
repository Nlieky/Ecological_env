import { describe, expect, it } from 'vitest'
import { useAuditDetail } from '../useAuditDetail'
import type { ConversationDetail, SessionTrace } from '@/api/types/api.types'

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (error: unknown) => void
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
const conversation = (id: string): ConversationDetail => ({ id, title: id, message_count: 0, messages: [] })
const evidence = (id: string, recorded = true): SessionTrace => ({
  session_id: id, api_call: null, master_decision: recorded ? { id } : null,
  subagent_executions: [], operator_calls: [], llm_calls: [],
})

describe('audit detail retrieval', () => {
  it('does not overwrite selected B when delayed A finishes', async () => {
    const a = deferred<{ data: ConversationDetail }>()
    const state = useAuditDetail({
      detail: id => id === 'A' ? a.promise : Promise.resolve({ data: conversation(id) }),
      trace: id => Promise.resolve(evidence(id)),
    })
    const first = state.select('A')
    await state.select('B')
    a.resolve({ data: conversation('A') })
    await first
    expect(state.selectedId.value).toBe('B')
    expect(state.detail.value?.id).toBe('B')
    expect(state.trace.value?.session_id).toBe('B')
  })

  it('does not apply stale failures or finish loading a newer request', async () => {
    const a = deferred<{ data: ConversationDetail }>()
    const b = deferred<{ data: ConversationDetail }>()
    const state = useAuditDetail({ detail: id => id === 'A' ? a.promise : b.promise, trace: id => Promise.resolve(evidence(id)) })
    const first = state.select('A')
    const second = state.select('B')
    a.reject(new Error('old error'))
    await first
    expect(state.detailError.value).toBeNull()
    expect(state.loadingDetail.value).toBe(true)
    b.resolve({ data: conversation('B') })
    await second
    expect(state.detail.value?.id).toBe('B')
  })

  it('preserves conversation while displaying a trace request failure', async () => {
    const trace = deferred<SessionTrace>()
    const state = useAuditDetail({ detail: id => Promise.resolve({ data: conversation(id) }), trace: () => trace.promise })
    const pending = state.select('A')
    await Promise.resolve()
    expect(state.detail.value?.id).toBe('A')
    expect(state.loadingDetail.value).toBe(false)
    expect(state.loadingTrace.value).toBe(true)
    trace.reject(new Error('offline'))
    await pending
    expect(state.detail.value?.id).toBe('A')
    expect(state.traceError.value).toBe('追溯加载失败，请重试')
    expect(state.trace.value).toBeNull()
  })

  it('recognizes an empty successful trace without calling it an error', async () => {
    const state = useAuditDetail({ detail: id => Promise.resolve({ data: conversation(id) }), trace: id => Promise.resolve(evidence(id, false)) })
    await state.select('A')
    expect(state.trace.value).toBeNull()
    expect(state.traceError.value).toBeNull()
  })

  it('keeps operator-only evidence rather than classifying it as empty', async () => {
    const trace = { ...evidence('A', false), operator_calls: [{ id: 1 }] }
    const state = useAuditDetail({ detail: id => Promise.resolve({ data: conversation(id) }), trace: () => Promise.resolve(trace) })
    await state.select('A')
    expect(state.trace.value?.operator_calls).toHaveLength(1)
  })

  it('clears previous detail failures on a successful retry', async () => {
    let failed = true
    const state = useAuditDetail({
      detail: id => failed ? Promise.reject(new Error('offline')) : Promise.resolve({ data: conversation(id) }),
      trace: id => Promise.resolve(evidence(id)),
    })
    await state.select('A')
    expect(state.detailError.value).toBe('会话加载失败，请重试')
    failed = false
    await state.select('A')
    expect(state.detailError.value).toBeNull()
    expect(state.detail.value?.id).toBe('A')
  })

  it('invalidates pending state updates on dispose', async () => {
    const pending = deferred<{ data: ConversationDetail }>()
    const state = useAuditDetail({ detail: () => pending.promise, trace: id => Promise.resolve(evidence(id)) })
    const request = state.select('A')
    state.dispose()
    pending.resolve({ data: conversation('A') })
    await request
    expect(state.detail.value).toBeNull()
    expect(state.trace.value).toBeNull()
  })

  it('ignores a delayed list callback trying to select after disposal', async () => {
    const state = useAuditDetail({ detail: id => Promise.resolve({ data: conversation(id) }), trace: id => Promise.resolve(evidence(id)) })
    state.dispose()
    await state.select('A')
    expect(state.selectedId.value).toBe('')
    expect(state.detail.value).toBeNull()
  })

  it('does not apply an old trace failure to the newly selected session', async () => {
    const oldTrace = deferred<SessionTrace>()
    const state = useAuditDetail({
      detail: id => Promise.resolve({ data: conversation(id) }),
      trace: id => id === 'A' ? oldTrace.promise : Promise.resolve(evidence(id)),
    })
    const first = state.select('A')
    await state.select('B')
    oldTrace.reject(new Error('old trace failure'))
    await first
    expect(state.traceError.value).toBeNull()
    expect(state.trace.value?.session_id).toBe('B')
  })

  it('does not finish a newer trace load when an older trace succeeds', async () => {
    const a = deferred<SessionTrace>()
    const b = deferred<SessionTrace>()
    const state = useAuditDetail({ detail: id => Promise.resolve({ data: conversation(id) }), trace: id => id === 'A' ? a.promise : b.promise })
    const first = state.select('A')
    const second = state.select('B')
    a.resolve(evidence('A'))
    await first
    expect(state.trace.value).toBeNull()
    expect(state.loadingTrace.value).toBe(true)
    b.resolve(evidence('B'))
    await second
    expect(state.trace.value?.session_id).toBe('B')
    expect(state.loadingTrace.value).toBe(false)
  })

  it('clears previous trace error on a successful retry', async () => {
    let failed = true
    const state = useAuditDetail({
      detail: id => Promise.resolve({ data: conversation(id) }),
      trace: id => failed ? Promise.reject(new Error('offline')) : Promise.resolve(evidence(id)),
    })
    await state.select('A')
    expect(state.traceError.value).not.toBeNull()
    failed = false
    await state.select('A')
    expect(state.traceError.value).toBeNull()
    expect(state.trace.value?.session_id).toBe('A')
  })

  it('reports an HTTP 200 failure envelope rather than a blank selection', async () => {
    const state = useAuditDetail({
      detail: async () => ({ success: false, data: null }),
      trace: id => Promise.resolve(evidence(id)),
    })
    await state.select('missing')
    expect(state.detail.value).toBeNull()
    expect(state.detailError.value).toBe('会话加载失败，请重试')
  })
})
