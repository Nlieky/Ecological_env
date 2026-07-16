# Frontend Architecture Refactoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the frontend architecture to fix API integration issues, unify state management, and establish a clear layered architecture while keeping the UI unchanged.

**Architecture:** Implement a 4-layer architecture: Views → Stores → Composables → API Services → HTTP Client, with a single-direction data flow and centralized state management via Pinia.

**Tech Stack:** Vue 3.5, TypeScript, Vite 6, Pinia 3, Element Plus 2, Axios 1, ECharts 5

---

## File Structure

### Files to Create
```
src/
├── api/
│   ├── client.ts                    # Unified HTTP client
│   ├── services/
│   │   ├── query.service.ts         # Query API service
│   │   ├── realtime.service.ts      # Realtime data service
│   │   ├── events.service.ts        # Events API service
│   │   └── logs.service.ts          # Logs API service
│   └── types/
│       └── api.types.ts             # API type definitions
├── composables/
│   ├── useQueryAgent.ts             # Query agent logic
│   ├── useRealtimePolling.ts        # Realtime polling logic
│   └── useEvidenceChain.ts          # Evidence chain display logic
└── types/
    └── index.ts                      # Business type definitions
```

### Files to Modify
```
src/
├── stores/
│   ├── chat.ts                       # Refactor: remove unused methods, add new ones
│   ├── realtime.ts                   # Refactor: simplify, use API services
│   └── events.ts                     # Refactor: use API services
└── views/
    ├── AIOpsChat.vue                 # Refactor: use composable, keep UI
    ├── Dashboard.vue                 # Refactor: use polling composable
    ├── EventCenter.vue               # Refactor: use store
    └── Logs.vue                      # Refactor: use API service
```

### Files to Delete
```
src/api/
├── index.ts                          # Replace with client.ts
├── query.ts                          # Replace with query.service.ts
├── realtime.ts                       # Replace with realtime.service.ts
├── events.ts                         # Replace with events.service.ts
└── tracing.ts                        # Replace with logs.service.ts
```

---

## Task 1: Create API Type Definitions

**Files:**
- Create: `frontend/src/api/types/api.types.ts`

This task defines all TypeScript interfaces that match the backend API contracts exactly.

- [ ] **Step 1: Create the API types file with all backend-matching interfaces**

```bash
cd frontend
mkdir -p src/api/types
```

- [ ] **Step 2: Write the complete API type definitions**

Create `frontend/src/api/types/api.types.ts`:

```typescript
// ========== Query Interface ==========
export interface QueryRequest {
  query: string
  session_id?: string
  context?: PageContext
}

export interface QueryResponse {
  content: string
  session_id: string
  timestamp: string
  chartData?: any
  decision_path: DecisionPath[]
  reasoning?: string
  metadata?: Record<string, any>
}

export interface DecisionPath {
  step_number: number
  step_name: string
  decision: string
  action: string
}

// ========== Realtime Data Interface ==========
export interface PlantData {
  id: string
  name: string
  status: 'online' | 'offline'
  metrics: WaterMetrics
  metric_status: MetricStatus
  last_update: string
}

export interface WaterMetrics {
  ph: number
  cod: number
  ammonia_nitrogen: number
  total_nitrogen: number
  total_phosphorus: number
  flow: number
}

export interface MetricStatus {
  ph: 'normal' | 'abnormal' | 'offline'
  cod: 'normal' | 'abnormal' | 'offline'
  ammonia_nitrogen: 'normal' | 'abnormal' | 'offline'
  total_nitrogen: 'normal' | 'abnormal' | 'offline'
  total_phosphorus: 'normal' | 'abnormal' | 'offline'
  flow: 'normal' | 'abnormal' | 'offline'
}

// ========== Events Interface ==========
export interface EventListRequest {
  type?: string
  plantId?: string
  severity?: string
  status?: string
  startTime?: string
  endTime?: string
  page?: number
  pageSize?: number
}

export interface AlertEvent {
  id: string
  timestamp: string
  type: string
  plant_id: string
  severity: 'low' | 'medium' | 'high'
  status: 'pending' | 'processing' | 'resolved' | 'ignored'
  evidence?: any
}

export interface EventListResponse {
  items: AlertEvent[]
  total: number
  page: number
  pageSize: number
}

// ========== Logs Interface ==========
export interface LogsRequest {
  type?: string
  startTime?: string
  endTime?: string
  page?: number
  pageSize?: number
}

export interface LogEntry {
  id: string
  timestamp: string
  type: string
  level: string
  message: string
  details?: any
}

// ========== Common Types ==========
export interface PageContext {
  page?: string
  plant_id?: string
  time_range?: string
}
```

