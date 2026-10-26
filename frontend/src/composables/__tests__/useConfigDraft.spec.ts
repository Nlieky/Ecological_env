import { describe, it, expect } from 'vitest'
import { useConfigDraft } from '../useConfigDraft'

describe('configuration draft acknowledgements', () => {
  it('acknowledges only persisted captured values, preserving later edits and skipped fields', () => {
    const state = useConfigDraft()
    state.initialize([{ key: 'a', value: 'old' }, { key: 'b', value: 'old' }])
    state.draft.value.a = 'sent'; state.draft.value.b = 'skipped'
    const sent = state.payload()
    state.draft.value.a = 'newer'
    state.acknowledge(sent, { success: true, applied_keys: ['a'], restart_needed: true })
    expect(state.baseline.value).toEqual({ a: 'sent', b: 'old' })
    expect(state.dirty.value).toBe(true)
    state.acknowledge({}, { success: true, applied_keys: [], restart_needed: false })
    expect(state.restartHint.value).toBe(true)
  })
  it('keeps secrets blank initially and preserves a new secret while save is pending', () => {
    const state = useConfigDraft()
    state.initialize([{ key: 'key', value: '***', type: 'secret' }])
    expect(state.payload()).toEqual({})
    state.draft.value.key = 'sent'
    const sent = state.payload()
    state.draft.value.key = 'new'
    state.acknowledge(sent, { success: true, applied_keys: ['key'], restart_needed: false })
    expect(state.draft.value.key).toBe('new')
    expect(state.dirty.value).toBe(true)
  })
  it('rejects explicit unsuccessful saves without acknowledging changes', () => {
    const state = useConfigDraft()
    state.initialize([{ key: 'a', value: 'old' }]); state.draft.value.a = 'new'
    expect(() => state.acknowledge(state.payload(), { success: false, applied_keys: ['a'], restart_needed: false })).toThrow()
    expect(state.baseline.value.a).toBe('old')
  })
})
