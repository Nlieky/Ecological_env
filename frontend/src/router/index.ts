import { createRouter, createWebHistory } from 'vue-router'
import CockpitShell from '@/layout/CockpitShell.vue'
import AdminShell from '@/layout/AdminShell.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    {
      path: '/dashboard',
      component: CockpitShell,
      children: [{ path: '', component: () => import('@/views/DashboardView.vue'), meta: { title: '监测大屏' } }],
    },
    {
      path: '/',
      component: AdminShell,
      children: [
        { path: 'chat', component: () => import('@/views/AIOpsChatView.vue'), meta: { title: 'AI 助手' } },
        { path: 'events', component: () => import('@/views/EventCenterView.vue'), meta: { title: '事件中心' } },
        { path: 'logs', component: () => import('@/views/LogsView.vue'), meta: { title: '系统日志' } },
        { path: 'logs/trace/:id', component: () => import('@/views/TraceView.vue'), meta: { title: '会话追溯' } },
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
