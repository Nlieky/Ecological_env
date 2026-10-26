import { createSSRApp, createRenderer, h, nextTick, ssrContextKey } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import PlantBoardPanel from '../PlantBoardPanel.vue'
import MetricsView from '../MetricsView.vue'
import DashboardView from '../DashboardView.vue'
import { plantsService } from '@/api/modules/plants'
import { usePlantsStore } from '@/stores/plants'
import PageState from '@/components/common/PageState.vue'
import * as Vue from 'vue'
import { compile } from '@vue/compiler-dom'
import { parse, compileScript } from '@vue/compiler-sfc'
import boardSource from '../PlantBoardPanel.vue?raw'
import pageStateSource from '@/components/common/PageState.vue?raw'
import historySource from '../SituationHistoryView.vue?raw'
import treeSource from '@/components/cockpit/PlantTree.vue?raw'
import SituationHistoryView from '../SituationHistoryView.vue'
import SystemStatusView from '../SystemStatusView.vue'
import PlantTree from '@/components/cockpit/PlantTree.vue'
import api from '@/api/client'
import { executeAssistantAction } from '@/assistant/executor'
import { useAssistantContextStore } from '@/stores/assistantContext'
import { useActionStore } from '@/stores/action'

const route = Vue.reactive<{ path: string; query: { plant?: string } }>({ path: '/dashboard', query: {} })
vi.mock('vue-router', async importOriginal => ({ ...await importOriginal<typeof import('vue-router')>(), useRoute: () => route, useRouter: () => ({ push: vi.fn() }) }))

vi.mock('@/lib/echarts', () => ({ default: { init: vi.fn(() => ({ setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn() })) } }))

beforeEach(() => { setActivePinia(createPinia()); vi.stubGlobal('window', { addEventListener: vi.fn(), removeEventListener: vi.fn() }); vi.stubGlobal('document', { activeElement: null }) })
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers(); route.query = {} })
async function renderBoard() {
  const app = createSSRApp({ render: () => h(PlantBoardPanel, { plantId: '厂A' }) })
  app.use(createPinia())
  // Use the seeded store in the same Pinia as the rendered component.
  const store = usePlantsStore(app.config.globalProperties.$pinia)
  store.dashboard = { plant_id: '厂A', window_hours: 24, indicators: {}, influent_points: 0, effluent_points: 2,
    data_context: { origin: 'real', mode: 'historical', freshness: 'historical' } } as any
  return renderToString(app)
}
it('labels replay as history and does not light a realtime status for historical data', async () => {
  const html = await renderBoard()
  expect(html).toContain('历史回放')
  expect(html).not.toMatch(/class="(?:on live-dot|live-dot on)"/)
})

