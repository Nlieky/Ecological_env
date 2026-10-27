# 全系统助手页面操作契约实施计划

> For agentic workers: use subagent-driven-development with TDD and separate specification/quality reviews. User requires original checkout and no commits, merges, pushes or worktrees. Execute all tasks, retain review/test evidence below.

**Goal:** 让所有现有注册页面能力通过自然语言可靠准备、执行、验证和反馈，不加入特定句式/厂站/指标特判。

**Architecture:** Python声明式契约为事实来源，通过生成的静态JSON供Vue同步校验，API与Skill注入同一描述。服务端准备器处理白名单补参及待补充意图，前端绑定可信页面快照、按能力校验、按动作存储结果；页面handler核实效果。现有事件确认与并行隔离不变。

**Tech Stack:** Existing FastAPI/Pydantic, Hermes main Skill, Vue/Pinia/ECharts, pytest/Vitest/Playwright. No new dependencies or services.

## Task 1: 契约、准备态与协议（完成）

Files: shared/assistant/{contract,preparation}.py (new), protocol.py, master_turn.py; backend/models/assistant.py; backend/api/routes/assistant.py; backend/services/assistant_service.py; skills/system-interaction-core/SKILL.md; scripts/generate_assistant_contract.py (new); frontend/src/assistant/contract.generated.json (new); tests/assistant/test_operation_contract.py (new).

- [x] 写失败测试覆盖全部能力描述、生成JSON一致性、结构化缺参/继承/默认/非法参数、服务端重算pending及脱敏错误。
- [x] 运行 `.\ecological_env\Scripts\python.exe -m pytest tests/assistant/test_operation_contract.py -q`，确认业务断言RED而非环境错误。
- [x] 建立可序列化能力描述，保留SCHEMAS重导出兼容；使用apply_patch保存生成产物，提供只读--check一致性验证。能力描述包含schema/required/context/default/invalidation/target/title/level。
- [x] 请求允许受限pending意图；模型可返回intent提案，服务器只接受允许字段，计算缺参并返回pending或完整action；参数来源由服务端计算。所有补参仍严格验证，不拯救损坏JSON、不推断写权限。当前页对象由前端快照绑定，模型不能覆盖。
- [x] 完整旧actions保持兼容；响应携带契约版本；proxy验证准备结果，不二次套用默认值。默认算法只在用户委托策略选择时使用声明式iforest默认，不以pH或具体句式特判。
- [x] Skill仅解释通用意图/补参规则，能力说明由代码注入；保留专业handoff、工具禁用、事件关闭机制。
- [x] 运行相关pytest并逐项规格、质量复核。

## Task 2: 通用前端执行闭环

Files: frontend/src/assistant/{capabilities,executor}.ts; new preparation.ts/execution.ts if needed; stores/assistant.ts; api/modules/assistant.ts; components/assistant/{AssistantHost,AssistantPanel}.vue; existing assistant tests plus new operationContract.spec.ts.

- [x] 失败测试覆盖无关revision变化可执行、相对操作绑定对象/时间/来源、显式定位跨页等待handler注册、守卫取消/超时/离开目标、版本不匹配、重复点击、失败回执不污染正文、刷新恢复无可点击动作。
- [x] 用 `E:/nodejs/node.exe node_modules/vitest/vitest.mjs run src/assistant/__tests__ src/stores/__tests__/assistant.spec.ts` 在frontend目录确认RED。
- [x] 从generated契约推导schema/目标/中文标题，保留本地执行handler白名单；后端契约版本不匹配时禁用操作。页面发问快照不可被模型提供context覆盖。
- [x] 按能力判断上下文依赖，变化提示具体字段；等待页面handler注册用事件通知和有界超时而非固定sleep。执行后检查真实目标页及handler反馈。
- [x] 每个候选独立prepared/running/succeeded/empty/failed/stale状态，存回执code/message/details；同候选running/完成禁止重入，失败允许明确重试或重新准备，未知写结果维持原检索键。
- [x] 发送pending并保留多轮参数；切换主题可丢弃。候选卡中文展示对象/时段/参数来源，状态与回执独立于模型正文。历史持久化只保存回执与对话，不恢复动作/pending。
- [x] 保留事件proposal专用路径，真实写开关false，配置草稿不自动保存。运行Vitest、type-check并复核。

## Task 3: 页面处理器与检测可视化

Files: views/{DashboardView,PlantBoardPanel,MetricsView,EventCenterView,AgentAuditView,KnowledgeGraphView,LogsView,AgentConfigView}.vue as needed; stores/action.ts; new assistant/annotations.ts; API detection routes only if required; tests and script verification helpers.

