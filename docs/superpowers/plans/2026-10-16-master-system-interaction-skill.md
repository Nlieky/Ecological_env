# 主智能体系统交互 Skill 迁移实施计划

> **For agentic workers:** 按 executing-plans 逐项实施与复核，使用checkbox记录，不自动提交或创建worktree。

**Goal:** 移除侧栏独立模型调用，将系统交互统一交由现有主智能体的Skill处理，不增加服务、角色或子智能体。

**Architecture:** 保留8000公共助手API，将其改为8642现有Agent服务的协议代理；后者通过统一工厂创建同身份的会话级隔离实例运行受限Skill；与专业主实例并行，不获取其全局锁。候选动作解析和真实执行仍隔离，确认写入机制不变。

**Tech Stack:** 现有Hermes AIAgent、FastAPI/Pydantic、Vue/Pinia、Pytest/Vitest、Python Playwright。

设计依据：`docs/superpowers/specs/2026-10-16-master-system-interaction-skill-design.md`。用户已确认并行修订，连续实施并审核；原目录原分支，不改真实事件、配置或密钥。

## 执行结果（2026-10-16）

第1—5项已实施并完成规格与代码质量复核。下方保留原计划的测试示例；实际实现与验收以下列记录为准：任务ID使用客户端会话ID的SHA-256，而不是原文拼接；侧栏通过实例级工具禁用、分发阻断及请求级ContextVar隔离插件，不修改专业实例的全局权限。

- 8000改为现有8642服务的代理；统一主智能体工厂、身份和provider配置。新增system-interaction-core Skill，不新增服务、端口、身份或子智能体。
- 每侧栏会话独立运行实例，最多2个同时执行；同会话忙碌或容量满返回409。超时后，外层及底层provider子线程真正结束前不释放执行槽；实例隔离淘汰，不影响专业主实例。
- 补充身份文件白名单、禁用持久记忆与调试快照、插件/环境变量/工具目录的请求级隔离。当前chat-completions通道启用已有JSON响应模式；其他传输仍使用严格协议解析。handoff不再附带额外导航动作。
- TDD覆盖代理、并发、工具拒绝、共享状态隔离、底层线程超时及handoff；最终助手/事件/并发/流式相关pytest为86项通过（17条警告），不是宣称全部系统测试均已运行。
- 前端34个测试文件、216项通过；type-check和build均通过。现有Vue轮询生命周期提示、Rollup PURE注释及大包警告仍保留，不属于本次迁移修复范围。
- 浏览器夹具24项通过，覆盖主题/四种分辨率、页面上下文、动作、确认/取消/未知结果恢复；真实写入被拦截。
- 真实模型五场景通过：页面解释、单一事件筛选候选、事件变更候选、专业问题交接、提示注入拒绝。另以真实浏览器执行事件筛选成功；证据分别位于logs/assistant-verification/migration-scenarios/api-only和browser-only。
- 真实并行验证通过：同客户端ID的专业请求和侧栏请求均200且执行时间重叠；专业请求只做身份问答，没有发起重业务分析。Barrier/Event测试另证明专业主锁被占用时侧栏仍可完成。
- 真实模型连续12轮及刷新后第13轮通过，无页面错误；最终协议归一化后再次回归。原8000/8642已重启加载修改，5173与InfluxDB继续使用原服务，事件写入开关保持关闭。
- 框架说明提到的scripts/run_tests.sh在本机副本不存在，使用项目虚拟环境pytest与隔离测试目录替代；未运行上游Hermes全量测试。

边界：专业页面内部多个专业会话仍使用原有串行锁，本次实现的是专业入口与侧栏并行，以及侧栏不同会话间的受限并行。修改Skill后需重启现有Agent服务加载。未进行真实事件/配置写入，未增加新的审计界面；运行阶段以脱敏任务日志追踪。

按用户要求，保留原目录与codex/hermes-phase1-hardening分支及既有未提交改动；不提交、合并、推送或创建worktree。

## 1. 固化迁移契约

Files：新增 `tests/assistant/test_master_skill_bridge.py`、`tests/system/test_system_interaction_turn.py`；读取 `scripts/start_agent.py`、`backend/models/assistant.py`。

- [ ] 写失败测试：保留公共request/response结构；代理调用的是8642而非模型地址；内部模式由专用路由确定，客户端无法传tools、skill_path或mode。
- [ ] 写失败测试：专业主锁已占用时侧栏仍完成；同侧栏会话重入409；侧栏容量已满409；Agent未初始化503。
- [ ] 契约示例（fixture替换真实HTTP）：

```python
payload = {'query': '解释当前页面', 'session_id': 'same',
           'context': {'pageId': 'dashboard'}, 'history': []}
response = client.post('/api/assistant/respond', json=payload)
assert response.status_code == 200
assert captured_url.endswith('/system-assistant/respond')
assert separate_model_client_count == 0
```

- [ ] 执行 `ecological_env/Scripts/python.exe -m pytest tests/assistant/test_master_skill_bridge.py tests/system/test_system_interaction_turn.py -q`，确认断言因迁移未实现而失败，不接受导入或fixture错误作为RED。

## 2. 单一Skill与协议组件

Files：新增 `skills/system-interaction-core/SKILL.md`、`shared/assistant/protocol.py`、`shared/assistant/__init__.py`；修改 `skills/action-command-core/SKILL.md`、`workspace/AGENTS.md`；测试 `tests/assistant/test_assistant.py`。