type Host = { parent: Host | null; children: Host[]; text: string; props: Record<string, any>; addEventListener: () => void }
const host = (text = ''): Host => ({ parent: null, children: [], text, props: {}, addEventListener() {} })
const renderer = createRenderer<Host, Host>({
  createElement: host, createText: host, createComment: host,
  setText(n, text) { n.text = text }, setElementText(n, text) { n.text = text }, patchProp(n, key, _old, value) { n.props[key] = value },
  parentNode: n => n.parent, nextSibling: n => n.parent?.children[n.parent.children.indexOf(n) + 1] ?? null,
  insert(n, parent, anchor) { if (n.parent) n.parent.children.splice(n.parent.children.indexOf(n), 1); n.parent = parent; const index = anchor ? parent.children.indexOf(anchor) : -1; if (index < 0) parent.children.push(n); else parent.children.splice(index, 0, n) },
  remove(n) { if (n.parent) n.parent.children.splice(n.parent.children.indexOf(n), 1) },
})
const flush = async () => { await Promise.resolve(); await Promise.resolve(); await nextTick() }
function mountTab(view: any, render: any = () => null) {
  const app = renderer.createApp({ ...view, render })
  app.use(createPinia()); app.provide(ssrContextKey, { modules: new Set() })
  const root = host(); app.mount(root)
  return { app, root, state: (app._instance as any).setupState }
}
it('system status preserves its successful snapshot on refresh failure and distinguishes initial failure', async () => {
  vi.useFakeTimers()
  const get = vi.spyOn(api, 'get').mockRejectedValueOnce(new Error('offline'))
  const { app, state } = mountTab(SystemStatusView)
  try {
    await flush(); expect(state.viewState).toBe('error')
    get.mockResolvedValueOnce({ data: { generated_at: 'now', services: [{ name: 'db', title: 'db', status: 'up' }], plants: [], counters: {} } })
    await state.load(); expect(state.viewState).toBe('ready')
    get.mockRejectedValueOnce(new Error('refresh failed'))
    await state.load(); expect(state.status?.generated_at).toBe('now'); expect(state.viewState).toBe('error')
  } finally { app.unmount() }
})
it('history preserves only matching windows, ignores old responses, and restores charts after an empty result', async () => {
  vi.useFakeTimers()
  const observer = { observe: vi.fn(), unobserve: vi.fn(), disconnect: vi.fn() }
  vi.stubGlobal('ResizeObserver', class { observe = observer.observe; unobserve = observer.unobserve; disconnect = observer.disconnect })
  const row = { day: '2026-10-01', points: 2, influent_points: 1, effluent_points: 1, exceed: 0, metrics: {} }
  const get = vi.spyOn(api, 'get').mockResolvedValueOnce({ data: [row] })
  const { app, state } = mountTab(SituationHistoryView, templateRender(historySource))
  try {
    await flush(); await flush(); expect(observer.observe).toHaveBeenCalledTimes(3)
    get.mockRejectedValueOnce(new Error('offline')); await state.load()
    expect(state.rows).toHaveLength(1); expect(state.viewState).toBe('error')
    get.mockResolvedValueOnce({ data: [] }); await state.load(); await flush()
    expect(state.viewState).toBe('empty'); expect(observer.unobserve).toHaveBeenCalledTimes(3)
    get.mockResolvedValueOnce({ data: [row] }); await state.load(); await flush()
    expect(observer.observe).toHaveBeenCalledTimes(6)
    let finish!: (v: any) => void
    get.mockImplementationOnce(() => new Promise(r => { finish = r }))
    state.days = 7; await flush()
    expect(state.rows).toEqual([])
    get.mockResolvedValueOnce({ data: [] }); state.days = 90; await flush()
    finish({ data: [row] }); await flush()
    expect(state.rows).toEqual([])
  } finally { app.unmount() }
  expect(observer.disconnect).toHaveBeenCalledOnce()
})
it('history does not register charts, listeners or polling after a pending load unmounts', async () => {
  vi.useFakeTimers()
  let finish!: (v: any) => void
  const get = vi.spyOn(api, 'get').mockImplementation(() => new Promise(r => { finish = r }))
  const { app, state } = mountTab(SituationHistoryView)
  app.unmount(); const calls = vi.mocked(window.addEventListener).mock.calls.length
  finish({ data: [{ day: 'late' }] }); await flush()
  expect(state.rows).toEqual([])
  expect(window.addEventListener).toHaveBeenCalledTimes(calls)
  await vi.advanceTimersByTimeAsync(60_000); expect(get).toHaveBeenCalledTimes(1)
})
it('history first failure offers a retry and a successful empty retry is an empty state', async () => {
  vi.useFakeTimers()
  const get = vi.spyOn(api, 'get').mockRejectedValueOnce(new Error('offline'))
  const { app, root, state } = mountTab(SituationHistoryView, templateRender(historySource))
  const nodes = (n: Host): Host[] => [n, ...n.children.flatMap(nodes)]
  try {
    await flush(); expect(state.viewState).toBe('error')
    expect(nodes(root).some(n => n.text === '历史态势加载失败，请重试。')).toBe(true)
    get.mockResolvedValueOnce({ data: [] })
    nodes(root).find(n => n.text === '重试')!.props.onClick()
    await flush(); expect(state.viewState).toBe('empty'); expect(state.error).toBe('')
  } finally { app.unmount() }
})
it('system status ignores a late successful response after unmount', async () => {
  vi.useFakeTimers()
  let finish!: (v: any) => void
  const get = vi.spyOn(api, 'get').mockImplementation(() => new Promise(r => { finish = r }))
  const { app, state } = mountTab(SystemStatusView)
  app.unmount(); finish({ data: { generated_at: 'late' } }); await flush()
  expect(state.status).toBeNull()
  await vi.advanceTimersByTimeAsync(15_000); expect(get).toHaveBeenCalledTimes(1)
})
it('tree failure renders a retry that forces a fresh tree request', async () => {
  const pinia = createPinia(); const store = usePlantsStore(pinia)
  store.treeError = 'offline'; const fetch = vi.spyOn(store, 'fetchTree').mockResolvedValue(null)
  const app = renderer.createApp({ ...PlantTree, render: templateRender(treeSource) }); app.use(pinia); app.provide(ssrContextKey, { modules: new Set() })
  const root = host(); app.mount(root)
  const nodes = (n: Host): Host[] => [n, ...n.children.flatMap(nodes)]
  try {
    const retry = nodes(root).find(n => n.text === '重试')
    expect(retry).toBeDefined(); retry!.props.onClick()
    expect(fetch).toHaveBeenLastCalledWith(true)
  } finally { app.unmount() }
})
it('dashboard selects and expands the route plant after tree readiness and follows a reused route', async () => {
  const pinia = createPinia(); const store = usePlantsStore(pinia)
  route.query.plant = '厂B'
  let finish!: (v: any) => void
  vi.spyOn(store, 'fetchTree').mockImplementation(() => new Promise(r => { finish = r }))
  const expand = vi.spyOn(store, 'expandTo')
  const app = renderer.createApp({ ...DashboardView, render: () => null }); app.use(pinia); app.provide(ssrContextKey, { modules: new Set() }); app.mount(host())
  try {
    store.tree = { cities: [], ungrouped: [{ plant_id: '厂A' }, { plant_id: '厂B' }] } as any
    finish(store.tree); await flush()
    expect(store.activePlant).toBe('厂B'); expect(expand).toHaveBeenCalledWith('厂B')
    route.query.plant = '厂A'; await flush(); expect(store.activePlant).toBe('厂A')
  } finally { app.unmount() }
})
// Compile the actual SFC template for the in-memory Vue renderer: the test runs
// real refs, v-if teardown, event handlers and DOM text without needing jsdom.
function templateRender(source: string) {
  const { descriptor } = parse(source)
  const bindings = compileScript(descriptor, { id: 'monitoring' }).bindings
  return new Function('Vue', compile(descriptor.template!.content, { mode: 'function', prefixIdentifiers: true, bindingMetadata: bindings }).code)(Vue)
}
const boardRender = templateRender(boardSource)
;(PageState as any).render = templateRender(pageStateSource)
function mountBoard() {
  const pinia = createPinia(); const store = usePlantsStore(pinia)
  const dashboard = { plant_id: '厂A', window_hours: 24, influent_points: 0, effluent_points: 2,
    indicators: { COD: { label: 'COD', unit: 'mg/L', status: 'normal', influent: null, effluent: 2,
      series: { influent: [], effluent: [{ time: '2026-01-01 00:00:00', value: 1 }, { time: '2026-01-01 01:00:00', value: 2 }] } } },
    data_context: { origin: 'real', mode: 'historical', freshness: 'historical' } } as any
  vi.spyOn(store, 'fetchDashboard').mockImplementation(async () => { store.dashboard = dashboard; return dashboard })
  const app = renderer.createApp({ ...PlantBoardPanel, render: boardRender }, { plantId: '厂A' })
  app.use(pinia); app.provide(ssrContextKey, { modules: new Set() }); const root = host(); app.mount(root)
  return { app, root, store, state: (app._instance as any).setupState }
}
it('unobserves replaced refs and every chart removed by a new query', async () => {
  vi.useFakeTimers()
  const observer = { observe: vi.fn(), unobserve: vi.fn(), disconnect: vi.fn() }
  vi.stubGlobal('ResizeObserver', class { observe = observer.observe; unobserve = observer.unobserve; disconnect = observer.disconnect })
  const { app, store, state } = mountBoard()
  try {
    await flush()
    const initial = observer.observe.mock.calls[observer.observe.mock.calls.length - 1]![0]
    const replacement = host()
    state.setChartRef('COD', replacement)
    expect(observer.unobserve).toHaveBeenCalledWith(initial)
    state.setChartRef('COD', null)
    expect(observer.unobserve).toHaveBeenCalledWith(replacement)
    state.setChartRef('COD', replacement)
    store.dashboard = null
    await flush()
    expect(observer.unobserve.mock.calls.filter(([el]) => el === replacement)).toHaveLength(2)
  } finally { app.unmount() }
  expect(observer.disconnect).toHaveBeenCalledOnce()
})
it('starts historical replay at runtime, advances its cursor and keeps the live lamp off', async () => {
  vi.useFakeTimers()
  const { app, root, state } = mountBoard()
  const nodes = (n: Host): Host[] => [n, ...n.children.flatMap(nodes)]
  try {
    await flush(); state.stopReplay(); await flush()
    const replay = nodes(root).find(n => n.text.includes('▶ 历史回放'))!
    replay.props.onClick()
    await flush()
    expect(state.replaying).toBe(true)
    expect(nodes(root).some(n => n.text === '历史回放')).toBe(true)
    expect(nodes(root).find(n => String(n.props.class).includes('live-dot'))?.props.class).not.toMatch(/\bon\b/)
    await vi.advanceTimersByTimeAsync(1600)
    expect(state.cursor).toBe(1)
  } finally { app.unmount() }
})
it('rejects reversed custom dates before making a request and retains a successful query on retry failure', async () => {
  const pinia = createPinia()
  const store = usePlantsStore(pinia)
  store.activePlant = '厂A'
  vi.spyOn(store, 'fetchTree').mockResolvedValue(null)
  const api = vi.spyOn(plantsService, 'dashboard').mockResolvedValue({ success: true, data: { plant_id: '厂A', window_hours: 24, indicators: {}, influent_points: 1, effluent_points: 1 } })
  const app = renderer.createApp({ ...MetricsView, render: () => null })
  app.use(pinia); app.provide(ssrContextKey, { modules: new Set() }); app.mount(host())
  await flush()
  const state = (app._instance as any).setupState
  state.customRange = { start: '2026-10-15', end: '2026-10-01' }
  const calls = api.mock.calls.length
  await state.load()
  expect(api).toHaveBeenCalledTimes(calls)
  expect(state.rangeError).toBe('结束日期不能早于开始日期')
  state.customRange = { start: '', end: '' }
  api.mockRejectedValueOnce(new Error('refresh failed'))
  await state.load()
  expect(state.dashboard?.plant_id).toBe('厂A')
  expect(state.viewState).toBe('error')
  app.unmount()
})
it('does not select a plant when the automatic tree request resolves after dashboard unmount', async () => {
  const pinia = createPinia(); const store = usePlantsStore(pinia)
  let resolve!: (value: any) => void
  vi.spyOn(store, 'fetchTree').mockImplementation(() => new Promise(r => { resolve = r }))
  const app = renderer.createApp({ ...DashboardView, render: () => null })
  app.use(pinia); app.provide(ssrContextKey, { modules: new Set() }); app.mount(host()); app.unmount()
  resolve({ ungrouped: [{ plant_id: 'too-late' }] }); await flush()
  expect(store.activePlant).toBe('')
})
it.each(['plant', 'route', 'unmount', 'unchanged', 'refresh'])('checks the assistant dashboard lease after a deferred tree request: %s', async change => {
  route.path = '/dashboard'
  const pinia = createPinia(), store = usePlantsStore(pinia)
  store.activePlant = 'original'
  store.tree = { cities: [], ungrouped: [{ plant_id: 'requested' }] } as any
  const fetch = vi.spyOn(store, 'fetchTree').mockResolvedValue(null)
  const app = renderer.createApp({ ...DashboardView, render: () => null })
  app.use(pinia); app.provide(ssrContextKey, { modules: new Set() }); app.mount(host())
  const context = useAssistantContextStore(pinia), actions = useActionStore(pinia)
  const dispatch = vi.spyOn(actions, 'dispatch')
  let finish!: (value: any) => void
  fetch.mockImplementationOnce(() => new Promise(resolve => { finish = resolve }))
  const router = { currentRoute: { value: route }, push: vi.fn() } as any
  const pending = executeAssistantAction({ capability: 'dashboard.view', parameters: { plant: 'requested', indicator: 'COD' } }, context.snapshot(), router)
  try {
    if (change === 'plant') { store.activePlant = 'user-selected'; await flush() }
    if (change === 'route') { route.path = '/events'; await flush() }
    if (change === 'unmount') app.unmount()
    if (change === 'refresh') context.register('refresh-test', { ...context.snapshot()!, freshness: 'updated' })
    finish(null)
    const result = await pending
    expect(result.success).toBe(change === 'unchanged' || change === 'refresh')
    expect(store.activePlant).toBe(change === 'unchanged' || change === 'refresh' ? 'requested' : change === 'plant' ? 'user-selected' : 'original')
    expect(dispatch).toHaveBeenCalledTimes(change === 'unchanged' || change === 'refresh' ? 1 : 0)
  } finally { if (change !== 'unmount') app.unmount(); route.path = '/dashboard' }
})
it('captures the dashboard lease after cross-page assistant navigation', async () => {
  route.path = '/events'
  const pinia = createPinia(), store = usePlantsStore(pinia), context = useAssistantContextStore(pinia)
  store.activePlant = 'original'
  store.tree = { cities: [], ungrouped: [{ plant_id: 'requested' }] } as any
  vi.spyOn(store, 'fetchTree').mockResolvedValue(null)
  context.register('events', { route: '/events', pageId: 'events', objectId: 'event-one' })
  const frozen = context.snapshot()
  const app = renderer.createApp({ ...DashboardView, render: () => null })
  app.use(pinia); app.provide(ssrContextKey, { modules: new Set() })
  const router = { currentRoute: { value: route }, push: vi.fn(async () => { route.path = '/dashboard'; app.mount(host()) }) } as any
  try {
    const result = await executeAssistantAction({ capability: 'dashboard.view', parameters: { plant: 'requested', indicator: 'COD' } }, frozen, router)
    expect(result.success).toBe(true)
    expect(router.push).toHaveBeenCalledWith('/dashboard')
    expect(store.activePlant).toBe('requested')
  } finally { app.unmount(); route.path = '/dashboard' }
})
it.each(['plant', 'route', 'unmount', 'unchanged', 'refresh'])('checks the assistant metrics lease after a deferred tree request: %s', async change => {
  route.path = '/metrics'
  const pinia = createPinia(), store = usePlantsStore(pinia)
  store.activePlant = 'original'
  store.tree = { cities: [], ungrouped: [{ plant_id: 'requested' }] } as any
  const fetch = vi.spyOn(store, 'fetchTree').mockResolvedValue(null)
  vi.spyOn(plantsService, 'dashboard').mockResolvedValue({ success: true, data: { plant_id: 'requested', window_hours: 24, indicators: {}, influent_points: 1, effluent_points: 1 } })
  const app = renderer.createApp({ ...MetricsView, render: () => null })
  app.use(pinia); app.provide(ssrContextKey, { modules: new Set() }); app.mount(host())
  await flush(); await flush()
  const state = (app._instance as any).setupState, context = useAssistantContextStore(pinia)
  let finish!: (value: any) => void
  fetch.mockImplementationOnce(() => new Promise(resolve => { finish = resolve }))
  const router = { currentRoute: { value: route }, push: vi.fn() } as any
  const pending = executeAssistantAction({ capability: 'metrics.filter', parameters: { plant: 'requested', indicator: 'TN' } }, context.snapshot(), router)
  try {
    if (change === 'plant') { store.activePlant = 'user-selected'; await flush() }
    if (change === 'route') { route.path = '/events'; await flush() }
    if (change === 'unmount') app.unmount()
    if (change === 'refresh') context.register('refresh-test', { ...context.snapshot()!, freshness: 'updated' })
    finish(null)
    const result = await pending
    expect(result.success).toBe(change === 'unchanged' || change === 'refresh')
    expect(store.activePlant).toBe(change === 'unchanged' || change === 'refresh' ? 'requested' : change === 'plant' ? 'user-selected' : 'original')
    expect(state.indicator).toBe(change === 'unchanged' || change === 'refresh' ? 'TN' : 'COD')
  } finally { if (change !== 'unmount') app.unmount(); route.path = '/dashboard' }
})
it('explains a missing water side and offers a retry', async () => {
  const html = await renderBoard()
  expect(html).toContain('缺少进水数据')
  expect(html).toContain('重试')
})

