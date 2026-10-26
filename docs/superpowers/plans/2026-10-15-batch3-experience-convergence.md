# 第三批现有功能体验收口实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 完成正式/实验导航治理、公共页面结构与状态统一，并让主要既有页面在常用桌面分辨率下具备一致、可信、可恢复的体验。

**Architecture:** `featureRegistry` 是导航和功能状态的单一来源；小型公共组件统一结构与状态表达，页面继续持有业务查询逻辑；格式工具统一来源、时效、风险、时间和空值语义。

**Tech Stack:** Vue 3、Pinia、Vue Router、Element Plus、TypeScript、Vitest、Vite、Playwright。

---

## 约束与文件边界

在原目录和 `codex/hermes-phase1-hardening` 分支执行；不创建 worktree、不提交、不推送、不合并。每项执行 RED → GREEN → REFACTOR。不得修改业务数据、真实事件状态、密钥、Prometheus、Grafana 或论文分支。

新增：

- `frontend/src/config/featureRegistry.ts`
- `frontend/src/components/common/{PageShell,PageState,StatusBadge,ExperimentalFeature}.vue`
- `frontend/src/components/layout/ExperimentalMenu.vue`
- `frontend/src/composables/useAsyncView.ts`
- `frontend/src/utils/displayFormat.ts`
- `frontend/src/views/ExperimentalFeaturesView.vue`
- 对应 `__tests__` 测试文件
- `scripts/verify_batch3_ui.py`

修改路由、侧栏、AdminShell，以及 Dashboard、PlantBoardPanel、Metrics、EventCenter、KnowledgeGraph、AgentConfig、AIOpsChat、AgentAudit、Logs 和六个实验页面。

### Task 1: 功能注册表与正式导航

**Files:**
- Create: `frontend/src/config/featureRegistry.ts`
- Create: `frontend/src/config/__tests__/featureRegistry.spec.ts`
- Modify: `frontend/src/components/layout/AppSidebar.vue`
- Modify: `frontend/src/router/index.ts`
- Test: `frontend/src/views/__tests__/navigation.spec.ts`

- [x] **Step 1: 写失败测试**

```ts
expect(stableNavigation().flatMap(g => g.items).map(i => i.path)).toEqual([
  '/chat', '/agents/audit', '/agents/knowledge', '/agents/config',
  '/dashboard', '/metrics', '/plants/config', '/events', '/logs',
])
expect(featureByPath('/grafana')?.status).toBe('experimental')
expect(featureByPath('/datasources')?.title).toBe('可观测性数据源')
```

挂载侧栏并断言不渲染 Grafana、链路追踪、告警中心、事件源和系统设置。

- [x] **Step 2: 运行 RED**

`cd frontend; npx vitest run src/config/__tests__/featureRegistry.spec.ts src/views/__tests__/navigation.spec.ts`

预期：注册表不存在且侧栏仍硬编码全部入口。

- [x] **Step 3: 最小实现**

定义 `FeatureStatus = 'stable' | 'experimental' | 'hidden'`、`FeatureDefinition`、`FEATURES`、`featureByPath()`、`stableNavigation()` 和 `experimentalFeatures()`。侧栏从注册表生成；路由保留实验路径并新增 `/experimental`。

- [x] **Step 4: 运行 GREEN 并检查**

重复测试，执行 `git diff --check`，不提交。

### Task 2: 实验功能目录

