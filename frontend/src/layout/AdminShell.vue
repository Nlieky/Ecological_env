<template>
  <div class="admin">
    <AppSidebar />
    <div class="main">
      <AppHeader />
      <main class="content">
        <ExperimentalFeature v-if="experimentalFeature" :feature="experimentalFeature"><router-view /></ExperimentalFeature>
        <router-view v-else />
      </main>
    </div>
    <AssistantHost />
  </div>
</template>

<script setup lang="ts">
import AppSidebar from '@/components/layout/AppSidebar.vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import AssistantHost from '@/components/assistant/AssistantHost.vue'
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { featureByPath } from '@/config/featureRegistry'
import ExperimentalFeature from '@/components/common/ExperimentalFeature.vue'
const route = useRoute()
const experimentalFeature = computed(() => {
  const feature = featureByPath(route.path)
  return feature?.status === 'experimental' ? feature : undefined
})
</script>

<style scoped>
/* 常驻布局：侧栏(flex 子项) | 主区(顶栏 + 内容)。无全屏、无条件渲染，最稳健。 */
.admin { display: flex; height: 100vh; overflow: hidden; background: var(--content-bg) }
.main { flex: 1; display: flex; flex-direction: column; min-width: 0; min-height: 0 }
.content { flex: 1; min-height: 0; min-width: 0; overflow: auto; padding: 20px }
</style>
