# 前端重构 · Phase 3 平台外壳 + 分组导航 + 浮动助手 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans.

**背景：** Phase 0-2 完成了地基 / 监测大屏 / AI 助手。用户提供了一张企业级 AIOps 参考图，要求前端从「5 个扁平页面」升级为「完整平台形态」：一套侧栏 + 4 大分组折叠菜单 + 右下角浮动 AI 助手。本计划是这次升级的 **Phase A（外壳与骨架）**，Phase B 为后续逐页补内容的路线图。

**已确认的 4 个方向决策（用户拍板）：**
1. **监控可视化**：原生 ECharts cockpit 为主（保留），Grafana 作为后续可选嵌入页（Phase B，需确认 Grafana 实例在跑且开 iframe）。
2. **导航外壳**：统一成**单壳 + 分组折叠菜单**（参考图形态）；大屏也从侧栏进入，保留「全屏切换」按钮。
3. **新页面数据**：智能体配置/审计接真实数据（capabilities + logs/trace）；事件源/设置等无后端页面先占位「建设中」。
4. **交付节奏**：分阶段。Phase A 搭骨架（最快见到参考图整体形态），Phase B 逐页补内容。

**Goal(Phase A):** 不新建业务页面内容，只搭**平台骨架**——统一单壳、4 大分组导航（含 Phase B 占位项）、/dashboard 并入侧栏且保留全屏沉浸、右下角全局浮动 AI 助手。完成后整体形态即接近参考图。

**Tech Stack:** Vue3+TS · Pinia · Element Plus · vue-router（已有，无新依赖）。
**分支:** `frontend-refactor`（继续）。
**环境:** Windows+Git Bash;`export PATH="/e/nodejs:$PATH"` 后用 npm。
**测试策略:** 本期多为布局/导航，无纯逻辑可 TDD;用 type-check(0 错)+ build(`✓ built`)+ 16 测仍 PASS + 视觉确认(分组菜单/全屏切换/浮动助手唤起)。

---

## 目标导航结构（Phase A 落地完整结构，Phase B 项指向占位页）

```
智能助手
  ├─ AI 助手              /chat              ✅ 真实(Phase 2)
  ├─ 智能体配置           /agents/config     🔲 占位(Phase B)
  └─ 智能体审计           /agents/audit      🔲 占位(Phase B)
监控大屏
  ├─ 监测大屏             /dashboard         ✅ 真实(Phase 1,新增全屏切换)
  ├─ 指标查询             /metrics           🔲 占位(Phase B)
  ├─ 日志中心             /logs              ✅ 真实(Phase 0/3)
  ├─ 链路追踪             /tracing           🔲 占位(Phase B,接 observability/tracing)
  ├─ 数据源               /datasources       🔲 占位(Phase B,接 tracing/datasources CRUD)
  ├─ 告警中心             /alerts            🔲 占位(Phase B,复用 events 数据)
  └─ Grafana 大屏         /grafana           🔲 占位(Phase B,iframe,待确认实例)
事件中心
  ├─ 事件中心             /events            ✅ 真实(Phase 0/3)
  └─ 事件源               /event-sources     🔲 占位(Phase B)
设置
  └─ 系统设置             /settings          🔲 占位(Phase B)
```

> Phase A 只需保证：真实页继续工作 + 占位页统一渲染「建设中」+ 浮动助手全站可用。Phase B 逐个把 🔲 换成真实 view。

---

## File Structure

**新建:**
- `frontend/src/views/PlaceholderView.vue`（通用「建设中」占位）
- `frontend/src/components/aiops/FloatingAssistant.vue`（右下角 FAB + 对话抽屉）

