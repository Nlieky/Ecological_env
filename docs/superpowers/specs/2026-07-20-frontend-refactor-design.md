# 前端重构设计 · 废水监测智能体系统

> 状态：设计已与用户确认（大屏 / 外壳 / AI助手 三块可视化原型均通过）
> 日期：2026-07-20
> 后端前提：FastAPI@8000 → Agent@8642 → AIAgent 主智能体（ctgu-vlm）全链路已验证打通

---

## 1. 目标与非目标

### 目标
- **全面重构，分阶段交付**：代码结构 + UX 视觉 + 功能补全一起做，拆成可独立交付的阶段。
- **丢弃现有废弃内容**：当前 `frontend/` 的死代码（`AppLayout_ref.vue`、`TraceObservability.vue`、`ObservabilityTabs.vue` 等）不借鉴、不 salvage，从干净基线重建。
- **以 `sxdevops-main/frontend` 为设计参考**：移植其设计系统（tokens、外壳、卡片美学、组件约定），技术栈保持不变。
- **针对我们的后端裁剪**：只做后端真实提供能力的页面；突出智能体（decision_path / sub_agent_calls / 证据链）。
- **技术栈不变**：Vue 3.5 + TS + Vite 6 + Pinia 3 + Element Plus 2 + ECharts 5 + Axios（参考项目是 JS，我们保留 TS 并补全类型）。

### 非目标（明确不做）
- 登录 / 权限 / RBAC（后端无鉴权，菜单静态、路由无守卫）。
- DevOps 专有功能：CMDB 拓扑、任务/工单/Ansible、事件墙、容器、SQL 审计。
- 真实传感器实时数据流（当前用历史 CSV 模拟，见后端 `monitoring_data_loader.py`）。
- 后台页面的暗色模式切换（后台恒定浅色；仅大屏是深色）。
- 移动端响应式（桌面端优先，移动端延后）。

---

## 2. 已锁定的关键决策（brainstorm 阶段确认）

| 议题 | 决策 |
|---|---|
| 重构策略 | B+C：浅色后台（按参考项目）+ 智能体深加工展示；监测大屏单独定制深色 |
| 现有死代码 | 丢弃（不 salvage `_ref`/`TraceObservability` 等），仅借鉴参考项目设计 |
| 鉴权 | 不做（静态菜单、无路由守卫） |
| 大屏数据粒度 | **一个格子 = 一条指标趋势**（不是“一个厂”）；按 进水/出水/衍生 分组 |
| 大屏模式 | 双模式：单厂全指标（默认，真实数据 ~16 格）/ 全厂总览（多厂接入后，每厂一格） |
| 外壳 | **A 双模式**：`/dashboard` 全屏深色驾驶舱；`/chat` `/events` `/logs` 浅色后台外壳 |
| AI 助手 | 浅色，对话 + **内联推理卡片**（决策路径/子智能体/证据链） |
| 后端小改动 | 暴露 氨氮/流量/排放量 指标（现 v1 仅 pH/COD/TN/TP），让大屏更密 |

---

## 3. 架构

### 3.1 双外壳（Dual Shell）

应用有两套外壳，按路由切换：

- **CockpitShell（深色驾驶舱）**：全屏沉浸，无侧栏；顶部仅极简条（标题 + 实时更新指示 + 数据时间 + 「退出大屏」）。挂载 `/dashboard`。
- **AdminShell（浅色后台）**：左侧栏（config-driven 菜单）+ 顶部 header（面包屑 + 通知 + 用户）+ 内容区。挂载 `/chat` `/events` `/logs`。

路由结构（嵌套，懒加载，meta 带 title/icon）：

```
/                  → redirect /dashboard
/dashboard         → CockpitShell + DashboardView   (深色全屏)
/chat              → AdminShell + AIOpsChatView
/events            → AdminShell + EventCenterView
/logs              → AdminShell + LogsView
/logs/trace/:id    → AdminShell + TraceView         (从 AI助手"查看完整追溯"跳入)
```

> 「退出大屏」= 从 `/dashboard` 跳 `/chat`（或上一操作页）。两套外壳共用同一个 `appStore`（UI 状态）和同一套 api 模块。

### 3.2 目录结构（重建后）

