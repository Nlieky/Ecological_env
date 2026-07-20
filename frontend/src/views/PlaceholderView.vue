<template>
  <div class="ph">
    <div class="card">
      <div class="icon">🚧</div>
      <div class="t">{{ title }} · 建设中</div>
      <div class="d">{{ desc }}</div>
      <div class="hint" v-if="hint">{{ hint }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const title = computed(() => (route.meta?.phTitle as string) || '页面')
const desc = computed(() => (route.meta?.phDesc as string) || '该模块规划中，将在后续阶段补全。')
const hint = computed(() => (route.meta?.phHint as string) || '')
</script>

<style scoped>
.ph { display: grid; place-items: center; min-height: 60vh }
.card { text-align: center; background: #fff; border: 1px solid var(--brd); border-radius: 14px;
  padding: 44px 56px; box-shadow: 0 1px 3px rgba(0,0,0,.04); max-width: 480px }
.icon { font-size: 40px; margin-bottom: 12px }
.t { font-size: 17px; font-weight: 700; color: var(--text-primary) }
.d { font-size: 13px; color: var(--text-muted); margin-top: 8px; line-height: 1.6 }
.hint { margin-top: 14px; font-size: 12px; color: var(--primary); background: var(--primary-light, #eef2ff);
  border-radius: 8px; padding: 8px 12px }
</style>
