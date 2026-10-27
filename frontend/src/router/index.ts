import { createRouter, createWebHistory } from 'vue-router'
import AdminShell from '@/layout/AdminShell.vue'
import { featureMeta } from '@/config/featureRegistry'

// 占位页懒加载（所有 Phase B 占位路由共用，props 由 route.meta 注入）
const Placeholder = () => import('@/views/PlaceholderView.vue')

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/chat' },
    {
      path: '/',
      component: AdminShell,
      children: [
        // ── 智能助手 ──
        { path: 'chat', component: () => import('@/views/AIOpsChatView.vue'),
          meta: featureMeta('/chat') },
        { path: 'agents/config', component: () => import('@/views/AgentConfigView.vue'),
          meta: featureMeta('/agents/config') },
        { path: 'agents/audit', component: () => import('@/views/AgentAuditView.vue'),
          meta: featureMeta('/agents/audit') },
        { path: 'agents/knowledge', component: () => import('@/views/KnowledgeGraphView.vue'),
          meta: featureMeta('/agents/knowledge') },
        // ── 监控大屏 ──
        { path: 'dashboard', component: () => import('@/views/DashboardView.vue'),
          meta: featureMeta('/dashboard') },
        // 旧单厂路由：已并入 /dashboard 仪表盘 tab（看板列表选厂），重定向兼容
        { path: 'plants/:plantId', redirect: to => ({ path: '/dashboard', query: { plant: to.params.plantId } }) },
        // 厂区配置独立页（数据域配置，从智能体配置页拆出，归监控大屏组末位）
        { path: 'plants/config', component: () => import('@/views/PlantsConfigView.vue'),
          meta: featureMeta('/plants/config') },
        { path: 'metrics', component: () => import('@/views/MetricsView.vue'),
          meta: featureMeta('/metrics') },
        { path: 'logs', component: () => import('@/views/LogsView.vue'),
          meta: featureMeta('/logs') },
        { path: 'logs/trace/:id', component: () => import('@/views/TraceView.vue'),
          meta: { title: '会话追溯', group: '监控大屏' } },
        { path: 'tracing', component: () => import('@/views/TracingView.vue'),
          meta: featureMeta('/tracing') },
        { path: 'datasources', component: () => import('@/views/DatasourcesView.vue'),
          meta: featureMeta('/datasources') },
        { path: 'alerts', component: () => import('@/views/AlertCenterView.vue'),
          meta: featureMeta('/alerts') },
        { path: 'grafana', component: () => import('@/views/GrafanaView.vue'),
          meta: featureMeta('/grafana') },
        { path: 'experimental', component: () => import('@/views/ExperimentalFeaturesView.vue'),
          meta: featureMeta('/experimental') },
        // ── 事件中心 ──
        { path: 'events', component: () => import('@/views/EventCenterView.vue'),
          meta: featureMeta('/events') },
        { path: 'event-sources', component: Placeholder,
          meta: { ...featureMeta('/event-sources'), phTitle: '事件源',
            phDesc: '事件来源（双数据流等）配置',
            phHint: 'Phase B' } },
        // ── 设置 ──
        { path: 'settings', component: Placeholder,
          meta: { ...featureMeta('/settings'), phTitle: '系统设置',
            phDesc: '系统与 LLM 配置',
            phHint: 'Phase B' } },
      ],
    },
  ],
})

router.afterEach((to) => {
  const t = typeof to.meta?.title === 'string' && to.meta.title.trim()
    ? `${to.meta.title} - 废水监测系统` : '废水监测智能体系统'
  document.title = t
})

export default router
