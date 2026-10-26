<template>
  <div class="gf">
    <div class="bar">
      <div>
        <span class="ttl">Grafana 大屏</span>
        <span class="sub">未来系统监测 · 未启用，不承担当前废水业务数据显示</span>
      </div>
      <a class="open" :href="dashUrl" target="_blank" rel="noopener">↗ 显式打开外部 Grafana</a>
    </div>
    <div class="frame-wrap">
      <iframe v-if="opened" :src="dashUrl" class="frame" referrerpolicy="no-referrer" title="Grafana 大屏" />
      <div v-else class="empty"><p>Grafana 尚未启用。需要先配置 Grafana、系统监测指标源和仪表盘。</p><button type="button" class="open" @click="opened = true">尝试加载实验仪表盘</button></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
const opened = ref(false)
// 实验入口仅在用户主动选择后访问外部仪表盘。保留原地址配置以兼容现有部署。
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
.empty { padding: 36px; color: var(--text-muted); line-height: 1.8 }
</style>