**修改:**
- `frontend/src/stores/app.ts`（加 `fullscreen` / `assistantOpen` + setters）
- `frontend/src/components/layout/AppSidebar.vue`（扁平 → 分组 `el-sub-menu`）
- `frontend/src/layout/AdminShell.vue`（全屏模式隐藏 chrome + 挂浮动助手）
- `frontend/src/layout/CockpitShell.vue`（退化为 dashboard 全屏皮肤;或合并,见 Task 5 说明）
- `frontend/src/views/DashboardView.vue`（加「全屏」按钮）
- `frontend/src/components/layout/AppHeader.vue`（标题映射补全新路由 + 全屏退出控件）
- `frontend/src/router/index.ts`（统一单壳 + 占位路由）

---

## Task 1: appStore 扩展(fullscreen / assistantOpen)

**Files:** Modify `frontend/src/stores/app.ts`

- [ ] **替换为(在现有基础上加 2 个状态):**

```ts
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const activePlant = ref<string>('第一污水处理厂')
  const dashboardFilters = ref({
    category: 'all' as 'all' | 'influent' | 'effluent',
    sort: 'anomaly' as 'anomaly' | 'value' | 'delta',
    timeWindow: '24h' as '1h' | '6h' | '24h',
  })
  // 大屏全屏沉浸模式(仅 /dashboard 有意义):隐藏侧栏+顶栏
  const fullscreen = ref(false)
  // 右下角浮动 AI 助手抽屉开关
  const assistantOpen = ref(false)

  function toggleSidebar() { sidebarCollapsed.value = !sidebarCollapsed.value }
  function setFullscreen(v: boolean) { fullscreen.value = v }
  function toggleAssistant() { assistantOpen.value = !assistantOpen.value }

  return { sidebarCollapsed, activePlant, dashboardFilters, fullscreen, assistantOpen,
           toggleSidebar, setFullscreen, toggleAssistant }
})
```

- [ ] **type-check** → 0 错。
- [ ] **Commit** — `git add frontend/src/stores/app.ts && git commit -m "feat(frontend): appStore fullscreen + assistantOpen flags"`

---

## Task 2: PlaceholderView.vue（通用占位页）

**Files:** Create `frontend/src/views/PlaceholderView.vue`

```vue
<template>
  <div class="ph">
    <div class="card">
      <div class="icon">🚧</div>
      <div class="t">{{ title }} · 建设中</div>
      <div class="d">{{ desc || '该模块规划中，将在后续阶段补全。' }}</div>
      <div class="hint" v-if="hint">{{ hint }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ title: string; desc?: string; hint?: string }>()
</script>

<style scoped>
.ph { display: grid; place-items: center; min-height: 60vh }
.card { text-align: center; background: #fff; border: 1px solid var(--brd); border-radius: 14px;
  padding: 44px 56px; box-shadow: 0 1px 3px rgba(0,0,0,.04); max-width: 480px }
.icon { font-size: 40px; margin-bottom: 12px }
.t { font-size: 17px; font-weight: 700; color: var(--text-primary) }
.d { font-size: 13px; color: var(--text-muted); margin-top: 8px; line-height: 1.6 }
.hint { margin-top: 14px; font-size: 12px; color: var(--primary); background: var(--primary-light, #eef2ff);
  border-radius: 8px; padding: 8px 12px }
</style>
```

- [ ] build → `✓ built`;Commit `feat(frontend): PlaceholderView (建设中 stub for Phase B pages)`。

---

## Task 3: 路由重构（统一单壳 + 占位路由）

**Files:** Modify `frontend/src/router/index.ts`

- [ ] **替换为（所有路由统一挂 AdminShell;/dashboard 并入;CockpitShell 不再作为独立路由,全屏由 appStore.fullscreen 控制）:**

