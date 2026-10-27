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
        <el-sub-menu v-for="g in groups" :key="g.title" :index="g.title">
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
    <ExperimentalMenu :collapsed="app.sidebarCollapsed" />
  </aside>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import ExperimentalMenu from './ExperimentalMenu.vue'
import { useAppStore } from '@/stores/app'
import { ChatDotRound, Setting, Document, Monitor, DataAnalysis, Notebook, Tickets, OfficeBuilding, Share, Menu } from '@element-plus/icons-vue'
import type { Component } from 'vue'
import { stableNavigation } from '@/config/featureRegistry'
import type { FeaturePath } from '@/config/featureRegistry'

const groupIcons: Record<string, Component> = {
  智能助手: ChatDotRound,
  监测分析: Monitor,
  事件处置: Tickets,
  系统运维: Notebook,
}
const itemIcons: Partial<Record<FeaturePath, Component>> = {
  '/chat': ChatDotRound,
  '/agents/audit': Document,
  '/agents/knowledge': Share,
  '/agents/config': Setting,
  '/dashboard': Monitor,
  '/metrics': DataAnalysis,
  '/plants/config': OfficeBuilding,
  '/events': Tickets,
  '/logs': Notebook,
}
const defaultIcon = Menu
const groups = stableNavigation().map(group => ({
  ...group,
  icon: groupIcons[group.title] ?? defaultIcon,
  items: group.items.map(item => ({
    ...item,
    icon: itemIcons[item.path as FeaturePath] ?? defaultIcon,
  })),
}))

const app = useAppStore()
const route = useRoute()
const openGroups = groups.map(group => group.title)
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
