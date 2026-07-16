<template>
  <div class="logs-page">
    <!-- Hero Section -->
    <section class="hero panel">
      <div>
        <p class="eyebrow">Log Center</p>
        <h2>系统日志查询</h2>
        <p class="subtitle">查询 API 调用、智能体决策、算子执行、LLM 调用等系统日志</p>
      </div>
      <div class="hero-actions">
        <el-button @click="loadLogs" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button type="primary" @click="runQuery" :loading="loading">
          <el-icon><Search /></el-icon>
          查询
        </el-button>
      </div>
    </section>

    <!-- Filter Section -->
    <section class="panel">
      <div class="panel-head">
        <h3>日志筛选</h3>
      </div>
      <el-form :inline="true" :model="filterForm" label-width="80px">
        <el-form-item label="日志类型">
          <el-select v-model="filterForm.log_type" placeholder="选择类型" style="width: 150px">
            <el-option label="API 调用" value="api" />
            <el-option label="主智能体" value="master" />
            <el-option label="子智能体" value="subagent" />
            <el-option label="算子调用" value="operator" />
            <el-option label="LLM 调用" value="llm" />
            <el-option label="系统错误" value="error" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="timeRange"
            type="datetimerange"
            value-format="x"
            format="YYYY-MM-DD HH:mm:ss"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
          />
        </el-form-item>
        <el-form-item label="每页条数">
          <el-select v-model="filterForm.page_size" style="width: 100px">
            <el-option label="20" :value="20" />
            <el-option label="50" :value="50" />
            <el-option label="100" :value="100" />
          </el-select>
        </el-form-item>
      </el-form>
    </section>

    <!-- Stats Grid -->
    <section class="stats-grid">
      <div class="stat-card warm">
        <span>总日志数</span>
        <strong>{{ total }}</strong>
      </div>
      <div class="stat-card cool">
        <span>当前类型</span>
        <strong>{{ logTypeLabel }}</strong>
      </div>
      <div class="stat-card accent">
        <span>查询耗时</span>
        <strong>{{ latency }}</strong>
      </div>
      <div class="stat-card neutral">
        <span>错误数量</span>
        <strong>{{ errorCount }}</strong>
      </div>
    </section>

    <!-- Logs Table -->
    <section class="panel">
      <div class="panel-head">
        <h3>日志列表</h3>
        <el-button @click="exportLogs" :loading="exporting">
          <el-icon><Download /></el-icon>
          导出
        </el-button>
      </div>

      <div v-if="loading && !logs.length" class="empty-state">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>加载日志中...</span>
      </div>
      <div v-else-if="!logs.length" class="empty-state">
        <el-icon><Document /></el-icon>
        <span>暂无日志记录</span>
      </div>
      <div v-else class="log-list">
        <article v-for="(log, index) in logs" :key="log.id || index" class="log-card">
          <button class="log-main" @click="toggleRow(index)">
            <div class="log-meta">
              <span class="log-time">{{ formatTime(log.timestamp || log.created_at) }}</span>
              <el-tag size="small" :type="getLogTypeTag(filterForm.log_type)">
                {{ filterForm.log_type }}
              </el-tag>
              <span v-if="log.module" class="log-module">{{ log.module }}</span>
              <span v-if="log.latency_ms || log.execution_time_ms" class="log-latency">
                {{ log.latency_ms || log.execution_time_ms }}ms
              </span>
            </div>
            <div class="log-message">{{ getLogSummary(log) }}</div>
          </button>
          <div v-if="expandedRows.has(index)" class="log-detail">
            <div class="attribute-grid">
              <div v-for="(value, key) in getLogAttributes(log)" :key="key" class="attribute-card">
                <strong>{{ key }}</strong>
                <span>{{ formatValue(value) }}</span>
              </div>
            </div>
            <pre v-if="log.content || log.error_message">{{ log.content || log.error_message }}</pre>
          </div>
        </article>
      </div>

      <el-pagination
        v-if="total > 0"
        v-model:current-page="filterForm.page"
        v-model:page-size="filterForm.page_size"
        :total="total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="runQuery"
        @current-change="runQuery"
      />
    </section>

    <!-- Session Trace -->
    <section v-if="selectedSessionId" class="panel">
      <div class="panel-head">
        <h3>会话证据链</h3>
        <el-button size="small" @click="selectedSessionId = null">关闭</el-button>
      </div>
      <div class="trace-content">
        <div class="trace-section">
          <h4>主智能体决策</h4>
          <div v-if="sessionTrace.master_decision" class="trace-item">
            <pre>{{ JSON.stringify(sessionTrace.master_decision, null, 2) }}</pre>
          </div>
          <div v-else class="empty-state-small">无记录</div>
        </div>
        <div class="trace-section">
          <h4>子智能体执行</h4>
          <div v-if="sessionTrace.subagent_executions?.length" class="trace-list">
            <div v-for="(item, index) in sessionTrace.subagent_executions" :key="index" class="trace-item">
              <strong>{{ item.subagent_name }}</strong>
              <span>状态: {{ item.status }}</span>
              <span>耗时: {{ item.execution_time_ms }}ms</span>
            </div>
          </div>
          <div v-else class="empty-state-small">无记录</div>
        </div>
        <div class="trace-section">
          <h4>算子调用</h4>
          <div v-if="sessionTrace.operator_calls?.length" class="trace-list">
            <div v-for="(item, index) in sessionTrace.operator_calls" :key="index" class="trace-item">
              <strong>{{ item.operator_name }}</strong>
              <span>{{ item.category }}</span>
            </div>
          </div>
          <div v-else class="empty-state-small">无记录</div>
        </div>
        <div class="trace-section">
          <h4>LLM 调用</h4>
          <div v-if="sessionTrace.llm_calls?.length" class="trace-list">
            <div v-for="(item, index) in sessionTrace.llm_calls" :key="index" class="trace-item">
              <strong>{{ item.model }}</strong>
              <span>Tokens: {{ item.total_tokens }}</span>
              <span>耗时: {{ item.latency_ms }}ms</span>
            </div>
          </div>
          <div v-else class="empty-state-small">无记录</div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { logsService } from '@/api/services/logs.service'