```ts
import { createRouter, createWebHistory } from 'vue-router'
import AdminShell from '@/layout/AdminShell.vue'

// 占位路由统一工厂
const ph = (title: string, desc?: string, hint?: string) => () =>
  import('@/views/PlaceholderView.vue').then((m) => ({ default: { ...m, __ph: { title, desc, hint } } }))

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/chat' },
    {
      path: '/',
      component: AdminShell,
      children: [
        // 智能助手
        { path: 'chat', component: () => import('@/views/AIOpsChatView.vue'), meta: { title: 'AI 助手', group: '智能助手' } },
        { path: 'agents/config', component: ph('智能体配置', '主智能体/4 个子智能体的身份与能力配置展示', 'Phase B 接 /api/query/capabilities'), meta: { title: '智能体配置', group: '智能助手' } },
        { path: 'agents/audit', component: ph('智能体审计', '主智能体决策与会话追溯审计', 'Phase B 接 /api/logs + /api/logs/trace'), meta: { title: '智能体审计', group: '智能助手' } },
        // 监控大屏
        { path: 'dashboard', component: () => import('@/views/DashboardView.vue'), meta: { title: '监测大屏', group: '监控大屏' } },
        { path: 'metrics', component: ph('指标查询', '按指标/时间窗口查询历史监测数据', 'Phase B 接 /api/v1/data/history'), meta: { title: '指标查询', group: '监控大屏' } },
        { path: 'logs', component: () => import('@/views/LogsView.vue'), meta: { title: '日志中心', group: '监控大屏' } },
        { path: 'logs/trace/:id', component: () => import('@/views/TraceView.vue'), meta: { title: '会话追溯', group: '监控大屏' } },
        { path: 'tracing', component: ph('链路追踪', '可观测性链路追踪', 'Phase B 接 /api/observability/tracing/*'), meta: { title: '链路追踪', group: '监控大屏' } },
        { path: 'datasources', component: ph('数据源', '追踪数据源管理(增删改查/测试连接)', 'Phase B 接 /api/observability/tracing/datasources'), meta: { title: '数据源', group: '监控大屏' } },
        { path: 'alerts', component: ph('告警中心', '告警事件汇总与处置', 'Phase B 复用 /api/events'), meta: { title: '告警中心', group: '监控大屏' } },
        { path: 'grafana', component: ph('Grafana 大屏', '嵌入 Grafana 双数据流监控面板', 'Phase B:需确认 Grafana 实例在跑且开启 iframe 嵌入'), meta: { title: 'Grafana 大屏', group: '监控大屏' } },
        // 事件中心
        { path: 'events', component: () => import('@/views/EventCenterView.vue'), meta: { title: '事件中心', group: '事件中心' } },
        { path: 'event-sources', component: ph('事件源', '事件来源(双数据流等)配置', 'Phase B'), meta: { title: '事件源', group: '事件中心' } },
        // 设置
        { path: 'settings', component: ph('系统设置', '系统与 LLM 配置', 'Phase B'), meta: { title: '系统设置', group: '设置' } },
      ],
    },
  ],
})

router.afterEach((to) => {
  const t = typeof to.meta?.title === 'string' && to.meta.title.trim()
    ? `${to.meta.title} - 废水监测系统` : '废水监测智能体系统'
  document.title = t
})

export default router
```

> 注:`ph()` 工厂用动态 import 拿到模块后注入 props——但 PlaceholderView 的 props 需从 route.meta 传更稳妥。**改用更简洁可靠方案:** 占位路由统一指向 PlaceholderView,props 从 `route.meta` 取。最终落地代码用:

```ts
// 占位路由(meta 带 phTitle/phDesc/phHint,PlaceholderView 读 route.meta)
{ path: 'agents/config', component: () => import('@/views/PlaceholderView.vue'),
  meta: { title: '智能体配置', group: '智能助手', phTitle: '智能体配置', phDesc: '主智能体/4 个子智能体的身份与能力配置展示', phHint: 'Phase B 接 /api/query/capabilities' } },
```

PlaceholderView 改为读 `useRoute().meta`:`const r = useRoute(); const title = (r.meta.phTitle as string) || '页面'`。其余占位路由同构(每个带 phTitle/phDesc/phHint)。**执行时以此方案为准(Task 2 的 PlaceholderView 同步改成读 meta)。**

- [ ] type-check → 0 错。
- [ ] **Commit** — `feat(frontend): unified single-shell router + Phase B placeholder routes`

