<template>
  <aside class="sidebar" :class="{ collapsed: app.sidebarCollapsed }">
    <div class="logo">
      <span class="dot"></span>
      <div v-if="!app.sidebarCollapsed" class="logo-copy">
        <span class="t">废水监测</span>
        <span class="s">智能体平台</span>
      </div>
    </div>
    <el-scrollbar class="nav-scroll">
      <el-menu :default-active="route.path" :default-openeds="openGroups" :collapse="app.sidebarCollapsed" router class="nav">
        <el-sub-menu v-for="g in GROUPS" :key="g.title" :index="g.title">
          <template #title>
            <el-icon><component :is="g.icon"/></el-icon>
            <span>{{ g.title }}</span>
          </template>
          <el-menu-item v-for="item in g.items" :key="item.path" :index="item.path">
            <el-icon><component :is="item.icon"/></el-icon>
            <template #title>{{ item.title }}</template>
          </el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-scrollbar>
  </aside>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import {
  ChatDotRound, Setting, Document, Monitor, DataAnalysis, Notebook,
  Connection, Coin, Bell, DataLine, Tickets, Tools, OfficeBuilding, Share,
} from '@element-plus/icons-vue'
import type { Component } from 'vue'

interface NavItem { path: string; title: string; icon: Component }
interface NavGroup { title: string; icon: Component; items: NavItem[] }

const GROUPS: NavGroup[] = [
  { title: '智能助手', icon: ChatDotRound, items: [
    { path: '/chat', title: 'AI 助手', icon: ChatDotRound },
    { path: '/agents/config', title: '智能体配置', icon: Setting },
    { path: '/agents/audit', title: '智能体审计', icon: Document },
    { path: '/agents/knowledge', title: '知识图谱', icon: Share },
  ]},
  { title: '监控大屏', icon: Monitor, items: [
    { path: '/dashboard', title: '监测大屏', icon: Monitor },
    { path: '/metrics', title: '指标查询', icon: DataAnalysis },
    { path: '/logs', title: '日志中心', icon: Notebook },
    { path: '/tracing', title: '链路追踪', icon: Connection },
    { path: '/datasources', title: '数据源', icon: Coin },
    { path: '/alerts', title: '告警中心', icon: Bell },
    { path: '/grafana', title: 'Grafana 大屏', icon: DataLine },
    { path: '/plants/config', title: '厂区配置', icon: OfficeBuilding },
  ]},
  { title: '事件中心', icon: Tickets, items: [
    { path: '/events', title: '事件中心', icon: Tickets },
    { path: '/event-sources', title: '事件源', icon: Connection },
  ]},
  { title: '设置', icon: Tools, items: [
    { path: '/settings', title: '系统设置', icon: Tools },
  ]},
]

const app = useAppStore()
const route = useRoute()
const openGroups = GROUPS.map((g) => g.title)
</script>

<style scoped>
.sidebar { width: var(--sidebar-width); flex-shrink: 0; position: relative; z-index: 10; background: #fff; border-right: 1px solid var(--brd);
  transition: width var(--transition); overflow: hidden; display: flex; flex-direction: column }
.sidebar.collapsed { width: var(--sidebar-collapsed-width) }
.logo { display: flex; align-items: center; gap: 10px; padding: 14px; flex-shrink: 0 }
.dot { width: 24px; height: 24px; border-radius: 7px; background: var(--brand-gradient) }
.logo-copy { display: flex; flex-direction: column }
.logo-copy .t { font-size: 14px; font-weight: 700 }
.logo-copy .s { font-size: 11px; color: var(--text-muted) }
.nav-scroll { flex: 1; min-height: 0 }
.nav { border-right: 0 }
:deep(.el-sub-menu__title) { font-size: 13px; font-weight: 600; color: var(--text-secondary) }
:deep(.el-menu-item) { font-size: 13px; height: 40px; line-height: 40px }
:deep(.el-menu-item.is-active) { color: var(--primary); background: var(--primary-light, #eef2ff) }
</style>
