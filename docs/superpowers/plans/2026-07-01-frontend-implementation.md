# 废水监测系统前端界面实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标**: 构建 Vue 3 前端应用，实现监测大屏、AI 助手、事件中心等核心功能

**架构**: 借鉴 SxDevOps 前端代码，针对废水监测业务定制化修改。采用 Vue 3 + Vite + Element Plus + ECharts 技术栈。

**技术栈**: Vue 3、Vite、Element Plus、ECharts、Pinia、Vue Router

---

## 文件结构

```
frontend/                          # 新建前端项目
├── src/
│   ├── views/                     # 页面组件
│   │   ├── Dashboard.vue          # 监测大屏（4×4 厂区）
│   │   ├── AIOpsChat.vue          # AI 助手完整版
│   │   └── EventCenter.vue        # 事件中心
│   ├── components/                # 可复用组件
│   │   ├── layout/                # 布局组件
│   │   │   ├── AppLayout.vue      # 主布局（左侧导航+中间内容）
│   │   │   └── SideNav.vue        # 左侧导航栏
│   │   ├── dashboard/             # 监测大屏组件
│   │   │   ├── PlantCard.vue      # 厂区卡片
│   │   │   └── PlantGrid.vue      # 4×4 网格布局
│   │   ├── aiops/                 # AI 助手组件
│   │   │   ├── ChatWidget.vue     # 浮窗组件
│   │   │   ├── ChatMessage.vue    # 消息组件
│   │   │   └── EChartsChart.vue    # ECharts 图表组件
│   │   └── events/                # 事件中心组件
│   │       ├── EventList.vue      # 告警列表
│   │       └── EventDetail.vue    # 告警详情弹窗
│   ├── api/                       # API 调用封装
│   │   ├── index.ts                # Axios 实例配置
│   │   ├── query.ts               # 查询接口
│   │   ├── realtime.ts            # 实时数据接口
│   │   └── events.ts              # 事件接口
│   ├── router/                    # 路由配置
│   │   └── index.ts
│   ├── stores/                    # Pinia 状态管理
│   │   ├── realtime.ts            # 实时数据状态
│   │   ├── chat.ts                # 聊天状态
│   │   └── events.ts              # 事件状态
│   ├── types/                     # TypeScript 类型定义
│   │   └── index.ts
│   ├── utils/                     # 工具函数
│   │   └── index.ts
│   ├── App.vue                    # 根组件
│   └── main.ts                    # 入口文件
├── public/
│   └── favicon.ico
├── index.html
├── vite.config.ts
├── tsconfig.json
├── package.json
└── tsconfig.node.json

backend/                           # 现有后端扩展
├── api/
│   └── routes/
│       ├── realtime.py            # 新增：实时数据接口
│       └── events.py              # 新增：事件接口
└── models/
    └── event.py                   # 新增：事件数据模型
```

---

## 任务分解

### Phase 1: 项目初始化

### Task 1: 创建前端项目结构

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/vite-env.d.ts`

- [ ] **Step 1: 创建 package.json**

```json
{
  "name": "ecological-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.2.0",
    "pinia": "^2.1.0",
    "element-plus": "^2.5.0",
    "@element-plus/icons-vue": "^2.3.0",
    "echarts": "^5.5.0",
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "vue-tsc": "^1.8.0"
  }
}
```

- [ ] **Step 2: 创建 vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true
      }
    }
  }
})
```

- [ ] **Step 3: 创建 tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "preserve",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src/**/*.ts", "src/**/*.d.ts", "src/**/*.tsx", "src/**/*.vue"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 4: 创建 tsconfig.node.json**

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 5: 创建 index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>废水监测智能体系统</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

- [ ] **Step 6: 创建 src/main.ts**

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'

const app = createApp(App)
const pinia = createPinia()

// 注册所有 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(pinia)
app.use(router)
app.use(ElementPlus)
app.mount('#app')
```

- [ ] **Step 7: 创建 src/App.vue**

```vue
<template>
  <router-view />
</template>

<script setup lang="ts">
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  height: 100vh;
  overflow: hidden;
}
</style>
```

- [ ] **Step 8: 创建 src/vite-env.d.ts**

```typescript
declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}
```

- [ ] **Step 9: 安装依赖**

```bash
cd frontend
npm install
```

- [ ] **Step 10: 验证项目启动**

```bash
npm run dev
```

访问 http://localhost:3000，应该看到空白页面（App.vue 渲染）

- [ ] **Step 11: 提交**

```bash
git add frontend/
git commit -m "feat: initialize Vue 3 frontend project"
```

---

### Task 2: 创建类型定义和 API 配置

**Files:**
- Create: `frontend/src/types/index.ts`
- Create: `frontend/src/api/index.ts`
- Create: `frontend/src/api/realtime.ts`
- Create: `frontend/src/api/query.ts`
- Create: `frontend/src/api/events.ts`

- [ ] **Step 1: 创建类型定义 src/types/index.ts**

```typescript
// 水质指标
export interface WaterMetrics {
  pH: number
  cod: number
  ammoniaNitrogen: number
  totalNitrogen: number
  totalPhosphorus: number
  flow: number
}

// 指标状态
export type MetricStatus = 'normal' | 'abnormal' | 'offline'

// 厂区数据
export interface PlantData {
  id: string
  name: string
  status: 'online' | 'offline'
  metrics: WaterMetrics | null
  metricStatus: Record<keyof WaterMetrics, MetricStatus>
  lastUpdate: string
}

// AI 消息
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  evidence?: any[]
  chartData?: any
}

// 告警事件
export interface AlertEvent {
  id: string
  timestamp: string
  type: string
  plantId: string
  severity: 'low' | 'medium' | 'high'
  status: 'pending' | 'processing' | 'resolved' | 'ignored'
  evidence: {
    dataSnapshot: WaterMetrics
    operators: Array<{
      name: string
      result: any
    }>
    rules: Array<{
      name: string
      matched: boolean
    }>
    llmReasoning: string
  }
}

// 页面上下文
export interface PageContext {
  page: string
  plantId?: string
  timeRange?: [string, string]
  suggestedQuestions?: string[]
}
```

- [ ] **Step 2: 创建 Axios 配置 src/api/index.ts**

```typescript
import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

api.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    ElMessage.error(error.response?.data?.message || '请求失败')
    return Promise.reject(error)
  }
)

export default api
```

- [ ] **Step 3: 创建实时数据 API src/api/realtime.ts**

```typescript
import api from './index'
import type { PlantData } from '@/types'

export const realtimeApi = {
  // 获取所有厂区实时数据
  getAllPlants: () => {
    return api.get<any, PlantData[]>('/realtime/plants')
  },

  // 获取单个厂区数据
  getPlant: (id: string) => {
    return api.get<any, PlantData>(`/realtime/plants/${id}`)
  }
}
```

- [ ] **Step 4: 创建查询 API src/api/query.ts**

```typescript
import api from './index'
import type { ChatMessage } from '@/types'

