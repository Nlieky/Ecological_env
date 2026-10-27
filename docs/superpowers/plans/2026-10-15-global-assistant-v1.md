# 全系统 AIOps 助手首版实施计划

> **For agentic workers:** 使用 subagent-driven-development 执行任务，逐项规格与质量审核；用 checkbox 跟踪。用户已批准方案并要求继续，无需再次询问执行方式。

**Goal:** 将右下角动作浮窗升级为独立、有页面上下文、可解释及可核验操作的全系统助手，保留原浅蓝玻璃主题。

**Architecture:** 独立assistant store/API承载会话；页面注册结构化上下文，服务端受限模型只产生候选动作，前端能力注册表验证并执行。单事件写入经服务端提议、显式确认、比较更新、幂等与事务审计；默认关闭。

**Tech Stack:** Vue3/Pinia/TypeScript/ElementPlus、FastAPI/Pydantic/SQLAlchemy、Vitest/Pytest/Playwright。

## 约束

原目录原开发分支；不提交、推送、合并或创建worktree。不改真实业务数据、密钥及供应商配置。沿用上一轮用户选择的子智能体实施与两阶段审核。五个增量按依赖集成，代码可在互不重叠的文件中并行准备。

## A：独立会话与侧边界面

Files: 新增 `frontend/src/stores/assistant.ts`、`frontend/src/components/assistant/AssistantPanel.vue`、`frontend/src/api/modules/assistant.ts` 与测试；修改 `FloatingAssistant.vue`、`AdminShell.vue`。

- [x] 先测试主聊天与助手store完全独立、跨页保留、关闭不取消、发送失败可恢复。
- [x] 使用独立消息模型（text/action/proposal/handoff），不调用useChatStore。
- [x] 原胶囊入口与玻璃主题保留；420/560宽侧栏，剩余业务宽>=900时并排，否则可收起抽屉；原生抽屉交替呈现。
- [x] 输入、历史、上下文、操作卡分区，执行状态有明确结果；/chat页也可使用。
- [x] 聚焦Vitest、类型检查、三种桌面及1100窄窗截图验证。

## B：上下文与受限帮助API

Files: 新增 `frontend/src/stores/assistantContext.ts`、`frontend/src/composables/useAssistantContext.ts`；新增 `backend/models/assistant.py`、`backend/services/assistant_service.py`、`backend/api/routes/assistant.py`、帮助资料；修改 `backend/main.py`注册路由；页面分别接入。

- [x] 先验证schema拒绝多余/敏感字段、上下文失效/切页以及不会调用专业Agent写工具。
- [x] 上下文仅包含页面、对象ID、厂站、指标、采样时间范围、来源时效、筛选、加载状态、可用动作；请求冻结快照。
- [x] `POST /api/assistant/respond`返回文字与候选动作，`GET /api/assistant/capabilities`返回真实支持范围。
- [x] 独立受限LLM提示与结构化校验，复用当前provider读取，模型失败明确反馈；系统帮助可从固定资料可靠回答，不能只靠关键词模板假称自然语言能力。
- [ ] 模型无法执行任意HTTP、文件、SQL；页面文本视作数据。后端核验对象及动作参数，前端再校验白名单。
- [x] Pytest测试使用临时DB与模型夹具，不修改真实模型配置。

## C：只读执行与交接

Files: 新增 `frontend/src/assistant/{capabilities,executor,handoff}.ts` 和 `AssistantActionCard.vue`；接入 Dashboard/Metrics/EventCenter/AgentAudit/KnowledgeGraph/Logs/AgentConfig；必要非敏感草稿桥接。

- [x] 先测试非法动作拒绝、旧上下文不操作新对象、URL参数编码、未支持筛选明确拒绝、结果失败不宣称成功。
- [x] 首版白名单：导航、厂站/指标/时间、事件筛选/详情、会话/图谱定位、日志已有模块筛选、既有检测标注。
- [x] 执行器返回结构化结果，实际页面确认后显示完成；不把dispatch成功当异步检测成功。
- [x] 专业任务交接卡携带对象/时间/问题，点击只预填主AI草稿，不自动请求。
- [x] 配置仅允许已定义字段草稿diff，沿用原页面保存和dirty guard；未有schema不承诺编辑。
- [x] 前端关键回归与GET fixture浏览器验证，不提交真实事件/配置变更。

## D：单事件确认写入

Files: 新增 `backend/models/assistant_operation.py`、`backend/services/assistant_operations.py`及测试；assistant路由增加提议/确认/结果；前端新增确认卡和API。