---

## Task 4: AppSidebar 重写（分组 el-sub-menu）

**Files:** Modify `frontend/src/components/layout/AppSidebar.vue`

- [ ] **替换为（按 group 渲染 4 个折叠分组;default-open 全展开;每项 icon+title）:**

```vue
<template>
  <aside class="sidebar" :class="{ collapsed: app.sidebarCollapsed }">
    <div class="logo">
      <span class="dot"></span>
      <div v-if="!app.sidebarCollapsed" class="logo-copy">
        <span class="t">废水监测</span>
        <span class="s">智能体平台</span>
      </div>
    </div>
    <el-scrollbar class="nav-scroll">
      <el-menu :default-active="route.path" :default-openeds="openGroups" :collapse="app.sidebarCollapsed" router class="nav">
        <el-sub-menu v-for="g in GROUPS" :key="g.title" :index="g.title">
          <template #title>
            <el-icon><component :is="g.icon"/></el-icon>
            <span>{{ g.title }}</span>
          </template>
          <el-menu-item v-for="item in g.items" :key="item.path" :index="item.path">
            <el-icon><component :is="item.icon"/></el-icon>
            <template #title>{{ item.title }}</template>
          </el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-scrollbar>
  </aside>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import {
  ChatDotRound, Setting, Document, Monitor, DataAnalysis, Notebook,
  Connection, Coin, Bell, DataLine, Tickets, Tools,
} from '@element-plus/icons-vue'
import type { Component } from 'vue'

interface NavItem { path: string; title: string; icon: Component }
interface NavGroup { title: string; icon: Component; items: NavItem[] }

const GROUPS: NavGroup[] = [
  { title: '智能助手', icon: ChatDotRound, items: [
    { path: '/chat', title: 'AI 助手', icon: ChatDotRound },
    { path: '/agents/config', title: '智能体配置', icon: Setting },
    { path: '/agents/audit', title: '智能体审计', icon: Document },
  ]},
  { title: '监控大屏', icon: Monitor, items: [
    { path: '/dashboard', title: '监测大屏', icon: Monitor },
    { path: '/metrics', title: '指标查询', icon: DataAnalysis },
    { path: '/logs', title: '日志中心', icon: Notebook },
    { path: '/tracing', title: '链路追踪', icon: Connection },
    { path: '/datasources', title: '数据源', icon: Coin },
    { path: '/alerts', title: '告警中心', icon: Bell },
    { path: '/grafana', title: 'Grafana 大屏', icon: DataLine },
  ]},
  { title: '事件中心', icon: Tickets, items: [
    { path: '/events', title: '事件中心', icon: Tickets },
    { path: '/event-sources', title: '事件源', icon: Connection },
  ]},
  { title: '设置', icon: Tools, items: [
    { path: '/settings', title: '系统设置', icon: Tools },
  ]},
]

const app = useAppStore()
const route = useRoute()
const openGroups = GROUPS.map((g) => g.title)
</script>

<style scoped>
.sidebar { width: var(--sidebar-width); background: #fff; border-right: 1px solid var(--brd);
  transition: width var(--transition); overflow: hidden; display: flex; flex-direction: column }
.sidebar.collapsed { width: var(--sidebar-collapsed-width) }
.logo { display: flex; align-items: center; gap: 10px; padding: 14px; flex-shrink: 0 }
.dot { width: 24px; height: 24px; border-radius: 7px; background: var(--brand-gradient) }
.logo-copy { display: flex; flex-direction: column }
.logo-copy .t { font-size: 14px; font-weight: 700 }
.logo-copy .s { font-size: 11px; color: var(--text-muted) }
.nav-scroll { flex: 1; min-height: 0 }
.nav { border-right: 0 }
:deep(.el-sub-menu__title) { font-size: 13px; font-weight: 600; color: var(--text-secondary) }
:deep(.el-menu-item) { font-size: 13px; height: 40px; line-height: 40px }
:deep(.el-menu-item.is-active) { color: var(--primary); background: var(--primary-light, #eef2ff) }
</style>
```