export const queryApi = {
  // 发送查询
  sendQuery: (query: string, context?: any) => {
    return api.post<any, { sessionId: string; response: string }>('/query', {
      query,
      context
    })
  }
}
```

- [ ] **Step 5: 创建事件 API src/api/events.ts**

```typescript
import api from './index'
import type { AlertEvent } from '@/types'

export const eventsApi = {
  // 获取事件列表
  getEvents: (params: {
    startTime?: string
    endTime?: string
    type?: string
    plantId?: string
    severity?: string
    status?: string
    page?: number
    pageSize?: number
  }) => {
    return api.get<any, { data: AlertEvent[]; total: number }>('/events', { params })
  },

  // 获取事件详情
  getEventDetail: (id: string) => {
    return api.get<any, AlertEvent>(`/events/${id}`)
  },

  // 更新事件状态
  updateEventStatus: (id: string, status: string) => {
    return api.put<any, AlertEvent>(`/events/${id}/status`, { status })
  },

  // 导出事件
  exportEvents: (params: any, format: 'xlsx' | 'pdf' | 'json' = 'xlsx') => {
    return api.get(`/events/export`, {
      params: { ...params, format },
      responseType: 'blob'
    })
  }
}
```

- [ ] **Step 6: 提交**

```bash
git add frontend/src/types frontend/src/api
git commit -m "feat: add type definitions and API modules"
```

---

### Task 3: 创建 Pinia 状态管理

**Files:**
- Create: `frontend/src/stores/realtime.ts`
- Create: `frontend/src/stores/chat.ts`
- Create: `frontend/src/stores/events.ts`

- [ ] **Step 1: 创建实时数据状态 stores/realtime.ts**

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { PlantData } from '@/types'
import { realtimeApi } from '@/api/realtime'

export const useRealtimeStore = defineStore('realtime', () => {
  const plants = ref<PlantData[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // 初始化厂区数据（4×4 框架，1个有数据）
  const initializePlants = async () => {
    loading.value = true
    error.value = null
    try {
      const data = await realtimeApi.getAllPlants()
      plants.value = data
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  // 更新单个厂区数据
  const updatePlant = (plantId: string, data: Partial<PlantData>) => {
    const index = plants.value.findIndex(p => p.id === plantId)
    if (index !== -1) {
      plants.value[index] = { ...plants.value[index], ...data }
    }
  }

  return {
    plants,
    loading,
    error,
    initializePlants,
    updatePlant
  }
})
```

- [ ] **Step 2: 创建聊天状态 stores/chat.ts**

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ChatMessage, PageContext } from '@/types'
import { queryApi } from '@/api/query'

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const loading = ref(false)
  const currentSessionId = ref<string | null>(null)
  const pageContext = ref<PageContext | null>(null)

  // 发送消息
  const sendMessage = async (content: string) => {
    loading.value = true

    // 添加用户消息
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date().toISOString()
    }
    messages.value.push(userMessage)

    try {
      const response = await queryApi.sendQuery(content, pageContext.value)
      currentSessionId.value = response.sessionId

      // 添加助手消息
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.response,
        timestamp: new Date().toISOString()
      }
      messages.value.push(assistantMessage)
    } catch (e: any) {
      messages.value.push({
        id: (Date.now() + 1).toString(),
        role: 'system',
        content: '查询失败，请稍后重试',
        timestamp: new Date().toISOString()
      })
    } finally {
      loading.value = false
    }
  }

  // 设置页面上下文
  const setPageContext = (context: PageContext) => {
    pageContext.value = context
  }

  // 清空消息
  const clearMessages = () => {
    messages.value = []
    currentSessionId.value = null
  }

  return {
    messages,
    loading,
    currentSessionId,
    pageContext,
    sendMessage,
    setPageContext,
    clearMessages
  }
})
```

- [ ] **Step 3: 创建事件状态 stores/events.ts**

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { AlertEvent } from '@/types'
import { eventsApi } from '@/api/events'

export const useEventsStore = defineStore('events', () => {
  const events = ref<AlertEvent[]>([])
  const total = ref(0)
  const loading = ref(false)
  const currentPage = ref(1)
  const pageSize = ref(20)

  // 获取事件列表
  const fetchEvents = async (params?: any) => {
    loading.value = true
    try {
      const result = await eventsApi.getEvents({
        page: currentPage.value,
        pageSize: pageSize.value,
        ...params
      })
      events.value = result.data
      total.value = result.total
    } finally {
      loading.value = false
    }
  }

  // 更新事件状态
  const updateStatus = async (id: string, status: string) => {
    await eventsApi.updateEventStatus(id, status)
    const index = events.value.findIndex(e => e.id === id)
    if (index !== -1) {
      events.value[index].status = status as any
    }
  }

  return {
    events,
    total,
    loading,
    currentPage,
    pageSize,
    fetchEvents,
    updateStatus
  }
})
```

- [ ] **Step 4: 提交**

```bash
git add frontend/src/stores
git commit -m "feat: add Pinia stores for state management"
```

---

### Task 4: 创建路由配置

**Files:**
- Create: `frontend/src/router/index.ts`

- [ ] **Step 1: 创建路由配置 src/router/index.ts**

```typescript
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/dashboard'
    },
    {
      path: '/dashboard',
      component: () => import('@/views/Dashboard.vue'),
      meta: { title: '监测大屏' }
    },
    {
      path: '/chat',
      component: () => import('@/views/AIOpsChat.vue'),
      meta: { title: 'AI 助手' }
    },
    {
      path: '/events',
      component: () => import('@/views/EventCenter.vue'),
      meta: { title: '事件中心' }
    }
  ]
})

export default router
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/router
git commit -m "feat: add router configuration"
```

---

### Task 5: 创建布局组件

**Files:**
- Create: `frontend/src/components/layout/AppLayout.vue`
- Create: `frontend/src/components/layout/SideNav.vue`

- [ ] **Step 1: 创建主布局组件 components/layout/AppLayout.vue**

```vue
<template>
  <el-container class="app-layout">
    <el-aside width="200px">
      <SideNav />
    </el-aside>
    <el-main>
      <router-view />
    </el-main>
    <ChatWidget v-if="showChatWidget" />
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import SideNav from './SideNav.vue'
import ChatWidget from '@/components/aiops/ChatWidget.vue'

const route = useRoute()
const showChatWidget = computed(() => route.path !== '/chat')
</script>

<style scoped>
.app-layout {
  height: 100vh;
}

.el-aside {
  background-color: #1a1a2e;
  border-right: 1px solid #16213e;
}

.el-main {
  padding: 20px;
  overflow: auto;
}
</style>
```

- [ ] **Step 2: 创建侧边导航栏 components/layout/SideNav.vue**

