<template>
  <header class="header">
    <button class="collapse" @click="app.toggleSidebar"><el-icon><Fold v-if="!app.sidebarCollapsed"/><Expand v-else/></el-icon></button>
    <span class="title">{{ currentTitle }}</span>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { Fold, Expand } from '@element-plus/icons-vue'
const app = useAppStore()
const route = useRoute()
const titles: Record<string,string> = { '/chat':'AI 智能助手','/events':'事件中心','/logs':'系统日志','/logs/query':'日志查询','/dashboard':'监测大屏' }
const currentTitle = computed(() => {
  for (const k of Object.keys(titles)) if (route.path.startsWith(k)) return titles[k]
  return '废水监测系统'
})
</script>

<style scoped>
.header{height:var(--header-height);background:#fff;border-bottom:1px solid var(--brd);display:flex;align-items:center;gap:12px;padding:0 18px}
.collapse{border:1px solid var(--brd);background:#fff;border-radius:9px;width:34px;height:34px;cursor:pointer;display:grid;place-items:center}
.title{font-size:15px;font-weight:600;color:var(--text-primary)}
</style>