```
src/
├── layout/
│   ├── CockpitShell.vue        # 深色大屏外壳
│   └── AdminShell.vue          # 浅色后台外壳（侧栏+header）
├── views/
│   ├── DashboardView.vue       # 迷你图矩阵大屏
│   ├── AIOpsChatView.vue       # AI 助手
│   ├── EventCenterView.vue     # 事件中心
│   ├── LogsView.vue            # 日志查询
│   └── TraceView.vue           # 会话追溯（证据链全貌）
├── components/
│   ├── cockpit/                # 大屏专用（深色）
│   │   ├── CockpitFilterBar.vue
│   │   ├── IndicatorMatrix.vue
│   │   ├── IndicatorGroup.vue
│   │   ├── SparklineCell.vue
│   │   ├── AnomalyList.vue
│   │   └── PlantOverviewGrid.vue
│   ├── aiops/                  # AI 助手专用
│   │   ├── ConversationList.vue
│   │   ├── ChatMessage.vue
│   │   ├── ChatComposer.vue
│   │   ├── DecisionFlow.vue    # 决策路径（4 步流程）
│   │   ├── SubAgentChips.vue   # 子智能体调用
│   │   └── EvidenceChain.vue   # 证据链
│   └── shared/                 # 跨页复用
│       ├── StatCard.vue
│       ├── StatusDot.vue
│       ├── TrendChart.vue      # ECharts 封装
│       └── MarkdownRenderer.vue
├── stores/
│   ├── app.ts                  # UI 状态（shell 模式、时间窗口、筛选）
│   ├── chat.ts                 # 对话/消息（接 conversations）
│   ├── realtime.ts             # 监测指标矩阵数据
│   └── events.ts               # 事件
├── api/
│   ├── client.ts               # axios 实例 + 拦截器（TS）
│   ├── modules/
│   │   ├── query.ts            # /api/query, /api/query/capabilities
│   │   ├── monitoring.ts       # /api/v1/monitoring/*, /api/v1/data/*
│   │   ├── conversations.ts    # /api/v1/conversations
│   │   ├── events.ts           # /api/events
│   │   ├── logs.ts             # /api/logs, /api/logs/trace
│   │   └── plants.ts           # /api/realtime/plants
│   └── types/                  # TS 类型（响应/请求）
├── composables/
│   ├── useSparkline.ts         # 趋势线生成 + 涨跌/波动判定
│   ├── useQueryAgent.ts        # 查询 → 渲染答案 → 拉 trace → 渲染卡片
│   ├── usePolling.ts           # 自动刷新（监测数据）
│   └── useRouteTabState.ts     # tab 与路由同步（移植参考项目）
├── lib/
│   └── echarts.ts              # ECharts 按需 tree-shake
├── styles/
│   ├── tokens.css              # 设计 tokens（浅色 + 深色 cockpit 双套 CSS 变量）
│   └── base.css
└── router/
    └── index.ts
```

### 3.3 状态管理（Pinia，setup 风格）

- `appStore`：`shellMode`（'cockpit' | 'admin'）、`sidebarCollapsed`、`dashboardFilters`（分类/排序/时间窗口/异常规则）、`activePlant`。
- `chatStore`：`conversations`、`currentSessionId`、`messages`、`loading`、`trace`（当前会话的决策/子智能体/证据）。
- `realtimeStore`：`indicatorMatrix`（分组后的指标格子数据）、`anomalies`、`lastUpdate`。
- `eventsStore`：`events`、`total`、分页。

### 3.4 API 层（TS）

`client.ts`：`baseURL='/api'`（vite proxy → 8000）、`timeout=300000`（适配 AI 查询）、响应拦截器统一弹错（`ElMessage`）、请求拦截器预留（无 token）。每个 `api/modules/*.ts` 返回强类型 Promise。

---

## 4. 设计系统 / Tokens

两套 CSS 变量（`styles/tokens.css`），移植自参考项目 `main.css` 并扩展：

**浅色后台（AdminShell）：**
- `--primary:#6366f1`、`--brand-gradient`、`--card-radius:12px`、`--card-shadow`、状态色（success/warning/danger/info）、`--text-primary/secondary/muted`、`--sidebar-width:188px`、`--header-height:60px`、`--transition`。