```vue
<template>
  <div class="side-nav">
    <div class="logo">
      <h2>废水监测</h2>
    </div>
    <el-menu
      :default-active="activeMenu"
      router
      background-color="#1a1a2e"
      text-color="#eaeaea"
      active-text-color="#409eff"
    >
      <el-menu-item index="/chat">
        <el-icon><ChatDotRound /></el-icon>
        <span>AI 助手</span>
      </el-menu-item>
      <el-sub-menu index="dashboard">
        <template #title>
          <el-icon><Monitor /></el-icon>
          <span>监测大屏</span>
        </template>
        <el-menu-item index="/dashboard">厂区概览</el-menu-item>
      </el-sub-menu>
      <el-menu-item index="/events">
        <el-icon><Bell /></el-icon>
        <span>事件中心</span>
      </el-menu-item>
    </el-menu>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { ChatDotRound, Monitor, Bell } from '@element-plus/icons-vue'

const route = useRoute()
const activeMenu = computed(() => {
  return route.path
})
</script>

<style scoped>
.side-nav {
  height: 100%;
}

.logo {
  padding: 20px;
  text-align: center;
  color: #409eff;
  font-size: 18px;
  font-weight: bold;
}

.el-menu {
  border-right: none;
}
</style>
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/layout
git commit -m "feat: add layout components"
```

---

### Task 6: 创建监测大屏组件

**Files:**
- Create: `frontend/src/views/Dashboard.vue`
- Create: `frontend/src/components/dashboard/PlantGrid.vue`
- Create: `frontend/src/components/dashboard/PlantCard.vue`

- [ ] **Step 1: 创建厂区卡片组件 components/dashboard/PlantCard.vue**

```vue
<template>
  <div class="plant-card" :class="{ 'has-data': hasData, 'placeholder': !hasData }">
    <template v-if="hasData">
      <div class="plant-header">
        <el-icon><OfficeBuilding /></el-icon>
        <span>{{ plant.name }}</span>
      </div>
      <div class="plant-metrics">
        <div v-for="(value, key) in displayMetrics" :key="key" class="metric-item">
          <span class="metric-label">{{ metricLabels[key as keyof WaterMetrics] }}</span>
          <span class="metric-value" :class="getMetricStatusClass(key, value)">
            {{ formatMetricValue(key, value) }}
            <el-icon v-if="getMetricIcon(key, value)">
              <component :is="getMetricIcon(key, value)" />
            </el-icon>
          </span>
        </div>
      </div>
      <div class="plant-footer">
        <span>更新: {{ formatTime(plant.lastUpdate) }}</span>
        <el-tag :type="plant.status === 'online' ? 'success' : 'info'" size="small">
          {{ plant.status === 'online' ? '正常运行' : '离线' }}
        </el-tag>
      </div>
    </template>
    <template v-else>
      <div class="placeholder">
        <el-icon :size="32"><OfficeBuilding /></el-icon>
        <span>待接入厂区</span>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { OfficeBuilding, CircleCheck, Warning, CircleClose } from '@element-plus/icons-vue'
import type { PlantData, WaterMetrics, MetricStatus } from '@/types'

const props = defineProps<{
  plant: PlantData
}>()

const hasData = computed(() => props plant.status === 'online' && props.plant.metrics)

const displayMetrics = computed(() => {
  return hasData.value ? props.plant.metrics! : {}
})

const metricLabels: Record<keyof WaterMetrics, string> = {
  pH: 'pH',
  cod: 'COD',
  ammoniaNitrogen: '氨氮',
  totalNitrogen: '总氮',
  totalPhosphorus: '总磷',
  flow: '流量'
}

const getMetricStatus = (key: keyof WaterMetrics, value: number): MetricStatus => {
  const thresholds: Record<keyof WaterMetrics, { min: number; max: number }> = {
    pH: { min: 6, max: 9 },
    cod: { min: 0, max: 50 },
    ammoniaNitrogen: { min: 0, max: 15 },
    totalNitrogen: { min: 0, max: 20 },
    totalPhosphorus: { min: 0, max: 1 },
    flow: { min: 0.001, max: Infinity }
  }

  const threshold = thresholds[key]
  if (value < threshold.min || value > threshold.max) {
    return 'abnormal'
  }
  return 'normal'
}

const getMetricStatusClass = (key: keyof WaterMetrics, value: number) => {
  const status = getMetricStatus(key, value)
  return {
    'status-normal': status === 'normal',
    'status-abnormal': status === 'abnormal'
  }
}

const getMetricIcon = (key: keyof WaterMetrics, value: number) => {
  const status = getMetricStatus(key, value)
  if (status === 'normal') return CircleCheck
  if (status === 'abnormal') return Warning
  return null
}

const formatMetricValue = (key: keyof WaterMetrics, value: number) => {
  if (key === 'pH' || key === 'cod') return value.toFixed(1)
  if (key === 'flow') return value.toFixed(0)
  return value.toFixed(1)
}

const formatTime = (time: string) => {
  return new Date(time).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.plant-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  min-height: 180px;
  background: white;
  transition: all 0.3s;
}

.plant-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.plant-card.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
}

.placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #909399;
}

.plant-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: bold;
  margin-bottom: 16px;
  color: #409eff;
}

.plant-metrics {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.metric-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.metric-label {
  color: #606266;
}

.metric-value {
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: 500;
}

.metric-value.status-normal {
  color: #67c23a;
}

.metric-value.status-abnormal {
  color: #e6a23c;
}

.plant-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #e4e7ed;
  font-size: 12px;
  color: #909399;
}
</style>
```

- [ ] **Step 2: 创建 4×4 网格组件 components/dashboard/PlantGrid.vue**

```vue
<template>
  <div class="plant-grid">
    <div
      v-for="i in 16"
      :key="i"
      class="grid-item"
    >
      <PlantCard
        v-if="plants[i - 1]"
        :plant="plants[i - 1]"
      />
      <PlantCard
        v-else
        :plant="{ id: `empty-${i}`, name: `厂区 ${i}`, status: 'offline', metrics: null, metricStatus: {} as any, lastUpdate: '' }"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import PlantCard from './PlantCard.vue'
import { useRealtimeStore } from '@/stores/realtime'

const realtimeStore = useRealtimeStore()

const plants = computed(() => {
  const result: any[] = []
  result[0] = realtimeStore.plants[0] || null // A 厂在第一个位置
  return result
})
</script>

<style scoped>
.plant-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.grid-item {
  min-height: 180px;
}

@media (max-width: 1400px) {
  .plant-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 1000px) {
  .plant-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
```

- [ ] **Step 3: 创建监测大屏页面 views/Dashboard.vue**

