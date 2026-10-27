<template>
  <div class="experimental-directory">
    <h1>实验功能</h1>
    <p class="intro">以下六项能力尚未投入运行。可查看原有页面，接入所需服务后再评估使用。</p>
    <div class="feature-grid">
      <article v-for="feature in features" :key="feature.path" class="feature-card">
        <header><h2>{{ feature.title }}</h2><span>未投入运行</span></header>
        <p>{{ feature.purpose }}</p>
        <p class="dependency">依赖：{{ feature.dependency }}</p>
        <RouterLink :to="feature.path">查看实验页面 →</RouterLink>
      </article>
    </div>
  </div>
</template>
<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { experimentalFeatures } from '@/config/featureRegistry'
const features = experimentalFeatures()
</script>
<style scoped>
h1 { font-size: 22px; margin: 0 0 10px }
.intro { color: var(--text-muted); margin-bottom: 24px; line-height: 1.6 }
.feature-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 310px), 1fr)); gap: 16px }
.feature-card { padding: 22px; border: 1px solid var(--brd); border-radius: 12px; background: var(--card-bg, #fff) }
header { display: flex; justify-content: space-between; gap: 12px; align-items: center }
h2 { font-size: 16px; margin: 0 }
header span { font-size: 12px; color: #82651d; white-space: nowrap }
p { font-size: 13px; line-height: 1.7 }
.dependency { color: var(--text-muted) }
a { display: inline-block; margin-top: 12px; color: var(--primary); font-size: 13px }
</style>