- [ ] **Step 3: Verify TypeScript compilation**

Run: `cd frontend && npm run type-check`
Expected: No type errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/types/api.types.ts
git commit -m "feat(api): add API type definitions matching backend contracts"
```

---

## Task 2: Create Unified HTTP Client

**Files:**
- Create: `frontend/src/api/client.ts`
- Delete: `frontend/src/api/index.ts` (later)

- [ ] **Step 1: Create the HTTP client with unified error handling**

Create `frontend/src/api/client.ts`:

```typescript
import axios, { AxiosError } from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 300000  // 5分钟超时，适配AI查询耗时
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error: AxiosError) => {
    // 统一错误处理
    const message = (error.response?.data as any)?.detail || error.message || '请求失败'
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

export default api
```

- [ ] **Step 2: Verify no TypeScript errors**

Run: `cd frontend && npm run type-check`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "feat(api): create unified HTTP client with error handling"
```

---

## Task 3: Create Query Service

**Files:**
- Create: `frontend/src/api/services/query.service.ts`

- [ ] **Step 1: Create the services directory and query service**

```bash
cd frontend
mkdir -p src/api/services
```

- [ ] **Step 2: Write the query service implementation**

Create `frontend/src/api/services/query.service.ts`:

```typescript
import api from '../client'
import type { QueryRequest, QueryResponse } from '../types/api.types'

export class QueryService {
  private readonly basePath = '/query'

  /**
   * 执行自然语言查询
   */
  async executeQuery(request: QueryRequest): Promise<QueryResponse> {
    return api.post(this.basePath, request)
  }

  /**
   * 获取智能体能力说明
   */
  async getCapabilities(): Promise<any> {
    return api.get(`${this.basePath}/capabilities`)
  }
}

export const queryService = new QueryService()
```

- [ ] **Step 3: Verify TypeScript compilation**

Run: `cd frontend && npm run type-check`
Expected: No type errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/services/query.service.ts
git commit -m "feat(api): add query service"
```

---

## Task 4: Create Realtime Service

**Files:**
- Create: `frontend/src/api/services/realtime.service.ts`

- [ ] **Step 1: Write the realtime service implementation**

Create `frontend/src/api/services/realtime.service.ts`:

```typescript
import api from '../client'
import type { PlantData } from '../types/api.types'

export class RealtimeService {
  /**
   * 获取所有污水厂数据
   */
  async getAllPlants(): Promise<PlantData[]> {
    return api.get('/realtime/plants')
  }

  /**
   * 获取单个污水厂数据
   */
  async getPlant(id: string): Promise<PlantData> {
    return api.get(`/realtime/plants/${id}`)
  }
}

export const realtimeService = new RealtimeService()
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend && npm run type-check`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/services/realtime.service.ts
git commit -m "feat(api): add realtime service"
```

---

## Task 5: Create Events Service

**Files:**
- Create: `frontend/src/api/services/events.service.ts`

- [ ] **Step 1: Write the events service implementation**

Create `frontend/src/api/services/events.service.ts`:

```typescript
import api from '../client'
import type { EventListRequest, AlertEvent, EventListResponse } from '../types/api.types'

export class EventsService {
  /**
   * 获取事件列表
   */
  async getEvents(params?: EventListRequest): Promise<EventListResponse> {
    return api.get('/events', { params })
  }

  /**
   * 获取事件详情
   */
  async getEventDetail(id: string): Promise<AlertEvent> {
    return api.get(`/events/${id}`)
  }

  /**
   * 更新事件状态
   */
  async updateStatus(id: string, status: string): Promise<void> {
    return api.put(`/events/${id}/status`, { status })
  }

  /**
   * 导出事件报告
   */
  async exportEvents(params?: any): Promise<Blob> {
    return api.get('/events/export', {
      params,
      responseType: 'blob'
    })
  }
}

export const eventsService = new EventsService()
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend && npm run type-check`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/services/events.service.ts
git commit -m "feat(api): add events service"
```

---

## Task 6: Create Logs Service

**Files:**
- Create: `frontend/src/api/services/logs.service.ts`

- [ ] **Step 1: Write the logs service implementation**

Create `frontend/src/api/services/logs.service.ts`:

```typescript
import api from '../client'
import type { LogsRequest, LogEntry } from '../types/api.types'

export class LogsService {
  /**
   * 获取日志列表
   */
  async getLogs(params?: LogsRequest): Promise<{
    items: LogEntry[]
    total: number
    page: number
    pageSize: number
  }> {
    return api.get('/logs', { params })
  }

  /**
   * 获取会话证据链
   */
  async getSessionTrace(sessionId: string): Promise<any> {
    return api.get(`/logs/trace/${sessionId}`)
  }
}

export const logsService = new LogsService()
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend && npm run type-check`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/services/logs.service.ts
git commit -m "feat(api): add logs service"
```

---

## Task 7: Update API Types File

**Files:**
- Modify: `frontend/src/api/types/api.types.ts`

- [ ] **Step 1: Add Logs interface to API types**

Edit `frontend/src/api/types/api.types.ts`, add before the Common Types section:

```typescript
// ========== Logs Interface ==========
export interface LogsRequest {
  type?: string
  startTime?: string
  endTime?: string
  page?: number
  pageSize?: number
}

export interface LogEntry {
  id: string
  timestamp: string
  type: string
  level: string
  message: string
  details?: any
}
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend && npm run type-check`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/types/api.types.ts
git commit -m "feat(api): add logs interface definitions"
```

---

## Task 8: Create Business Types File

**Files:**
- Create: `frontend/src/types/index.ts`

- [ ] **Step 1: Create the business types file**

Create `frontend/src/types/index.ts`:

```typescript
import type { QueryResponse, DecisionPath, PlantData, AlertEvent } from '@/api/types/api.types'

// ========== Chat Message ==========
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  chartData?: any
  evidence?: DecisionPath[]
}