it('attaches a verified influent annotation to the influent series, not effluent', async () => {
  vi.useFakeTimers()
  const pinia = createPinia(), store = usePlantsStore(pinia), actions = useActionStore(pinia)
  const data = { plant_id: '厂A', window_hours: 24, segment_start: '2026-07-01 00:00:00', segment_end: '2026-07-02 00:00:00',
    indicators: { TN: { label: '总氮', unit: '', limit: 15, status: 'normal', influent: 20, effluent: 3,
      series: { influent: [{ time: '2026-07-01 08:00:00', value: 20 }], effluent: [{ time: '2026-07-01 08:00:00', value: 3 }] } } },
    influent_points: 1, effluent_points: 1, data_context: { bucket: 'real', timezone: 'Asia/Shanghai' } }
  store.dashboard = data as any
  vi.spyOn(store, 'fetchDashboard').mockResolvedValue(data as any)
  const app = renderer.createApp({ ...PlantBoardPanel, render: () => null }, { plantId: '厂A' })
  app.use(pinia); app.provide(ssrContextKey, { modules: new Set() }); app.mount(host())
  try {
    await flush()
    const state = (app._instance as any).setupState
    state.stopReplay()
    actions.annotations = [{ timestamp: '2026-07-01 08:00:00', value: 20, type: 'iforest' }]
    actions.annotationIndicator = 'TN'
    ;(actions as any).annotationContext = { plant: '厂A', source: 'real', start: data.segment_start, end: data.segment_end, side: 'influent', indicator: 'TN', algorithm: 'iforest' }
    const setOption = vi.fn()
    state.charts.set('TN', { setOption, resize: vi.fn(), dispose: vi.fn() })
    state.renderAll()
    const series = setOption.mock.calls[setOption.mock.calls.length - 1]![0].series
    expect(series.find((s: any) => s.name === '进水').markPoint?.data ?? []).toHaveLength(1)
    expect(series.find((s: any) => s.name === '出水').markPoint?.data ?? []).toHaveLength(0)
  } finally { app.unmount() }
})