```vue
<template>
  <div class="dashboard">
    <div class="dashboard-header">
      <h2>监测大屏</h2>
      <el-button @click="refresh" :loading="loading">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>
    <PlantGrid />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import PlantGrid from '@/components/dashboard/PlantGrid.vue'
import { useRealtimeStore } from '@/stores/realtime'

const realtimeStore = useRealtimeStore()
const loading = ref(false)

const refresh = async () => {
  loading.value = true
  await realtimeStore.initializePlants()
  loading.value = false
}

onMounted(() => {
  refresh()
})
</script>

<style scoped>
.dashboard {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.dashboard-header h2 {
  margin: 0;
  color: #303133;
}
</style>
```

- [ ] **Step 4: 提交**

```bash
git add frontend/src/components/dashboard frontend/src/views/Dashboard.vue
git commit -m "feat: add dashboard with plant grid and cards"
```

---

### Task 7: 创建 AI 助手组件

**Files:**
- Create: `frontend/src/components/aiops/ChatWidget.vue`
- Create: `frontend/src/components/aiops/ChatMessage.vue`
- Create: `frontend/src/components/aiops/EChartsChart.vue`
- Create: `frontend/src/views/AIOpsChat.vue`

- [ ] **Step 1: 创建消息组件 components/aiops/ChatMessage.vue**

```vue
<template>
  <div :class="['chat-message', `message-${message.role}`]">
    <div class="message-content">
      <div class="message-text">{{ message.content }}</div>
      <div v-if="message.evidence && message.evidence.length > 0" class="message-evidence">
        <el-divider content-position="left">
          <el-icon><Link /></el-icon>
          证据链
        </el-divider>
        <div v-for="(item, index) in message.evidence" :key="index" class="evidence-item">
          <el-tag size="small" type="info">{{ item.type }}</el-tag>
          <span>{{ item.content }}</span>
        </div>
      </div>
      <div v-if="message.chartData" class="message-chart">
        <EChartsChart :data="message.chartData" />
      </div>
    </div>
    <div class="message-time">{{ formatTime(message.timestamp) }}</div>
  </div>
</template>

<script setup lang="ts">
import { Link } from '@element-plus/icons-vue'
import EChartsChart from './EChartsChart.vue'
import type { ChatMessage } from '@/types'

const props = defineProps<{
  message: ChatMessage
}>()

const formatTime = (time: string) => {
  return new Date(time).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.chat-message {
  display: flex;
  flex-direction: column;
  margin-bottom: 16px;
  max-width: 80%;
}

.message-user {
  align-self: flex-end;
}

.message-assistant,
.message-system {
  align-self: flex-start;
}

.message-content {
  padding: 12px;
  border-radius: 8px;
  background: #f5f7fa;
}

.message-user .message-content {
  background: #409eff;
  color: white;
}

.message-text {
  line-height: 1.6;
  white-space: pre-wrap;
}

.message-evidence {
  margin-top: 12px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 4px;
}

.evidence-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 13px;
}

.evidence-item:last-child {
  margin-bottom: 0;
}

.message-chart {
  margin-top: 12px;
}

.message-time {
  font-size: 11px;
  color: #909399;
  margin-top: 4px;
}

.message-user .message-time {
  text-align: right;
}
</style>
```

- [ ] **Step 2: 创建 ECharts 图表组件 components/aiops/EChartsChart.vue**

```vue
<template>
  <div ref="chartRef" class="echarts-chart"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{
  data: any
}>()

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

onMounted(() => {
  if (!chartRef.value) return

  chart = echarts.init(chartRef.value)

  const option: echarts.EChartsOption = {
    title: {
      text: 'COD 浓度趋势',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis'
    },
    xAxis: {
      type: 'category',
      data: props.data?.times || []
    },
    yAxis: {
      type: 'value',
      name: 'COD (mg/L)'
    },
    series: [
      {
        name: 'COD',
        type: 'line',
        data: props.data?.values || [],
        smooth: true,
        markArea: {
          data: props.data?.anomalies || []
        }
      }
    ]
  }

  chart.setOption(option)
})

onUnmounted(() => {
  chart?.dispose()
})
</script>

<style scoped>
.echarts-chart {
  width: 100%;
  height: 300px;
}
</style>
```

- [ ] **Step 3: 创建浮窗组件 components/aiops/ChatWidget.vue**

```vue
<template>
  <div v-if="isOpen" class="chat-widget">
    <div class="chat-header" @mousedown="startDrag">
      <span>🤖 废水监测助手</span>
      <div class="header-actions">
        <el-button text @click.stop="minimize">
          <el-icon><Minus /></el-icon>
        </el-button>
        <el-button text @click.stop="close">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
    </div>
    <div v-if="!isMinimized" class="chat-body">
      <div ref="messagesRef" class="chat-messages">
        <ChatMessage
          v-for="message in chatStore.messages"
          :key="message.id"
          :message="message"
        />
        <div v-if="chatStore.loading" class="loading-indicator">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>思考中...</span>
        </div>
      </div>
      <div class="chat-input">
        <el-input
          v-model="inputText"
          type="textarea"
          :rows="2"
          placeholder="输入问题..."
          @keydown.ctrl.enter="sendMessage"
        />
        <el-button
          type="primary"
          :loading="chatStore.loading"
          @click="sendMessage"
        >
          发送 (Ctrl+Enter)
        </el-button>
      </div>
    </div>
  </div>
  <div v-else class="chat-widget-mini" @click="isMinimized = false">
    <el-icon :size="24"><ChatDotRound /></el-icon>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from 'vue'
import { Minus, Close, ChatDotRound, Loading } from '@element-plus/icons-vue'
import ChatMessage from './ChatMessage.vue'
import { useChatStore } from '@/stores/chat'

const chatStore = useChatStore()
const inputText = ref('')
const isOpen = ref(false)
const isMinimized = ref(false)
const messagesRef = ref<HTMLDivElement>()

// 初始化时从页面上下文设置建议问题
onMounted(() => {
  const context = chatStore.pageContext
  if (context?.suggestedQuestions) {
    isOpen.value = true
  }
})

const sendMessage = () => {
  if (!inputText.value.trim()) return
  chatStore.sendMessage(inputText.value)
  inputText.value = ''
  nextTick(() => {
    messagesRef.value?.scrollTo({ top: messagesRef.value.scrollHeight, behavior: 'smooth' })
  })
}

const minimize = () => {
  isMinimized.value = true
}

const close = () => {
  isOpen.value = false
}

const startDrag = (e: MouseEvent) => {
  // 简化版拖拽，可以后续完善
}
</script>

<style scoped>
.chat-widget {
  position: fixed;
  right: 20px;
  bottom: 20px;
  width: 400px;
  height: 500px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  z-index: 1000;
}

.chat-widget-mini {
  position: fixed;
  right: 20px;
  bottom: 20px;
  width: 50px;
  height: 50px;
  background: #409eff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4);
  z-index: 1000;
  transition: transform 0.2s;
}

.chat-widget-mini:hover {
  transform: scale(1.1);
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #409eff;
  color: white;
  border-radius: 8px 8px 0 0;
  cursor: move;
  user-select: none;
}

.header-actions {
  display: flex;
  gap: 4px;
}

.chat-header .el-button {
  color: white;
}

.chat-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-messages {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
}

.loading-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #909399;
  padding: 8px 0;
}

.chat-input {
  padding: 12px 16px;
  border-top: 1px solid #e4e7ed;
  display: flex;
  gap: 8px;
}

.chat-input .el-textarea {
  flex: 1;
}
</style>
```