// ========== Session Info ==========
export interface Session {
  id: string
  createdAt: string
  messageCount: number
}

// ========== Page Context ==========
export interface PageContext {
  page?: string
  plantId?: string
  timeRange?: string
  suggestedQuestions?: string[]
}

// Re-export API types
export type { QueryResponse, DecisionPath, PlantData, AlertEvent }
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend && npm run type-check`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat(types): add business type definitions"
```

---

## Task 9: Create useQueryAgent Composable

**Files:**
- Create: `frontend/src/composables/useQueryAgent.ts`

- [ ] **Step 1: Create composables directory**

```bash
cd frontend
mkdir -p src/composables
```

- [ ] **Step 2: Write the useQueryAgent composable**

Create `frontend/src/composables/useQueryAgent.ts`:

```typescript
import { computed } from 'vue'
import { useChatStore } from '@/stores/chat'
import { queryService } from '@/api/services/query.service'
import type { PageContext } from '@/api/types/api.types'

export function useQueryAgent() {
  const chatStore = useChatStore()

  /**
   * 执行查询
   */
  const query = async (content: string, context?: PageContext) => {
    // 1. 添加用户消息
    chatStore.addUserMessage(content)

    // 2. 设置加载状态
    chatStore.setLoading(true)

    try {
      // 3. 调用 API
      const request = {
        query: content,
        session_id: chatStore.currentSessionId,
        context
      }
      const response = await queryService.executeQuery(request)

      // 4. 更新会话 ID
      chatStore.setSessionId(response.session_id)

      // 5. 添加助手消息
      chatStore.addAssistantMessage(response)

      return response
    } catch (error) {
      // 错误已在拦截器中处理
      chatStore.addErrorMessage('查询失败，请稍后重试')
      throw error
    } finally {
      chatStore.setLoading(false)
    }
  }

  return {
    query,
    isQuerying: computed(() => chatStore.loading),
    currentSessionId: computed(() => chatStore.currentSessionId)
  }
}
```

- [ ] **Step 3: Verify TypeScript compilation**

