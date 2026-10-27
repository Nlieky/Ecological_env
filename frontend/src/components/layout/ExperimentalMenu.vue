<template>
  <RouterLink to="/experimental" class="experimental-entry" :class="{ active: featureByPath(route.path)?.path === '/experimental' || featureByPath(route.path)?.status === 'experimental' }" :title="collapsed ? '实验功能' : undefined" aria-label="实验功能">
    <span aria-hidden="true">⚗</span><span v-if="!collapsed">实验功能</span>
  </RouterLink>
</template>
<script setup lang="ts">
import { RouterLink, useRoute } from 'vue-router'
import { featureByPath } from '@/config/featureRegistry'
defineProps<{ collapsed: boolean }>()
const route = useRoute()
</script>
<style scoped>
.experimental-entry { display: flex; gap: 10px; align-items: center; padding: 15px 20px; border-top: 1px solid var(--brd); color: var(--text-muted); text-decoration: none; font-size: 13px; flex-shrink: 0 }
.experimental-entry:visited { color: var(--text-muted) }
.experimental-entry:hover, .experimental-entry.active, .experimental-entry.active:visited { color: #2563eb; background: #eff6ff }
.experimental-entry:focus-visible { outline: 2px solid #2563eb; outline-offset: -3px }
</style>