- [ ] **Step 4: 创建 AI 助手页面 views/AIOpsChat.vue**

```vue
<template>
  <div class="aiops-chat">
    <div class="chat-header-full">
      <h2>🤖 废水监测智能助手</h2>
      <div class="header-actions">
        <el-button @click="chatStore.clearMessages()">
          <el-icon><Plus /></el-icon>
          新对话
        </el-button>
      </div>
    </div>
    <div class="chat-container">
      <div ref="messagesRef" class="chat-messages-full">
        <ChatMessage
          v-for="message in chatStore.messages"
          :key="message.id"
          :message="message"
        />
        <div v-if="chatStore.loading" class="loading-indicator">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>思考中...</span>
        </div>
      </div>
      <div class="chat-input-full">
        <el-input
          v-model="inputText"
          type="textarea"
          :rows="3"
          placeholder="输入问题... (Ctrl+Enter 发送)"
          @keydown.ctrl.enter="sendMessage"
        />
        <el-button
          type="primary"
          size="large"
          :loading="chatStore.loading"
          @click="sendMessage"
        >
          <el-icon><Promotion /></el-icon>
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { Plus, Promotion, Loading } from '@element-plus/icons-vue'
import ChatMessage from '@/components/aiops/ChatMessage.vue'
import { useChatStore } from '@/stores/chat'

const chatStore = useChatStore()
const inputText = ref('')
const messagesRef = ref<HTMLDivElement>()

const sendMessage = () => {
  if (!inputText.value.trim()) return
  chatStore.sendMessage(inputText.value)
  inputText.value = ''
  nextTick(() => {
    messagesRef.value?.scrollTo({ top: messagesRef.value.scrollHeight, behavior: 'smooth' })
  })
}

onMounted(() => {
  // 可以在这里添加欢迎消息
})
</script>

<style scoped>
.aiops-chat {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.chat-header-full {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid #e4e7ed;
}

.chat-header-full h2 {
  margin: 0;
  color: #303133;
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-messages-full {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

.chat-input-full {
  padding: 16px 24px;
  border-top: 1px solid #e4e7ed;
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.chat-input-full .el-textarea {
  flex: 1;
}
</style>
```

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/aiops frontend/src/views/AIOpsChat.vue
git commit -m "feat: add AI chat components and page"
```

---

### Task 8: 创建事件中心组件

**Files:**
- Create: `frontend/src/views/EventCenter.vue`
- Create: `frontend/src/components/events/EventList.vue`
- Create: `frontend/src/components/events/EventDetail.vue`

- [ ] **Step 1: 创建事件列表组件 components/events/EventList.vue**

```vue
<template>
  <div class="event-list">
    <div class="list-header">
      <el-form :inline="true" :model="filterForm">
        <el-form-item label="时间范围">
          <el-select v-model="filterForm.timeRange" @change="handleSearch">
            <el-option label="最近1小时" value="1h" />
            <el-option label="今天" value="today" />
            <el-option label="最近7天" value="7d" />
          </el-select>
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="filterForm.type" @change="handleSearch">
            <el-option label="全部" value="" />
            <el-option label="COD超标" value="cod_high" />
            <el-option label="pH异常" value="ph_abnormal" />
            <el-option label="氨氮异常" value="ammonia_high" />
            <el-option label="流量异常" value="flow_abnormal" />
          </el-select>
        </el-form-item>
        <el-form-item label="严重程度">
          <el-select v-model="filterForm.severity" @change="handleSearch">
            <el-option label="全部" value="" />
            <el-option label="高" value="high" />
            <el-option label="中" value="medium" />
            <el-option label="低" value="low" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filterForm.status" @change="handleSearch">
            <el-option label="全部" value="" />
            <el-option label="待处理" value="pending" />
            <el-option label="处理中" value="processing" />
            <el-option label="已解决" value="resolved" />
            <el-option label="已忽略" value="ignored" />
          </el-select>
        </el-form-item>
      </el-form>
      <div class="header-actions">
        <el-button @click="exportEvents" :loading="exporting">
          <el-icon><Download /></el-icon>
          导出报告
        </el-button>
        <el-button @click="handleSearch">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <el-table :data="eventsStore.events" v-loading="eventsStore.loading" stripe>
      <el-table-column prop="timestamp" label="时间" width="180">
        <template #default="{ row }">
          {{ formatTime(row.timestamp) }}
        </template>
      </el-table-column>
      <el-table-column prop="type" label="类型" width="120">
        <template #default="{ row }">
          {{ getTypeLabel(row.type) }}
        </template>
      </el-table-column>
      <el-table-column prop="plantId" label="厂区" width="100" />
      <el-table-column prop="severity" label="严重程度" width="100">
        <template #default="{ row }">
          <el-tag :type="getSeverityType(row.severity)">
            {{ getSeverityLabel(row.severity) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)">
            {{ getStatusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" @click="viewDetail(row)">
            详情
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total="eventsStore.total"
      :page-sizes="[10, 20, 50, 100]"
      layout="total, sizes, prev, pager, next, jumper"
      @size-change="handleSearch"
      @current-change="handleSearch"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Download, Refresh } from '@element-plus/icons-vue'
import { useEventsStore } from '@/stores/events'
import type { AlertEvent } from '@/types'

const emit = defineEmits<{
  viewDetail: [event: AlertEvent]
}>()

const eventsStore = useEventsStore()

const filterForm = reactive({
  timeRange: 'today',
  type: '',
  severity: '',
  status: ''
})

const currentPage = ref(1)
const pageSize = ref(20)
const exporting = ref(false)

const getTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    cod_high: 'COD超标',
    ph_abnormal: 'pH异常',
    ammonia_high: '氨氮异常',
    flow_abnormal: '流量异常'
  }
  return labels[type] || type
}

const getSeverityLabel = (severity: string) => {
  const labels: Record<string, string> = { high: '高', medium: '中', low: '低' }
  return labels[severity] || severity
}

const getSeverityType = (severity: string) => {
  const types: Record<string, any> = { high: 'danger', medium: 'warning', low: 'info' }
  return types[severity] || ''
}

const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    pending: '待处理',
    processing: '处理中',
    resolved: '已解决',
    ignored: '已忽略'
  }
  return labels[status] || status
}

const getStatusType = (status: string) => {
  const types: Record<string, any> = {
    pending: 'warning',
    processing: 'primary',
    resolved: 'success',
    ignored: 'info'
  }
  return types[status] || ''
}

const formatTime = (time: string) => {
  return new Date(time).toLocaleString('zh-CN')
}

