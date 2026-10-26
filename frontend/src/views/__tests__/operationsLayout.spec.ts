import { createRenderer, nextTick, ssrContextKey, h } from 'vue'
import * as Vue from 'vue'
import { compile } from '@vue/compiler-dom'
import graphSource from '../KnowledgeGraphView.vue?raw'
import echarts from '@/lib/echarts'
import SkillsPanel from '@/components/agents/config/SkillsPanel.vue'
import { afterEach, expect, it, vi } from 'vitest'
import AgentConfigView from '../AgentConfigView.vue'
import { agentConfigService } from '@/api/modules/agentConfig'
import KnowledgeGraphView from '../KnowledgeGraphView.vue'
import { createPinia } from 'pinia'
import { useKnowledgeStore } from '@/stores/knowledge'
import EventCenterView from '../EventCenterView.vue'
import { eventsService } from '@/api/modules/events'

vi.mock('vue-router', () => ({ useRoute: () => ({ path: '/agents/config', query: {} }), useRouter: () => ({ replace: vi.fn() }), onBeforeRouteLeave: vi.fn() }))
vi.mock('@/lib/echarts', () => ({ default: { init: vi.fn() } }))
type Host = { parent: Host | null; children: Host[]; style: Record<string, string> }
const host = (): Host => ({ parent: null, children: [], style: {} })
const renderer = createRenderer<Host, Host>({
  createElement: host, createText: host, createComment: host, setText() {}, setElementText() {}, patchProp() {},
  parentNode: n => n.parent, nextSibling: () => null,
  insert(n, p) { n.parent = p; p.children.push(n) },
  remove(n) { if (n.parent) n.parent.children.splice(n.parent.children.indexOf(n), 1) },
})
const flush = async () => { await Promise.resolve(); await Promise.resolve(); await nextTick() }
let cleanup: (() => void) | undefined
afterEach(() => { cleanup?.(); cleanup = undefined; vi.restoreAllMocks(); vi.unstubAllGlobals() })
function mount() {
  const windowMock = { addEventListener: vi.fn(), removeEventListener: vi.fn(), confirm: vi.fn(() => false) }
  vi.stubGlobal('window', windowMock)
  const app = renderer.createApp({ ...AgentConfigView, render: () => null })
  app.use(createPinia())
  app.provide(ssrContextKey, { modules: new Set() }); app.mount(host())
  cleanup = () => app.unmount()
  return { app, state: (app._instance as any).setupState, windowMock }
}
it('exposes configuration initialization failure and retries successfully', async () => {
  vi.spyOn(agentConfigService, 'entities').mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ success: true, data: [{ name: 'master', label: '主控' }] } as any)
  const { state } = mount(); await flush()
  expect(state.configState).toBe('error')
  expect(state.loadError).toContain('初始化失败')
  await state.loadEntities()
  expect(state.configState).toBe('ready')
})
it('warns about unsaved edits on browser unload and removes the listener', async () => {
  vi.spyOn(agentConfigService, 'entities').mockResolvedValue({ success: true, data: [] })
  const { app, state, windowMock } = mount(); await flush()
  const handler = windowMock.addEventListener.mock.calls.find(c => c[0] === 'beforeunload')![1] as (e: any) => void
  const event = { preventDefault: vi.fn(), returnValue: undefined }
  handler(event); expect(event.preventDefault).not.toHaveBeenCalled()
  state.editorRef = { dirty: true }
  handler(event); expect(event.preventDefault).toHaveBeenCalledOnce()
  app.unmount(); cleanup = undefined
  expect(windowMock.removeEventListener).toHaveBeenCalledWith('beforeunload', handler)
})
it('ignores configuration initialization resolving after unmount', async () => {
  let resolve!: (value: any) => void
  vi.spyOn(agentConfigService, 'entities').mockImplementation(() => new Promise(r => { resolve = r }))
  const { app, state } = mount(); app.unmount(); cleanup = undefined
  resolve({ success: true, data: [{ name: 'late' }] }); await flush()
  expect(state.entities).toEqual([])
})
it('distinguishes graph initialization, empty graph and retryable failures without matchMedia', async () => {
  const pinia = createPinia(); const store = useKnowledgeStore(pinia)
  let finish!: () => void
  vi.spyOn(store, 'loadGraph').mockImplementation(() => new Promise<void>(resolve => { finish = resolve }))
  const windowMock = { innerWidth: 1100, addEventListener: vi.fn(), removeEventListener: vi.fn() }
  vi.stubGlobal('window', windowMock)
  const app = renderer.createApp({ ...KnowledgeGraphView, render: () => null }); app.use(pinia)
  app.provide(ssrContextKey, { modules: new Set() }); app.mount(host()); cleanup = () => app.unmount()
  const state = (app._instance as any).setupState
  store.loading = true; expect(state.graphState).toBe('initial-loading')
  store.loading = false; expect(state.graphState).toBe('empty')
  store.error = 'offline'; expect(state.graphState).toBe('error')
  expect(state.narrowDetail).toBe(true)
  windowMock.innerWidth = 1366
  windowMock.addEventListener.mock.calls.find(c => c[0] === 'resize')![1]()
  expect(state.narrowDetail).toBe(false)
  store.selectedNodeId = 'missing'; state.closeNode(); expect(store.selectedNodeId).toBe('')
  app.unmount(); cleanup = undefined; finish(); await flush()
  expect(windowMock.removeEventListener).toHaveBeenCalledWith('resize', expect.any(Function))
})
it('cancelling an event status confirmation never sends a write request', async () => {
  vi.stubGlobal('window', { confirm: vi.fn(() => false) })
  vi.spyOn(eventsService, 'list').mockResolvedValue({ data: [], total: 0, page: 1, pageSize: 20 } as any)
  const write = vi.spyOn(eventsService, 'updateStatus')
  const app = renderer.createApp({ ...EventCenterView, render: () => null })
  app.use(createPinia())
  app.provide(ssrContextKey, { modules: new Set() }); app.mount(host()); cleanup = () => app.unmount()
  const state = (app._instance as any).setupState
  state.current = { id: 'event-1', status: 'pending' }
  await state.confirmStatus('processing')
  expect(window.confirm).toHaveBeenCalledOnce()
  expect(write).not.toHaveBeenCalled()
})
it('includes skill drafts in tab, entity, route and unload protection', async () => {
  vi.spyOn(agentConfigService, 'entities').mockResolvedValue({ success: true, data: [] })
  const { state, windowMock } = mount(); await flush()
  state.skillsRef = { dirty: true }
  expect(state.dirty).toBe(true)
  state.switchTab('files'); expect(state.tab).toBe('overview')
  state.switchEntity('__service__'); expect(state.activeEntity).toBe('master')
  expect(state.allowTransition()).toBe(false)
  const event = { preventDefault: vi.fn(), returnValue: undefined }
  windowMock.addEventListener.mock.calls.find(c => c[0] === 'beforeunload')![1](event)
  expect(event.preventDefault).toHaveBeenCalledOnce()
})
it('exposes the real skill editor dirty value to its parent', async () => {
  vi.spyOn(agentConfigService, 'getSkills').mockResolvedValue({ success: true, data: { skills: [], templates: [] } } as any)
  const app = renderer.createApp({ ...SkillsPanel, render: () => null }, { entity: 'master' })
  app.provide(ssrContextKey, { modules: new Set() }); app.mount(host()); cleanup = () => app.unmount()
  const instance = app._instance as any
  expect(instance.exposed?.dirty?.value).toBe(false)
  instance.setupState.content = 'changed draft'
  expect(instance.exposed.dirty.value).toBe(true)
})
it('recreates the graph instance when its actual template removes and restores the canvas', async () => {
  const pinia = createPinia(); const store = useKnowledgeStore(pinia)
  vi.stubGlobal('window', { innerWidth: 1366, addEventListener: vi.fn(), removeEventListener: vi.fn() })
  vi.spyOn(store, 'loadGraph').mockResolvedValue(undefined)
  store.seeded = true
  const charts = [0, 1].map(() => ({ setOption: vi.fn(), resize: vi.fn(), on: vi.fn(), dispose: vi.fn() }))
  vi.mocked(echarts.init).mockReturnValueOnce(charts[0] as any).mockReturnValueOnce(charts[1] as any)
  const template = graphSource.slice(graphSource.indexOf('<template>') + 10, graphSource.indexOf('<script setup'))
    .replace(/<\/template>\s*$/, '').replace('(row: any)', '(row)').replace(/selectedNodeId!/g, 'selectedNodeId')
  const compiled = new Function('Vue', compile(template, { mode: 'function' }).code)(Vue)
  const Shell = { setup(_: unknown, { slots }: any) { return () => h('main', slots.default?.()) } }
  const State = { setup(_: unknown, { slots }: any) { return () => h('div', slots.default?.()) } }
  const app = renderer.createApp({ ...KnowledgeGraphView, components: { PageShell: Shell, PageState: State }, render(this: any) { return compiled(this.$.setupState, []) } })
  app.config.warnHandler = () => {}
  app.use(pinia); app.provide(ssrContextKey, { modules: new Set() }); app.mount(host()); cleanup = () => app.unmount()
  await flush(); await flush()
  expect(echarts.init).toHaveBeenCalledTimes(1)
  const firstCanvas = vi.mocked(echarts.init).mock.calls[0][0]
  store.seeded = false; await flush()
  expect(charts[0].dispose).toHaveBeenCalledOnce()
  store.seeded = true; await flush(); await flush()
  expect(echarts.init).toHaveBeenCalledTimes(2)
  expect(vi.mocked(echarts.init).mock.calls[1][0]).not.toBe(firstCanvas)
  expect(charts[1].on).toHaveBeenCalledWith('click', expect.any(Function))
})