**Files:**
- Create: `frontend/src/views/ExperimentalFeaturesView.vue`
- Create: `frontend/src/components/common/ExperimentalFeature.vue`
- Create: `frontend/src/views/__tests__/ExperimentalFeaturesView.spec.ts`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/views/{TracingView,DatasourcesView,AlertCenterView,GrafanaView,PlaceholderView}.vue`

- [x] **Step 1: 写失败测试**

断言目录包含六个实验入口；Grafana 说明包含“系统监测”和“不承担当前废水业务数据显示”；可观测性数据源说明包含 Jaeger；依赖不可达显示 unavailable 而非空白 iframe。

- [x] **Step 2: 运行 RED**

`cd frontend; npx vitest run src/views/__tests__/ExperimentalFeaturesView.spec.ts`

- [x] **Step 3: 最小实现**

`ExperimentalFeature` 接收 `title/status/dependency/purpose`，目录只读取注册表。实验路由保留，顶部统一显示状态和限制。

- [x] **Step 4: 运行 GREEN**

运行实验页面测试和路由测试；浏览六个深层路由，不启动 Grafana/Prometheus。

### Task 3: 公共骨架与滚动

**Files:**
- Create: `frontend/src/components/common/{PageShell,PageState,StatusBadge}.vue`
- Create: `frontend/src/components/common/__tests__/{PageShell,PageState}.spec.ts`
- Modify: `frontend/src/layout/AdminShell.vue`

- [x] **Step 1: 写失败测试**

PageShell 覆盖 title/subtitle/actions/context/content 插槽；PageState 覆盖 initial-loading、empty、not-found、partial、error、unavailable、disabled、stale；error/unavailable 发出 retry，empty 不带错误角色。

- [x] **Step 2: 运行 RED**

`cd frontend; npx vitest run src/components/common/__tests__/PageShell.spec.ts src/components/common/__tests__/PageState.spec.ts`

- [x] **Step 3: 最小实现**

PageShell 提供唯一内容滚动边界；PageState 使用正确的 `role=status/alert`；StatusBadge 同时使用文字与颜色。AdminShell 的 shell/main/router-view 链路统一 `min-height:0`。

- [x] **Step 4: 运行 GREEN**

重复测试，并在 1366×768 检查无浏览器与内容区双滚动。

### Task 4: 异步状态和展示格式

**Files:**
- Create: `frontend/src/composables/useAsyncView.ts`
- Create: `frontend/src/composables/__tests__/useAsyncView.spec.ts`
- Create: `frontend/src/utils/displayFormat.ts`
- Create: `frontend/src/utils/__tests__/displayFormat.spec.ts`

- [x] **Step 1: 写失败测试**

```ts
expect(formatValue(null)).toBe('—')
expect(formatSource({ origin: 'real', mode: 'historical' })).toBe('真实导入 · 历史数据')
expect(formatRisk('suspected')).toBe('违规嫌疑')
expect(formatDuration(128433)).toBe('2分08秒')
```

useAsyncView 必须证明迟到请求不覆盖新请求、刷新失败保留旧内容、首次失败进入 error、dispose 后不写状态。

- [x] **Step 2: 运行 RED**

`cd frontend; npx vitest run src/composables/__tests__/useAsyncView.spec.ts src/utils/__tests__/displayFormat.spec.ts`

- [x] **Step 3: 最小实现**

暴露 `data/state/error/run/refresh/retry/dispose`。固定 Asia/Shanghai；缺失值不转零；无人工确认的违规统一为“违规嫌疑”。不替换已有成熟的请求代次控制，只做状态适配。

- [x] **Step 4: 运行 GREEN**

重复测试并执行类型检查。

### Task 5: 监测大屏与指标查询接入

**Files:**
- Modify: `frontend/src/views/{DashboardView,PlantBoardPanel,MetricsView}.vue`
- Modify: `frontend/src/composables/dashboardData.ts`
- Create: `frontend/src/views/__tests__/batch3-monitoring.spec.ts`

- [x] **Step 1: 写失败测试**

测试历史来源显示“真实导入 · 历史数据”；陈旧数据无实时绿灯；仅出水为 partial；请求失败和成功空结果不同；结束时间早于开始时间不发请求；null 指标不生成零值。

- [x] **Step 2: 运行 RED**

`cd frontend; npx vitest run src/views/__tests__/batch3-monitoring.spec.ts src/composables/__tests__/dashboardData.spec.ts`

- [x] **Step 3: 最小接入**

使用公共骨架、状态和格式化工具；大屏和指标查询展示一致的厂站、来源、模式、采样时间和范围。保留现有 InfluxDB 查询及图表逻辑，不修改数据口径。

- [x] **Step 4: 运行 GREEN**

运行新测试及既有 dashboard/realtime/plants 测试，浏览真实导入、模拟、仅出水、失败重试四类 fixture。

### Task 6: 事件、图谱与配置接入

**Files:**
- Modify: `frontend/src/views/{EventCenterView,KnowledgeGraphView,AgentConfigView}.vue`
- Modify: `frontend/src/components/agents/config/*.vue`（仅公共状态和操作区）
- Create: `frontend/src/views/__tests__/batch3-operations.spec.ts`

- [x] **Step 1: 写失败测试**

断言事件严重程度、处理状态、可信度分开；无 conversation ID 不显示审计入口；图谱空图/404/500 不同；窄宽度使用详情抽屉；配置区分保存、下一请求生效、重启生效和运行已生效。

- [x] **Step 2: 运行 RED**

`cd frontend; npx vitest run src/views/__tests__/batch3-operations.spec.ts src/views/__tests__/navigation.spec.ts`

- [x] **Step 3: 最小接入**

只调整布局、状态和文案；复用现有事件确认写入、图谱请求代次和配置生效语义。窄屏详情使用 Element Plus drawer，不改变后端接口。

- [x] **Step 4: 运行 GREEN**

运行事件、知识图谱、配置聚焦测试；所有写操作使用 fixture/intercept。

### Task 7: 已优化页面接入

**Files:**
- Modify: `frontend/src/views/{AIOpsChatView,AgentAuditView,LogsView}.vue`
- Modify: `frontend/src/components/aiops/ConversationList.vue`
- Create: `frontend/src/views/__tests__/batch3-existing-pages.spec.ts`

- [x] **Step 1: 写失败测试**

断言三页使用公共结构；AI 列表与消息区独立滚动；审计分页留在列表区；日志上下文只展开当前行；既有多会话、搜索和日志筛选保持不变。

- [x] **Step 2: 运行 RED**

`cd frontend; npx vitest run src/views/__tests__/batch3-existing-pages.spec.ts src/stores/__tests__/chat.spec.ts src/composables/__tests__/useAuditList.spec.ts src/views/__tests__/navigation.spec.ts`

- [x] **Step 3: 最小接入**

不改变 chat runtime、审计查询或日志 API，只替换重复框架与状态展示。

- [x] **Step 4: 运行 GREEN**

复验两个会话同时执行、审计多关键词搜索和日志上下文展开。

### Task 8: 全量和浏览器验收

**Files:**
- Create: `scripts/verify_batch3_ui.py`
- Modify: `docs/superpowers/plans/2026-10-15-batch3-experience-convergence.md`（仅记录执行证据）

- [x] **Step 1: 编写验收脚本**

Playwright 分别使用 1366×768、1440×900、1920×1080，遍历正式入口、实验目录和六个实验路由；记录控制台错误、请求失败、横向溢出、双滚动、关键操作与分页可见性；截图写入忽略目录 `logs/batch3-verification/`。

- [x] **Step 2: 完整验证**

```powershell
cd frontend
npm test
npm run type-check
npm run build
cd ..
.\ecological_env\Scripts\python.exe scripts\verify_batch1_business.py --http
.\ecological_env\Scripts\python.exe scripts\verify_batch3_ui.py
git diff --check
```

预期全部退出码 0；仅允许已有依赖弃用、Rollup 注释和 bundle 大小警告。

- [x] **Step 3: 服务与范围核验**

确认 5173、8000、8642、8086 和 `/api/health`、Agent `/health`；Prometheus/Grafana 无需运行。检查业务数据、事件状态、密钥、服务配置、论文分支和 Git 历史无非预期修改。

- [x] **Step 4: 记录最终证据**

记录测试数量、构建、浏览器流程、截图目录、服务 PID 和遗留警告；保留当前分支与混合工作区，不提交。

## 完成定义

## 执行记录（2026-10-15，持续更新）

- [x] Task 1 功能注册表：正式九入口、实验六路由、路由元信息单一来源及尾斜杠兼容。规格与质量复审通过。
- [x] Task 2 实验目录：用途/依赖说明、独立入口、Grafana显式加载、选中对比度。规格与质量复审通过。
- [x] Task 3 公共骨架与状态：六个公共组件及布局插槽。规格与质量复审通过；实际滚动继续由全系统浏览器验收覆盖。
- [x] Task 4 异步状态和格式：九项聚焦测试通过；修复陈旧与刷新失败混淆、毫秒档和运行状态缺项；规格与质量复审通过。
- [x] Task 5 监测页：系统态势、态势历史、目录重试、旧厂站深链接与图表生命周期补齐；33项聚焦测试、规格/质量及最终集成复审通过。
- [x] Task 6 事件/图谱/配置：技能草稿保护与空图恢复生命周期已修复；52项相关测试及两阶段复审通过。
- [x] Task 7 既有页面：厂区配置固定操作头与草稿保护、追溯404刷新提示、日志分页遮挡修复；32项相关测试及两阶段复审通过。
- [x] Task 8 验收：48个页面/分辨率组合检查通过，无页面异常或正式页面外层溢出；10/10组状态交互通过，包含普通日志分页点击、空图恢复和技能草稿保护。原始15,568条数据逐值/时间/哈希核验及HTTP业务验收通过。最新全量前端31文件194项通过，类型检查通过，生产构建通过。最终独立集成审核APPROVED，补跑6文件45项通过。

- 正式导航仅有 9 个已投入使用入口。
- 六个实验入口从普通导航隐藏，但目录和深层路由可访问。
- 主要页面区分 loading、refreshing、empty、not-found、partial、error、unavailable、disabled、stale。
- 历史数据无实时在线表达；无人工确认不显示“确认违规”。
- 1366×768 下主要筛选、操作和分页可用，无双滚动或遮挡。
- 第三批测试、完整前端测试、类型检查、构建、业务回归和浏览器验收全部通过。
- 当前开发分支保留，不提交、不推送、不合并。

## 最终交付证据

- 浏览器脚本：`scripts/verify_batch3_ui.py`、`scripts/verify_batch3_states.py`。
- 截图与机器可读结果：`logs/batch3-verification/acceptance.json`、`states.json`、`state-*.png`；该目录受Git忽略。
- 分辨率：1366×768、1440×900、1920×1080；每种16个路由，48组合通过。实验Grafana/告警页面允许内容纵向滚动，正式页面无外层溢出。
- 测试中的配置、事件、模型写请求使用夹具，不执行实际变更；状态验收 `blocked_mutations=[]`。
- 服务：Frontend 5173 PID16656，Backend 8000 PID508，Agent 8642 PID13932，InfluxDB 8086 PID15620。四个HTTP入口200；Agent `agent_initialized=true`。
- 无提交、推送、合并或新worktree；原混合工作区保留。未修改业务采样、凭据和Prometheus/Grafana配置。
- 既有警告保留：usePolling的两条测试生命周期提示、Rollup依赖注释与混合导入提示、约2MB主包。不是新功能失败。