const handleSearch = () => {
  eventsStore.fetchEvents({
    ...filterForm,
    page: currentPage.value,
    pageSize: pageSize.value
  })
}

const viewDetail = (event: AlertEvent) => {
  emit('viewDetail', event)
}

const exportEvents = async () => {
  exporting.value = true
  try {
    // TODO: 调用导出 API
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  handleSearch()
})
</script>

<style scoped>
.event-list {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.el-pagination {
  margin-top: 16px;
  justify-content: center;
}
</style>
```

- [ ] **Step 2: 创建事件详情弹窗组件 components/events/EventDetail.vue**

```vue
<template>
  <el-dialog
    v-model="visible"
    title="告警详情"
    width="600px"
    @close="handleClose"
  >
    <div v-if="event" class="event-detail">
      <div class="detail-section">
        <h3>基本信息</h3>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="时间">
            {{ formatTime(event.timestamp) }}
          </el-descriptions-item>
          <el-descriptions-item label="类型">
            {{ getTypeLabel(event.type) }}
          </el-descriptions-item>
          <el-descriptions-item label="厂区">
            {{ event.plantId }}
          </el-descriptions-item>
          <el-descriptions-item label="严重程度">
            <el-tag :type="getSeverityType(event.severity)">
              {{ getSeverityLabel(event.severity) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="当前状态" :span="2">
            <el-tag :type="getStatusType(event.status)">
              {{ getStatusLabel(event.status) }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <div class="detail-section">
        <h3>证据链</h3>
        <el-collapse>
          <el-collapse-item title="📊 数据快照" name="data">
            <div class="evidence-content">
              <div v-for="(value, key) in event.evidence.dataSnapshot" :key="key" class="data-item">
                <span class="data-label">{{ getMetricLabel(key) }}:</span>
                <span class="data-value">{{ value }}</span>
              </div>
            </div>
          </el-collapse-item>

          <el-collapse-item title="🔧 算子调用" name="operators">
            <div class="evidence-content">
              <div v-for="(op, index) in event.evidence.operators" :key="index" class="operator-item">
                <el-tag size="small" type="info">{{ op.name }}</el-tag>
                <span>{{ op.result }}</span>
              </div>
            </div>
          </el-collapse-item>

          <el-collapse-item title="⚖️ 规则匹配" name="rules">
            <div class="evidence-content">
              <div v-for="(rule, index) in event.evidence.rules" :key="index" class="rule-item">
                <el-tag :type="rule.matched ? 'success' : 'danger'" size="small">
                  {{ rule.matched ? '✓' : '✗' }}
                </el-tag>
                <span>{{ rule.name }}</span>
              </div>
            </div>
          </el-collapse-item>

          <el-collapse-item title="🤖 LLM 推理过程" name="llm">
            <div class="evidence-content">
              {{ event.evidence.llmReasoning }}
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>

      <div class="detail-section actions">
        <el-button @click="updateStatus('resolved')" type="success">
          标记已解决
        </el-button>
        <el-button @click="exportEvidence">
          导出证据
        </el-button>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useEventsStore } from '@/stores/events'
import type { AlertEvent } from '@/types'

const eventsStore = useEventsStore()

const visible = ref(false)
const event = ref<AlertEvent | null>(null)

const getTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    cod_high: 'COD超标',
    ph_abnormal: 'pH异常',
    ammonia_high: '氨氮异常',
    flow_abnormal: '流量异常'
  }
  return labels[type] || type
}

const getSeverityLabel = (severity: string) => {
  const labels: Record<string, string> = { high: '高', medium: '中', low: '低' }
  return labels[severity] || severity
}

const getSeverityType = (severity: string) => {
  const types: Record<string, any> = { high: 'danger', medium: 'warning', low: 'info' }
  return types[severity] || ''
}

const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    pending: '待处理',
    processing: '处理中',
    resolved: '已解决',
    ignored: '已忽略'
  }
  return labels[status] || status
}

const getStatusType = (status: string) => {
  const types: Record<string, any> = {
    pending: 'warning',
    processing: 'primary',
    resolved: 'success',
    ignored: 'info'
  }
  return types[status] || ''
}

const getMetricLabel = (key: string) => {
  const labels: Record<string, string> = {
    pH: 'pH',
    cod: 'COD',
    ammoniaNitrogen: '氨氮',
    totalNitrogen: '总氮',
    totalPhosphorus: '总磷',
    flow: '流量'
  }
  return labels[key] || key
}

const formatTime = (time: string) => {
  return new Date(time).toLocaleString('zh-CN')
}

const open = (evt: AlertEvent) => {
  event.value = evt
  visible.value = true
}

const updateStatus = async (status: string) => {
  if (!event.value) return
  await eventsStore.updateStatus(event.value.id, status)
  visible.value = false
}

const exportEvidence = () => {
  // TODO: 导出证据
}

const handleClose = () => {
  visible.value = false
}

defineExpose({ open })
</script>

<style scoped>
.event-detail {
  max-height: 600px;
  overflow-y: auto;
}

.detail-section {
  margin-bottom: 24px;
}

.detail-section h3 {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: #303133;
}

.evidence-content {
  padding: 8px 0;
}

.data-item,
.operator-item,
.rule-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}

.data-label {
  font-weight: 500;
  color: #606266;
}

.data-value {
  color: #303133;
}

.actions {
  display: flex;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid #e4e7ed;
}
</style>
```

- [ ] **Step 3: 创建事件中心页面 views/EventCenter.vue**

```vue
<template>
  <div class="event-center">
    <div class="page-header">
      <h2>📋 事件中心</h2>
    </div>
    <EventList @view-detail="handleViewDetail" />
    <EventDetail ref="detailDialogRef" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import EventList from '@/components/events/EventList.vue'
import EventDetail from '@/components/events/EventDetail.vue'
import type { AlertEvent } from '@/types'

const detailDialogRef = ref<InstanceType<typeof EventDetail>>()

const handleViewDetail = (event: AlertEvent) => {
  detailDialogRef.value?.open(event)
}
</script>

<style scoped>
.event-center {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  color: #303133;
}
</style>
```

- [ ] **Step 4: 提交**

```bash
git add frontend/src/components/events frontend/src/views/EventCenter.vue
git commit -m "feat: add event center components and page"
```

---

### Task 9: 更新 App.vue 使用布局组件

**Files:**
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: 更新 App.vue**

```vue
<template>
  <AppLayout />
</template>

<script setup lang="ts">
import AppLayout from '@/components/layout/AppLayout.vue'
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  height: 100vh;
  overflow: hidden;
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/App.vue
git commit -m "feat: wrap app with layout component"
```

---

### Phase 2: 后端 API 实现

### Task 10: 添加实时数据后端接口

**Files:**
- Create: `backend/api/routes/realtime.py`
- Modify: `backend/main.py`
- Create: `backend/models/realtime.py`

- [ ] **Step 1: 创建实时数据模型 backend/models/realtime.py**

```python
from pydantic import BaseModel
from typing import Optional, Dict


