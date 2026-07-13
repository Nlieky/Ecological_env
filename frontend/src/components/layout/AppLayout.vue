<template>
  <div class="app-layout">
    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-logo">
        <div class="logo-icon">
          <img src="@/assets/brand-mark.svg" alt="废水监测" class="brand-mark" />
        </div>
        <div class="logo-copy">
          <span class="logo-text">废水监测</span>
          <span class="logo-subtext">智能体系统</span>
        </div>
      </div>

      <el-menu
        :default-active="activeMenu"
        class="sidebar-nav el-menu-vertical"
        :collapse="sidebarCollapsed"
        router
        :collapse-transition="false"
        :default-openeds="['observability', 'events']"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Monitor /></el-icon>
          <template #title><span>监测大屏</span></template>
        </el-menu-item>

        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <template #title><span>AI 助手</span></template>
        </el-menu-item>

        <el-sub-menu index="observability">
          <template #title>
            <el-icon><DataAnalysis /></el-icon>
            <span>可观测性</span>
          </template>
          <el-menu-item index="/observability/tracing">
            <el-icon><Connection /></el-icon>
            <template #title><span>链路追踪</span></template>
          </el-menu-item>
          <el-menu-item index="/observability/metrics">
            <el-icon><TrendCharts /></el-icon>
            <template #title><span>指标查询</span></template>
          </el-menu-item>
          <el-menu-item index="/logs/query">
            <el-icon><Document /></el-icon>
            <template #title><span>日志查询</span></template>
          </el-menu-item>
          <el-menu-item index="/logs">
            <el-icon><Notebook /></el-icon>
            <template #title><span>系统日志</span></template>
          </el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="events">
          <template #title>
            <el-icon><Bell /></el-icon>
            <span>事件中心</span>
          </template>
          <el-menu-item index="/events">
            <el-icon><Warning /></el-icon>
            <template #title><span>告警事件</span></template>
          </el-menu-item>
          <el-menu-item index="/events/sources">
            <el-icon><Setting /></el-icon>
            <template #title><span>事件源配置</span></template>
          </el-menu-item>
        </el-sub-menu>
      </el-menu>
    </aside>

    <div class="main-area">
      <header class="header">
        <div class="header-left">
          <button class="collapse-btn" @click="sidebarCollapsed = !sidebarCollapsed">
            <el-icon><Fold v-if="!sidebarCollapsed" /><Expand v-else /></el-icon>
          </button>
          <span class="breadcrumb">{{ currentTitle }}</span>
        </div>
        <div class="header-right">
          <el-tooltip content="查看废水监测系统介绍" placement="bottom">
            <button class="promo-trigger" type="button" @click="openPromo">
              <el-icon :size="17"><Promotion /></el-icon>
              <span>系统介绍</span>
            </button>
          </el-tooltip>

          <el-tooltip content="打开智能助手" placement="bottom">
            <button class="assistant-trigger" type="button" @click="openAssistant">
              <el-icon :size="18"><Service /></el-icon>
            </button>
          </el-tooltip>

          <el-popover placement="bottom-end" :width="360" trigger="click">
            <template #reference>
              <button class="notice-trigger" type="button">
                <el-badge :value="notificationCount" :max="99" :hidden="!notificationCount">
                  <el-icon :size="18"><Bell /></el-icon>
                </el-badge>
              </button>
            </template>

            <div class="notice-panel">
              <div class="notice-panel__header">
                <div>
                  <div class="notice-panel__title">系统提醒</div>
                  <div class="notice-panel__subtitle">
                    {{ notificationCount ? `当前有 ${notificationCount} 条待关注动态` : '当前暂无待关注动态' }}
                  </div>
                </div>
                <el-button link type="primary" :loading="notificationsLoading" @click="loadNotifications">刷新</el-button>
              </div>

              <div v-if="notificationItems.length" class="notice-list">
                <button
                  v-for="item in notificationItems"
                  :key="item.key"
                  type="button"
                  class="notice-item"
                  @click="goNotification(item)"
                >
                  <div class="notice-item__dot" :class="`is-${item.dotTone}`"></div>
                  <div class="notice-item__body">
                    <div class="notice-item__top">
                      <div class="notice-item__title-wrap">
                        <span class="notice-item__title">{{ item.title }}</span>
                        <el-tag size="small" effect="light" :type="item.tagType">{{ item.tag }}</el-tag>
                      </div>
                      <span class="notice-item__time">{{ formatDateTime(item.time) }}</span>
                    </div>
                    <div class="notice-item__desc">{{ item.description }}</div>
                  </div>
                </button>
              </div>
              <div v-else class="notice-empty">
                <el-icon><Bell /></el-icon>
                <span>告警与事件会在这里实时汇总</span>
              </div>
            </div>
          </el-popover>

          <el-dropdown @command="handleUserCommand">
            <div class="user-trigger">
              <el-avatar :size="36" class="user-avatar">
                <span>管</span>
              </el-avatar>
              <div class="user-meta">
                <span class="user-name">系统管理员</span>
                <span class="user-role">超级管理员</span>
              </div>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="about">关于系统</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <main class="content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" :key="route.path" />
          </transition>
        </router-view>
      </main>
    </div>

    <!-- 悬浮 AI 助手 -->
    <EcoAIOpsWidget />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  Monitor, ChatDotRound, Bell, Document, Connection, Fold, Expand,
  Service, DataAnalysis, TrendCharts, Warning, Setting, Notebook, Promotion
} from '@element-plus/icons-vue'
import { eventsApi } from '@/api/events'
import EcoAIOpsWidget from '@/components/aiops/EcoAIOpsWidget.vue'

