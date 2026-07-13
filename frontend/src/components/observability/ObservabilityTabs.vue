<template>
  <div v-if="tabs.length" class="observability-tabs">
    <button
      v-for="tab in tabs"
      :key="tab.key"
      type="button"
      class="tab-button"
      :class="{ active: isActive(tab) }"
      @click="goToTab(tab)"
    >
      <el-icon><component :is="tab.icon" /></el-icon>
      <span>{{ tab.title }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

interface TabItem {
  key: string
  title: string
  icon: string
  path: string
}

const props = defineProps<{
  group: 'query' | 'datasources' | 'all'
}>()

const route = useRoute()
const router = useRouter()

const tabGroups: Record<string, TabItem[]> = {
  query: [
    { key: 'metrics', title: '指标查询', icon: 'DataAnalysis', path: '/observability/metrics' },
    { key: 'logs', title: '日志查询', icon: 'Search', path: '/logs/query' },
    { key: 'tracing', title: '链路追踪', icon: 'Connection', path: '/observability/tracing' }
  ],
  datasources: [
    { key: 'metric-ds', title: '指标数据源', icon: 'DataBoard', path: '/observability/metrics', query: { tab: 'datasources' } },
    { key: 'log-ds', title: '日志数据源', icon: 'DataBoard', path: '/logs/datasources' },
    { key: 'trace-ds', title: '链路数据源', icon: 'DataBoard', path: '/observability/tracing', query: { tab: 'datasources' } }
  ],
  all: [
    { key: 'overview', title: '概览', icon: 'DataLine', path: '/observability/overview' },
    { key: 'metrics', title: '指标查询', icon: 'DataAnalysis', path: '/observability/metrics' },
    { key: 'logs', title: '日志查询', icon: 'Search', path: '/logs/query' },
    { key: 'tracing', title: '链路追踪', icon: 'Connection', path: '/observability/tracing' },
    { key: 'datasources', title: '数据源', icon: 'DataBoard', path: '/observability/datasources' }
  ]
}

const tabs = computed(() => tabGroups[props.group] || [])

function isActive(tab: TabItem) {
  if (tab.query) {
    return route.path === tab.path && JSON.stringify(route.query) === JSON.stringify(tab.query)
  }
  return route.path === tab.path
}

function goToTab(tab: TabItem) {
  router.push({
    path: tab.path,
    query: tab.query || {}
  })
}
</script>

<style scoped>
.observability-tabs {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 16px;
}

.tab-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  background: #ffffff;
  color: #606266;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-button:hover {
  color: #409eff;
  border-color: #409eff;
}

.tab-button.active {
  background: #409eff;
  color: #ffffff;
  border-color: #409eff;
}

.tab-button .el-icon {
  font-size: 14px;
}
</style>