Run: `cd frontend && npm run type-check`
Expected: No type errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/composables/useQueryAgent.ts
git commit -m "feat(composables): add useQueryAgent composable"
```

---

## Task 10: Create useRealtimePolling Composable

**Files:**
- Create: `frontend/src/composables/useRealtimePolling.ts`

- [ ] **Step 1: Write the useRealtimePolling composable**

Create `frontend/src/composables/useRealtimePolling.ts`:

```typescript
import { ref, onMounted, onUnmounted } from 'vue'
import { useRealtimeStore } from '@/stores/realtime'
import { realtimeService } from '@/api/services/realtime.service'

export function useRealtimePolling(interval = 10000) {
  const realtimeStore = useRealtimeStore()
  const isPolling = ref(true)
  let timer: number | null = null

  const fetch = async () => {
    try {
      const data = await realtimeService.getAllPlants()
      realtimeStore.setPlants(data)
    } catch (error) {
      console.error('Failed to fetch realtime data:', error)
    }
  }

  const startPolling = () => {
    if (timer) return
    fetch()
    timer = window.setInterval(fetch, interval)
    isPolling.value = true
  }

  const stopPolling = () => {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
    isPolling.value = false
  }

  onMounted(() => {
    startPolling()
  })

  onUnmounted(() => {
    stopPolling()
  })

  return {
    isPolling,
    startPolling,
    stopPolling,
    refresh: fetch
  }
}
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend && npm run type-check`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/composables/useRealtimePolling.ts
git commit -m "feat(composables): add useRealtimePolling composable"
```

---

## Task 11: Create useEvidenceChain Composable

**Files:**
- Create: `frontend/src/composables/useEvidenceChain.ts`

- [ ] **Step 1: Write the useEvidenceChain composable**

Create `frontend/src/composables/useEvidenceChain.ts`:

```typescript
import { ref } from 'vue'
import type { DecisionPath } from '@/api/types/api.types'

export interface EvidenceItem {
  type: string
  description: string
  stepNumber: number
}

export function useEvidenceChain() {
  const expanded = ref(false)

  const formatEvidence = (decisionPath: DecisionPath[]): EvidenceItem[] => {
    return decisionPath.map(step => ({
      type: step.step_name,
      description: `${step.decision} → ${step.action}`,
      stepNumber: step.step_number
    }))
  }

  const toggleExpanded = () => {
    expanded.value = !expanded.value
  }

  return {
    expanded,
    formatEvidence,
    toggleExpanded
  }
}
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend && npm run type-check`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/composables/useEvidenceChain.ts
git commit -m "feat(composables): add useEvidenceChain composable"
```

---

## Task 12: Refactor Chat Store

**Files:**
- Modify: `frontend/src/stores/chat.ts`

- [ ] **Step 1: Read the current chat store to understand its structure**

Run: `cat frontend/src/stores/chat.ts`

- [ ] **Step 2: Replace with new chat store implementation**

Replace the entire content of `frontend/src/stores/chat.ts`:

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ChatMessage } from '@/types'
import type { QueryResponse } from '@/api/types/api.types'

export const useChatStore = defineStore('chat', () => {
  // ========== 状态 ==========
  const messages = ref<ChatMessage[]>([])
  const currentSessionId = ref<string>()
  const loading = ref(false)

  // ========== 计算属性 ==========
  const messageCount = computed(() => messages.value.length)
  const lastMessage = computed(() => messages.value[messages.value.length - 1])

  // ========== 操作方法 ==========

  /**
   * 添加用户消息
   */
  const addUserMessage = (content: string) => {
    const message: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date().toISOString()
    }
    messages.value.push(message)
  }

  /**
   * 添加助手消息
   */
  const addAssistantMessage = (response: QueryResponse) => {
    const message: ChatMessage = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: response.content,
      timestamp: response.timestamp,
      chartData: response.chartData,
      evidence: response.decision_path
    }
    messages.value.push(message)
  }

  /**
   * 添加错误消息
   */
  const addErrorMessage = (content: string) => {
    const message: ChatMessage = {
      id: (Date.now() + 1).toString(),
      role: 'system',
      content,
      timestamp: new Date().toISOString()
    }
    messages.value.push(message)
  }

  /**
   * 清空消息
   */
  const clearMessages = () => {
    messages.value = []
    currentSessionId.value = undefined
  }

  /**
   * 设置会话 ID
   */
  const setSessionId = (id: string) => {
    currentSessionId.value = id
  }

  /**
   * 设置加载状态
   */
  const setLoading = (value: boolean) => {
    loading.value = value
  }

  return {
    // 状态
    messages,
    currentSessionId,
    loading,
    // 计算属性
    messageCount,
    lastMessage,
    // 方法
    addUserMessage,
    addAssistantMessage,
    addErrorMessage,
    clearMessages,
    setSessionId,
    setLoading
  }
}, {
  id: 'chat'
})
```

