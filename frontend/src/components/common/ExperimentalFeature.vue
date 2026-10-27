<template>
  <section class="experimental-feature">
    <aside class="notice" aria-label="实验功能说明">
      <div class="heading"><strong>{{ feature.title }}</strong><span>实验功能 · 未投入运行</span></div>
      <p>{{ feature.purpose }}</p>
      <p>依赖：{{ feature.dependency }}</p>
      <p class="hint">当前入口用于预览与接入准备，尚不作为生产业务依据。<RouterLink to="/experimental">查看全部实验功能</RouterLink></p>
    </aside>
    <slot />
  </section>
</template>
<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { FeatureDefinition } from '@/config/featureRegistry'
defineProps<{ feature: FeatureDefinition }>()
</script>
<style scoped>
.notice { padding: 16px 20px; border: 1px solid #e8d8a6; border-radius: 10px; background: #fffaf0; margin-bottom: 20px; color: var(--text-secondary) }
.heading { display: flex; gap: 14px; align-items: center; flex-wrap: wrap }
.heading span { font-size: 12px; color: #82651d }
p { margin: 8px 0 0; line-height: 1.6; font-size: 13px }
.hint { color: var(--text-muted) }
a { margin-left: 10px; color: var(--primary) }
</style>