**深色驾驶舱（CockpitShell，新增）：**
- 背景：石墨黑→深蓝渐变（`#070b14 → #0c1424 → #0a1018`）+ HUD 网格线。
- 玻璃拟态卡片：`rgba(150,180,230,0.05)` + `backdrop-filter:blur` + 细发光边框。
- 数据高光：青蓝 `#22d3ee`、翡翠绿 `#34d399`（上升）、警示红 `#fb5a6a`（下降）、琥珀 `#f5b042`（波动）、紫 `#8b9bff`。
- 趋势色规则：**上升绿 / 下降红 / 波动黄**（行情板隐喻）。

组件约定：`StatCard`、`StatusDot`（带发光）、`TrendChart`（ECharts 封装，统一主题）、`MarkdownRenderer`（AI 回答）。

---

## 5. 页面设计

### 5.1 监测大屏（DashboardView · CockpitShell）★ 核心

**布局**：顶部分类筛选条 + 主体迷你图矩阵 + 底部异常清单。

**双模式**（顶部 segmented 切换）：
- **单厂全指标（默认）**：按 `进水指标 / 出水指标 / 衍生指标` 三组铺开格子。
- **全厂总览（多厂接入后）**：每厂一格（关键指标 + 健康度条），点格子钻取进该厂单厂视图。

**格子（SparklineCell）内容**：指标名 + 状态点（发光）+ 当前值 + 单位 + 迷你趋势线（SVG/Canvas，带发光）+ 涨跌幅。异常格子琥珀色描边高亮。

**分组与指标来源**（单厂真实数据）：
- 进水：pH、COD、TN、氨氮、TP、流量（6）
- 出水：pH、COD、TN、氨氮、TP（5）
- 衍生（前端计算，数据来自 history 窗口，不需新数据源）：COD去除率、进出水pH相关性、氨氮/总氮比、数据完整率、3σ异常计数（5）
- 合计 ~16 格真实密度。

**筛选条**：分类（全部/进水/出水）、排序（异常优先/当前值/涨跌幅）、时间窗口（1H/6H/24H）、异常规则（阈值/波动）、右侧 正常/波动/异常 计数。

**交互**：格子点击 → 钻取该指标详情；悬停 tooltip；自动刷新（`usePolling`，默认 30s，历史数据下体现为窗口滚动）；异常格子高亮；矩阵滚动；趋势线入场动画。控件融入大屏（非普通表单）。

**底部异常清单（AnomalyList）**：突然下跌 / 持续低迷 / 波动过大 三类，映射后端违规模式（稀释排放、插瓶干扰、人工拟合、恶意逃避）。

### 5.2 AI 助手（AIOpsChatView · AdminShell）★ 核心

**布局**：左侧会话历史侧栏 + 中间对话主区 + 答案下方内联推理卡片。

**数据流**（关键接线）：
1. 用户发送 → `POST /api/query` → 渲染回答（markdown + 内联 chartData 趋势图）。
2. 拿到 `session_id` → `GET /api/logs/trace/{session_id}` → 渲染推理卡片。
3. 会话历史 → `GET /api/v1/conversations`；某会话详情 → `GET /api/v1/conversations/{id}`（含 messages）。

> **后端现实**：当前 `/api/query` 转发回来的 `decision_path`/`sub_agent_calls` 是空数组（路由写死 `[]`）；真实决策/子智能体数据在 `/api/logs/trace/{session_id}`（已验证 200）。因此必须二次拉 trace。可选优化：让 `/api/query` 内联 trace（见 §8，延后决策）。

**内联推理卡片**（折叠在每条助手回答下）：
- **决策路径（DecisionFlow）**：①数据感知 → ②异常检测 → ③规则推理 → ④研判处置；已执行打勾、未调用置灰。
- **子智能体调用（SubAgentChips）**：4 个 chip（名称 + 耗时 + 状态），「查看完整追溯」跳 `/logs/trace/:id`。
- **证据链（EvidenceChain）**：数据源 → 检出异常 → 规则匹配 → 置信度，横向时间线。

### 5.3 事件中心（EventCenterView · AdminShell）

标准后台：事件列表（按严重度/状态筛选、分页）+ 详情抽屉 + 状态流转（`PUT /api/events/{id}/status`）。接 `/api/events`、`/{id}`。通知 bell 复用 `eventsStore`。

### 5.4 日志与追溯（LogsView + TraceView · AdminShell）

