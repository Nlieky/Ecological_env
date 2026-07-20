<template>
  <div class="cockpit">
    <div class="topbar">
      <div class="brand">
        <span class="logo-dot"></span>
        <span class="ttl">运营驾驶舱 · 迷你图矩阵大屏</span>
      </div>
      <div class="meta">
        <span class="pulse"><i></i>实时更新</span>
        <span v-if="realtime.lastUpdate" class="ts">数据更新 {{ realtime.lastUpdate }}</span>
        <router-link to="/chat" class="exit">退出大屏 →</router-link>
      </div>
    </div>
    <main class="content"><router-view/></main>
  </div>
</template>

<script setup lang="ts">
import { useRealtimeStore } from '@/stores/realtime'
import { usePolling } from '@/composables/usePolling'
const realtime = useRealtimeStore()
const { start } = usePolling(() => realtime.fetchRealtime(), 30000)
start()
</script>

<style scoped>
.cockpit{height:100vh;overflow:auto;background:var(--cockpit-bg);color:var(--text-primary);
  background-image:
    linear-gradient(var(--hud-grid) 1px,transparent 1px),
    linear-gradient(90deg,var(--hud-grid) 1px,transparent 1px);
  background-size:46px 46px;padding:18px 22px}
.topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}
.brand{display:flex;align-items:center;gap:10px}
.logo-dot{width:14px;height:14px;border-radius:4px;background:linear-gradient(135deg,var(--cyan),var(--violet))}
.ttl{font-size:18px;font-weight:700}
.meta{display:flex;align-items:center;gap:16px;font-size:12px;color:var(--text-secondary)}
.pulse{display:inline-flex;align-items:center;gap:6px;color:var(--emerald)}
.pulse i{width:7px;height:7px;border-radius:50%;background:var(--emerald);box-shadow:0 0 8px var(--emerald);animation:bl 1.6s infinite}
@keyframes bl{0%,100%{opacity:1}50%{opacity:.35}}
.exit{color:var(--cyan);text-decoration:none;border:1px solid var(--brd);padding:5px 11px;border-radius:9px;font-size:12px}
</style>