const route = useRoute()
const sidebarCollapsed = ref(false)
const notificationsLoading = ref(false)
const notificationItems = ref<any[]>([])
const notificationCount = ref(0)
let notificationTimer: any = null

const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/chat')) return '/chat'
  if (path.startsWith('/observability/tracing')) return '/observability/tracing'
  if (path.startsWith('/observability/metrics')) return '/observability/metrics'
  if (path.startsWith('/logs/query')) return '/logs/query'
  if (path.startsWith('/logs')) return '/logs'
  if (path.startsWith('/events') && path !== '/events') return '/events'
  return path
})

const currentTitle = computed(() => {
  const titles: Record<string, string> = {
    '/dashboard': '监测大屏',
    '/chat': 'AI 智能助手',
    '/observability/tracing': '链路追踪',
    '/observability/metrics': '指标查询',
    '/logs/query': '日志查询',
    '/logs': '系统日志',
    '/events': '告警事件'
  }
  for (const [key, value] of Object.entries(titles)) {
    if (route.path.startsWith(key)) return value
  }
  return '废水监测系统'
})

function formatDateTime(value: string) {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString('zh-CN', {
    hour12: false,
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function loadNotifications() {
  notificationsLoading.value = true
  try {
    const result = await eventsApi.getEvents({ page: 1, pageSize: 6, status: 'pending' })
    const items = (result.data || []).map((item: any) => {
      const severityMap: any = {
        high: { tag: '严重告警', tagType: 'danger', dotTone: 'danger' },
        medium: { tag: '告警提醒', tagType: 'warning', dotTone: 'warning' },
        low: { tag: '信息提醒', tagType: 'info', dotTone: 'info' },
      }
      const meta = severityMap[item.severity] || { tag: '平台提醒', tagType: 'info', dotTone: 'info' }
      return {
        key: `event-${item.id}`,
        title: `${item.type} - ${item.plantId}`,
        description: `时间: ${formatDateTime(item.timestamp)}`,
        time: item.timestamp,
        route: '/events',
        tag: meta.tag,
        tagType: meta.tagType,
        dotTone: meta.dotTone,
      }
    })
    notificationItems.value = items
    notificationCount.value = result.total || 0
  } catch {
    notificationItems.value = []
    notificationCount.value = 0
  } finally {
    notificationsLoading.value = false
  }
}

function goNotification(item: any) {
  if (item?.route && window) {
    window.location.href = item.route
  }
}

function openAssistant() {
  window.dispatchEvent(new Event('ecological-aiops-open'))
}

function openPromo() {
  // 可以在这里添加打开系统介绍页面的逻辑
  console.log('打开系统介绍')
}

function handleUserCommand(command: string) {
  if (command === 'logout') {
    // 添加退出登录逻辑
    console.log('退出登录')
  } else if (command === 'about') {
    // 添加关于系统逻辑
    console.log('关于系统')
  }
}

onMounted(() => {
  void loadNotifications()
  notificationTimer = window.setInterval(() => {
    void loadNotifications()
  }, 60000)
})

onBeforeUnmount(() => {
  if (notificationTimer) {
    window.clearInterval(notificationTimer)
    notificationTimer = null
  }
})
</script>

<style scoped>
.brand-mark {
  width: 24px;
  height: 24px;
  display: block;
}

.assistant-trigger,
.notice-trigger,
.promo-trigger {
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
}

.promo-trigger {
  width: auto;
  min-width: 102px;
  padding: 0 12px;
  gap: 6px;
  color: #5b7fc7;
  border-color: rgba(96, 165, 250, 0.22);
  background: linear-gradient(135deg, rgba(239, 246, 255, 0.92) 0%, rgba(236, 253, 245, 0.74) 100%);
  box-shadow: 0 8px 18px rgba(59, 130, 246, 0.08);
  font-size: 13px;
  font-weight: 700;
}

.promo-trigger:hover {
  color: #3f6fbd;
  border-color: rgba(96, 165, 250, 0.36);
  background: linear-gradient(135deg, rgba(219, 234, 254, 0.98) 0%, rgba(209, 250, 229, 0.84) 100%);
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(59, 130, 246, 0.12);
}

.assistant-trigger {
  position: relative;
  overflow: hidden;
  color: #3b82f6;
  border-color: rgba(96, 165, 250, 0.22);
  background: linear-gradient(135deg, rgba(239, 246, 255, 0.92) 0%, rgba(255, 247, 237, 0.72) 100%);
  box-shadow: 0 8px 18px rgba(59, 130, 246, 0.08);
}

.assistant-trigger::after {
  content: '';
  position: absolute;
  inset: 6px;
  border-radius: 9px;
  border: 1px solid rgba(59, 130, 246, 0.12);
  pointer-events: none;
}

.assistant-trigger:hover {
  color: #2563eb;
  border-color: rgba(96, 165, 250, 0.34);
  background: linear-gradient(135deg, rgba(219, 234, 254, 0.96) 0%, rgba(255, 237, 213, 0.82) 100%);
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(59, 130, 246, 0.12);
}

.notice-trigger:hover {
  color: #356fc8;
  border-color: rgba(96, 165, 250, 0.26);
  background: rgba(239, 246, 255, 0.86);
}

.notice-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.notice-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.notice-panel__title {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.notice-panel__subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.notice-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 420px;
  overflow-y: auto;
  padding-right: 4px;
}

.notice-item {
  width: 100%;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 10px 10px 8px;
  border: 1px solid rgba(226, 232, 240, 0.72);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.92);
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
}

.notice-item:hover {
  border-color: rgba(148, 163, 184, 0.26);
  background: rgba(248, 250, 252, 0.96);
}

.notice-item__dot {
  width: 8px;
  height: 8px;
  margin-top: 6px;
  flex-shrink: 0;
  border-radius: 999px;
  background: #94a3b8;
}

.notice-item__dot.is-danger {
  background: #ef4444;
  box-shadow: 0 0 0 4px rgba(239, 68, 68, 0.08);
}

.notice-item__dot.is-warning {
  background: #f59e0b;
  box-shadow: 0 0 0 4px rgba(245, 158, 11, 0.08);
}

.notice-item__dot.is-info {
  background: #60a5fa;
  box-shadow: 0 0 0 4px rgba(96, 165, 250, 0.08);
}

.notice-item__body {
  min-width: 0;
  flex: 1;
}

.notice-item__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.notice-item__title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.notice-item__title {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}

.notice-item__time {
  flex-shrink: 0;
  font-size: 11px;
  color: #94a3b8;
}

.notice-item__desc {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.55;
  color: #64748b;
}

.notice-empty {
  min-height: 120px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #94a3b8;
  font-size: 12px;
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 40px;
  padding: 2px 4px 2px 2px;
  border-radius: 14px;
  cursor: pointer;
  transition: background 0.2s ease;
}

.user-trigger:hover {
  background: rgba(255, 255, 255, 0.56);
}

.user-avatar {
  background: linear-gradient(135deg, #72c1b5 0%, #5f90c1 58%, #506ba5 100%);
  color: #ffffff;
  box-shadow: 0 8px 18px rgba(80, 107, 165, 0.18);
}

.user-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.user-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}

.user-role {
  font-size: 11px;
  color: var(--text-secondary);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
