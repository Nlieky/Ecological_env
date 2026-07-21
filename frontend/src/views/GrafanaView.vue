<template>
  <div class="gf">
    <div class="bar">
      <div>
        <span class="ttl">Grafana 大屏</span>
        <span class="sub">废水监测双数据流 · Prometheus 实时指标</span>
      </div>
      <a class="open" :href="dashUrl" target="_blank" rel="noopener">↗ 在新窗口打开</a>
    </div>
    <div class="frame-wrap">
      <iframe v-if="!failed" :src="dashUrl" class="frame" @load="onLoad" referrerpolicy="no-referrer" />
      <div v-if="failed" class="fallback">
        <div class="fb-ttl">⚠ 无法在页面内嵌入 Grafana</div>
        <div class="fb-d">Grafana 默认禁止 iframe 嵌入。请在 Grafana 配置里开启：</div>
        <pre class="fb-code">[security]
allow_embedding = true

[auth.anonymous]
enabled = true
org_role = Viewer</pre>
        <div class="fb-d">改完后重启 Grafana，并刷新本页。或直接<a :href="dashUrl" target="_blank" rel="noopener">在新窗口打开 ↗</a></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'

const GRAFANA_BASE = 'http://localhost:3000'
const DASH_UID = 'wastewater-dual-stream'
const dashUrl = `${GRAFANA_BASE}/d/${DASH_UID}/_?kiosk=tv`

const failed = ref(false)
const loaded = ref(false)
let timer: ReturnType<typeof setTimeout> | null = null

function onLoad() { loaded.value = true }

onMounted(() => {
  // 若 8 秒内 iframe 没 load 事件（被 X-Frame-Options 拦），显示兜底说明
  timer = setTimeout(() => { if (!loaded.value) failed.value = true }, 8000)
})
onBeforeUnmount(() => { if (timer) clearTimeout(timer) })
</script>

<style scoped>
.gf { display: flex; flex-direction: column; gap: 12px; height: calc(100vh - var(--header-height) - 40px) }
.bar { display: flex; justify-content: space-between; align-items: center }
.ttl { font-size: 16px; font-weight: 700 }
.sub { font-size: 12px; color: var(--text-muted); margin-left: 10px }
.open { font-size: 13px; color: var(--primary); text-decoration: none; border: 1px solid var(--brd);
  padding: 6px 12px; border-radius: 8px; background: var(--card-bg) }
.open:hover { border-color: var(--primary) }
.frame-wrap { flex: 1; min-height: 0; background: var(--card-bg); border: 1px solid var(--brd); border-radius: 13px; overflow: hidden }
.frame { width: 100%; height: 100%; border: 0; display: block }
.fallback { padding: 40px; text-align: center; color: var(--text-secondary) }
.fb-ttl { font-size: 16px; font-weight: 700; color: var(--danger); margin-bottom: 12px }
.fb-d { font-size: 13px; margin: 8px 0 }
.fb-code { display: inline-block; text-align: left; background: #0f172a; color: #e2e8f0; padding: 12px 16px;
  border-radius: 9px; font-size: 12px; margin: 12px 0 }
.fb-d a { color: var(--primary) }
</style>
