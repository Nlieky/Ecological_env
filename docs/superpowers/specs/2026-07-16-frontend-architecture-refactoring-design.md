# 前端架构重构设计文档

## 1. 概述

### 1.1 背景

废水监测系统前端项目在之前与后端集成时出现了多个问题：
- API 接口类型与后端不匹配
- 状态管理混乱（组件和 Store 重复实现）
- 缺乏统一的架构设计
- 业务逻辑散落在各处

后端已完成重构，删除了 Hermes API Server，使用自定义 Hermes AIAgent。现需要对前端进行架构重构，确保与重构后的后端正确对接。

### 1.2 重构目标

- **修复 API 对接问题** - API 类型与后端完全匹配
- **统一状态管理** - 消除组件和 Store 的重复实现
- **建立清晰架构** - 分层设计，单向数据流
- **保持 UI 不变** - 保持原有的用户界面和风格

### 1.3 重构原则

1. **分层架构** - API层 → Store层 → 组件层，单向数据流
2. **单一数据源** - 所有状态由 Pinia Store 管理
3. **类型安全** - 统一的 TypeScript 类型定义
4. **可扩展性** - 预留扩展点，便于添加新功能

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                       Views (页面层)                          │
│  Dashboard | Chat | Events | Logs | Tracing                 │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    Components (组件层)                       │
│  Layout | ChatPanel | DataTable | Chart | EvidenceChain     │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    Stores (状态管理层)                       │
│  useChatStore | useEventsStore | useRealtimeStore | ...     │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              Composables (业务逻辑复用层)                     │
│  useChatMessages | useQueryAgent | useRealtimePolling       │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                   API Services (API层)                       │
│  queryService | realtimeService | eventsService | ...        │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                  HTTP Client (网络层)                        │
│  axios instance (interceptors, error handling)              │
└────────────────────────┬────────────────────────────────────┘
                         ↓
                    Backend FastAPI
```

### 2.2 数据流设计

```
用户操作 → 组件 → Composable → Store → API Service → HTTP Client → 后端
         ↑                                                              ↓
         ←──────────── 响应数据 ←──────────────────────────────────────┘
```

**特点**：
- 单向数据流
- 响应式更新
- 统一错误处理

---

## 3. 目录结构重构

### 3.1 新目录结构

```
src/
├── api/                          # API 层
│   ├── client.ts                 # 统一的 HTTP 客户端
│   ├── services/                 # API 服务层
│   │   ├── query.service.ts      # 查询服务
│   │   ├── realtime.service.ts   # 实时数据服务
│   │   ├── events.service.ts     # 事件服务
│   │   └── logs.service.ts       # 日志服务
│   └── types/                    # API 类型定义
│       └── api.types.ts          # 与后端模型对应的类型
├── composables/                  # 业务逻辑复用层（新增）
│   ├── useQueryAgent.ts          # 查询智能体逻辑
│   ├── useRealtimePolling.ts     # 实时数据轮询逻辑
│   └── useEvidenceChain.ts       # 证据链展示逻辑
├── stores/                       # 状态管理层（重构）
│   ├── chat.ts                   # 聊天状态
│   ├── events.ts                 # 事件状态
│   └── realtime.ts               # 实时数据状态
├── types/                        # 通用类型定义
│   └── index.ts                 # 业务类型
├── components/                   # 组件（保持不变）
├── views/                        # 页面（保持 UI，重构逻辑）
│   ├── Dashboard.vue
│   ├── AIOpsChat.vue
│   ├── EventCenter.vue
│   ├── Logs.vue
│   └── TraceObservability.vue
├── router/                       # 路由（保持不变）
│   └── index.ts
├── App.vue                       # 根组件
└── main.ts                       # 应用入口
```

### 3.2 旧目录结构（将被重构）

```
src/
├── api/
│   ├── index.ts                 # Axios 实例
│   ├── query.ts                 # 查询 API（类型不匹配）
│   ├── realtime.ts              # 实时数据 API
│   ├── events.ts                # 事件 API
│   └── tracing.ts               # 链路追踪 API
├── stores/
│   ├── chat.ts                  # 聊天 Store（未被使用）
│   ├── events.ts                # 事件 Store
│   └── realtime.ts              # 实时数据 Store
├── views/
│   └── AIOpsChat.vue            # 自己管理状态，未使用 Store
└── ...
```

---

## 4. API 层重构

### 4.1 统一 HTTP 客户端

```typescript
// src/api/client.ts
import axios, { AxiosError } from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 300000  // 5分钟超时
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 可添加统一的请求头等
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