class WaterMetrics(BaseModel):
    pH: float
    cod: float
    ammoniaNitrogen: float
    totalNitrogen: float
    totalPhosphorus: float
    flow: float


class MetricStatus(BaseModel):
    status: str  # normal, abnormal, offline


class PlantData(BaseModel):
    id: str
    name: str
    status: str  # online, offline
    metrics: Optional[WaterMetrics] = None
    metricStatus: Optional[Dict[str, str]] = None
    lastUpdate: str
```

- [ ] **Step 2: 创建实时数据接口 backend/api/routes/realtime.py**

```python
from fastapi import APIRouter
from backend.models.realtime import PlantData, WaterMetrics
from datetime import datetime

router = APIRouter()

# 模拟数据：4×4 框架，目前只有 A 厂有数据
_mock_plants = {
    "plant_a": PlantData(
        id="plant_a",
        name="废水处理厂 A区",
        status="online",
        metrics=WaterMetrics(
            pH=7.2,
            cod=45.0,
            ammoniaNitrogen=8.5,
            totalNitrogen=15.0,
            totalPhosphorus=0.8,
            flow=120.0
        ),
        metricStatus={
            "pH": "normal",
            "cod": "normal",
            "ammoniaNitrogen": "normal",
            "totalNitrogen": "normal",
            "totalPhosphorus": "normal",
            "flow": "normal"
        },
        lastUpdate=datetime.now().isoformat()
    )
}

@router.get("/realtime/plants")
async def get_all_plants() -> list[PlantData]:
    """获取所有厂区数据（4×4 框架）"""
    # 返回 16 个位置，只有第一个有数据
    plants = []
    for i in range(1, 17):
        if i == 1:
            plants.append(_mock_plants["plant_a"])
        else:
            plants.append(PlantData(
                id=f"plant_{i}",
                name=f"厂区 {i}",
                status="offline",
                metrics=None,
                metricStatus=None,
                lastUpdate=datetime.now().isoformat()
            ))
    return plants

@router.get("/realtime/plants/{plant_id}")
async def get_plant(plant_id: str) -> PlantData:
    """获取单个厂区数据"""
    if plant_id in _mock_plants:
        return _mock_plants[plant_id]
    return PlantData(
        id=plant_id,
        name=f"厂区 {plant_id}",
        status="offline",
        metrics=None,
        metricStatus=None,
        lastUpdate=datetime.now().isoformat()
    )
```

- [ ] **Step 3: 注册路由 backend/main.py**

```python
"""
废水监测系统后端 - Hermes API Server 集成

为已完成的 Hermes 智能体系统提供 HTTP 接口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from backend.api.routes import health, hermes, query, realtime  # 新增 realtime
from backend.core.config import settings
from backend.metrics.definitions import (
    api_requests_total,
    api_request_duration_seconds
)

app = FastAPI(
    title="废水监测系统 API",
    version="2.0.0",
    description="""
## Hermes 智能体 HTTP 接口层

本系统为已完成的 **Hermes 智能体系统** 提供 HTTP 接口，
通过 Hermes API Server 调用主智能体，展示其完整的决策过程。

### 核心接口

- `/api/query` - 查询接口（展示决策树和调用链）
- `/api/hermes/system` - Hermes 系统完整信息
- `/api/hermes/skills` - 加载的技能列表
- `/api/health` - 健康检查
- `/api/realtime/plants` - 实时厂区数据（新增）

### 架构

```
前端 → FastAPI → Hermes API Server → 主智能体（决策树）→ 4 个子智能体
```