- [x] RED覆盖默认关闭、一次性短期提议、原状态/updated_at比较、冲突、重复幂等、确认绑定客户端会话和目标、理由校验、终态状态机、审计失败回滚。
- [x] API：`POST /api/assistant/event-proposals`；`POST /api/assistant/event-proposals/{id}/confirm`；`GET /api/assistant/operations/{id}`。
- [x] 服务端开关默认false；拒绝模型/前端自行启用。身份记为未认证本地操作会话，不伪装已授权用户。
- [x] 事务中比较更新事件并记录完整前后值/理由/来源/结果；确认前状态变动则409，超时可查结果不盲重试。
- [x] 前端确认卡显示事件、厂站、原/新状态、理由、有效期；切对象时失效。没有明确确认不发送写请求。
- [x] 用内存SQLite与模拟故障验证，实际部署仍保持开关关闭。

## E：最终集成与验收

Files: 新增 `scripts/verify_global_assistant_ui.py`；更新本计划执行记录。

- [x] 每单元规格审核后质量审核，修复所有阻断问题。
- [x] 完整前端Vitest、type-check、build；后端assistant及事件回归；业务数据只读核验。
- [x] 浏览器验证独立会话、七页面上下文、只读操作、交接草稿、配置草稿、确认/取消和关闭恢复；所有写入使用夹具。
- [x] 1366×768、1440×900、1920×1080和1100窄窗口无分页遮挡、无drawer焦点冲突，图表resize正确。
- [x] 主题与原浮窗对照：浅蓝白渐变、模糊、高光、阴影、圆角和机器人图标保持一致。
- [x] 记录已支持能力、实际未覆盖边界、服务加载状态与测试数量。保留当前混合工作区。

## 2026-10-16 执行记录

已在原目录、原开发分支实现独立系统助手：保留胶囊与浅蓝玻璃主题，支持420/560侧栏和响应式并排/抽屉；七页面结构化上下文、受限帮助API、候选动作白名单、主AI草稿交接及非敏感策略diff草稿。单事件提议/确认/结果查询采用持久提议、状态与版本CAS、会话绑定、幂等和事务审计；实际部署开关仍为false。

审核修复包括：provider沿用运行参数读取链路、旧页面测试初始化、显式取消、执行异常反馈、准备期间冻结事件快照、确认目标以服务端提议为准、未知结果恢复记录不被普通历史截断。大屏与指标查询的异步页面动作均新增过期租约，并通过切页、换厂、卸载及正常执行回归。

验证记录：后端assistant+events 40项通过；前端最终34文件215项通过、type-check通过；生产构建通过。四分辨率及上下文/导航/筛选/定位/草稿/确认取消/未知恢复浏览器23项通过，正常确认另1项通过；所有写入与模型调用在浏览器验收中均由夹具拦截。真实受限模型只读烟测“请打开事件中心”返回正确navigate候选。服务已恢复：5173前端、8000后端、8642主Agent、8086 InfluxDB。

边界：助手/respond不查询实时对象事实，页面上下文是客户端快照；执行时由页面接口核对对象，事件由服务端提议核对。配置仅支持既定策略字段草稿，不直接保存配置；专业分析只交接主AI草稿。事件写入尚未对实际部署开放，不代表已有身份认证授权。构建仍有既有大包及Rollup注释警告，测试有既有usePolling生命周期警告。本轮无提交、推送、合并、worktree或真实事件/配置写入。

最终生产构建再次通过；业务只读HTTP核验通过15568条原始记录，来源SHA256、数值、时间戳及AI/大屏COD一致。初启动InfluxDB时首次查询超时、随后验证与后端重启重叠导致连接中断，服务稳定后重跑通过，未通过放宽数据断言处理。

最终浏览器统一复跑24/24通过，page_errors=0，非夹具写入=0；包含正常确认及模拟断网后未知结果刷新恢复，不重复提交。证据：`logs/assistant-verification/results.json`与同目录四分辨率截图。

### 真实模型503回归修复

用户复测报错后，使用真实浏览器连续对话复现503；独立观察相同完整上下文/历史的上游响应，确认HTTP200、finish_reason=stop但content为普通中文文本，原实现json.loads失败被统一转为503。修复为：严格JSON仍按白名单校验，完整json代码围栏可解析，普通文本仅展示且actions为空；畸形JSON、非法动作和截断回答仍拒绝，不从文本推断动作。新增仅记录阶段/异常类型的脱敏日志；前端展示服务端detail，不只显示英文HTTP状态。

新回归先红后绿。最终前端216项、后端assistant/events48项、type-check及build通过（既有警告保留）。`scripts/verify_assistant_live.py`实际调用运行模型，连续12轮含完整页面上下文和最长20条历史，刷新恢复后再1轮，13/13返回200、无浏览器异常；证据`logs/assistant-verification/live-503/results.json`及`after.png`。未点击任何业务写入或配置保存，真实写入开关仍关闭。
