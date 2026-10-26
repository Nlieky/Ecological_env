import { createSSRApp, h, nextTick } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { createPinia } from 'pinia'
import { expect, it } from 'vitest'
import AssistantPanel from '@/components/assistant/AssistantPanel.vue'
import { useAssistantStore } from '@/stores/assistant'

it('renders candidate receipts and clears the matching pending state', async () => {
  const pinia = createPinia(), store = useAssistantStore(pinia)
  store.messages = [{ id: 'm', role: 'assistant', content: '准备完成', context: { plant: 'A' }, status: 'complete',
    actions: [{ capability: 'dashboard.detect', parameters: { algorithm: 'iforest', side: 'effluent', indicator: 'COD' } }],
    candidates: [{ state: 'succeeded', receipt: { success: true, message: '完成检测', details: { anomaly_count: 2, visible_count: 2, side: 'effluent' } } }] }]
  const app = createSSRApp({ render: () => h(AssistantPanel, { currentContext: {} }) })
  app.use(pinia)
  const html = await renderToString(app)
  expect(html).toContain('已完成')
  expect(html).toContain('检测算法：离群检测')
  expect(html).toContain('进水或出水侧别：出水')
  expect(html).toContain('检出数量：2')
  expect(html).not.toContain('anomaly_count')
  store.messages[0].pending = { capability: 'dashboard.detect', parameters: {}, missing: ['algorithm'], parameter_sources: {}, context: {}, contract_version: '1.0.0' }
  store.pending = store.messages[0].pending
  store.clearPending(); await nextTick()
  expect(store.messages[0].pending).toBeUndefined()
  expect(store.pending).toBeUndefined()
})
