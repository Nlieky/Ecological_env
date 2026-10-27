import { createRenderer, ssrContextKey } from 'vue'
import { describe, it, expect, vi } from 'vitest'
import ServiceControl from './ServiceControl.vue'
import { agentConfigService } from '@/api/modules/agentConfig'
import { ElMessage, ElMessageBox } from 'element-plus'
vi.mock('@/api/modules/agentConfig', () => ({ agentConfigService: { serviceStatus: vi.fn(), serviceRestart: vi.fn() } }))
vi.mock('element-plus', () => ({ ElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn() }, ElMessageBox: { confirm: vi.fn().mockResolvedValue(true) } }))
const renderer = createRenderer<any, any>({ createElement: () => ({}), createText: () => ({}), createComment: () => ({}), setText() {}, setElementText() {}, parentNode: () => null, nextSibling: () => null, patchProp() {}, insert() {}, remove() {} })
function mount() {
  const app = renderer.createApp({ ...ServiceControl, render: () => null })
  app.provide(ssrContextKey, { modules: new Set() }); app.mount({})
  return { app, state: (app as any)._instance.setupState }
}
describe('service readiness', () => {
  it('allows only one confirmation and restart when called twice before confirmation resolves', async () => {
    let confirm!: (v: any) => void
    vi.mocked(ElMessageBox.confirm).mockImplementationOnce(() => new Promise(r => { confirm = r }))
    vi.mocked(agentConfigService.serviceRestart).mockResolvedValue({ ok: true, new_ready: true })
    const { app, state } = mount()
    const first = state.doRestart(); const second = state.doRestart()
    expect(ElMessageBox.confirm).toHaveBeenCalledTimes(1)
    confirm(true); await Promise.all([first, second])
    expect(agentConfigService.serviceRestart).toHaveBeenCalledTimes(1)
    app.unmount(); vi.clearAllMocks()
  })
  it('preserves last status but exposes refresh failure, rejecting older successful responses', async () => {
    const ready = { success: true, data: { alive: true, ready: true, port: 8642, pids: [1], model: 'saved', saved_model: 'saved' } }
    vi.mocked(agentConfigService.serviceStatus).mockResolvedValue(ready)
    const { app, state } = mount(); await Promise.resolve(); await Promise.resolve()
    expect(state.status.ready).toBe(true)
    let resolve!: (v: any) => void
    vi.mocked(agentConfigService.serviceStatus).mockImplementationOnce(() => new Promise(r => { resolve = r }))
    const oldRefresh = state.refresh()
    vi.mocked(agentConfigService.serviceStatus).mockRejectedValueOnce(new Error('latest refresh failed'))
    await state.refresh()
    expect(state.statusError).toBe('latest refresh failed')
    expect(state.status.ready).toBe(true)
    resolve({ ...ready, data: { ...ready.data, pids: [2] } }); await oldRefresh
    expect(state.statusError).toBe('latest refresh failed')
    expect(state.status.pids).toEqual([1])
    app.unmount(); vi.clearAllMocks()
  })
  it('warns for reachable but unready restart, without success', async () => {
    vi.mocked(agentConfigService.serviceStatus).mockResolvedValue({ success: true, data: { alive: true, ready: false, port: 8642, pids: [], model: 'saved', saved_model: 'saved' } })
    vi.mocked(agentConfigService.serviceRestart).mockResolvedValue({ ok: true, new_alive: true, new_ready: false })
    const { app, state } = mount(); await state.doRestart()
    expect(ElMessage.success).not.toHaveBeenCalled()
    expect(ElMessage.warning).toHaveBeenCalled()
    app.unmount(); vi.clearAllMocks()
  })
  it('does not refresh or notify after unmount during restart', async () => {
    let resolve!: (v: any) => void
    vi.mocked(agentConfigService.serviceRestart).mockImplementation(() => new Promise(r => { resolve = r }))
    const { app, state } = mount(); const pending = state.doRestart(); await Promise.resolve()
    app.unmount(); const calls = vi.mocked(agentConfigService.serviceStatus).mock.calls.length
    resolve({ ok: true, new_ready: true }); await pending
    expect(agentConfigService.serviceStatus).toHaveBeenCalledTimes(calls)
    expect(ElMessage.success).not.toHaveBeenCalled()
    vi.clearAllMocks()
  })
})
