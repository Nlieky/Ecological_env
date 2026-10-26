import { createRenderer, nextTick, reactive, ssrContextKey } from 'vue'
import { afterEach, describe, expect, it, vi } from 'vitest'
import AgentAuditView from '../AgentAuditView.vue'
import { conversationsService } from '@/api/modules/conversations'
import { logsService } from '@/api/modules/logs'
import { createPinia } from 'pinia'

const route = reactive<{ path: string; query: { session?: string } }>({ path: '/agents/audit', query: {} })
vi.mock('vue-router', () => ({ useRoute: () => route }))
vi.mock('@/api/modules/conversations', () => ({ conversationsService: { list: vi.fn(), detail: vi.fn() } }))
vi.mock('@/api/modules/logs', () => ({ logsService: { trace: vi.fn() } }))

// A small in-memory Vue host exercises the real view/composables without a DOM dependency.
type Node = { text: string; children: Node[]; parent: Node | null; props: Record<string, any> }
const node = (text = ''): Node => ({ text, children: [], parent: null, props: {} })
const renderer = createRenderer<Node, Node>({
  createElement: () => node(), createText: node, createComment: node,
  setText: (n, text) => { n.text = text },
  setElementText: (n, text) => { n.text = text; n.children = [] },
  parentNode: n => n.parent,
  nextSibling: n => n.parent?.children[n.parent.children.indexOf(n) + 1] ?? null,
  patchProp: (n, key, _old, value) => { n.props[key] = value },
  insert: (n, parent, anchor) => {
    if (n.parent) n.parent.children.splice(n.parent.children.indexOf(n), 1)
    n.parent = parent
    const index = anchor ? parent.children.indexOf(anchor) : -1
    if (index < 0) parent.children.push(n); else parent.children.splice(index, 0, n)
  },
  remove: n => { if (n.parent) n.parent.children.splice(n.parent.children.indexOf(n), 1) },
})
const flush = async () => { await Promise.resolve(); await Promise.resolve(); await nextTick() }
let unmount: (() => void) | undefined
afterEach(() => { unmount?.(); unmount = undefined; vi.clearAllMocks(); route.query = {} })

describe('audit session navigation', () => {
  it('loads a direct session outside the list, preserves it on list settlement, and reacts to navigation', async () => {
    route.query.session = 'outside'
    let resolve!: (value: any) => void
    vi.mocked(conversationsService.list).mockImplementation(() => new Promise(r => { resolve = r }))
    vi.mocked(conversationsService.detail).mockImplementation(async id => ({ success: true, data: { id, title: `Title ${id}`, message_count: 0, messages: [] } }))
    vi.mocked(logsService.trace).mockRejectedValue(new Error('trace unavailable'))
    const root = node()
    // Node compiles the SFC for SSR. Preserve its real setup/watch/lifecycle logic
    // and use an empty render in this host; browser verification covers its markup.
    const app = renderer.createApp({ ...AgentAuditView, render: () => null })
    app.use(createPinia())
    app.provide(ssrContextKey, { modules: new Set() })
    app.mount(root); unmount = () => app.unmount()
    await flush()
    expect(conversationsService.detail).toHaveBeenCalledWith('outside')
    resolve({ success: true, data: { conversations: [{ id: 'first', title: 'First', message_count: 0 }], total_count: 51, page: 1, page_size: 50 } })
    await flush()
    expect(conversationsService.detail).toHaveBeenCalledTimes(1)
    route.query.session = 'another'
    await flush()
    expect(conversationsService.detail).toHaveBeenLastCalledWith('another')
    expect(logsService.trace).toHaveBeenLastCalledWith('another')
  })
})