- [x] 先为进出水标记、完整时区时间匹配、窗口切换清除、值不匹配/不可见、空结果及处理期间对象变化写失败测试。
- [x] 提取独立标注归属/匹配函数；绑定厂站/来源/窗口/指标/侧别；不以截断日期匹配。时间使用已有采样时区工具，未提供时按明确Asia/Shanghai业务默认；不能按浏览器当地时区猜测。
- [x] 将标记挂到对应series；校验返回值与采样点一致。handler等待图表应用，返回真实匹配数；0异常为empty，非零但0可见为失败并说明。
- [x] 提供结果定位，回放暂停显示异常而不更换采样窗口；切换厂站/窗口隔离旧标注，保留旧actionData兼容。
- [x] 检查其他页面handler返回前已应用筛选/定位/diff；禁止未找到对象仍成功或覆盖已有未保存草稿。
- [x] 运行对应Vitest、pytest及浏览器夹具后复核。

## Task 4: 综合验收与交付

Files: scripts/verify_assistant_operations.py (new), existing verify_assistant_navigation.py/verify_master_skill_parallel.py/verify_global_assistant_ui.py; current plan execution records.

- [x] Browser fixtures: 至少覆盖导航、事件/日志筛选、审计/图谱定位、指标查询、大屏时间、双侧标注、配置diff及写保护。按操作类别交叉验证刷新、对象/窗口变化、加载、失败、空结果、重复点击和恢复。
- [x] Real model: 不同指标/厂站/同义表达与多轮补充；使用真实只读检测，记录实际图表markPoint与对应side，不仅HTTP200。写请求全部拦截。
- [x] 有针对性重启原8000/8642加载新Skill；确认5173/8000/8642/8086健康，不新增进程或服务，事件写仍false。
- [x] 运行 `pytest tests/assistant tests/events tests/system/test_system_interaction_turn.py tests/system/test_system_owned_provider_threads.py tests/system/test_assistant_plugin_scope.py tests/system/test_stream_lifecycle.py tests/system/test_stream_proxy.py -q`（项目venv）；全量Vitest、type-check、build、修改范围diff-check。
- [x] 重新验证主页面与侧栏并行；独立规格及质量审查通过才交付，记录准确数量与限制。保留原分支全部既有修改。

## 执行记录

### 2026-10-19 最终验收

四个任务已实施并通过规格、质量复核；上方逐步清单已完成，以本验收记录为最终状态。

- 前端全量 Vitest：38文件、240项通过；相关后端 pytest：125项通过。类型检查、生产构建、契约生成一致性检查通过。已有轮询生命周期、第三方PURE注释及大包告警不影响本轮通过，不视为已消除技术债。
- 浏览器夹具最终重跑：24项全局助手UI + 7项页面操作通过，覆盖主题、导航、筛选、定位、配置diff、事件确认保护及双侧真实ECharts标记。模型/写入使用夹具，不冒充真实业务写入验收。
- 真实模型、真实Influx只读检测：4项通过。进水TN标记3点；出水COD恒值结果0点且诚实显示空结果；多轮补参后进水pH标记3点；跨页事件筛选生效。核对实际图表series和执行绑定，不仅检查HTTP200。记录：logs/assistant-verification/operation-live-verified-final/results.json。
- 夹具记录：logs/assistant-verification/operation-20261019-ui-delivery、operation-20261019-fixtures-delivery。真实测试阻止非白名单写请求，无真实事件或配置写入。
- 主页面与侧栏并行复验：均200，实际重叠，分别1.39秒和1.52秒；此为轻量身份请求，不代表专业多会话自身锁已取消。
- 实测修复Influx厂站查询混合类型分组错误；显式午夜结束时间不再被扩为整日，仅日期输入保留整日语义；均先验证失败再修复。
- 结构化协议错误最多重新生成一次，共用原超时、隔离实例与禁用工具设置；仍非法则安全失败，不自动执行。准备状态文案由验证后的可信字段生成。
- 参数来源真实区分请求解析、页面继承和服务端默认。模型展开的参数不伪标为服务端默认；真实默认插入另有单元测试。通用契约覆盖12项注册能力，不含pH/厂站/自然语言句式特判。
- 限制：不支持任意DOM操作，不保证所有自然语言表述均正确；必须核对候选后确认。真实事件写开关保持false，配置只生成受保护草稿。同范围后续失败可能保留上一次成功标记，失败候选不会声称新标记成功。
- 保留原项目目录、codex/hermes-phase1-hardening及既有脏工作区；未提交、合并、推送或新建服务。

初始代码定位完成：当前原目录codex/hermes-phase1-hardening，脏工作区属于用户已有工作，不清理。按四任务顺序执行，不同时派遣多个实现者，避免共享状态冲突。此清单会随实测结果更新，不将旧测试数量当本轮证据。
