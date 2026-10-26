import { createRenderer, ssrContextKey } from 'vue'
import { createPinia } from 'pinia'
import { afterEach, expect, it, vi } from 'vitest'
import AssistantEventCard from '@/components/assistant/AssistantEventCard.vue'
import AssistantHost from '@/components/assistant/AssistantHost.vue'
import { useAssistantContextStore } from '@/stores/assistantContext'
import { assistantService } from '@/api/modules/assistant'
import { eventsService } from '@/api/modules/events'
import { executeAssistantAction } from '@/assistant/executor'
import { useAssistantStore } from '@/stores/assistant'

vi.mock('vue-router', () => ({ useRoute: () => ({ path: '/events' }), useRouter: () => ({}) }))
vi.mock('@/assistant/executor', () => ({ executeAssistantAction: vi.fn() }))
const renderer = createRenderer<any, any>({ createElement: () => ({}), createText: () => ({}), createComment: () => ({}), setText() {}, setElementText() {}, parentNode: () => null, nextSibling: () => null, patchProp() {}, insert() {}, remove() {} })
let cleanup = () => {}
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals() })
function mount(view: any, props: Record<string, unknown> = {}, pinia = createPinia()) {
  const app = renderer.createApp({ ...view, render: () => null }, props)
  app.use(pinia); app.provide(ssrContextKey, { modules: new Set() }); app.mount({})
  cleanup = () => app.unmount()
  return (app as any)._instance.setupState
}
it('cancels a prepared event proposal without confirming or retaining a confirmable proposal', async () => {
  const pinia = createPinia(), context = useAssistantContextStore(pinia)
  context.register('events', { route: '/events', pageId: 'events', objectId: 'e1' })
  vi.spyOn(eventsService, 'detail').mockResolvedValue({ id: 'e1', status: 'pending', updatedAt: 'now' } as any)
  vi.spyOn(assistantService, 'proposeEvent').mockResolvedValue({ proposal_id: 'p1', event_id: 'e1', expires_at: '2099-01-01' } as any)
  const confirm = vi.spyOn(assistantService, 'confirmEvent')
  const state = mount(AssistantEventCard, { context: context.snapshot(), parameters: { eventId: 'e1', new_status: 'resolved', reason: 'reviewed' } }, pinia)
  await state.prepare()
  expect(state.proposal?.proposal_id).toBe('p1')
  expect(typeof state.cancel).toBe('function')
  state.cancel()
  expect(state.proposal).toBeUndefined()
  await state.confirm()
  expect(confirm).not.toHaveBeenCalled()
})
it('records unexpected execution failure and permits retry without an unhandled rejection', async () => {
  vi.stubGlobal('document', { querySelector: () => null, body: {}, querySelectorAll: () => [] })
  vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} })
  vi.stubGlobal('MutationObserver', class { observe() {} disconnect() {} })
  vi.stubGlobal('cancelAnimationFrame', vi.fn())
  vi.mocked(executeAssistantAction).mockRejectedValue(new Error('unexpected executor failure'))
  const state = mount(AssistantHost)
  const action = { capability: 'navigate', parameters: { pageId: 'logs' } }
  const message: any = { id: 'm1', content: 'answer', context: {}, actions: [action] }
  await expect(state.execute(action, message)).resolves.toBeUndefined()
  expect(message.candidates[0].receipt.message).toContain('unexpected executor failure')
  expect(message.content).toBe('answer')
  vi.mocked(executeAssistantAction).mockResolvedValueOnce({ success: false, message: 'retry reached executor' })
  await state.execute(action, message)
  expect(message.candidates[0].receipt.message).toContain('retry reached executor')
})
it('binds preparation and confirmed operation to the captured event while inputs change during requests', async () => {
  const pinia = createPinia(), context = useAssistantContextStore(pinia)
  context.register('events', { route: '/events', pageId: 'events', objectId: 'A' })
  let finishDetail!: (value: any) => void, finishProposal!: (value: any) => void
  vi.spyOn(eventsService, 'detail').mockImplementation(() => new Promise(resolve => { finishDetail = resolve }))
  const propose = vi.spyOn(assistantService, 'proposeEvent').mockImplementation(() => new Promise(resolve => { finishProposal = resolve }))
  vi.spyOn(assistantService, 'confirmEvent').mockResolvedValue({ operation_id: 'op-A' } as any)
  vi.spyOn(assistantService, 'eventOperation').mockResolvedValue({ operation_id: 'op-A', event_id: 'A', new_status: 'resolved', identity: 'local' } as any)
  const state = mount(AssistantEventCard, { context: context.snapshot(), parameters: { eventId: 'A', new_status: 'resolved', reason: 'original reason' } }, pinia)
  const preparing = state.prepare()
  state.target = 'B'; state.newStatus = 'ignored'; state.reason = 'changed reason'
  finishDetail({ id: 'A', status: 'pending', updatedAt: 'now' })
  await Promise.resolve(); await Promise.resolve()
  expect(propose).toHaveBeenCalledWith(expect.objectContaining({ event_id: 'A', new_status: 'resolved', reason: 'original reason' }))
  finishProposal({ proposal_id: 'p-A', event_id: 'A', expires_at: '2099-01-01' })
  await preparing
  await state.confirm()
  expect(useAssistantStore(pinia).messages[0].eventOperation?.eventId).toBe('A')
  expect(useAssistantStore(pinia).messages[0].content).toContain('A')
})
