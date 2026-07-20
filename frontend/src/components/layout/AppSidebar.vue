<template>
  <aside class="sidebar" :class="{ collapsed: app.sidebarCollapsed }">
    <div class="logo">
      <span class="dot"></span>
      <div v-if="!app.sidebarCollapsed" class="logo-copy">
        <span class="t">废水监测</span>
        <span class="s">智能体系统</span>
      </div>
    </div>
    <el-menu :default-active="route.path" :collapse="app.sidebarCollapsed" router>
      <el-menu-item index="/chat"><el-icon><ChatDotRound/></el-icon><template #title>AI 助手</template></el-menu-item>
      <el-menu-item index="/events"><el-icon><Bell/></el-icon><template #title>事件中心</template></el-menu-item>
      <el-menu-item index="/logs"><el-icon><Notebook/></el-icon><template #title>日志</template></el-menu-item>
      <el-menu-item index="/dashboard"><el-icon><Monitor/></el-icon><template #title>监测大屏</template></el-menu-item>
    </el-menu>
  </aside>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { ChatDotRound, Bell, Notebook, Monitor } from '@element-plus/icons-vue'
const app = useAppStore()
const route = useRoute()
</script>

<style scoped>
.sidebar{width:var(--sidebar-width);background:#fff;border-right:1px solid var(--brd);transition:width var(--transition);overflow:hidden}
.sidebar.collapsed{width:var(--sidebar-collapsed-width)}
.logo{display:flex;align-items:center;gap:10px;padding:14px}
.dot{width:24px;height:24px;border-radius:7px;background:var(--brand-gradient)}
.logo-copy{display:flex;flex-direction:column}
.logo-copy .t{font-size:14px;font-weight:700}
.logo-copy .s{font-size:11px;color:var(--text-muted)}
</style>
