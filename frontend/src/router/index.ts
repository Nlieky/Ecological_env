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
      meta: { title: 'Monitoring Dashboard' }
    },
    {
      path: '/chat',
      component: () => import('@/views/AIOpsChat.vue'),
      meta: { title: 'AI Assistant' }
    },
    {
      path: '/events',
      component: () => import('@/views/EventCenter.vue'),
      meta: { title: 'Event Center' }
    }
  ]
})

export default router