- **LogsView**：6 类日志查询（`log_type=api|master|subagent|operator|llm|error`，注意是短名）+ 分页 + 导出桩。接 `/api/logs`。
- **TraceView**（`/logs/trace/:id`）：会话完整证据链全貌——master_decision + subagent_executions + operator_calls + llm_calls。从 AI助手「查看完整追溯」跳入。接 `/api/logs/trace/{id}`。

---

## 6. 数据契约映射

| 前端组件 | 后端端点 | 数据 |
|---|---|---|
| IndicatorMatrix（单厂） | `GET /api/v1/monitoring/realtime`、`/api/v1/data/history?time_range=24h` | 当前值 + 窗口趋势 |
| IndicatorMatrix（总览） | `GET /api/realtime/plants` | 厂列表（现为 mock，多厂接入后真实） |
| 衍生指标 | 前端由 history 计算（或后端 `/api/v1/data/aggregated`） | 去除率/相关性/完整率 |
| AnomalyList | `/api/v1/monitoring/quality` + 前端规则 | 异常计数 + 违规模式映射 |
| ChatMessage（答案） | `POST /api/query` | content + chartData + reasoning |
| DecisionFlow / SubAgentChips / EvidenceChain | `GET /api/logs/trace/{session_id}` | master_decision + subagent_executions |
| ConversationList | `GET /api/v1/conversations`；`/{id}` | 会话列表 + messages |
| EventCenter | `/api/events`；`/{id}`；`PUT /{id}/status` | 事件 |
| LogsView | `/api/logs?log_type=...` | 6 类日志 |
| TraceView | `/api/logs/trace/{id}` | 完整证据链 |

> 自动刷新：监测数据 `usePolling`（默认 30s）。历史数据下表现为时间窗口滚动，非真实时；CLAUDE.md 已注明。

---

## 7. 需配合的后端小改动（ enabling ）

1. **扩展暴露指标**（必做，让大屏达到 ~16 格真实密度）：
   `backend/services/monitoring_data_loader.py` 的 `RESPONSE_INDICATORS` 由 `["pH","COD","TN","TP"]` 扩展为含 `AN`（氨氮）、`flow`（流量）；`discharge`（排放量）仅进水侧。
   影响：`/api/v1/monitoring/*` 与 `/api/v1/data/*` 响应增加这些键；`compute_quality_score` 纳入更多列（可接受）。需补/调对应测试。
2. **（可选，延后）`/api/query` 内联 trace**：查询响应直接带 `decision_path`/`sub_agent_calls`（由 trace 派生），省去前端二次请求。本期前端先按二次拉取实现，此优化不阻塞。

---

## 8. 分阶段交付

- **Phase 0 · 地基**：tokens（双主题）、CockpitShell + AdminShell、router（双外壳嵌套）、axios client + `api/modules/*`（TS）、appStore、`lib/echarts`。各页占位。可独立交付（空壳能跑）。
- **Phase 1 · 监测大屏**：CockpitShell 内的迷你图矩阵大屏——SparklineCell/IndicatorMatrix/AnomalyList/PlantOverviewGrid + 双模式 + 筛选 + 自动刷新。**同步完成后端指标扩展（§7.1）**。
- **Phase 2 · AI 助手**：对话 + 内联推理卡片（DecisionFlow/SubAgentChips/EvidenceChain）+ trace 接线 + 会话历史。
- **Phase 3 · 事件中心 + 日志追溯**：EventCenter + LogsView + TraceView。

每阶段独立可交付、可验收。

---

## 9. 测试与质量

- **类型安全**：TS 全量，`vue-tsc` 通过；`api/types/` 覆盖所有响应。
- **构建**：`npm run build` 通过（dist 产物）。
- **冒烟**：每阶段交付后按 §6 契约逐端点冒烟（后端已验证 200）。
- **组件测试**：若引入 vitest，优先覆盖 `useSparkline`（涨跌/波动判定）与 `useQueryAgent`（查询→trace 时序）；否则手动冒烟。

---

## 10. 可视化原型索引（本次 brainstorm 产出，存于 `.superpowers/brainstorm/manual-vc/content/`）

- `dashboard-mockup.html` / `dashboard-mockup-v2.html` — 大屏（双模式 + 分组）
- `shell-layout.html` — 外壳 A/B 对比（已选 A 双模式）
- `aiops-chat.html` — AI 助手 + 内联推理卡片
