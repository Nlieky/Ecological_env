import { createRenderer, nextTick, ssrContextKey, reactive } from 'vue'
import { afterEach, expect, it, vi } from 'vitest'
import LogsView from '../LogsView.vue'
import TraceView from '../TraceView.vue'
import { logsService } from '@/api/modules/logs'
import PlantsConfigPanel from '@/components/agents/config/PlantsConfigPanel.vue'
import { agentConfigService } from '@/api/modules/agentConfig'
import { ElMessageBox } from 'element-plus'
import ConversationList from '@/components/aiops/ConversationList.vue'
import { conversationsService } from '@/api/modules/conversations'
import { createPinia } from 'pinia'
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn(), success: vi.fn(), warning: vi.fn() }, ElMessageBox: { confirm: vi.fn(), prompt: vi.fn() } }))
const route = reactive({ path: '/logs', params: { id: 'first' } })
vi.mock('vue-router', () => ({ useRoute: () => route }))
type Host = { parent: Host | null; children: Host[] }
const host = (): Host => ({ parent: null, children: [] })
const renderer = createRenderer<Host, Host>({
  createElement: host, createText: host, createComment: host, setText() {}, setElementText() {}, patchProp() {},
  parentNode: n => n.parent, nextSibling: () => null,
  insert(n, p) { n.parent = p; p.children.push(n) },
  remove(n) { if (n.parent) n.parent.children.splice(n.parent.children.indexOf(n), 1) },
})
let cleanup: (() => void) | undefined
afterEach(() => { cleanup?.(); vi.restoreAllMocks(); route.params.id = 'first' })
function mount(view: any) {
  const app = renderer.createApp({ ...view, render: () => null })
  app.use(createPinia())
  app.provide(ssrContextKey, { modules: new Set() }); app.mount(host()); cleanup = () => app.unmount()
  return (app._instance as any).setupState
}
const flush = async () => { await Promise.resolve(); await Promise.resolve(); await nextTick() }
it('keeps logs after same-query refresh failure, but clears them when the filter changes', async () => {
  const list = vi.spyOn(logsService, 'list').mockResolvedValueOnce({ data: [{ id: 1, module: 'api', content: 'retained' }], total: 1 } as any)
  const state = mount(LogsView); await flush()
  list.mockRejectedValue(new Error('offline'))
  await state.load()
  expect(state.rows[0].content).toBe('retained')
  expect(state.error).toBe('offline')
  state.setType('error'); await flush()
  expect(state.rows).toEqual([])
  expect(state.total).toBe(0)
  expect(list).toHaveBeenLastCalledWith({ log_type: 'error', page: 1, page_size: 20 })
})
it('keeps trace on same-session refresh failure and clears it on URL session change', async () => {
  const trace = vi.spyOn(logsService, 'trace').mockResolvedValueOnce({ session_id: 'first' } as any)
  const state = mount(TraceView); await flush()
  trace.mockRejectedValue(new Error('offline'))
  await state.load()
  expect(state.trace.session_id).toBe('first')
  expect(state.error).toBe('offline')
  route.params.id = 'second'; await flush()
  expect(state.trace).toBeNull()
  expect(trace).toHaveBeenLastCalledWith('second')
})
it('reports a missing trace during same-session refresh instead of presenting retained data as ready', async () => {
  const request = vi.spyOn(logsService, 'trace').mockResolvedValueOnce({ session_id: 'first' } as any)
  const state = mount(TraceView); await flush()
  request.mockRejectedValue({ response: { status: 404 } })
  await state.load()
  expect(state.trace.session_id).toBe('first')
  expect(state.error).toContain('已过期')
})
it('formats dynamic trace timing cells consistently', () => {
  vi.spyOn(logsService, 'trace').mockResolvedValue({ session_id: 'first' } as any)
  const state = mount(TraceView)
  expect(state.formatTraceCell({ latency_ms: 1500 }, { property: 'latency_ms' })).toBe('1秒')
  expect(state.formatTraceCell({ timestamp: 'invalid' }, { property: 'timestamp' })).toBe('—')
})
it('ignores plant configuration loads settling after unmount', async () => {
  let finish!: (value: any) => void
  vi.spyOn(agentConfigService, 'getPlants').mockImplementation(() => new Promise(resolve => { finish = resolve }))
  const state = mount(PlantsConfigPanel)
  cleanup?.(); cleanup = undefined
  finish({ data: { hierarchy: { Late: {} } } }); await flush()
  expect(state.loaded).toBe(false)
  expect(state.cfg.hierarchy).toEqual({})
})
it('surfaces plant load failures and retries while protecting unsaved changes', async () => {
  const config = { hierarchy: {}, plant_aliases: {}, report_name_map: {}, plant_configs: {} }
  const request = vi.spyOn(agentConfigService, 'getPlants').mockRejectedValueOnce(new Error('offline')).mockResolvedValue({ data: config } as any)
  const state = mount(PlantsConfigPanel); await flush()
  expect(state.loadError).toContain('offline')
  expect(state.loaded).toBe(false)
  await state.load()
  expect(state.loaded).toBe(true)
  state.cfg.plant_aliases.draft = 'local'
  vi.mocked(ElMessageBox.confirm).mockRejectedValueOnce('cancel')
  const calls = request.mock.calls.length
  await state.load()
  expect(request).toHaveBeenCalledTimes(calls)
  expect(state.cfg.plant_aliases.draft).toBe('local')
})
it('ignores superseded plant loads and preserves edits made while a refresh is pending', async () => {
  const pending: ((value: any) => void)[] = []
  vi.spyOn(agentConfigService, 'getPlants').mockImplementation(() => new Promise(resolve => { pending.push(resolve) }))
  const state = mount(PlantsConfigPanel)
  const latest = state.load()
  pending[1]({ data: { hierarchy: { Current: {} }, plant_aliases: {}, report_name_map: {}, plant_configs: {} } }); await latest
  pending[0]({ data: { hierarchy: { Stale: {} } } }); await flush()
  expect(state.cfg.hierarchy).toEqual({ Current: {} })
  const refresh = state.load()
  state.cfg.plant_aliases.draft = 'local'
  pending[2]({ data: { hierarchy: { Remote: {} }, plant_aliases: {} } }); await refresh
  expect(state.cfg.plant_aliases.draft).toBe('local')
  expect(state.loadError).toContain('保留当前草稿')
})
it('shows conversation list failures and retains successful history on a failed refresh', async () => {
  const request = vi.spyOn(conversationsService, 'list').mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ success: true, data: { conversations: [{ id: 'session-1', title: 'History' }] } } as any)
  const state = mount(ConversationList); await flush()
  expect(state.listError).toBe('offline')
  await state.refresh()
  expect(state.chat.conversations[0].id).toBe('session-1')
  request.mockRejectedValueOnce(new Error('refresh offline'))
  await state.refresh()
  expect(state.listError).toBe('refresh offline')
  expect(state.chat.conversations[0].id).toBe('session-1')
})