- [ ] 先补页面帮助、缺参数询问、专业任务handoff、纯文本无动作、非法动作拒绝的失败回归。
- [ ] 把现有SCHEMAS、validate_actions、parse_model_answer迁入protocol，保持字段及限制不变；原服务临时重导出，避免先破坏已验证调用方。代码只做移动，不重新实现解析规则。
- [ ] 新Skill逐项说明当前已有能力及参数：navigate、dashboard.view/range/detect、metrics.filter、events.filter/detail、audit.focus、graph.focus、logs.filter、strategy.draft、event.propose。声明仅候选、非已执行。
- [ ] 页面帮助资料迁入Skill；候选schema由代码注入，不在Skill复制一份枚举清单。
- [ ] workspace路由优先处理受信任的system-interaction模式；普通专业请求仍用orchestrator-core。旧action-command-core仅保留协议兼容入口及已有检测脚本说明，通用动作规则指向新Skill。
- [ ] 执行 `ecological_env/Scripts/python.exe -m pytest tests/assistant -q`，校验兼容性及非法动作拒绝。

## 3. 主智能体会话级隔离实例与并行执行

Files：新增 `shared/assistant/master_turn.py`；修改 `scripts/start_agent.py`；测试 `tests/system/test_system_interaction_turn.py`。禁止修改全局registry权限来控制单次请求。

- [ ] 用fake agent和Barrier/Event先覆盖专业锁被占时侧栏仍完成、两会话重叠、同ID隔离、同会话忙碌、容量满、异常和超时隔离失败用例。
- [ ] 新增专用同步路由 `/system-assistant/respond`，请求沿用RespondRequest；复用主智能体类、身份、配置解析及统一实例工厂，建立有界侧栏会话缓存和独立执行槽，不复用专业对象或锁。
- [ ] 服务端构造命名空间任务ID，专业/query与/query/stream拒绝保留前缀。侧栏history不写入专业session_histories，不调用_fresh_session_dir。
- [ ] 服务初始化时从受信任路径预加载Skill，创建侧栏实例时设置ephemeral_system_prompt，运行run_conversation时显式传入独立conversation_history和命名空间task_id；每会话独立实例，工厂固定workspace身份和受限模式，不另建身份文件。
- [ ] 使用受限运行上下文临时屏蔽所有工具schema，并在真实工具分发入口阻断全部工具调用；测试即使模型伪造call_subagent、run_detector和MCP名字也不会触达handler。核对 `_invoke_tool` 与批量分发路径均受约束。
- [ ] 每实例独立会话字段；最大迭代2、墙钟60秒；关闭或隔离持久记忆/recall/hooks。超时工作线程退出前占用原槽和会话锁，不复用实例；空闲淘汰不得销毁活跃会话。
- [ ] 加入以下断言再运行目标测试：

```python
assert master.calls[0]['task_id'] == 'system-assistant:same'
assert professional_histories == histories_before
assert handler_calls == []
assert master.tools == tools_before
assert runtime_instance is not professional_instance
```

- [ ] 执行 `ecological_env/Scripts/python.exe -m pytest tests/system/test_system_interaction_turn.py tests/system/test_stream_lifecycle.py tests/system/test_stream_proxy.py -q`。同时测试正常专业轮次仍可调用原编排工具。

## 4. 切换代理并删除独立模型通道

Files：修改 `backend/services/assistant_service.py`、`backend/api/routes/assistant.py`、`tests/assistant/test_master_skill_bridge.py`、`tests/assistant/test_assistant.py`；必要时修改 `frontend/src/stores/assistant.ts`及其测试。

- [ ] RED覆盖内部409/502/503/504透传、连接失败503、响应schema错误502、无自动模型fallback、无自动确认写入。
- [ ] respond只向现有Agent服务URL追加 `/system-assistant/respond` 发请求；复用项目Agent服务地址配置，连接与总超时明确区分。
- [ ] 删除该服务直接解析provider、拼接chat/completions及独立system提示词的代码。固定帮助也由Skill处理，禁止保留一条静默旧路径。
- [ ] 保留解析函数重导出兼容已有测试；现有模型夹具测试改为验证新主运行层的provider共享，而非继续测试被删除的独立请求。
- [ ] 前端409保持原问题并显示忙碌可重试；后端错误detail继续展示。其余UI、接口和动作执行器不做重构。
- [ ] 执行 `ecological_env/Scripts/python.exe -m pytest tests/assistant tests/events -q`；`npm test -- --reporter=dot`及 `npm run type-check`，记录实际数量，不能以旧基线代替新鲜结果。

## 5. 整体验证与交付

Files：更新 `scripts/verify_assistant_live.py`、`scripts/verify_global_assistant_ui.py`及本计划执行记录。

- [ ] 代码复核：Skill强制载入、工具真正拒绝、实例会话隔离和有界回收、超时隔离、命名空间、旧通道彻底移除。
- [ ] 有针对性地重启现有8642和8000，不启动额外服务；确认5173/8000/8642/8086健康。
- [ ] 运行 `ecological_env/Scripts/python.exe scripts/verify_assistant_live.py`，真实模型至少12轮加刷新恢复；增加跨侧栏和主AI相同ID隔离验证。
- [ ] 使用Barrier/Event并行fixture证明专业任务等待期间侧栏仍能结束，不用真实业务研判制造副作用；另测侧栏容量和同会话忙碌提示。
- [ ] 运行 `ecological_env/Scripts/python.exe scripts/verify_global_assistant_ui.py`，真实业务写入全部由fixture拦截。保持原有确认/取消/未知结果恢复及四分辨率主题验证。
- [ ] 执行 `npm run build`和修改范围 `git diff --check`，记录警告而非隐瞒。
- [ ] 通过进程/端口只读对照及源码检查，证明没有新增进程且8000不再直连模型；记录真实模型与fixture覆盖边界。
- [ ] 在对话中交付修改摘要、已测数量、同会话与容量限制、不同入口并行；保留当前分支及用户全部原有变更，不提交/合并/推送。