import type { LogsRequest } from '@/api/types/api.types'
import { ElMessage } from 'element-plus'
import {
  Refresh, Search, Download, Document, Loading
} from '@element-plus/icons-vue'

const loading = ref(false)
const exporting = ref(false)
const logs = ref<any[]>([])
const total = ref(0)
const latency = ref('--')
const errorCount = ref(0)
const expandedRows = reactive(new Set())
const selectedSessionId = ref(null)
const sessionTrace = ref({})

const timeRange = ref([Date.now() - 3600 * 1000, Date.now()])

const filterForm = reactive<LogsRequest>({
  log_type: 'api',
  page: 1,
  page_size: 20
})

const logTypeLabel = computed(() => {
  const labels: Record<string, string> = {
    api: 'API 调用',
    master: '主智能体',
    subagent: '子智能体',
    operator: '算子调用',
    llm: 'LLM 调用',
    error: '系统错误'
  }
  return labels[filterForm.log_type] || filterForm.log_type
})

function getLogTypeTag(type: string) {
  const tags: Record<string, any> = {
    api: 'primary',
    master: 'success',
    subagent: 'warning',
    operator: 'info',
    llm: 'danger',
    error: 'danger'
  }
  return tags[type] || ''
}

function formatTime(iso: string) {
  if (!iso) return '--'
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}

