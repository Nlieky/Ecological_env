import { createRenderer, nextTick, ssrContextKey } from 'vue'
import { afterEach, describe, it, expect, vi } from 'vitest'
import StrategyPanel from './StrategyPanel.vue'
import ParamsPanel from './ParamsPanel.vue'
import ProvidersPanel from './ProvidersPanel.vue'
import McpPanel from './McpPanel.vue'
import { agentConfigService as api } from '@/api/modules/agentConfig'
vi.mock('@/api/modules/agentConfig', () => ({ agentConfigService: { getStrategy: vi.fn(), saveStrategy: vi.fn(), getParams: vi.fn(), saveParams: vi.fn(), getProviders: vi.fn(), putProvider: vi.fn(), getMcp: vi.fn(), testMcp: vi.fn(), putMcp: vi.fn() } }))
vi.mock('element-plus', () => ({ ElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() }, ElMessageBox: { confirm: vi.fn().mockResolvedValue(true) } }))
const renderer = createRenderer<any, any>({ createElement: () => ({}), createText: () => ({}), createComment: () => ({}), setText() {}, setElementText() {}, parentNode: () => null, nextSibling: () => null, patchProp() {}, insert() {}, remove() {} })
const apps: any[] = []
function mount(component: any) {
  const app = renderer.createApp({ ...component, render: () => null })
  app.provide(ssrContextKey, { modules: new Set() }); app.mount({}); apps.push(app)
  return (app as any)._instance.setupState
}
const flush = async () => { await Promise.resolve(); await Promise.resolve(); await nextTick() }
function deferred() { let resolve!: (value: any) => void; const promise = new Promise<any>(r => { resolve = r }); return { promise, resolve } }
afterEach(() => { apps.splice(0).forEach(a => a.unmount()); vi.clearAllMocks() })
const param = { key: 'temperature', value: 1, default: 1, type: 'int' as const, effect: 'restart' as const, reader: 'client', desc: 'test', read_timing: '初始化读取' }
describe('real configuration panel saves', () => {
  it('does not overwrite manual edits while preparing an assistant draft', async () => {
    vi.mocked(api.getStrategy).mockResolvedValue({ success: true, data: { groups: { style: [{ ...param, key: 'language_constraint', value: 'zh', type: 'enum' as const }] }, params: [] } } as any)
    const s = mount(StrategyPanel); await flush()
    s.draft.language_constraint = 'none'
    const result = await s.prepareAssistantDraft({ language_constraint: 'en' })
    expect(result.success).toBe(false)
    expect(s.draft.language_constraint).toBe('none')
    expect(s.assistantDiff).toEqual([])
  })
  it('keeps an existing unapplied assistant draft and treats it as dirty', async () => {
    vi.mocked(api.getStrategy).mockResolvedValue({ success: true, data: { groups: { style: [{ ...param, key: 'language_constraint', value: 'zh', type: 'enum' as const }] }, params: [] } } as any)
    const s = mount(StrategyPanel); await flush()
    expect((await s.prepareAssistantDraft({ language_constraint: 'en' })).success).toBe(true)
    expect(s.dirty).toBe(true)
    expect((await s.prepareAssistantDraft({ language_constraint: 'none' })).success).toBe(false)
    expect(s.assistantDiff[0].after).toBe('en')
  })
  it('strategy baseline follows only applied captured values and retains restart hint', async () => {
    vi.mocked(api.getStrategy).mockResolvedValue({ success: true, data: { groups: { style: [{ ...param, key: 'style' }] }, params: [param] } })
    const s = mount(StrategyPanel); await flush(); s.draft.style = 2
    const pending = deferred(); vi.mocked(api.saveStrategy).mockReturnValue(pending.promise)
    const save = s.saveStrategy(); s.draft.style = 3
    pending.resolve({ success: true, applied_keys: ['style'], effects: { style: 'restart' }, restart_needed: true }); await save
    expect(s.draft.style).toBe(3); expect(s.dirty).toBe(true)
    s.draft.style = 2; expect(s.dirty).toBe(false)
    s.paramDraft.temperature = 2
    vi.mocked(api.saveParams).mockResolvedValue({ success: true, applied_keys: ['temperature'], effects: { temperature: 'immediate' }, restart_needed: false })
    await s.saveParams(); expect(s.restartHint).toBe(true); expect(s.dirty).toBe(false)
  })
  it('standalone params never submits masked secrets or clears newer draft', async () => {
    vi.mocked(api.getParams).mockResolvedValue({ success: true, data: [{ ...param, key: 'api_key', type: 'secret', value: '•••' }] })
    const s = mount(ParamsPanel); await flush(); expect(s.draft.api_key).toBe('')
    s.draft.api_key = 'captured'; const pending = deferred(); vi.mocked(api.saveParams).mockReturnValue(pending.promise)
    const save = s.save(); s.draft.api_key = 'newer'
    pending.resolve({ success: true, applied_keys: ['api_key'], restart_needed: true, effects: { api_key: 'restart' } }); await save
    expect(s.draft.api_key).toBe('newer'); expect(s.dirty).toBe(true)
    expect(api.getParams).toHaveBeenCalledTimes(1)
  })
  it('provider preserves edits made during save and rejects explicit failure', async () => {
    vi.mocked(api.getProviders).mockResolvedValue({ success: true, data: { providers: [], eligible: [], current_default: '' } })
    const s = mount(ProvidersPanel); await flush(); s.openCreate(); s.form.name = 'p'; s.form.model = 'captured'
    const pending = deferred(); vi.mocked(api.putProvider).mockReturnValue(pending.promise)
    const save = s.save(); s.form.model = 'newer'; pending.resolve({ success: true }); await save
    expect(s.showForm).toBe(true); expect(s.form.model).toBe('newer'); expect(s.dirty).toBe(true)
    vi.mocked(api.putProvider).mockResolvedValue({ success: false }); await s.save()
    expect(s.showForm).toBe(true); expect(s.dirty).toBe(true)
  })
  it('MCP changed configuration invalidates successful and pending tests', async () => {
    vi.mocked(api.getMcp).mockResolvedValue({ success: true, data: { servers: {}, presets: [] } })
    const s = mount(McpPanel); await flush(); s.showAdd = true; s.addForm.name = 'mcp'
    vi.mocked(api.testMcp).mockResolvedValue({ ok: true, tools_seen: 2 }); await s.testAdd(); expect(s.testedAdd).toBe(true)
    s.addForm.command = 'different'; expect(s.testedAdd).toBe(null)
    const pending = deferred(); vi.mocked(api.testMcp).mockReturnValue(pending.promise)
    const test = s.testAdd(); s.addForm.timeout = 90; pending.resolve({ ok: true, tools_seen: 2 }); await test
    expect(s.testedAdd).toBe(null); expect(s.dirty).toBe(true)
    await s.add(); expect(api.putMcp).not.toHaveBeenCalled()
  })
})
