import { createRenderer, nextTick, reactive, ssrContextKey } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, expect, it, vi } from 'vitest'
import LogsView from '../LogsView.vue'
import TraceView from '../TraceView.vue'
import KnowledgeGraphView from '../KnowledgeGraphView.vue'
import { logsService } from '@/api/modules/logs'
import { knowledgeService } from '@/api/modules/knowledge'
import { useKnowledgeStore } from '@/stores/knowledge'
import echarts from '@/lib/echarts'
const route = reactive<any>({ path: '/logs', params: { id: 'A' }, query: {} })
vi.mock('vue-router', () => ({ useRoute: () => route, RouterLink: {} }))
vi.mock('@/api/modules/logs', () => ({ logsService: { list: vi.fn(), trace: vi.fn() } }))
vi.mock('@/api/modules/knowledge', () => ({ knowledgeService: { graph: vi.fn(), node: vi.fn() } }))
vi.mock('@/lib/echarts', () => ({ default: { init: vi.fn() } }))
const renderer = createRenderer<any, any>({ createElement: () => ({}), createText: () => ({}), createComment: () => ({}), setText() {}, setElementText() {}, parentNode: () => null, nextSibling: () => null, patchProp() {}, insert() {}, remove() {} })
let cleanup = () => {}
function mount(view: any) {
  route.path = view === KnowledgeGraphView ? '/agents/knowledge' : view === LogsView ? '/logs' : '/logs/trace/A'
  const pinia = createPinia(); setActivePinia(pinia)
  const app = renderer.createApp({ ...view, render: () => null }); app.use(pinia); app.provide(ssrContextKey, { modules: new Set() }); app.mount({})
  cleanup = () => app.unmount()
  return (app as any)._instance.setupState
}
const flush = async () => { await Promise.resolve(); await Promise.resolve(); await nextTick(); await Promise.resolve() }
afterEach(() => { cleanup(); vi.resetAllMocks(); vi.unstubAllGlobals(); route.params.id = 'A'; route.query = {} })
it('graph resizes when a pending or missing sidebar opens and closes without a selected node', async () => {
  vi.stubGlobal('window', { addEventListener: vi.fn(), removeEventListener: vi.fn() })
  const chart = { setOption: vi.fn(), resize: vi.fn(), on: vi.fn(), dispose: vi.fn() }
  vi.mocked(echarts.init).mockReturnValue(chart as any)
  vi.mocked(knowledgeService.graph).mockResolvedValue({ nodes: [], edges: [], stats: {} as any, seeded: true, success: true })
  let fail!: (v: any) => void
  vi.mocked(knowledgeService.node).mockImplementation(() => new Promise((_resolve, reject) => { fail = reject }))
  const state = mount(KnowledgeGraphView); state.chartEl = {}; await flush(); await flush()
  chart.resize.mockClear()
  const pending = state.openNode('missing'); await flush()
  expect(chart.resize).toHaveBeenCalledTimes(1)
  fail({ response: { status: 404 } }); await pending; await flush()
  expect(useKnowledgeStore().selectedNodeNotFound).toBe(true)
  useKnowledgeStore().clearSelection(); await flush()
  expect(chart.resize).toHaveBeenCalledTimes(2)
})
it('logs and trace reject response updates after unmount', async () => {
  let finishLogs!: (v: any) => void
  vi.mocked(logsService.list).mockImplementation(() => new Promise(r => { finishLogs = r }))
  const logs = mount(LogsView); cleanup(); finishLogs({ data: [{ id: 'late' }], total: 1 }); await flush(); expect(logs.rows).toEqual([])
  let finishTrace!: (v: any) => void
  vi.mocked(logsService.trace).mockImplementation(() => new Promise(r => { finishTrace = r }))
  const trace = mount(TraceView); cleanup(); finishTrace({ session_id: 'A' }); await flush(); expect(trace.trace).toBeNull()
})
it('graph reveals a hidden focused type and stale detail cannot switch the newer target tab', async () => {
  vi.stubGlobal('window', { addEventListener: vi.fn(), removeEventListener: vi.fn() })
  vi.mocked(knowledgeService.graph).mockImplementation(() => new Promise(() => {}))
  let finish!: (v: any) => void
  vi.mocked(knowledgeService.node).mockImplementationOnce(() => new Promise(r => { finish = r })).mockResolvedValueOnce({ success: true, node: { id: 'service:B', type: 'service', label: 'B', props: {} }, neighbors: {} }).mockResolvedValueOnce({ success: true, node: { id: 'pattern:C', type: 'violation_pattern', label: 'C', props: {} }, neighbors: {} })
  mount(KnowledgeGraphView); const store = useKnowledgeStore(); route.query.focus = 'pattern:A'; await flush(); route.query.focus = 'service:B'; await flush()
  finish({ node: { id: 'pattern:A', type: 'violation_pattern', label: 'A', props: {} }, neighbors: {} }); await flush()
  expect(store.activeTab).toBe('topology'); expect(store.selectedNode?.id).toBe('service:B')
  store.setTab('domain'); store.toggleType('violation_pattern'); route.query.focus = 'pattern:C'; await flush()
  expect(store.visibleTypes).toContain('violation_pattern'); expect(store.selectedNode?.id).toBe('pattern:C')
})
it('logs resets filters to page one and only links real session strings', async () => {
  vi.mocked(logsService.list).mockResolvedValue({ data: [], total: 0 })
  const state = mount(LogsView); state.page = 4; state.logType = 'master'; state.onTypeChange(); await flush()
  expect(logsService.list).toHaveBeenLastCalledWith({ log_type: 'master', page: 1, page_size: 20 })
  expect(state.sessionId({ id: 'log-id', details: {} })).toBe('')
  expect(state.sessionId({ details: { session_id: 42 } })).toBe('')
  expect(state.sessionId({ details: { session_id: '  ' } })).toBe('')
  expect(state.sessionId({ details: { session_id: 'A/B?#' } })).toBe('A/B?#')
})
it('trace separates 404 from a successful all-empty trace and supports retry', async () => {
  vi.mocked(logsService.trace).mockRejectedValueOnce({ response: { status: 404 } }).mockResolvedValueOnce({ session_id: 'A', master_decision: null, subagent_executions: [], operator_calls: [], llm_calls: [] } as any)
  const state = mount(TraceView); await flush(); expect(state.error).toBeNull(); expect(state.trace).toBeNull(); expect(state.loaded).toBe(true)
  await state.load(); expect(state.noRecordedData).toBe(true); expect(state.error).toBeNull()
})
it('logs preserves failure separately from empty and ignores stale requests', async () => {
  let finish!: (v: any) => void
  vi.mocked(logsService.list).mockImplementationOnce(() => new Promise(r => { finish = r })).mockRejectedValueOnce(new Error('offline'))
  const state = mount(LogsView); await state.onPage(2); await flush()
  expect(state.error).toBe('offline'); expect(state.loading).toBe(false)
  finish({ data: [{ id: 'old' }], total: 1 }); await flush(); expect(state.rows).toEqual([]); expect(state.error).toBe('offline')
})
it('trace follows reused routes and separates transport errors from missing data', async () => {
  let finish!: (v: any) => void
  vi.mocked(logsService.trace).mockImplementationOnce(() => new Promise(r => { finish = r })).mockRejectedValueOnce(new Error('offline'))
  const state = mount(TraceView); route.params.id = 'B'; await flush()
  expect(logsService.trace).toHaveBeenLastCalledWith('B'); expect(state.error).toBe('offline')
  finish({ session_id: 'A' }); await flush(); expect(state.trace).toBeNull()
})
it('graph reacts to focus using actual pattern type and prevents late mount registration', async () => {
  const add = vi.fn(); const remove = vi.fn(); vi.stubGlobal('window', { addEventListener: add, removeEventListener: remove })
  let finish!: (v: any) => void
  vi.mocked(knowledgeService.graph).mockImplementation(() => new Promise(r => { finish = r }))
  vi.mocked(knowledgeService.node).mockResolvedValue({ success: true, node: { id: 'pattern:x', type: 'violation_pattern', label: 'x', props: {} }, neighbors: {} })
  mount(KnowledgeGraphView); const store = useKnowledgeStore(); store.setTab('topology'); route.query.focus = 'pattern:x'; await flush()
  expect(store.activeTab).toBe('domain'); expect(store.selectedNode?.id).toBe('pattern:x')
  cleanup(); const registeredAtUnmount = add.mock.calls.length
  finish({ nodes: [], edges: [], stats: {}, seeded: true }); await flush()
  expect(add).toHaveBeenCalledTimes(registeredAtUnmount)
  const resizeHandler = add.mock.calls.find(call => call[0] === 'resize')?.[1]
  expect(remove).toHaveBeenCalledWith('resize', resizeHandler)
  expect(store.selectedNode).toBeNull(); vi.unstubAllGlobals()
})
