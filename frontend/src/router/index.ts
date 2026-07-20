import { createRouter, createWebHistory } from 'vue-router'
import AdminShell from '@/layout/AdminShell.vue'

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
          meta: { title: 'AI 助手', group: '智能助手' } },
        { path: 'agents/config', component: () => import('@/views/AgentConfigView.vue'),
          meta: { title: '智能体配置', group: '智能助手' } },
        { path: 'agents/audit', component: () => import('@/views/AgentAuditView.vue'),
          meta: { title: '智能体审计', group: '智能助手' } },
        // ── 监控大屏 ──
        { path: 'dashboard', component: () => import('@/views/DashboardView.vue'),
          meta: { title: '监测大屏', group: '监控大屏' } },
        { path: 'metrics', component: () => import('@/views/MetricsView.vue'),
          meta: { title: '指标查询', group: '监控大屏' } },
        { path: 'logs', component: () => import('@/views/LogsView.vue'),
          meta: { title: '日志中心', group: '监控大屏' } },
        { path: 'logs/trace/:id', component: () => import('@/views/TraceView.vue'),
          meta: { title: '会话追溯', group: '监控大屏' } },
        { path: 'tracing', component: Placeholder,
          meta: { title: '链路追踪', group: '监控大屏', phTitle: '链路追踪',
            phDesc: '可观测性链路追踪',
            phHint: 'Phase B 接 /api/observability/tracing/*' } },
        { path: 'datasources', component: () => import('@/views/DatasourcesView.vue'),
          meta: { title: '数据源', group: '监控大屏' } },
        { path: 'alerts', component: Placeholder,
          meta: { title: '告警中心', group: '监控大屏', phTitle: '告警中心',
            phDesc: '告警事件汇总与处置',
            phHint: 'Phase B 复用 /api/events' } },
        { path: 'grafana', component: Placeholder,
          meta: { title: 'Grafana 大屏', group: '监控大屏', phTitle: 'Grafana 大屏',
            phDesc: '嵌入 Grafana 双数据流监控面板',
            phHint: 'Phase B：需确认 Grafana 实例在跑且开启 iframe 嵌入' } },
        // ── 事件中心 ──
        { path: 'events', component: () => import('@/views/EventCenterView.vue'),
          meta: { title: '事件中心', group: '事件中心' } },
        { path: 'event-sources', component: Placeholder,
          meta: { title: '事件源', group: '事件中心', phTitle: '事件源',
            phDesc: '事件来源（双数据流等）配置',
            phHint: 'Phase B' } },
        // ── 设置 ──
        { path: 'settings', component: Placeholder,
          meta: { title: '系统设置', group: '设置', phTitle: '系统设置',
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