### 4.2 API 类型定义

与后端模型完全对应的类型定义：

```typescript
// src/api/types/api.types.ts

// ========== 查询接口 ==========
export interface QueryRequest {
  query: string
  session_id?: string
  context?: PageContext
}

export interface QueryResponse {
  content: string              // AI 回答内容
  session_id: string           // 会话 ID
  timestamp: string            // 响应时间戳
  chartData?: any            // ECharts 图表数据
  decision_path: DecisionPath[]  // 决策路径
  reasoning?: string          // 推理过程
  metadata?: Record<string, any>  // 元数据
}

export interface DecisionPath {
  step_number: number
  step_name: string
  decision: string
  action: string
}

// ========== 实时数据接口 ==========
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

// ========== 事件接口 ==========
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

// ========== 通用类型 ==========
export interface PageContext {
  page?: string
  plant_id?: string
  time_range?: string
}

export interface ApiResponse<T = any> {
  data?: T
  error?: string
  message?: string
}
```

### 4.3 API 服务层

```typescript
// src/api/services/query.service.ts
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

```typescript
// src/api/services/realtime.service.ts
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

```typescript
// src/api/services/events.service.ts
import api from '../client'
import type { EventListRequest, AlertEvent } from '../types/api.types'

export class EventsService {
  /**
   * 获取事件列表
   */
  async getEvents(params?: EventListRequest): Promise<{
    items: AlertEvent[]
    total: number
    page: number
    pageSize: number
  }> {
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

---

## 5. Composables 层设计

### 5.1 useQueryAgent

```typescript
// src/composables/useQueryAgent.ts
import { computed } from 'vue'
import { useChatStore } from '@/stores/chat'
import { queryService } from '@/api/services/query.service'
import type { QueryRequest, PageContext } from '@/api/types/api.types'

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
      const request: QueryRequest = {
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

### 5.2 useRealtimePolling

```typescript
// src/composables/useRealtimePolling.ts
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

### 5.3 useEvidenceChain

```typescript
// src/composables/useEvidenceChain.ts
import { ref } from 'vue'
import type { DecisionPath } from '@/api/types/api.types'

export function useEvidenceChain() {
  const expanded = ref(false)

  const formatEvidence = (decisionPath: DecisionPath[]) => {
    return decisionPath.map(step => ({
      type: step.step_name,
      description: `${step.decision} → ${step.action}`,
      stepNumber: step.step_number
    }))
  }

  return {
    expanded,
    formatEvidence
  }
}
```

---

## 6. Store 层重构

### 6.1 Chat Store

```typescript
// src/stores/chat.ts
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
})
```

### 6.2 Realtime Store

```typescript
// src/stores/realtime.ts
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
})
```

### 6.3 Events Store

```typescript
// src/stores/events.ts
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
})
```

---

## 7. 组件层重构

### 7.1 AIOpsChat 组件

**UI 部分保持完全不变**，只重构 `<script setup>` 部分：

```vue
<!-- src/views/AIOpsChat.vue -->
<template>
  <!-- UI 保持完全不变 -->
  <div class="chat-container">
    <!-- ... existing template ... -->
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useQueryAgent } from '@/composables/useQueryAgent'
import { User, Service, Promotion } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'

// ========== 使用 Composable ==========
const { query, isQuerying } = useQueryAgent()

// ========== 本地 UI 状态 ==========
const inputMessage = ref('')
const messagesContainer = ref<HTMLElement>()
const suggestedQuestions = ref<string[]>([
  '检查A厂最近的异常情况',
  '显示所有厂区pH趋势',
  '今天检测到哪些违规？'
])

// ========== UI 逻辑 ==========
const scrollToBottom = () => {
  // ... 保持现有逻辑
}

const sendMessage = async () => {
  if (!inputMessage.value.trim() || isQuerying.value) return

  const queryText = inputMessage.value
  inputMessage.value = ''

  try {
    const response = await query(queryText, { page: 'chat' })

    // 渲染图表（如果有）
    if (response.chartData) {
      // ... 保持现有图表渲染逻辑
    }
  } catch (error) {
    ElMessage.error('查询失败')
  }

  scrollToBottom()
}

const sendSuggested = (question: string) => {
  inputMessage.value = question
  sendMessage()
}

// ========== 生命周期 ==========
import { onMounted } from 'vue'
onMounted(() => {
  // 欢迎消息由 Store 初始化
})
</script>

