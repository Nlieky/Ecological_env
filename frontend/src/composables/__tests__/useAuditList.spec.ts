import { describe, expect, it } from 'vitest'
import { useAuditList } from '../useAuditList'

describe('audit list states', () => {
  it('resets search pages, preserves a preferred selection and ignores stale pages', async () => {
    const requests: { page: number; search: string; resolve: (value: any) => void }[] = []
    const selections: string[] = []
    let selected = 'outside-page'
    const state = useAuditList((page, _size, search) => new Promise(resolve => {
      requests.push({ page, search, resolve })
    }), async id => { selections.push(id); selected = id }, { selectedId: () => selected })
    const old = state.setPage(2)
    const latest = state.setSearch('needle')
    expect(state.page.value).toBe(1)
    expect(requests.map(r => [r.page, r.search])).toEqual([[2, ''], [1, 'needle']])
    requests[1].resolve({ success: true, data: { conversations: [{ id: 'B' }], total_count: 3 } })
    await latest
    requests[0].resolve({ success: true, data: { conversations: [{ id: 'A' }], total_count: 99 } })
    await old
    expect(state.conversations.value[0].id).toBe('B')
    expect(state.total.value).toBe(3)
    expect(selections).toEqual([])
  })
  it('keeps list failures distinct from successful empty lists and retries', async () => {
    let fails = true
    const state = useAuditList(async () => {
      if (fails) throw new Error('offline')
      return { success: true, data: { conversations: [], total_count: 0 } }
    }, async () => {})
    await state.load()
    expect(state.error.value).toContain('offline')
    fails = false; await state.load()
    expect(state.error.value).toBe('')
    expect(state.conversations.value).toEqual([])
  })
  it('does not select or publish a delayed list after disposal', async () => {
    let resolve!: (value: any) => void
    let selected = false
    const state = useAuditList(() => new Promise(r => { resolve = r }), async () => { selected = true })
    const pending = state.load(); state.dispose()
    resolve({ success: true, data: { conversations: [{ id: 'A' }], total_count: 1 } })
    await pending
    expect(selected).toBe(false)
    expect(state.conversations.value).toEqual([])
  })
  it('rejects unsuccessful HTTP200 envelopes', async () => {
    const state = useAuditList(async () => ({ success: false, error: { message: 'list unavailable' } }), async () => {})
    await state.load()
    expect(state.error.value).toContain('list unavailable')
  })
})