- [ ] **Step 3: Verify TypeScript compilation**

Run: `cd frontend && npm run type-check`
Expected: No type errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/stores/chat.ts
git commit -m "refactor(stores): refactor chat store for new architecture"
```

---

## Task 13: Refactor Realtime Store

**Files:**
- Modify: `frontend/src/stores/realtime.ts`

- [ ] **Step 1: Replace with new realtime store implementation**

Replace the entire content of `frontend/src/stores/realtime.ts`:

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { PlantData } from '@/api/types/api.types'

export const useRealtimeStore = defineStore('realtime', () => {
  const plants = ref<PlantData[]>([])
  const loading = ref(false)
  const lastUpdate = ref<string>()

  const setPlants = (data: PlantData[]) => {
    plants.value = data
    lastUpdate.value = new Date().toISOString()
  }

  const getPlantById = (id: string) => {
    return plants.value.find(p => p.id === id)
  }

  return {
    plants,
    loading,
    lastUpdate,
    setPlants,
    getPlantById
  }
}, {
  id: 'realtime'
})
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend && npm run type-check`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/stores/realtime.ts
git commit -m "refactor(stores): refactor realtime store for new architecture"
```

---

## Task 14: Refactor Events Store

**Files:**
- Modify: `frontend/src/stores/events.ts`

- [ ] **Step 1: Replace with new events store implementation**

Replace the entire content of `frontend/src/stores/events.ts`:

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { AlertEvent, EventListRequest } from '@/api/types/api.types'
import { eventsService } from '@/api/services/events.service'

export const useEventsStore = defineStore('events', () => {
  const events = ref<AlertEvent[]>([])
  const loading = ref(false)
  const pagination = ref({
    total: 0,
    page: 1,
    pageSize: 20
  })

  const fetchEvents = async (params?: EventListRequest) => {
    loading.value = true
    try {
      const response = await eventsService.getEvents(params)
      events.value = response.items
      pagination.value = {
        total: response.total,
        page: response.page,
        pageSize: response.pageSize
      }
    } finally {
      loading.value = false
    }
  }

  const updateStatus = async (id: string, status: string) => {
    await eventsService.updateStatus(id, status)
    const event = events.value.find(e => e.id === id)
    if (event) {
      event.status = status as any
    }
  }

  return {
    events,
    loading,
    pagination,
    fetchEvents,
    updateStatus
  }
}, {
  id: 'events'
})
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend && npm run type-check`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/stores/events.ts
git commit -m "refactor(stores): refactor events store for new architecture"
```

---

## Task 15: Refactor AIOpsChat Component

**Files:**
- Modify: `frontend/src/views/AIOpsChat.vue`

- [ ] **Step 1: Read the current component to preserve UI**

Run: `cat frontend/src/views/AIOpsChat.vue`

- [ ] **Step 2: Replace script setup section while preserving template and style**

Edit `frontend/src/views/AIOpsChat.vue`. Keep the `<template>` and `<style>` sections exactly as they are. Replace only the `<script setup>` section:

```vue
<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useQueryAgent } from '@/composables/useQueryAgent'
import { useChatStore } from '@/stores/chat'
import { User, Service, Promotion } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'

// ========== Use Composables ==========
const { query, isQuerying, currentSessionId } = useQueryAgent()
const chatStore = useChatStore()

// ========== Local UI State ==========
const inputMessage = ref('')
const messagesContainer = ref<HTMLElement>()
const suggestedQuestions = ref<string[]>([
  '检查A厂最近的异常情况',
  '显示所有厂区pH趋势',
  '今天检测到哪些违规？'
])

