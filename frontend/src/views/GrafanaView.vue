<template>
  <div class="gf">
    <div class="bar">
      <div>
        <span class="ttl">Grafana 大屏</span>
        <span class="sub">废水监测双数据流 · 后端 wastewater_* 指标 → Prometheus → Grafana</span>
      </div>
      <a class="open" :href="dashUrl" target="_blank" rel="noopener">↗ 在新窗口打开</a>
    </div>
    <div class="frame-wrap">
      <iframe :src="dashUrl" class="frame" referrerpolicy="no-referrer" title="Grafana 大屏" />
    </div>
  </div>
</template>

<script setup lang="ts">
// 嵌入用 dashboard：stream_01（uid=wastewater-fixed，双数据流监控面板），kiosk=tv 隐藏顶栏。
// 前提：Grafana 开启匿名 Viewer 访问 + allow_embedding（已验证：kiosk URL 200、无 X-Frame-Options）。
// 若看不到图，点右上"新窗口打开"，或确认 Grafana/Prometheus(:9090)/后端(:8000) 都在跑。
// 地址/UID 外置到 vite 环境变量（frontend/.env 的 VITE_GRAFANA_URL / VITE_GRAFANA_DASH_UID），
// 默认 fallback 本地，部署时改 .env 即可，不用改代码。
const GRAFANA_BASE = import.meta.env.VITE_GRAFANA_URL || 'http://localhost:3000'
const DASH_UID = import.meta.env.VITE_GRAFANA_DASH_UID || 'wastewater-fixed'
const dashUrl = `${GRAFANA_BASE}/d/${DASH_UID}/_?kiosk=tv`
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
</style>