> icon 名称需在 `@element-plus/icons-vue` 实际存在;执行时若个别图标名报错,就近替换为存在的同类图标(如 `Coin`→`Wallet` 等)。`default-openeds` 让 4 组默认展开,接近参考图。

- [ ] build → `✓ built`;Commit `feat(frontend): grouped sidebar (4 groups, el-sub-menu)`。

---

## Task 5: AdminShell 全屏模式 + 挂浮动助手

**Files:** Modify `frontend/src/layout/AdminShell.vue`

- [ ] **替换为（fullscreen 时隐藏 sidebar/header,只留内容 + 浮动助手;退出全屏按钮浮于右上）:**

```vue
<template>
  <div class="admin" :class="{ fullscreen: app.fullscreen }">
    <AppSidebar v-if="!app.fullscreen" />
    <div class="main">
      <AppHeader v-if="!app.fullscreen" />
      <main class="content" :class="{ 'content--fs': app.fullscreen }"><router-view /></main>
    </div>
    <button v-if="app.fullscreen" class="exit-fs" @click="app.setFullscreen(false)">退出全屏 ✕</button>
    <FloatingAssistant />
  </div>
</template>

<script setup lang="ts">
import { watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import FloatingAssistant from '@/components/aiops/FloatingAssistant.vue'

const app = useAppStore()
const route = useRoute()
// fullscreen 仅对 /dashboard 有意义;离开 dashboard 自动退出全屏
watch(() => route.path, (p) => { if (app.fullscreen && p !== '/dashboard') app.setFullscreen(false) })
</script>

<style scoped>
.admin { display: flex; height: 100vh; overflow: hidden; background: var(--content-bg) }
.admin.fullscreen { background: var(--cockpit-bg) }
.main { flex: 1; display: flex; flex-direction: column; min-width: 0 }
.content { flex: 1; overflow: auto; padding: 20px }
.content--fs { padding: 0; overflow: auto }
.exit-fs { position: fixed; top: 16px; right: 20px; z-index: 50; border: 1px solid var(--brd);
  background: rgba(255,255,255,.9); color: var(--text-primary); border-radius: 9px; padding: 7px 13px;
  font-size: 12px; cursor: pointer }
</style>
```

> CockpitShell.vue 的全屏深色皮肤 + topbar(实时更新/数据时间/退出大屏)功能,在 Phase A 暂**保留 CockpitShell.vue 文件不动**(不再被路由引用),其 polling 逻辑由 DashboardView 自身在 fullscreen 下接管(见 Task 6)。如 Task 6 未引入 polling 冲突,CockpitShell 可留作遗留;后续 Phase B 清理。

- [ ] build → `✓ built`;Commit `feat(frontend): AdminShell fullscreen mode + mount FloatingAssistant`。

---

## Task 6: DashboardView 加「全屏」按钮

**Files:** Modify `frontend/src/views/DashboardView.vue`

- [ ] 在 DashboardView 现有顶部筛选条(CockpitFilterBar 或其等价位)右侧加一个「全屏」按钮:
  - 点击 `app.setFullscreen(true)`。
  - 进入全屏后,AdminShell 隐藏 chrome,DashboardView 自身已是深色,即恢复沉浸大屏形态。
- [ ] ** polling 自洽:** 原 CockpitShell 启动了 `usePolling(realtime.fetchRealtime, 30000)`。统一单壳后 CockpitShell 不再挂载,需把该 polling 移到 DashboardView 的 `onMounted`(若 DashboardView 内尚未自行轮询)。检查 DashboardView 现状:若已有轮询则免;若无,补:
```ts
import { onMounted, onBeforeUnmount } from 'vue'
import { useRealtimeStore } from '@/stores/realtime'
import { usePolling } from '@/composables/usePolling'
const realtime = useRealtimeStore()
const { start, stop } = usePolling(() => realtime.fetchRealtime(), 30000)
onMounted(start); onBeforeUnmount(stop)
```
- [ ] 视觉确认:`/dashboard` 正常显示(带侧栏)→ 点「全屏」→ 侧栏/顶栏消失,深色大屏沉浸 → 点「退出全屏 ✕」恢复。
- [ ] build → `✓ built`;Commit `feat(frontend): dashboard fullscreen toggle + self-polling`。

