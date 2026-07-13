<template>
  <div class="trace-observability-page">
    <div class="page-header">
      <h2>链路追踪</h2>
      <div class="header-actions">
        <el-button @click="refresh" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="trace-tabs">
      <!-- 链路查询标签 -->
      <el-tab-pane label="链路查询" name="query">
        <div class="trace-query-section">
          <!-- 搜索表单 -->
          <el-card class="search-card" shadow="never">
            <el-form :model="searchForm" inline>
              <el-form-item label="服务名">
                <el-select
                  v-model="searchForm.service"
                  placeholder="选择服务"
                  clearable
                  filterable
                  @focus="loadCatalog"
                >
                  <el-option
                    v-for="svc in catalogServices"
                    :key="svc.name"
                    :label="svc.name"
                    :value="svc.name"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="操作名">
                <el-select
                  v-model="searchForm.operation"
                  placeholder="选择操作"
                  clearable
                  filterable
                  :disabled="!searchForm.service"
                >
                  <el-option
                    v-for="op in catalogOperations"
                    :key="op"
                    :label="op"
                    :value="op"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="时间范围">
                <el-date-picker
                  v-model="searchForm.timeRange"
                  type="datetimerange"
                  range-separator="至"
                  start-placeholder="开始时间"
                  end-placeholder="结束时间"
                  :default-time="defaultTime"
                />
              </el-form-item>
              <el-form-item label="最短耗时">
                <el-input-number
                  v-model="searchForm.minDuration"
                  :min="0"
                  :step="100"
                  placeholder="毫秒"
                />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="searchTraces" :loading="searching">
                  <el-icon><Search /></el-icon>
                  查询
                </el-button>
                <el-button @click="resetSearch">重置</el-button>
              </el-form-item>
            </el-form>
          </el-card>

          <!-- 链路列表 -->
          <el-card class="results-card" shadow="never">
            <template #header>
              <span>查询结果 ({{ totalResults }} 条)</span>
            </template>

            <el-empty v-if="!searchResults.length && !searching" description="暂无数据，请调整查询条件" />

            <el-table v-else :data="searchResults" v-loading="searching" stripe>
              <el-table-column prop="traceID" label="Trace ID" width="280">
                <template #default="{ row }">
                  <el-link type="primary" @click="viewTraceDetail(row.traceID)">
                    {{ row.traceID }}
                  </el-link>
                </template>
              </el-table-column>
              <el-table-column prop="rootServiceName" label="服务" width="150" />
              <el-table-column prop="rootSpanName" label="操作" width="200" show-overflow-tooltip />
              <el-table-column label="开始时间" width="180">
                <template #default="{ row }">
                  {{ formatTimestamp(row.startTime) }}
                </template>
              </el-table-column>
              <el-table-column label="耗时" width="120">
                <template #default="{ row }">
                  <el-tag :type="getDurationType(row.duration)" size="small">
                    {{ formatDuration(row.duration) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="spanCount" label="Span 数" width="100" align="center" />
              <el-table-column label="操作" width="100" fixed="right">
                <template #default="{ row }">
                  <el-button text type="primary" @click="viewTraceDetail(row.traceID)">
                    详情
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <el-pagination
              v-if="totalResults > pageSize"
              v-model:current-page="currentPage"
              v-model:page-size="pageSize"
              :total="totalResults"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next"
              @size-change="handlePageChange"
              @current-change="handlePageChange"
            />
          </el-card>
        </div>
      </el-tab-pane>

      <!-- 数据源管理标签 -->
      <el-tab-pane label="数据源" name="datasources">
        <div class="datasources-section">
          <div class="section-header">
            <h3>链路追踪数据源</h3>
            <el-button type="primary" @click="showDataSourceDialog()">
              <el-icon><Plus /></el-icon>
              添加数据源
            </el-button>
          </div>

          <el-table :data="dataSources" v-loading="loadingDataSources" stripe>
            <el-table-column prop="name" label="名称" width="200" />
            <el-table-column prop="provider" label="类型" width="120">
              <template #default="{ row }">
                <el-tag size="small">{{ getProviderLabel(row.provider) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="配置" show-overflow-tooltip>
              <template #default="{ row }">
                {{ formatConfig(row.config) }}
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
                  {{ row.enabled ? '已启用' : '已禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="创建时间" width="180">
              <template #default="{ row }">
                {{ formatDateTime(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button text type="primary" @click="testConnection(row.id)" :loading="testing[row.id]">
                  测试连接
                </el-button>
                <el-button text @click="showDataSourceDialog(row)">编辑</el-button>
                <el-button text type="danger" @click="deleteDataSource(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 链路详情对话框 -->
    <el-dialog
      v-model="traceDetailVisible"
      :title="`链路详情 - ${currentTraceId}`"
      width="90%"
      top="5vh"
      @close="closeTraceDetail"
    >
      <div v-if="traceDetail" class="trace-detail">
        <!-- 链路摘要 -->
        <div class="trace-summary">
          <el-descriptions :column="4" border>
            <el-descriptions-item label="Trace ID">{{ traceDetail.traceID }}</el-descriptions-item>
            <el-descriptions-item label="Span 数量">{{ traceDetail.spans.length }}</el-descriptions-item>
            <el-descriptions-item label="总耗时">
              {{ formatDuration(calculateTraceDuration()) }}
            </el-descriptions-item>
            <el-descriptions-item label="服务数量">
              {{ Object.keys(traceDetail.processes).length }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 水瀑流图 -->
        <div class="trace-waterfall">
          <h4>Span 水瀑流</h4>
          <TraceWaterfall
            :spans="traceDetail.spans"
            :processes="traceDetail.processes"
            @span-click="handleSpanClick"
          />
        </div>

        <!-- Span 详情 -->
        <div v-if="selectedSpan" class="span-detail">
          <h4>Span 详情</h4>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="Span ID">{{ selectedSpan.spanID }}</el-descriptions-item>
            <el-descriptions-item label="操作名">{{ selectedSpan.operationName }}</el-descriptions-item>
            <el-descriptions-item label="服务名">
              {{ traceDetail.processes[selectedSpan.processID]?.serviceName }}
            </el-descriptions-item>
            <el-descriptions-item label="耗时">
              {{ formatDuration(selectedSpan.duration) }}
            </el-descriptions-item>
            <el-descriptions-item label="开始时间" :span="2">
              {{ formatTimestamp(selectedSpan.startTime) }}
            </el-descriptions-item>
          </el-descriptions>

          <h5>Tags</h5>
          <el-table :data="Object.entries(selectedSpan.tags).map(([k, v]) => ({ key: k, value: v }))" size="small" max-height="200">
            <el-table-column prop="key" label="Key" width="200" />
            <el-table-column prop="value" label="Value" show-overflow-tooltip />
          </el-table>

          <h5>Logs</h5>
          <el-table :data="selectedSpan.logs" size="small" max-height="200">
            <el-table-column label="时间戳" width="180">
              <template #default="{ row }">
                {{ formatTimestamp(row.timestamp) }}
              </template>
            </el-table-column>
            <el-table-column label="字段" show-overflow-tooltip>
              <template #default="{ row }">
                {{ Object.entries(row.fields).map(([k, v]) => `${k}=${v}`).join(', ') }}
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
      <div v-else v-loading="loadingTraceDetail" class="trace-detail-loading">
        加载中...
      </div>
    </el-dialog>

    <!-- 数据源对话框 -->
    <el-dialog
      v-model="dataSourceDialogVisible"
      :title="dataSourceForm.id ? '编辑数据源' : '添加数据源'"
      width="600px"
    >
      <el-form :model="dataSourceForm" label-width="100px">
        <el-form-item label="名称">
          <el-input v-model="dataSourceForm.name" placeholder="输入数据源名称" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="dataSourceForm.provider" placeholder="选择类型">
            <el-option label="Jaeger" value="jaeger" />
            <el-option label="Zipkin" value="zipkin" />
            <el-option label="SkyWalking" value="skywalking" />
          </el-select>
        </el-form-item>
        <el-form-item label="URL">
          <el-input v-model="dataSourceForm.config.url" placeholder="http://localhost:16686" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="dataSourceForm.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dataSourceDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveDataSource" :loading="savingDataSource">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { Refresh, Search, Plus } from '@element-plus/icons-vue'
import { tracingApi, type TraceSearchResult, type TraceDetail, type TracingDataSource } from '@/api/tracing'
import { ElMessage, ElMessageBox } from 'element-plus'

// 标签页
const activeTab = ref('query')

// 搜索表单
const searchForm = reactive({
  service: '',
  operation: '',
  timeRange: [] as Date[],
  minDuration: undefined as number | undefined,
  dataSourceId: ''
})

const defaultTime: [Date, Date] = [
  new Date(Date.now() - 3600000), // 1小时前
  new Date()
]

// 目录数据
const catalogServices = ref<Array<{ name: string; operations: string[] }>>([])
const catalogOperations = computed(() => {
  if (!searchForm.service) return []
  const service = catalogServices.value.find(s => s.name === searchForm.service)
  return service?.operations || []
})

// 搜索结果
const searchResults = ref<TraceSearchResult[]>([])
const searching = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const totalResults = ref(0)

// 加载状态
const loading = ref(false)

// 数据源
const dataSources = ref<TracingDataSource[]>([])
const loadingDataSources = ref(false)
const testing = ref<Record<string, boolean>>({})

// 链路详情
const traceDetailVisible = ref(false)
const currentTraceId = ref('')
const traceDetail = ref<TraceDetail | null>(null)
const loadingTraceDetail = ref(false)
const selectedSpan = ref<TraceDetail['spans'][0] | null>(null)

// 数据源对话框
const dataSourceDialogVisible = ref(false)
const dataSourceForm = reactive({
  id: '',
  name: '',
  provider: 'jaeger',
  config: { url: '' },
  enabled: true
})
const savingDataSource = ref(false)

// 加载目录
const loadCatalog = async () => {
  try {
    const result = await tracingApi.getCatalog()
    catalogServices.value = result.services
  } catch (error) {
    console.error('Failed to load catalog:', error)
  }
}

// 搜索链路
const searchTraces = async () => {
  searching.value = true
  try {
    const [startTimeMin, startTimeMax] = searchForm.timeRange.length
      ? [searchForm.timeRange[0].toISOString(), searchForm.timeRange[1].toISOString()]
      : []

    const results = await tracingApi.searchTraces({
      service: searchForm.service || undefined,
      operation: searchForm.operation || undefined,
      startTimeMin,
      startTimeMax,
      durationMin: searchForm.minDuration,
      limit: pageSize.value
    })

    searchResults.value = results
    totalResults.value = results.length
  } catch (error) {
    ElMessage.error('搜索链路失败')
  } finally {
    searching.value = false
  }
}

// 重置搜索
const resetSearch = () => {
  searchForm.service = ''
  searchForm.operation = ''
  searchForm.timeRange = []
  searchForm.minDuration = undefined
  searchResults.value = []
  totalResults.value = 0
}

// 分页变化
const handlePageChange = () => {
  // 实际应该重新调用搜索接口
}

// 查看链路详情
const viewTraceDetail = async (traceId: string) => {
  currentTraceId.value = traceId
  traceDetailVisible.value = true
  loadingTraceDetail.value = true
  try {
    traceDetail.value = await tracingApi.getTraceDetail(traceId)
    // 按开始时间排序 spans
    traceDetail.value.spans.sort((a, b) => a.startTime - b.startTime)
  } catch (error) {
    ElMessage.error('加载链路详情失败')
    traceDetailVisible.value = false
  } finally {
    loadingTraceDetail.value = false
  }
}

// 关闭链路详情
const closeTraceDetail = () => {
  traceDetail.value = null
  selectedSpan.value = null
  currentTraceId.value = ''
}

// 点击 Span
const handleSpanClick = (span: TraceDetail['spans'][0]) => {
  selectedSpan.value = span
}

// 计算链路总耗时
const calculateTraceDuration = () => {
  if (!traceDetail.value?.spans.length) return 0
  const times = traceDetail.value.spans.map(s => s.startTime + s.duration)
  return Math.max(...times) - Math.min(...traceDetail.value.spans.map(s => s.startTime))
}

// 格式化时间戳
const formatTimestamp = (timestamp: number) => {
  return new Date(timestamp / 1000).toLocaleString('zh-CN')
}

// 格式化耗时
const formatDuration = (microseconds: number) => {
  if (microseconds < 1000) return `${microseconds}μs`
  if (microseconds < 1000000) return `${(microseconds / 1000).toFixed(2)}ms`
  return `${(microseconds / 1000000).toFixed(2)}s`
}

// 获取耗时类型
const getDurationType = (microseconds: number) => {
  if (microseconds < 1000000) return 'success'
  if (microseconds < 3000000) return 'warning'
  return 'danger'
}

// 格式化日期时间
const formatDateTime = (datetime: string) => {
  return new Date(datetime).toLocaleString('zh-CN')
}

// 格式化配置
const formatConfig = (config: Record<string, any>) => {
  return Object.entries(config)
    .map(([k, v]) => `${k}=${v}`)
    .join(', ')
}

// 获取提供商标签
const getProviderLabel = (provider: string) => {
  const labels: Record<string, string> = {
    jaeger: 'Jaeger',
    zipkin: 'Zipkin',
    skywalking: 'SkyWalking'
  }
  return labels[provider] || provider
}

// 加载数据源
const loadDataSources = async () => {
  loadingDataSources.value = true
  try {
    dataSources.value = await tracingApi.getDataSources()
  } catch (error) {
    ElMessage.error('加载数据源失败')
  } finally {
    loadingDataSources.value = false
  }
}

// 显示数据源对话框
const showDataSourceDialog = (dataSource?: TracingDataSource) => {
  if (dataSource) {
    dataSourceForm.id = dataSource.id
    dataSourceForm.name = dataSource.name
    dataSourceForm.provider = dataSource.provider
    dataSourceForm.config = { ...dataSource.config }
    dataSourceForm.enabled = dataSource.enabled
  } else {
    dataSourceForm.id = ''
    dataSourceForm.name = ''
    dataSourceForm.provider = 'jaeger'
    dataSourceForm.config = { url: '' }
    dataSourceForm.enabled = true
  }
  dataSourceDialogVisible.value = true
}

// 保存数据源
const saveDataSource = async () => {
  savingDataSource.value = true
  try {
    if (dataSourceForm.id) {
      await tracingApi.updateDataSource(dataSourceForm.id, {
        name: dataSourceForm.name,
        provider: dataSourceForm.provider,
        config: dataSourceForm.config,
        enabled: dataSourceForm.enabled
      })
      ElMessage.success('数据源更新成功')
    } else {
      await tracingApi.createDataSource({
        name: dataSourceForm.name,
        provider: dataSourceForm.provider,
        config: dataSourceForm.config,
        enabled: dataSourceForm.enabled
      } as any)
      ElMessage.success('数据源创建成功')
    }
    dataSourceDialogVisible.value = false
    loadDataSources()
  } catch (error) {
    ElMessage.error('保存数据源失败')
  } finally {
    savingDataSource.value = false
  }
}

// 测试连接
const testConnection = async (id: string) => {
  testing.value[id] = true
  try {
    await tracingApi.testDataSource(id)
    ElMessage.success('连接测试成功')
  } catch (error) {
    ElMessage.error('连接测试失败')
  } finally {
    testing.value[id] = false
  }
}

// 删除数据源
const deleteDataSource = async (id: string) => {
  try {
    await ElMessageBox.confirm('确定要删除该数据源吗？', '提示', {
      type: 'warning'
    })
    await tracingApi.deleteDataSource(id)
    ElMessage.success('数据源删除成功')
    loadDataSources()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除数据源失败')
    }
  }
}

// 刷新
const refresh = () => {
  if (activeTab.value === 'query') {
    searchTraces()
  } else {
    loadDataSources()
  }
}

// 挂载
onMounted(() => {
  loadCatalog()
  loadDataSources()
})
</script>

<script lang="ts">
// TraceWaterfall 组件 - 水瀑流图
import { defineComponent } from 'vue'

export default defineComponent({
  components: {
    TraceWaterfall: defineComponent({
      props: {
        spans: Array,
        processes: Object
      },
      emits: ['spanClick'],
      template: `
        <div class="trace-waterfall-chart">
          <svg :width="chartWidth" :height="chartHeight" class="waterfall-svg">
            <!-- 时间轴 -->
            <line x1="150" y1="20" x2="150" y2="40" stroke="#e5e7eb" stroke-width="1"/>
            <line x1="chartWidth - 20" y1="20" x2="chartWidth - 20" y2="40" stroke="#e5e7eb" stroke-width="1"/>
            <line x1="150" y1="30" x2="chartWidth - 20" y2="30" stroke="#e5e7eb" stroke-width="1"/>
            <text x="150" y="15" font-size="10" fill="#6b7280">0ms</text>
            <text :x="chartWidth - 20" y="15" font-size="10" fill="#6b7280" text-anchor="end">{{ maxDuration }}ms</text>

            <!-- Spans -->
            <g v-for="(span, index) in sortedSpans" :key="span.spanID">
              <rect
                :x="spanX(span)"
                :y="40 + index * 35"
                :width="spanWidth(span)"
                :height="28"
                :fill="spanColor(span)"
                :class="{ 'cursor-pointer': true }"
                @click="$emit('spanClick', span)"
                rx="4"
              />
              <text
                :x="145"
                :y="58 + index * 35"
                font-size="11"
                fill="#374151"
                text-anchor="end"
              >{{ serviceName(span) }}</text>
              <text
                :x="spanX(span) + 5"
                :y="58 + index * 35"
                font-size="10"
                fill="#ffffff"
                v-if="spanWidth(span) > 50"
              >{{ span.operationName }}</text>
            </g>
          </svg>
        </div>
      `,
      computed: {
        sortedSpans() {
          return [...this.spans].sort((a, b) => a.startTime - b.startTime)
        },
        minTime() {
          return Math.min(...this.spans.map(s => s.startTime))
        },
        maxTime() {
          return Math.max(...this.spans.map(s => s.startTime + s.duration))
        },
        timeRange() {
          return this.maxTime - this.minTime
        },
        maxDuration() {
          return Math.round(this.timeRange / 1000)
        },
        chartWidth() {
          return 800
        },
        chartHeight() {
          return 40 + this.spans.length * 35 + 20
        }
      },
      methods: {
        spanX(span) {
          const offset = span.startTime - this.minTime
          const ratio = offset / this.timeRange
          return 150 + ratio * (this.chartWidth - 170)
        },
        spanWidth(span) {
          const ratio = span.duration / this.timeRange
          return Math.max(4, ratio * (this.chartWidth - 170))
        },
        serviceName(span) {
          return this.processes[span.processID]?.serviceName || 'Unknown'
        },
        spanColor(span) {
          const service = this.serviceName(span)
          const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']
          const hash = service.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
          return colors[hash % colors.length]
        }
      }
    })
  }
})
</script>

<style scoped>
.trace-observability-page {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  color: #303133;
}

.trace-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.trace-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow-y: auto;
}

.trace-query-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.search-card {
  margin-bottom: 16px;
}

.results-card {
  flex: 1;
}

.trace-waterfall-chart {
  margin-top: 20px;
  padding: 10px;
  background: #f9fafb;
  border-radius: 4px;
  overflow-x: auto;
}

.waterfall-svg {
  min-width: 100%;
}

.trace-detail {
  max-height: 70vh;
  overflow-y: auto;
}

.trace-summary {
  margin-bottom: 20px;
}

.trace-waterfall {
  margin-bottom: 20px;
}

.trace-waterfall h4 {
  margin: 0 0 10px 0;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.span-detail {
  border-top: 1px solid #e4e7ed;
  padding-top: 20px;
}

.span-detail h4 {
  margin: 0 0 15px 0;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.span-detail h5 {
  margin: 15px 0 10px 0;
  font-size: 13px;
  font-weight: 600;
  color: #606266;
}

.trace-detail-loading {
  padding: 40px;
  text-align: center;
  color: #909399;
}

.datasources-section {
  padding: 10px 0;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}
</style>