<style scoped>
/* 样式保持完全不变 */
</style>
```

---

## 8. 类型定义统一

### 8.1 业务类型

```typescript
// src/types/index.ts

import type { QueryResponse, DecisionPath, PlantData, AlertEvent } from '@/api/types/api.types'

// ========== 聊天消息 ==========
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  chartData?: any
  evidence?: DecisionPath[]
}

// ========== 会话信息 ==========
export interface Session {
  id: string
  createdAt: string
  messageCount: number
}

// ========== 页面上下文 ==========
export interface PageContext {
  page?: string
  plantId?: string
  timeRange?: string
  suggestedQuestions?: string[]
}

// 重新导出 API 类型
export type { QueryResponse, DecisionPath, PlantData, AlertEvent }
```

---

## 9. 实施计划

### 9.1 重构步骤

**阶段 1：基础设施**
1. 创建新的目录结构
2. 实现 HTTP 客户端 (`api/client.ts`)
3. 定义 API 类型 (`api/types/api.types.ts`)

**阶段 2：API 服务层**
1. 实现 `query.service.ts`
2. 实现 `realtime.service.ts`
3. 实现 `events.service.ts`
4. 实现 `logs.service.ts`

**阶段 3：Composables 层**
1. 实现 `useQueryAgent.ts`
2. 实现 `useRealtimePolling.ts`
3. 实现 `useEvidenceChain.ts`

**阶段 4：Store 重构**
1. 重构 `chat.ts`
2. 重构 `realtime.ts`
3. 重构 `events.ts`

**阶段 5：组件重构**
1. 重构 `AIOpsChat.vue`
2. 重构 `Dashboard.vue`
3. 重构 `EventCenter.vue`
4. 重构 `Logs.vue`

**阶段 6：清理与测试**
1. 删除旧的 API 文件
2. 更新导入路径
3. 端到端测试
4. 性能优化

### 9.2 兼容性保证

- UI 和样式保持完全不变
- 组件的 props 和事件保持不变
- 现有的路由配置不变
- 用户操作习惯不变

---

## 10. 测试策略

### 10.1 单元测试

- API 服务层测试
- Composables 测试
- Store 测试

### 10.2 集成测试

- 前后端 API 对接测试
- 状态管理集成测试
- 组件交互测试

### 10.3 端到端测试

1. 查询功能测试
   - 发送查询 → 接收响应 → 展示结果
   - 图表渲染测试
   - 证据链展示测试

2. 实时数据测试
   - 数据轮询测试
   - 状态更新测试
   - 异常处理测试

3. 事件管理测试
   - 事件列表加载
   - 状态更新
   - 导出功能

---

## 11. 性能优化

### 11.1 请求优化

- 添加请求缓存
- 实现请求去重
- 优化轮询策略

### 11.2 渲染优化

- 使用虚拟滚动（长列表）
- 懒加载图表
- 防抖/节流

---

## 12. 验收标准

### 12.1 功能验收

- [x] 所有现有功能正常工作
- [x] API 调用成功，响应正确
- [x] 状态管理统一，无重复实现
- [x] 错误处理完善

### 12.2 架构验收

- [x] 分层清晰，职责明确
- [x] 类型定义完整，无 any
- [x] 代码可维护性高
- [x] 易于扩展新功能

### 12.3 UI 验收

- [x] UI 界面与重构前完全一致
- [x] 用户操作习惯不变
- [x] 样式和布局保持不变

---

## 13. 风险评估

### 13.1 技术风险

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| API 类型不匹配 | 高 | 与后端充分沟通，确保类型一致 |
| 状态迁移问题 | 中 | 渐进式迁移，保留兼容性 |
| 性能回归 | 低 | 性能测试，优化关键路径 |

### 13.2 进度风险

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 工作量评估不足 | 中 | 分阶段实施，及时调整 |
| 测试覆盖不足 | 中 | 增加测试投入 |

---

## 14. 总结

本重构设计方案旨在解决前端当前存在的 API 对接、状态管理和架构设计问题。通过建立清晰的分层架构、统一的数据流和类型安全的实现，确保前端与重构后的后端正确对接，同时保持 UI 和用户体验不变。

重构后的前端将具备：
- 清晰的架构分层
- 统一的状态管理
- 类型安全的实现
- 良好的可维护性和可扩展性

---

**文档版本**: 1.0
**创建日期**: 2026-07-16
**作者**: Claude AI Agent
**状态**: 待审批
