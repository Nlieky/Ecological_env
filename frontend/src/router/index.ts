import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/dashboard'
    },
    {
      path: '/dashboard',
      component: () => import('@/views/Dashboard.vue'),
      meta: { title: '监测大屏' }
    },
    {
      path: '/chat',
      component: () => import('@/views/AIOpsChat.vue'),
      meta: { title: 'AI助手' }
    },
    {
      path: '/events',
      component: () => import('@/views/EventCenter.vue'),
      meta: { title: '事件中心' }
    },
    {
      path: '/logs',
      component: () => import('@/views/Logs.vue'),
      meta: { title: '系统日志' }
    },
    {
      path: '/observability',
      redirect: '/observability/tracing'
    },
    {
      path: '/observability/tracing',
      component: () => import('@/views/TraceObservability.vue'),
      meta: { title: '链路追踪' }
    },
    {
      path: '/observability/metrics',
      component: () => import('@/views/TraceObservability.vue'),
      meta: { title: '指标查询' }
    },
    {
      path: '/logs/query',
      component: () => import('@/views/Logs.vue'),
      meta: { title: '日志查询' }
    }
  ]
})

export default router