详细架构见：`docs/architecture/technical-design.md`
    """,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus 监控 - 自定义指标端点（兼容 Python 3.8）
from prometheus_client import generate_latest

@app.get("/metrics")
async def metrics():
    """Prometheus 指标端点"""
    from prometheus_client import CONTENT_TYPE_LATEST
    from fastapi.responses import Response
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

# 路由注册
app.include_router(health.router, prefix="/api")
app.include_router(hermes.router, prefix="/api")
app.include_router(query.router, prefix="/api")
app.include_router(realtime.router, prefix="/api")  # 新增


@app.get("/", tags=["根路径"])
async def root():
    """根路径 - 重定向到 API 文档"""
    return RedirectResponse(url="/docs")


@app.on_event("startup")
async def startup():
    """启动时初始化"""
    from backend.api.client import get_hermes_client
    # 验证 Hermes API Server 连接
    try:
        client = get_hermes_client()
        await client.health_check()
        print("[OK] Hermes API Server connected")
    except Exception as e:
        print(f"[ERROR] Hermes API Server connection failed: {e}")


@app.on_event("shutdown")
async def shutdown():
    """关闭时清理"""
    pass
```

- [ ] **Step 4: 测试接口**

```bash
curl http://localhost:8001/api/realtime/plants
```

预期返回：包含 16 个厂区的列表，第一个有数据

- [ ] **Step 5: 提交**

```bash
git add backend/api/routes/realtime.py backend/models/realtime.py backend/main.py
git commit -m "feat: add realtime data API endpoints"
```

---

### Task 11: 添加事件中心后端接口

**Files:**
- Create: `backend/api/routes/events.py`
- Create: `backend/models/event.py`
- Modify: `backend/main.py`

- [ ] **Step 1: 创建事件模型 backend/models/event.py**

```python
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class EvidenceSnapshot(BaseModel):
    pH: Optional[float] = None
    cod: Optional[float] = None
    ammoniaNitrogen: Optional[float] = None
    totalNitrogen: Optional[float] = None
    totalPhosphorus: Optional[float] = None
    flow: Optional[float] = None


class OperatorCall(BaseModel):
    name: str
    result: Any


class RuleMatch(BaseModel):
    name: str
    matched: bool


class EventEvidence(BaseModel):
    dataSnapshot: EvidenceSnapshot
    operators: List[OperatorCall]
    rules: List[RuleMatch]
    llmReasoning: str


class AlertEvent(BaseModel):
    id: str
    timestamp: str
    type: str
    plantId: str
    severity: str  # low, medium, high
    status: str  # pending, processing, resolved, ignored
    evidence: EventEvidence


class EventListResponse(BaseModel):
    data: List[AlertEvent]
    total: int


class EventStatusUpdate(BaseModel):
    status: str
```

- [ ] **Step 2: 创建事件接口 backend/api/routes/events.py**

```python
from fastapi import APIRouter, Query
from typing import Optional
from backend.models.event import AlertEvent, EventListResponse, EventEvidence, EventStatusUpdate
from datetime import datetime, timedelta

router = APIRouter()

# 模拟事件数据
_mock_events: list[AlertEvent] = [
    AlertEvent(
        id="evt_001",
        timestamp=(datetime.now() - timedelta(minutes=30)).isoformat(),
        type="cod_high",
        plantId="plant_a",
        severity="high",
        status="pending",
        evidence=EventEvidence(
            dataSnapshot={"cod": 125.0, "pH": 7.2, "ammoniaNitrogen": 8.5},
            operators=[
                {"name": "statistical.trend_detector", "result": "检测到上升趋势"},
                {"name": "ml.isolation_forest", "result": {"confidence": 0.92}}
            ],
            rules=[
                {"name": "pH-COD协同规则", "matched": False},
                {"name": "违规模式", "matched": True}
            ],
            llmReasoning="主智能体决策: 多维数据感知 → 异常检测 → 规则推理\n结论: 数据支持COD超标违规判定"
        )
    ),
    AlertEvent(
        id="evt_002",
        timestamp=(datetime.now() - timedelta(hours=2)).isoformat(),
        type="ph_abnormal",
        plantId="plant_a",
        severity="medium",
        status="processing",
        evidence=EventEvidence(
            dataSnapshot={"pH": 5.5, "cod": 42.0},
            operators=[{"name": "statistical.threshold_check", "result": "pH 低于下限"}],
            rules=[{"name": "pH阈值规则", "matched": True}],
            llmReasoning="pH值低于正常范围，需要关注"
        )
    ),
    AlertEvent(
        id="evt_003",
        timestamp=(datetime.now() - timedelta(days=1)).isoformat(),
        type="flow_abnormal",
        plantId="plant_a",
        severity="low",
        status="resolved",
        evidence=EventEvidence(
            dataSnapshot={"flow": 0.0},
            operators=[{"name": "connectivity_check", "result": "传感器离线"}],
            rules=[{"name": "连通性规则", "matched": True}],
            llmReasoning="流量传感器异常，已安排维护"
        )
    )
]

@router.get("/events", response_model=EventListResponse)
async def get_events(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    type: Optional[str] = None,
    plantId: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100)
):
    """获取事件列表"""
    filtered = _mock_events.copy()

    # 应用过滤
    if type:
        filtered = [e for e in filtered if e.type == type]
    if plantId:
        filtered = [e for e in filtered if e.plantId == plantId]
    if severity:
        filtered = [e for e in filtered if e.severity == severity]
    if status:
        filtered = [e for e in filtered if e.status == status]

    total = len(filtered)
    start = (page - 1) * pageSize
    end = start + pageSize
    paged = filtered[start:end]

    return EventListResponse(data=paged, total=total)


@router.get("/events/{event_id}", response_model=AlertEvent)
async def get_event_detail(event_id: str):
    """获取事件详情"""
    for event in _mock_events:
        if event.id == event_id:
            return event
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="事件不存在")


@router.put("/events/{event_id}/status", response_model=AlertEvent)
async def update_event_status(event_id: str, update: EventStatusUpdate):
    """更新事件状态"""
    for event in _mock_events:
        if event.id == event_id:
            event.status = update.status
            return event
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="事件不存在")


@router.get("/events/export")
async def export_events(
    format: str = Query("xlsx", regex="^(xlsx|pdf|json)$"),
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    type: Optional[str] = None
):
    """导出事件报告"""
    # TODO: 实现实际的导出功能
    from fastapi.responses import Response
    if format == "json":
        import json
        content = json.dumps([e.dict() for e in _mock_events], ensure_ascii=False, indent=2)
        return Response(content=content, media_type="application/json")
    else:
        # xlsx/pdf 暂未实现
        return Response(content="导出功能开发中", media_type="text/plain")
```

- [ ] **Step 3: 注册路由 backend/main.py**

在 backend/main.py 中添加：

```python
from backend.api.routes import health, hermes, query, realtime, events  # 新增 events

app.include_router(events.router, prefix="/api")  # 新增
```

完整修改后的 main.py 路由注册部分：

```python
# 路由注册
app.include_router(health.router, prefix="/api")
app.include_router(hermes.router, prefix="/api")
app.include_router(query.router, prefix="/api")
app.include_router(realtime.router, prefix="/api")
app.include_router(events.router, prefix="/api")
```

- [ ] **Step 4: 测试接口**

```bash
curl http://localhost:8001/api/events
curl http://localhost:8001/api/events/evt_001
```

- [ ] **Step 5: 提交**

```bash
git add backend/api/routes/events.py backend/models/event.py backend/main.py
git commit -m "feat: add events API endpoints"
```

---

### Phase 3: 构建与测试

### Task 12: 前端构建测试

- [ ] **Step 1: 安装前端依赖**

```bash
cd frontend
npm install
```

- [ ] **Step 2: 启动开发服务器**

```bash
npm run dev
```

访问 http://localhost:3000 验证：
- 监测大屏显示 4×4 网格
- 第一个卡片显示 A 厂数据
- 其他卡片显示占位符

- [ ] **Step 3: 启动后端服务**

```bash
cd ..
ecological_env\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload
```

- [ ] **Step 4: 测试前后端联调**

在浏览器中测试：
1. 访问 http://localhost:3000/dashboard
2. 验证厂区数据正常显示
3. 点击 AI 助手，发送消息测试
4. 访问事件中心，验证事件列表显示

- [ ] **Step 5: 构建生产版本**

```bash
cd frontend
npm run build
```

- [ ] **Step 6: 提交**

```bash
git add frontend/dist
git commit -m "build: add production build"
```

---

### Task 13: 更新 README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 更新 README.md 添加前端启动说明**

在 README.md 的"快速开始"部分添加前端启动说明：

```markdown
### 启动服务

**方式 1: FastAPI Backend + 前端（推荐）**

后端：
```bash
# Windows
scripts\start_backend.bat

# Linux/Mac
bash scripts/start_backend.sh
```

前端：
```bash
cd frontend
npm install
npm run dev
```

访问：
- 后端 API 文档：`http://localhost:8001/docs`
- 前端界面：`http://localhost:3000`
```

- [ ] **Step 2: 提交**

```bash
git add README.md
git commit -m "docs: add frontend setup instructions"
```

---

## 完成检查清单

- [ ] 前端项目结构完整
- [ ] 监测大屏显示 4×4 厂区框架
- [ ] 厂区卡片正确显示水质指标
- [ ] AI 助手可以发送查询
- [ ] 事件中心显示告警列表
- [ ] 告警详情弹窗正常工作
- [ ] 后端实时数据 API 正常
- [ ] 后端事件 API 正常
- [ ] 前后端联调成功
- [ ] 文档已更新

---

## 注意事项

1. **数据对接**：当前使用模拟数据，后续需要对接真实的 InfluxDB 或 CSV 数据源
2. **WebSocket 实时推送**：Phase 2 需要实现 WebSocket 接口
3. **ECharts 图表**：Phase 2 需要完善异常点标注功能
4. **导出功能**：需要实现 Excel/PDF 导出库
5. **SxDevOps 借鉴**：布局和交互模式已借鉴，组件名称和业务逻辑已适配废水监测场景
