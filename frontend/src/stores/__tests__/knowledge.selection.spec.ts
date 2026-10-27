import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { knowledgeService } from '@/api/modules/knowledge'
import { useKnowledgeStore } from '../knowledge'
vi.mock('@/api/modules/knowledge', () => ({ knowledgeService: { node: vi.fn() } }))
const result = (id: string) => ({ success: true, node: { id, type: 'violation_pattern', label: id, props: {} }, neighbors: {} })
describe('knowledge selection navigation', () => {
  beforeEach(() => { setActivePinia(createPinia()); vi.resetAllMocks() })
  it('keeps the latest selection when an earlier request settles last', async () => {
    let finish!: (value: any) => void
    vi.mocked(knowledgeService.node).mockImplementationOnce(() => new Promise(r => { finish = r })).mockResolvedValueOnce(result('B'))
    const store = useKnowledgeStore(); const old = store.selectNode('A'); await store.selectNode('B')
    finish(result('A')); await old
    expect(store.selectedNode?.id).toBe('B')
  })
  it('invalidates a pending request on close', async () => {
    let finish!: (value: any) => void
    vi.mocked(knowledgeService.node).mockImplementation(() => new Promise(r => { finish = r }))
    const store = useKnowledgeStore(); const pending = store.selectNode('A'); store.clearSelection()
    finish(result('A')); await pending
    expect(store.selectedNode).toBeNull()
  })
  it('distinguishes missing nodes from server errors without overwriting graph error', async () => {
    const store = useKnowledgeStore(); store.error = 'graph failed'
    vi.mocked(knowledgeService.node).mockRejectedValueOnce({ response: { status: 404 } }).mockRejectedValueOnce(new Error('offline'))
    await store.selectNode('missing'); expect(store.selectedNodeNotFound).toBe(true)
    await store.selectNode('offline'); expect(store.selectedNodeError).toBe('offline'); expect(store.selectedNodeNotFound).toBe(false)
    expect(store.error).toBe('graph failed')
  })
})
