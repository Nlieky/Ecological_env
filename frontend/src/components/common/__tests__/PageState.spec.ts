import { createSSRApp, h } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { expect, it } from 'vitest'
import PageState from '../PageState.vue'
import PageShell from '../PageShell.vue'

it('keeps prior content visible on stale data and offers retry', async () => {
  const html = await renderToString(createSSRApp({ render: () => h(PageState, { state: 'stale' }, () => '旧数据') }))
  expect(html).toContain('旧数据'); expect(html).toContain('重试'); expect(html).toContain('数据已陈旧')
  expect(html).not.toContain('刷新失败')
})
it('allows a page to explain its particular state', async () => {
  const html = await renderToString(createSSRApp({ render: () => h(PageState, { state: 'stale', title: '采样时间过早', message: '请重新采样' }) }))
  expect(html).toContain('采样时间过早'); expect(html).toContain('请重新采样')
})
it('blocks empty content but permits explicit retained error content', async () => {
  const render = (preserveContent: boolean) => renderToString(createSSRApp({ render: () => h(PageState, { state: 'error', preserveContent }, () => '已有内容') }))
  expect(await render(false)).not.toContain('已有内容')
  expect(await render(true)).toContain('已有内容')
})
it('renders shell actions and context with contained scrolling', async () => {
  const html = await renderToString(createSSRApp({ render: () => h(PageShell, { title: '页面', subtitle: '说明', scroll: 'contained' }, { actions: () => '主要动作', context: () => '来源', default: () => '内容' }) }))
  for (const text of ['页面', '说明', '主要动作', '来源', '内容', 'page-shell--contained']) expect(html).toContain(text)
})
