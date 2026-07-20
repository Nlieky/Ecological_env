<template>
  <div class="admin">
    <AppSidebar />
    <div class="main">
      <AppHeader />
      <main class="content"><router-view /></main>
    </div>
    <FloatingAssistant />
  </div>
</template>

<script setup lang="ts">
import AppSidebar from '@/components/layout/AppSidebar.vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import FloatingAssistant from '@/components/aiops/FloatingAssistant.vue'
</script>

<style scoped>
/* 常驻布局：侧栏(flex 子项) | 主区(顶栏 + 内容)。无全屏、无条件渲染，最稳健。 */
.admin { display: flex; height: 100vh; overflow: hidden; background: var(--content-bg) }
.main { flex: 1; display: flex; flex-direction: column; min-width: 0 }
.content { flex: 1; overflow: auto; padding: 20px }
</style>
