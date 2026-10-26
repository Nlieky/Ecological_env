import { describe, it, expect } from 'vitest'
import { useEventCenter } from '../useEventCenter'
import type { AlertEvent } from '@/api/types/api.types'

const event = (id: string, status: AlertEvent['status'] = 'pending') => ({ id, status, evidence: [], violationTypes: [] } as unknown as AlertEvent)
function deferred<T>() { let resolve!: (value: T) => void; let reject!: (reason: unknown) => void; const promise = new Promise<T>((a, b) => { resolve = a; reject = b }); return { promise, resolve, reject } }
const node = async () => ({ neighbors: {} })
describe('event center confirmed state', () => {
  it('synchronizes confirmed save when the same event is reopened before completion', async () => {
    const saved = deferred<AlertEvent>()
    const state = useEventCenter({ list: async () => ({ data: [event('a', 'resolved')], total: 1 }), updateStatus: () => saved.promise, node })
    const a = event('a'); state.events.value = [a]; state.openDetail(a)
    const save = state.saveStatus('resolved')
    state.openDetail(event('b')); state.openDetail(a)
    saved.resolve({ ...event('a', 'resolved'), action: 'confirmed action' }); await save
    expect(state.current.value?.status).toBe('resolved')
    expect(state.current.value?.action).toBe('confirmed action')
    expect(state.allowedStatuses.value).toEqual(['resolved'])
    expect(state.saving.value).toBe(false)
  })
  it('shows list failure independently from empty and clears it on retry', async () => {
    let attempts = 0
    const state = useEventCenter({ list: async () => { if (!attempts++) throw Error('offline'); return { data: [], total: 0 } }, updateStatus: async () => event('a'), node })
    await state.load(); expect(state.listError.value).toContain('offline'); expect(state.loading.value).toBe(false)
    await state.load(); expect(state.listError.value).toBe(''); expect(state.events.value).toEqual([])
  })
  it('refreshes current filters after confirmed full response and keeps refresh failures separate', async () => {
    const saved = deferred<AlertEvent>(); const params: unknown[] = []
    const state = useEventCenter({ list: async p => { params.push(p); throw Error('refresh failed') }, updateStatus: () => saved.promise, node })
    state.openDetail(event('a')); const save = state.saveStatus('resolved'); state.status.value = 'processing'
    saved.resolve({ ...event('a', 'resolved'), action: 'confirmed action' }); await save
    expect(state.current.value?.action).toBe('confirmed action'); expect(state.saveError.value).toBe(''); expect(state.listError.value).toContain('refresh failed'); expect(params[0]).toMatchObject({ status: 'processing' })
  })
  it('ignores relation response from a previous selection and after disposal', async () => {
    const old = deferred<{ neighbors: { plant: { id: string; label: string }[] } }>()
    const state = useEventCenter({ list: async () => ({ data: [], total: 0 }), updateStatus: async () => event('a'), node: () => old.promise })
    state.openDetail(event('a')); const request = state.loadRelation(); state.openDetail(event('b'))
    old.resolve({ neighbors: { plant: [{ id: 'old', label: 'old' }] } }); await request; expect(state.caseLink.value).toBeNull()
    state.dispose(); await state.loadRelation(); expect(state.current.value).toBeNull()
  })
  it('keeps latest list and resets filters to page one', async () => {
    const a = deferred<{ data: AlertEvent[]; total: number }>(); const b = deferred<{ data: AlertEvent[]; total: number }>()
    const calls: unknown[] = []; const queue = [a, b]
    const state = useEventCenter({ list: p => { calls.push(p); return queue.shift()!.promise }, updateStatus: async () => event('a'), node })
    state.page.value = 3; const first = state.load(); state.severity.value = 'high'; const second = state.filterChanged()
    b.resolve({ data: [event('b')], total: 1 }); await second; a.resolve({ data: [event('a')], total: 50 }); await first
    expect(state.events.value[0]?.id).toBe('b'); expect(state.page.value).toBe(1); expect(calls[1]).toMatchObject({ page: 1, severity: 'high' })
  })
  it('copies detail, bounds duplicate saves, and isolates selection during save', async () => {
    const save = deferred<AlertEvent>(); let saves = 0
    const state = useEventCenter({ list: async () => ({ data: [], total: 0 }), updateStatus: () => { saves++; return save.promise }, node })
    const a = event('a'); state.events.value = [a]; state.openDetail(a); const pending = state.saveStatus('resolved'); await state.saveStatus('processing')
    expect(a.status).toBe('pending'); expect(state.current.value?.status).toBe('pending'); expect(saves).toBe(1)
    state.openDetail(event('b')); expect(state.saving.value).toBe(false); save.resolve(event('a', 'resolved')); await pending
    expect(state.current.value?.id).toBe('b'); expect(state.current.value?.status).toBe('pending'); expect(state.saveError.value).toBe('')
  })
  it('preserves failed save and limits terminal transitions', async () => {
    const state = useEventCenter({ list: async () => ({ data: [], total: 0 }), updateStatus: async () => { throw Error('rejected') }, node })
    state.openDetail(event('a')); await state.saveStatus('resolved'); expect(state.current.value?.status).toBe('pending'); expect(state.saveError.value).toContain('rejected')
    state.openDetail(event('b', 'resolved')); expect(state.allowedStatuses.value).toEqual(['resolved'])
  })
  it('distinguishes relation 404, failure, retry and ignores closed responses', async () => {
    const pending = deferred<{ neighbors: {} }>(); let attempts = 0
    const state = useEventCenter({ list: async () => ({ data: [], total: 0 }), updateStatus: async () => event('a'), node: async () => { attempts++; if (attempts === 1) throw { response: { status: 404 } }; if (attempts === 2) throw Error('offline'); return pending.promise } })
    state.openDetail(event('a')); await state.loadRelation(); expect(state.caseLinkError.value).toBe('')
    await state.loadRelation(); expect(state.caseLinkError.value).toContain('offline'); const retry = state.loadRelation(); state.closeDetail(); pending.resolve({ neighbors: {} }); await retry
    expect(state.caseLinkLoading.value).toBe(false); expect(state.caseLink.value).toBeNull()
  })
  it('clamps an empty last page and ignores disposed list completion', async () => {
    const pending = deferred<{ data: AlertEvent[]; total: number }>(); let calls = 0
    const state = useEventCenter({ list: async () => { calls++; if (calls === 1) return { data: [], total: 20 }; return pending.promise }, updateStatus: async () => event('a'), node })
    state.page.value = 2; const load = state.load(); await Promise.resolve(); expect(state.page.value).toBe(1); state.dispose(); pending.resolve({ data: [event('a')], total: 20 }); await load; expect(state.events.value).toEqual([])
  })
})