it.each(['influent', 'effluent'] as const)('verifies applied %s markers and zero results against the actual chart option', async side => {
  vi.useFakeTimers()
  const pinia = createPinia(), store = usePlantsStore(pinia)
  const data = { plant_id: '厂B', window_hours: 24, segment_start: '2026-07-01 00:00:00', segment_end: '2026-07-02 00:00:00',
    indicators: { COD: { label: 'COD', unit: '', limit: null, status: 'normal', influent: 20, effluent: 3,
      series: { influent: [{ time: '2026-07-01 10:00:00', value: 20 }], effluent: [{ time: '2026-07-01 10:00:00', value: 3 }] } } },
    influent_points: 1, effluent_points: 1, data_context: { bucket: 'real', timezone: 'Asia/Shanghai' } }
  store.dashboard = data as any
  vi.spyOn(store, 'fetchDashboard').mockResolvedValue(data as any)
  const app = renderer.createApp({ ...PlantBoardPanel, render: () => null }, { plantId: '厂B' })
  app.use(pinia); app.provide(ssrContextKey, { modules: new Set() }); app.mount(host())
  try {
    await flush()
    const state = (app._instance as any).setupState
    let option: any = {}
    state.charts.set('COD', { setOption: (value: any) => { option = value }, getOption: () => option, resize: vi.fn(), dispose: vi.fn() })
    const binding = { plant: '厂B', source: 'real', start: data.segment_start, end: data.segment_end, indicator: 'COD', side, algorithm: 'iforest' }
    const annotation = { timestamp: '2026-07-01T02:00:00Z', value: side === 'influent' ? 20 : 3, type: '离群' }
    const result = await state.applyAssistantAnnotations([annotation], binding)
    expect(result.success).toBe(true)
    expect(result.details.visible_count).toBe(1)
    expect(state.replaying).toBe(false)
    const empty = await state.applyAssistantAnnotations([], binding)
    expect(empty.success).toBe(true)
    expect(empty.code).toBe('empty')
    expect(empty.details.visible_count).toBe(0)
    const invalid = await state.applyAssistantAnnotations([{ ...annotation, value: 500 }], binding)
    expect(invalid.success).toBe(false)
    expect(invalid.code).toBe('unmatched_annotations')
    store.dashboard = { ...data, data_context: { ...data.data_context, bucket: 'simulated' } } as any
    await flush()
    expect(useActionStore(pinia).annotationContext).toBeNull()
  } finally { app.unmount() }
})