---

## Task 7: FloatingAssistant.vue（右下角全局浮窗）

**Files:** Create `frontend/src/components/aiops/FloatingAssistant.vue`

- [ ] **右下角圆形 FAB,点击开 el-drawer(右侧抽屉),内嵌精简对话(复用 chat store + ChatMessage + ChatComposer):**

```vue
<template>
  <button class="fab" @click="app.toggleAssistant" title="AIOps 智能助手">
    <el-icon><ChatDotRound /></el-icon>
  </button>
  <el-drawer v-model="app.assistantOpen" title="AIOps 智能助手" direction="rtl" size="420px" :with-header="true">
    <div class="asst">
      <div class="body">
        <ChatMessage v-for="m in chat.messages" :key="m.id" :msg="m" />
        <div v-if="chat.loading" class="thinking">主智能体思考中…</div>
        <div v-if="!chat.messages.length" class="empty">向主智能体提问,例如:最近出水COD是否超标?</div>
      </div>
      <ChatComposer />
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { ChatDotRound } from '@element-plus/icons-vue'
import { useAppStore } from '@/stores/app'
import { useChatStore } from '@/stores/chat'
import ChatMessage from './ChatMessage.vue'
import ChatComposer from './ChatComposer.vue'
const app = useAppStore()
const chat = useChatStore()
</script>

<style scoped>
.fab { position: fixed; right: 26px; bottom: 26px; z-index: 100; width: 54px; height: 54px; border-radius: 50%;
  border: 0; cursor: pointer; color: #fff; font-size: 22px; background: var(--brand-gradient);
  box-shadow: 0 8px 24px rgba(99,102,241,.4); display: grid; place-items: center; transition: transform .15s }
.fab:hover { transform: scale(1.07) }
.asst { display: flex; flex-direction: column; height: calc(100vh - 120px) }
.body { flex: 1; overflow-y: auto; padding: 4px 6px }
.thinking { color: var(--text-muted); font-size: 13px; padding: 10px 0 }
.empty { color: var(--text-muted); font-size: 13px; padding: 30px 0; text-align: center }
</style>
```

> ChatMessage/ChatComposer 已在 Phase 2 实现并复用同一 chat store——浮窗与 `/chat` 页**共享会话状态**(任意页面提问,两边消息同步)。抽屉内宽度 420px,移动端可后续优化。FAB 在全屏大屏模式下也可用(`z-index:100` 浮于内容上)。

- [ ] build → `✓ built`;Commit `feat(frontend): FloatingAssistant (global FAB + chat drawer)`。

---

## Task 8: AppHeader 标题映射补全

**Files:** Modify `frontend/src/components/layout/AppHeader.vue`

- [ ] 把 `titles` 映射表补全为所有新路由(占位页也要有正确标题),并支持从 `route.meta.title` 优先取值:
```ts
const currentTitle = computed(() => {
  const meta = route.meta?.title
  if (typeof meta === 'string' && meta.trim()) return meta
  for (const k of Object.keys(titles)) if (route.path.startsWith(k)) return titles[k]
  return '废水监测系统'
})
```
> 这样所有路由(含占位)标题都正确,不必手维护映射表。`titles` 可保留作 fallback 或清空。

- [ ] build → `✓ built`;Commit `feat(frontend): AppHeader title from route.meta`。

---

## Task 9: 端到端验证