function formatValue(value: any) {
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function getLogSummary(log: any) {
  if (log.path) return `${log.method || 'GET'} ${log.path}`
  if (log.user_query) return log.user_query
  if (log.subagent_name) return `${log.subagent_name}: ${log.status}`
  if (log.operator_name) return `${log.operator_name} (${log.category})`
  if (log.model) return `${log.provider || 'LLM'}: ${log.model}`
  if (log.error_type) return `${log.error_type}: ${log.error_message}`
  if (log.content) return log.content
  if (log.error_message) return log.error_message
  return JSON.stringify(log)
}

function getLogAttributes(log: any) {
  const attrs: any = {}
  if (log.method) attrs['方法'] = log.method
  if (log.path) attrs['路径'] = log.path
  if (log.user_id) attrs['用户'] = log.user_id
  if (log.response_status) attrs['状态码'] = log.response_status
  if (log.session_id) {
    attrs['会话ID'] = log.session_id
    attrs['查看证据链'] = () => { selectedSessionId.value = log.session_id; loadSessionTrace(log.session_id) }
  }
  if (log.intent) attrs['意图'] = log.intent
  if (log.subagent_name) attrs['子智能体'] = log.subagent_name
  if (log.operator_name) attrs['算子'] = log.operator_name
  if (log.model) attrs['模型'] = log.model
  if (log.purpose) attrs['用途'] = log.purpose
  if (log.module) attrs['模块'] = log.module
  if (log.error_type) attrs['错误类型'] = log.error_type
  if (log.level) attrs['级别'] = log.level
  return attrs
}

function toggleRow(index: number) {
  if (expandedRows.has(index)) {
    expandedRows.delete(index)
  } else {
    expandedRows.add(index)
  }
}

async function runQuery() {
  loading.value = true
  try {
    const params: LogsRequest = {
      log_type: filterForm.log_type,
      page: filterForm.page,
      page_size: filterForm.page_size
    }
    if (timeRange.value && timeRange.value.length === 2) {
      params.start_time = new Date(timeRange.value[0]).toISOString()
      params.end_time = new Date(timeRange.value[1]).toISOString()
    }
    const response = await logsService.getLogs(params)
    logs.value = response.items
    total.value = response.total
    latency.value = response.took_ms ? `${response.took_ms}ms` : '--'
    errorCount.value = logs.value.filter((log: any) => {
      if (filterForm.log_type === 'api') return log.response_status >= 400
      if (filterForm.log_type === 'error') return true
      return false
    }).length
  } catch (error) {
    ElMessage.error('查询日志失败')
  } finally {
    loading.value = false
  }
}

async function loadSessionTrace(sessionId: string) {
  try {
    const response = await logsService.getSessionTrace(sessionId)
    sessionTrace.value = response
  } catch (error) {
    ElMessage.error('加载会话证据链失败')
  }
}

async function loadLogs() {
  await runQuery()
}

async function exportLogs() {
  exporting.value = true
  try {
    const params: any = {
      log_type: filterForm.log_type,
      format: 'json'
    }
    if (timeRange.value && timeRange.value.length === 2) {
      params.start_time = new Date(timeRange.value[0]).toISOString()
      params.end_time = new Date(timeRange.value[1]).toISOString()
    }
    const response = await logsService.exportLogs(params)
    const url = window.URL.createObjectURL(new Blob([response]))
    const a = document.createElement('a')
    a.href = url
    a.download = `logs_${filterForm.log_type}_${new Date().toISOString()}.json`
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  loadLogs()
})
</script>

<style scoped>
.logs-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.panel {
  background: linear-gradient(180deg, #ffffff 0%, #fffdf8 100%);
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 20px;
  padding: 22px;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
}

.hero {
  align-items: center;
  background:
    radial-gradient(circle at top left, rgba(251, 191, 36, 0.18), transparent 32%),
    radial-gradient(circle at bottom right, rgba(37, 99, 235, 0.15), transparent 28%),
    linear-gradient(135deg, #fff7ed 0%, #f8fbff 100%);
  display: flex;
  gap: 16px;
  justify-content: space-between;
}

.eyebrow {
  color: #9a3412;
  font-size: 12px;
  letter-spacing: 0.16em;
  margin: 0 0 8px;
  text-transform: uppercase;
}

.hero h2,
.panel h3 {
  color: #0f172a;
  margin: 0;
}

.hero h2 {
  font-size: 23px;
}

.subtitle {
  color: #475569;
  margin: 8px 0 0;
  max-width: 620px;
  line-height: 1.45;
}

.hero-actions {
  align-items: center;
  display: flex;
  gap: 8px;
}

.panel-head {
  align-items: center;
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
}

.panel h3 {
  font-size: 16px;
}

.stats-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(4, 1fr);
}

.stat-card {
  border-radius: 22px;
  color: #0f172a;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 116px;
  padding: 18px;
}

.stat-card span {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.stat-card strong {
  font-size: 28px;
  line-height: 1.1;
}

.stat-card.warm {
  background: linear-gradient(135deg, #fef3c7 0%, #fed7aa 100%);
}

.stat-card.cool {
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
}

.stat-card.accent {
  background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
}

.stat-card.neutral {
  background: linear-gradient(135deg, #e2e8f0 0%, #cbd5e1 100%);
}

.empty-state {
  align-items: center;
  display: flex;
  flex-direction: column;
  gap: 12px;
  justify-content: center;
  min-height: 180px;
  color: #94a3b8;
}

.empty-state-small {
  align-items: center;
  display: flex;
  justify-content: center;
  min-height: 60px;
  color: #94a3b8;
  font-size: 13px;
}

.log-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 500px;
  overflow-y: auto;
}

.log-card {
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  overflow: hidden;
}

.log-main {
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  border: 0;
  cursor: pointer;
  padding: 14px 16px;
  text-align: left;
  width: 100%;
  transition: background 0.2s;
}

.log-main:hover {
  background: #f1f5f9;
}

.log-meta {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  font-size: 12px;
  gap: 10px;
  margin-bottom: 8px;
}

.log-time {
  color: #64748b;
  font-weight: 600;
}

.log-module {
  color: #64748b;
}

.log-latency {
  color: #64748b;
  font-family: monospace;
}

.log-message {
  color: #0f172a;
  line-height: 1.6;
  word-break: break-word;
}

.log-detail {
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
  padding: 14px 16px;
}

.attribute-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, 1fr);
  margin-bottom: 12px;
}

.attribute-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
}

.attribute-card strong {
  color: #64748b;
  font-size: 12px;
}

.attribute-card span {
  color: #1e293b;
  word-break: break-word;
}

pre {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  margin: 0;
  padding: 12px;
  font-size: 12px;
  line-height: 1.6;
  overflow-x: auto;
}

.trace-content {
  display: grid;
  gap: 20px;
  grid-template-columns: repeat(2, 1fr);
}

.trace-section h4 {
  color: #1e293b;
  font-size: 14px;
  margin-bottom: 12px;
}

.trace-item {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 10px 12px;
  font-size: 13px;
}

.trace-item strong {
  color: #1e293b;
}

.trace-item span {
  color: #64748b;
}

.trace-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Responsive */
@media (max-width: 1080px) {
  .trace-content {
    grid-template-columns: 1fr;
  }
}
</style>
