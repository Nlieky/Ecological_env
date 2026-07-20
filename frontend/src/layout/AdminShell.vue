<template>
  <div class="admin" :class="{ fullscreen: app.fullscreen, cockpit: app.fullscreen }">
    <AppSidebar v-if="!app.fullscreen" />
    <div class="main">
      <AppHeader v-if="!app.fullscreen" />
      <main class="content" :class="{ 'content--fs': app.fullscreen }"><router-view /></main>
    </div>
    <button v-if="app.fullscreen" class="exit-fs" @click="app.setFullscreen(false)">退出全屏 ✕</button>
    <FloatingAssistant />
  </div>
</template>

<script setup lang="ts">
import { watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import FloatingAssistant from '@/components/aiops/FloatingAssistant.vue'

const app = useAppStore()
const route = useRoute()
// 监测大屏是深色沉浸式驾驶舱：进入 /dashboard 自动全屏（隐藏侧栏/顶栏 + .cockpit 深色主题）；
// 离开则退出全屏。immediate 保证刷新/直进 dashboard 时也立即生效（不受 HMR 残留影响）。
watch(() => route.path, (p) => { app.setFullscreen(p === '/dashboard') }, { immediate: true })
</script>

<style scoped>
.admin { display: flex; height: 100vh; overflow: hidden; background: var(--content-bg) }
/* 全屏 = cockpit 深色主题(.cockpit 类已重定义 --card-bg/--brd/--text-* 等) + HUD 网格 */
.admin.fullscreen {
  background: var(--cockpit-bg);
  background-image:
    linear-gradient(var(--hud-grid) 1px, transparent 1px),
    linear-gradient(90deg, var(--hud-grid) 1px, transparent 1px);
  background-size: 46px 46px;
}
.main { flex: 1; display: flex; flex-direction: column; min-width: 0 }
.content { flex: 1; overflow: auto; padding: 20px }
.content--fs { padding: 18px 22px; overflow: auto }
.exit-fs { position: fixed; top: 16px; right: 20px; z-index: 50; border: 1px solid var(--brd);
  background: rgba(255,255,255,.9); color: var(--text-primary); border-radius: 9px; padding: 7px 13px;
  font-size: 12px; cursor: pointer }
</style>
