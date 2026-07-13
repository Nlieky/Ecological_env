<template>
  <div class="event-center">
    <div class="event-header">
      <h2>Event Center</h2>
      <div class="header-actions">
        <el-select v-model="filterStatus" placeholder="Filter by status" style="width: 150px">
          <el-option label="All" value="" />
          <el-option label="Pending" value="pending" />
          <el-option label="Processing" value="processing" />
          <el-option label="Resolved" value="resolved" />
        </el-select>
        <el-select v-model="filterSeverity" placeholder="Filter by severity" style="width: 150px">
          <el-option label="All" value="" />
          <el-option label="High" value="high" />
          <el-option label="Medium" value="medium" />
          <el-option label="Low" value="low" />
        </el-select>
        <el-button @click="exportEvents" :icon="Download">Export</el-button>
      </div>
    </div>

    <el-table
      :data="filteredEvents"
      style="width: 100%"
      :height="tableHeight"
      stripe
      @row-click="showEventDetail"
    >
      <el-table-column prop="timestamp" label="Time" width="180">
        <template #default="{ row }">
          {{ formatTime(row.timestamp) }}
        </template>
      </el-table-column>
      <el-table-column prop="plantId" label="Plant" width="120" />
      <el-table-column prop="type" label="Event Type" width="180" />
      <el-table-column prop="severity" label="Severity" width="100">
        <template #default="{ row }">
          <el-tag :type="getSeverityType(row.severity)" size="small">
            {{ row.severity }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="Status" width="120">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)" size="small">
            {{ row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="summary" label="Summary" />
      <el-table-column label="Actions" width="150" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'pending'"
            type="primary"
            size="small"
            @click.stop="updateStatus(row.id, 'processing')"
          >
            Process
          </el-button>
          <el-button
            v-if="row.status === 'processing'"
            type="success"
            size="small"
            @click.stop="updateStatus(row.id, 'resolved')"
          >
            Resolve
          </el-button>
          <el-button
            type="info"
            size="small"
            @click.stop="showEventDetail(row)"
          >
            Details
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Event Detail Dialog -->
    <el-dialog
      v-model="detailVisible"
      :title="`Event Details - ${selectedEvent?.id}`"
      width="800px"
    >
      <div v-if="selectedEvent" class="event-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="Event ID">{{ selectedEvent.id }}</el-descriptions-item>
          <el-descriptions-item label="Plant">{{ selectedEvent.plantId }}</el-descriptions-item>
          <el-descriptions-item label="Type">{{ selectedEvent.type }}</el-descriptions-item>
          <el-descriptions-item label="Severity">
            <el-tag :type="getSeverityType(selectedEvent.severity)">
              {{ selectedEvent.severity }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="Status">
            <el-tag :type="getStatusType(selectedEvent.status)">
              {{ selectedEvent.status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="Timestamp">{{ formatTime(selectedEvent.timestamp) }}</el-descriptions-item>
        </el-descriptions>

        <div class="evidence-section">
          <h3>Evidence Chain</h3>
          <el-timeline>
            <el-timeline-item
              v-for="(item, idx) in selectedEvent.evidence?.operators || []"
              :key="idx"
              :timestamp="item.timestamp"
            >
              <div class="evidence-item">
                <strong>{{ item.name }}</strong>
                <pre>{{ JSON.stringify(item.result, null, 2) }}</pre>
              </div>
            </el-timeline-item>
          </el-timeline>
        </div>

        <div class="llm-reasoning" v-if="selectedEvent.evidence?.llmReasoning">
          <h3>LLM Reasoning</h3>
          <p>{{ selectedEvent.evidence.llmReasoning }}</p>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { eventsApi } from '@/api/events'
import type { AlertEvent } from '@/types'
import { Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const events = ref<AlertEvent[]>([])
const filterStatus = ref('')
const filterSeverity = ref('')
const detailVisible = ref(false)
const selectedEvent = ref<AlertEvent | null>(null)
const tableHeight = ref(600)

const filteredEvents = computed(() => {
  return events.value.filter(event => {
    if (filterStatus.value && event.status !== filterStatus.value) return false
    if (filterSeverity.value && event.severity !== filterSeverity.value) return false
    return true
  })
})

const formatTime = (iso: string) => {
  return new Date(iso).toLocaleString('zh-CN')
}

const getSeverityType = (severity: string) => {
  switch (severity) {
    case 'high': return 'danger'
    case 'medium': return 'warning'
    case 'low': return 'info'
    default: return ''
  }
}

const getStatusType = (status: string) => {
  switch (status) {
    case 'pending': return 'warning'
    case 'processing': return 'primary'
    case 'resolved': return 'success'
    case 'ignored': return 'info'
    default: return ''
  }
}

const showEventDetail = (event: AlertEvent) => {
  selectedEvent.value = event
  detailVisible.value = true
}

const updateStatus = async (eventId: string, status: string) => {
  try {
    await eventsApi.updateStatus(eventId, status)
    ElMessage.success(`Event updated to ${status}`)
    await loadEvents()
  } catch (error) {
    console.error('Failed to update event:', error)
    ElMessage.error('Failed to update event status')
  }
}

const exportEvents = async () => {
  try {
    const blob = await eventsApi.export({
      format: 'xlsx',
      status: filterStatus.value,
      severity: filterSeverity.value
    })

    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `events_${new Date().toISOString()}.xlsx`
    a.click()
    window.URL.revokeObjectURL(url)

    ElMessage.success('Events exported successfully')
  } catch (error) {
    console.error('Failed to export events:', error)
    ElMessage.error('Failed to export events')
  }
}

const loadEvents = async () => {
  try {
    const data = await eventsApi.list({
      page: 1,
      page_size: 100
    })
    events.value = data.items || []
  } catch (error) {
    console.error('Failed to load events:', error)
    ElMessage.error('Failed to load events')
  }
}

const handleResize = () => {
  tableHeight.value = window.innerHeight - 300
}

onMounted(() => {
  loadEvents()
  handleResize()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.event-center {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 20px;
}

.event-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.event-header h2 {
  margin: 0;
  color: #eaeaea;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.event-center :deep(.el-table) {
  background: #16213e;
}

.event-center :deep(.el-table th) {
  background: #1a1a2e;
  color: #eaeaea;
}

.event-center :deep(.el-table td) {
  color: #eaeaea;
}

.event-center :deep(.el-table__row:hover) {
  background: #1a1a2e;
}

.event-detail {
  color: #eaeaea;
}

.evidence-section {
  margin-top: 24px;
}

.evidence-section h3,
.llm-reasoning h3 {
  margin-bottom: 16px;
  color: #eaeaea;
}

.evidence-item {
  background: #333;
  padding: 12px;
  border-radius: 8px;
}

.evidence-item pre {
  margin: 8px 0 0 0;
  background: #222;
  padding: 8px;
  border-radius: 4px;
  font-size: 12px;
  overflow-x: auto;
}

.llm-reasoning {
  margin-top: 24px;
}

.llm-reasoning p {
  background: #333;
  padding: 12px;
  border-radius: 8px;
  line-height: 1.6;
}
</style>
