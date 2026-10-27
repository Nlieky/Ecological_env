import { createSSRApp, h } from 'vue'
import { createPinia } from 'pinia'
import { renderToString } from '@vue/server-renderer'
import { expect, it } from 'vitest'
import AssistantPanel from '@/components/assistant/AssistantPanel.vue'
import { useAssistantStore } from '@/stores/assistant'

it('shows readable parameter names and actual completion state instead of internal names', async () => {
  const pinia = createPinia()
  useAssistantStore(pinia).messages = [{ id: 'presentation', role: 'assistant', status: 'complete', content: '已准备操作', context: { pageId: 'dashboard', plant: '验收厂', range: { start: 'A', end: 'B' } },
    actions: [{ capability: 'dashboard.detect', parameters: { algorithm: 'iforest', indicator: 'TN', side: 'influent' }, parameter_sources: { algorithm: 'default', indicator: 'explicit', side: 'explicit' } }],
    candidates: [{ state: 'succeeded', receipt: { success: true, message: '已核验曲线标记', details: { visible_count: 2, side: 'influent' } } }] }]
  const app = createSSRApp({ render: () => h(AssistantPanel, { currentContext: { pageId: 'dashboard' } }) })
  app.use(pinia)
  const html = await renderToString(app)
  expect(html).toContain('已完成')
  expect(html).toContain('进水')
  expect(html).toContain('检测算法')
  expect(html).not.toContain('algorithm：')
  expect(html).not.toContain('visible_count')
})
