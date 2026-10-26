import { createPinia } from 'pinia'
import { createSSRApp, defineComponent, h } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { describe, expect, it, vi } from 'vitest'
import AppSidebar from '../../components/layout/AppSidebar.vue'
import GrafanaView from '../../views/GrafanaView.vue'
import ExperimentalFeaturesView from '../../views/ExperimentalFeaturesView.vue'
import ExperimentalFeature from '../../components/common/ExperimentalFeature.vue'
import ExperimentalMenu from '../../components/layout/ExperimentalMenu.vue'
import router from '../../router'
import {
  FEATURES,
  experimentalFeatures,
  featureByPath,
  stableNavigation,
} from '../featureRegistry'

const testRoute = vi.hoisted(() => ({ path: '/chat' }))
vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('vue-router')>()
  return {
    ...actual,
    createWebHistory: actual.createMemoryHistory,
    useRoute: () => testRoute,
  }
})

async function renderSidebar() {
  const passthrough = defineComponent({
    setup: (_, { slots }) => () => h('div', [slots.title?.(), slots.default?.()]),
  })
  const app = createSSRApp(AppSidebar)
  app.use(createPinia())
  app.use(router)
  for (const name of ['ElScrollbar', 'ElMenu', 'ElSubMenu', 'ElMenuItem', 'ElIcon']) {
    app.component(name, passthrough)
  }
  return renderToString(app)
}

describe('feature registry', () => {
  it('recognizes trailing slash routes for experimental notices and menu highlighting', () => {
    expect(router.resolve('/grafana/').matched.length).toBeGreaterThan(0)
    expect(featureByPath('/grafana/')?.status).toBe('experimental')
    expect(featureByPath('/datasources/')?.title).toBe('可观测性数据源')
  })

  it('highlights the experimental menu for trailing slash detail and directory routes', async () => {
    try {
      for (const path of ['/grafana/', '/experimental/']) {
        testRoute.path = path
        const app = createSSRApp(ExperimentalMenu, { collapsed: false })
        app.use(router)
        const html = await renderToString(app)
        expect(html).toContain('experimental-entry active')
      }
    } finally {
      testRoute.path = '/chat'
    }
  })
  it('describes every experimental feature purpose and dependency', () => {
    for (const feature of experimentalFeatures()) {
      expect(feature).toMatchObject({ purpose: expect.any(String), dependency: expect.any(String) })
    }
  })

  it('shows a separate experimental directory entry', async () => {
    expect(await renderSidebar()).toContain('实验功能')
  })

  it('does not load Grafana before an explicit user action', async () => {
    const html = await renderToString(createSSRApp(GrafanaView))
    expect(html).not.toContain('<iframe')
    expect(html).toContain('未启用')
    expect(html).toContain('未来系统监测')
  })

  it('renders six directory cards with their original destinations and dependencies', async () => {
    const app = createSSRApp(ExperimentalFeaturesView)
    app.use(router)
    const html = await renderToString(app)
    expect((html.match(/<article /g) ?? [])).toHaveLength(6)
    for (const feature of experimentalFeatures()) {
      expect(html).toContain(`href="${feature.path}"`)
      expect(html).toContain(feature.purpose)
      expect(html).toContain(feature.dependency)
    }
    expect((html.match(/未投入运行/g) ?? []).length).toBeGreaterThanOrEqual(6)
  })

  it('keeps the experimental explanation beside each original page content', async () => {
    for (const feature of experimentalFeatures()) {
      const app = createSSRApp({ render: () => h(ExperimentalFeature, { feature }, () => h('div', '原页面内容')) })
      app.use(router)
      const html = await renderToString(app)
      expect(html).toContain(feature.purpose)
      expect(html).toContain(feature.dependency)
      expect(html).toContain('未投入运行')
      expect(html).toContain('原页面内容')
    }
  })
  it('keeps the stable navigation in the approved order', () => {
    expect(stableNavigation().flatMap(group => group.items).map(item => item.path)).toEqual([
      '/chat',
      '/agents/audit',
      '/agents/knowledge',
      '/agents/config',
      '/dashboard',
      '/metrics',
      '/plants/config',
      '/events',
      '/logs',
    ])
  })

  it('classifies and names experimental observability features', () => {
    expect(featureByPath('/grafana')?.status).toBe('experimental')
    expect(featureByPath('/datasources')?.title).toBe('可观测性数据源')
  })

  it('does not leak experimental entries into stable navigation', () => {
    const experimentalPaths = experimentalFeatures().map(feature => feature.path)
    const stablePaths = stableNavigation().flatMap(group => group.items).map(item => item.path)
    expect(stablePaths).not.toEqual(expect.arrayContaining(experimentalPaths))
  })

  it('renders stable entries and hides experimental entries in the ordinary sidebar', async () => {
    const html = await renderSidebar()
    for (const title of ['AI助手', '智能体审计', '知识图谱', '智能体配置', '监测大屏', '指标查询', '厂区配置', '事件中心', '日志中心']) {
      expect(html).toContain(title)
    }
    for (const title of ['Grafana大屏', '链路追踪', '告警中心', '事件源', '系统设置']) {
      expect(html).not.toContain(title)
    }
  })

  it('resolves every registered feature with registry-owned route metadata', () => {
    const routePaths = router.getRoutes().map(route => route.path)
    for (const feature of FEATURES) {
      expect(routePaths).toContain(feature.path)
      const resolved = router.resolve(feature.path)
      expect(resolved.matched.length).toBeGreaterThan(0)
      expect(resolved.meta).toMatchObject({
        title: feature.title,
        group: feature.group,
        featureStatus: feature.status,
      })
    }
  })
})