- [ ] **Step 1: 全关卡** — `npm run type-check && npm test && npm run build` → 0 错 / 16 PASS / ✓ built。
- [ ] **Step 2: 视觉确认(人工)** — `http://localhost:5173`:
  - 左侧栏 4 大分组(智能助手/监控大屏/事件中心/设置),默认展开,每项 icon+文字。
  - 点各占位项 → 渲染「建设中」卡片(标题/描述/Phase B 提示)。
  - 真实页(`/chat` `/dashboard` `/logs` `/events`)正常工作。
  - `/dashboard` 点「全屏」→ 侧栏/顶栏消失,深色沉浸大屏 → 「退出全屏 ✕」恢复。
  - 右下角圆形 FAB → 点开右侧抽屉 → 可提问,与 `/chat` 共享消息;全屏大屏下 FAB 也可用。
- [ ] **Step 3: 收尾** — 无新提交(仅验证)。

---

## 验收标准(Phase A 完成)
- [ ] type-check 0 错;build ✓;16 测仍 PASS
- [ ] 统一单壳 + 4 大分组折叠导航(接近参考图形态)
- [ ] `/dashboard` 从侧栏进入,且支持全屏切换(沉浸大屏保留)
- [ ] 右下角全局浮动 AI 助手,任意页面(含全屏大屏)可唤起,与 `/chat` 共享会话
- [ ] 所有 Phase B 菜单项有占位页,不报错;真实页不受影响

---

## Phase B 路线图（后续逐页补内容,每页可独立交付）

按数据就绪度排序(先做有真实后端支撑的):

1. **指标查询 `/metrics`** — 接 `/api/v1/data/history` + realtime;按指标/时间窗口查询 + ECharts 趋势图(复用 TrendChart/SparklineCell)。
2. **数据源 `/datasources`** — 接 `/api/observability/tracing/datasources`(已完整 CRUD + test_connection);列表 + 新增/编辑/删除/测试连接表单。
3. **链路追踪 `/tracing`** — 接 `/api/observability/tracing/catalog` + `/search` + `/traces/{id}`;trace 列表 + 详情。
4. **告警中心 `/alerts`** — 复用 `/api/events` 数据,以「告警」视角重组(严重度/状态流转);可与事件中心共享 eventsStore。
5. **智能体配置 `/agents/config`** — 接 `/api/query/capabilities`(decision_tree + identity_files);只读展示主智能体 + 4 子智能体身份与能力。
6. **智能体审计 `/agents/audit`** — 接 `/api/logs?log_type=master|subagent` + `/api/logs/trace/{id}`;会话决策审计列表 + 钻取。
7. **Grafana 大屏 `/grafana`** — iframe 嵌入;**前置确认**:Grafana 实例在跑 + `grafana.ini` 的 `allow_embedding=true`(或用面板 snapshot);否则保留占位。
8. **事件源 `/event-sources`** + **系统设置 `/settings`** — 无后端,做配置展示(双数据流参数 / LLM 配置来自 `/api/health`),或继续占位。

> Phase B 每页独立可交付;优先级可按需调整。建议先做 1-4(有真实数据,价值高)。

## Self-Review
- **方向一致**:4 个用户决策(原生+Grafana可选/单壳分组/只读+占位/分阶段)均有对应 Task 或 Phase B 条目。
- **不破坏现有**:真实页(/chat /dashboard /logs /events /trace)路由保留,仅外壳与侧栏变化;Phase 1/2 代码不重写。
- **占位策略**:Phase B 项统一 PlaceholderView(meta 驱动),Phase B 仅替换 view,不动导航——骨架一次到位。
- **全屏沉浸保留**:`/dashboard` 并入单壳但保留 fullscreen 切换,不失原 cockpit 体验。
- **浮动助手复用**:不新建对话逻辑,直接复用 Phase 2 的 chat store/ChatMessage/ChatComposer,与 `/chat` 共享状态。
- **已知留白**:CockpitShell.vue 在 Phase A 后不再被路由引用(留作遗留,Phase B 清理);Grafana iframe 依赖外部实例(Phase B 前置确认);占位页无功能(Phase B 补)。