// ========== Computed ==========
const messages = computed(() => chatStore.messages)

// ========== UI Helpers ==========
const formatTime = (iso: string) => {
  return new Date(iso).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const renderMarkdown = (text: string) => {
  return text
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// ========== Actions ==========
const sendSuggested = (question: string) => {
  inputMessage.value = question
  sendMessage()
}

const sendMessage = async () => {
  if (!inputMessage.value.trim() || isQuerying.value) return

  const queryText = inputMessage.value
  inputMessage.value = ''

  try {
    const response = await query(queryText, { page: 'chat' })

    // 渲染图表（如果有）
    if (response.chartData) {
      nextTick(() => {
        const messageId = (Date.now() + 1).toString()
        const container = document.querySelector(`[data-chart-id="${messageId}"]`) as HTMLElement
        if (container) {
          const chart = echarts.init(container)
          chart.setOption(response.chartData)
        }
      })
    }
  } catch (error) {
    ElMessage.error('查询失败')
  }

  scrollToBottom()
}

// ========== Lifecycle ==========
onMounted(() => {
  // Welcome message
  chatStore.addAssistantMessage({
    content: '你好！我是废水监测AI助手。我可以帮助你：\n\n* 分析水质数据\n* 检测异常和违规\n* 解释法规和合规性\n* 生成报告和证据链',
    session_id: '',
    timestamp: new Date().toISOString(),
    decision_path: []
  })
})
</script>
```

- [ ] **Step 3: Verify TypeScript compilation**

Run: `cd frontend && npm run type-check`
Expected: No type errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/AIOpsChat.vue
git commit -m "refactor(views): refactor AIOpsChat to use new architecture"
```

---

## Task 16: Refactor Dashboard Component

**Files:**
- Modify: `frontend/src/views/Dashboard.vue`

- [ ] **Step 1: Read the current Dashboard component**

Run: `cat frontend/src/views/Dashboard.vue`

- [ ] **Step 2: Replace script setup section to use polling composable**

Edit `frontend/src/views/Dashboard.vue`. Keep the `<template>` and `<style>` sections exactly as they are. Replace only the `<script setup>` section:

```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import { useRealtimePolling } from '@/composables/useRealtimePolling'
import { useRealtimeStore } from '@/stores/realtime'

// ========== Use Composables ==========
const { isPolling, refresh } = useRealtimePolling(10000)
const realtimeStore = useRealtimeStore()

// ========== Computed ==========
const plants = computed(() => realtimeStore.plants)

// ========== Actions ==========
const handleRefresh = () => {
  refresh()
}

// ========== Lifecycle ==========
onMounted(() => {
  // Initial data fetch is handled by useRealtimePolling
})
</script>
```

- [ ] **Step 3: Verify TypeScript compilation**

Run: `cd frontend && npm run type-check`
Expected: No type errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/Dashboard.vue
git commit -m "refactor(views): refactor Dashboard to use new architecture"
```

---

## Task 17: Refactor EventCenter Component

**Files:**
- Modify: `frontend/src/views/EventCenter.vue`

- [ ] **Step 1: Read the current EventCenter component**

Run: `cat frontend/src/views/EventCenter.vue`

- [ ] **Step 2: Replace script setup section to use events store**

Edit `frontend/src/views/EventCenter.vue`. Keep the `<template>` and `<style>` sections exactly as they are. Replace only the `<script setup>` section:

```vue
<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useEventsStore } from '@/stores/events'
import type { EventListRequest } from '@/api/types/api.types'

// ========== Use Store ==========
const eventsStore = useEventsStore()

// ========== Local State ==========
const filters = ref<EventListRequest>({})

// ========== Computed ==========
const events = computed(() => eventsStore.events)
const loading = computed(() => eventsStore.loading)
const pagination = computed(() => eventsStore.pagination)

// ========== Actions ==========
const fetchEvents = async () => {
  await eventsStore.fetchEvents(filters.value)
}

const updateEventStatus = async (id: string, status: string) => {
  await eventsStore.updateStatus(id, status)
}

const handleFilterChange = () => {
  fetchEvents()
}

const handlePageChange = (page: number) => {
  filters.value.page = page
  fetchEvents()
}

// ========== Lifecycle ==========
onMounted(() => {
  fetchEvents()
})
</script>
```

- [ ] **Step 3: Verify TypeScript compilation**

Run: `cd frontend && npm run type-check`
Expected: No type errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/EventCenter.vue
git commit -m "refactor(views): refactor EventCenter to use new architecture"
```

---

## Task 18: Refactor Logs Component

**Files:**
- Modify: `frontend/src/views/Logs.vue`

- [ ] **Step 1: Read the current Logs component**

Run: `cat frontend/src/views/Logs.vue`

- [ ] **Step 2: Replace script setup section to use logs service**

Edit `frontend/src/views/Logs.vue`. Keep the `<template>` and `<style>` sections exactly as they are. Replace only the `<script setup>` section:

```vue
<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { logsService } from '@/api/services/logs.service'
import type { LogsRequest } from '@/api/types/api.types'

// ========== Local State ==========
const logs = ref<any[]>([])
const loading = ref(false)
const pagination = ref({
  total: 0,
  page: 1,
  pageSize: 20
})
const filters = ref<LogsRequest>({})

// ========== Actions ==========
const fetchLogs = async () => {
  loading.value = true
  try {
    const response = await logsService.getLogs(filters.value)
    logs.value = response.items
    pagination.value = {
      total: response.total,
      page: response.page,
      pageSize: response.pageSize
    }
  } finally {
    loading.value = false
  }
}

const getSessionTrace = async (sessionId: string) => {
  return await logsService.getSessionTrace(sessionId)
}

const handleFilterChange = () => {
  fetchLogs()
}

const handlePageChange = (page: number) => {
  filters.value.page = page
  fetchLogs()
}

// ========== Lifecycle ==========
onMounted(() => {
  fetchLogs()
})
</script>
```

- [ ] **Step 3: Verify TypeScript compilation**

Run: `cd frontend && npm run type-check`
Expected: No type errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/Logs.vue
git commit -m "refactor(views): refactor Logs to use new architecture"
```

---

## Task 19: Delete Old API Files

**Files:**
- Delete: `frontend/src/api/index.ts`
- Delete: `frontend/src/api/query.ts`
- Delete: `frontend/src/api/realtime.ts`
- Delete: `frontend/src/api/events.ts`
- Delete: `frontend/src/api/tracing.ts`

- [ ] **Step 1: Delete old API files**

```bash
cd frontend
rm src/api/index.ts
rm src/api/query.ts
rm src/api/realtime.ts
rm src/api/events.ts
rm src/api/tracing.ts
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend && npm run type-check`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add -A frontend/src/api/
git commit -m "chore(api): remove old API files replaced by new architecture"
```

---

## Task 20: Update Vite Config

**Files:**
- Modify: `frontend/vite.config.ts`

- [ ] **Step 1: Read the current vite config**

Run: `cat frontend/vite.config.ts`

- [ ] **Step 2: Ensure proper path aliases are configured**

The vite.config.ts should have these path aliases:

```typescript
export default defineConfig({
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  // ... rest of config
})
```

If this is already present, no changes are needed. If not, add the alias configuration.

- [ ] **Step 3: Verify build works**

Run: `cd frontend && npm run build`
Expected: Build succeeds without errors

- [ ] **Step 4: Commit if changes were made**

```bash
git add frontend/vite.config.ts
git commit -m "chore(config): ensure vite path aliases are configured"
```

---

## Task 21: End-to-End Testing

**Files:**
- Test: Manual testing

- [ ] **Step 1: Start the backend server**

```bash
# From project root
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Expected: Server starts on port 8000

- [ ] **Step 2: Start the frontend dev server**

```bash
cd frontend
npm run dev
```

Expected: Frontend starts on port 5173

- [ ] **Step 3: Test chat functionality**

1. Open browser to `http://localhost:5173/chat`
2. Send a test query: "检查A厂最近的异常情况"
3. Verify response is displayed correctly
4. Check browser console for errors

Expected: Query response is displayed, no console errors

- [ ] **Step 4: Test realtime data**

1. Navigate to Dashboard
2. Verify plant data is displayed
3. Wait for polling update (10 seconds)
4. Verify data refreshes

Expected: Plant data displays and refreshes automatically

- [ ] **Step 5: Test events functionality**

1. Navigate to Event Center
2. Verify events list loads
3. Try filtering by type or status
4. Try updating an event status

Expected: Events display correctly, filters work, status updates work

- [ ] **Step 6: Test logs functionality**

1. Navigate to Logs
2. Verify logs load
3. Try filtering by log type
4. Check session trace functionality

Expected: Logs display correctly, filters work

- [ ] **Step 7: Verify no TypeScript or build errors**

```bash
cd frontend
npm run type-check
npm run build
```

Expected: No errors

- [ ] **Step 8: Commit any fixes discovered during testing**

```bash
git add -A frontend/
git commit -m "fix: resolve issues discovered during e2e testing"
```

---

## Task 22: Documentation Update

**Files:**
- Create: `frontend/README.md`
- Modify: `docs/superpowers/specs/2026-07-16-frontend-architecture-refactoring-design.md`

- [ ] **Step 1: Create frontend README documenting the new architecture**

Create `frontend/README.md`:

```markdown
# 废水监测系统前端

## 技术栈

- Vue 3.5 (Composition API)
- TypeScript
- Vite 6
- Pinia 3 (状态管理)
- Element Plus 2 (UI组件库)
- Axios 1 (HTTP客户端)
- ECharts 5 (数据可视化)

## 架构

```
Views (页面层)
  ↓
Components (组件层)
  ↓
Stores (状态管理层) - Pinia
  ↓
Composables (业务逻辑复用层)
  ↓
API Services (API层)
  ↓
HTTP Client (axios)
  ↓
Backend FastAPI
```

## 目录结构

\`\`\`
src/
├── api/              # API层
│   ├── client.ts     # 统一HTTP客户端
│   ├── services/     # API服务
│   └── types/        # API类型定义
├── composables/      # 业务逻辑复用
├── stores/           # Pinia状态管理
├── types/            # 业务类型定义
├── components/       # Vue组件
├── views/            # 页面组件
└── router/           # 路由配置
\`\`\`

## 开发

\`\`\`bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 类型检查
npm run type-check

# 构建
npm run build
\`\`\`

## API集成

所有API调用通过 \`api/services/\` 下的服务类进行：

- \`queryService\` - 查询接口
- \`realtimeService\` - 实时数据接口
- \`eventsService\` - 事件管理接口
- \`logsService\` - 日志查询接口

## 状态管理

使用Pinia进行状态管理：

- \`useChatStore\` - 聊天状态
- \`useRealtimeStore\` - 实时数据状态
- \`useEventsStore\` - 事件状态

## 业务逻辑复用

使用Composables复用业务逻辑：

- \`useQueryAgent\` - 查询智能体逻辑
- \`useRealtimePolling\` - 实时数据轮询
- \`useEvidenceChain\` - 证据链展示
\`\`\`

## 后端API

- 基础URL: \`/api\`
- 超时时间: 5分钟
- 代理配置: Vite proxy → \`http://localhost:8000\`
\`\`\`
```

- [ ] **Step 2: Update the design document status**

Edit `docs/superpowers/specs/2026-07-16-frontend-architecture-refactoring-design.md`, change the status at the bottom:

```markdown
---
**文档版本**: 1.1
**创建日期**: 2026-07-16
**作者**: Claude AI Agent
**状态**: 已实施
```

- [ ] **Step 3: Commit documentation**

```bash
git add frontend/README.md docs/superpowers/specs/2026-07-16-frontend-architecture-refactoring-design.md
git commit -m "docs: update documentation after architecture refactoring"
```

---

## Verification Checklist

After completing all tasks, verify:

- [ ] All files created and committed
- [ ] TypeScript compilation passes (`npm run type-check`)
- [ ] Build succeeds (`npm run build`)
- [ ] Dev server starts (`npm run dev`)
- [ ] Chat functionality works end-to-end
- [ ] Realtime data polling works
- [ ] Events page loads and filters work
- [ ] Logs page loads and filters work
- [ ] No console errors in browser
- [ ] UI appearance unchanged from before refactor
- [ ] All old API files deleted
- [ ] Documentation updated

---

**Plan Complete**
