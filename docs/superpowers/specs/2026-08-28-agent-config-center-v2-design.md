# 智能体配置中心 V2 设计（strategy / skills / mcp / providers 四 tab）

> 日期：2026-08-28
> 状态：设计已与用户逐段确认（信息架构/策略/技能/MCP/供应商+错误处理+测试 五段全过）
> 前置：V1 已上线（身份文件/厂区配置/运行参数/服务重启，commit b9501bf~e6bbe08）

## 1. 目标

在 `/agents/config` 现有基础上新增四个能力 tab，把"智能体怎么执行"从代码默认变成页面上可管理：

| tab | 能力 | 一句话 |
|---|---|---|
| strategy | 智能体决策/执行策略 | 编排深度、守卫开关、回答风格、动作通道、默认供应商、运行参数（原 params 并入） |
| skills | 专业方法与工具依赖 | 技能展示/SKILL.md 在线编辑/禁用启用/自定义新建/内置模板库市场 |
| mcp | 外部 MCP 接入 | 管理接入、鉴权、运行边界（写 Hermes 原生 mcp_servers 配置），首批预置 4 个 |
| providers | 模型供应商 | 多 LLM 供应商 CRUD+测试连接，与 strategy 默认供应商联动 |

## 2. 信息架构与导航（用户指定：tab 放顶部导航栏，不放左侧）

```
/agents/config?entity=master&tab=strategy
┌─────────────┬────────────────────────────────────────────┐
│ 左栏（实体）  │ 顶部 tab 导航（?entity=&tab= 同步到 URL）    │
│             │ [概览] [身份文件] [技能] [策略] [MCP] [供应商]  │
│ 🧠 主智能体  │────────────────────────────────────────────│
│ 📊 数据感知  │                                            │
│ 🔍 异常检测  │            内容区（entity+tab 渲染）          │
│ ⚖️ 规则推理  │                                            │
│ 🚨 处置执行  │  · 概览/身份文件/技能/策略 → 每实体都有        │
│ ─────────   │  · MCP/供应商 → 仅主智能体（全局能力）         │
│ ⚙ 厂区配置  │  · 子智能体选中时 MCP/供应商 tab 置灰带提示    │
│ 🔄 服务管理  │                                            │
└─────────────┴────────────────────────────────────────────┘
```

**变更**：tab 从 `overview/files/params` 扩为六个；`params` 并入 `strategy`；tab 状态写 URL query（刷新/分享不丢）。现有身份文件编辑器/厂区/服务管理组件原样保留。

## 3. 策略 tab（strategy）

**存储**：SQLite 新表 `agent_strategy`（key/value/updated_at），复用 V1 参数中心模式（DB 优先→内置默认，effect 分类标注生效时机）。注册表 `STRATEGY_REGISTRY`：

| 组 | key | 类型 | 生效 |
|---|---|---|---|
| 编排深度 | `orchestration_stop_level`（①数据停/②异常停/③违规停/④处置） | enum | 立即 |
| 守卫与自愈 | `perception_guard_enabled` / `perception_heal_enabled` | bool | 立即 |
| 回答风格 | `language_constraint`（中文）/ `conclusion_first` / `confidence_labeling` | bool/enum | 立即 |
| 动作通道 | `action_guide_text` / `action_shortcircuit_timeout` / `action_inject_view_context` | str/int/bool | 文案立即，超时需重启 |
| 默认供应商 | `default_llm_provider`（引用 providers.name，仅 tested_ok 可选） | ref | 需重启 |
| 运行参数 | V1 的 8 个参数原样迁入展示 | int/str | 原标注 |

**UI**：按组分卡片，每项带说明+生效徽标（绿立即/黄需重启），bool 开关/enum 下拉/文案 textarea，按组独立保存，保存后汇总提示+一键重启入口。

**接线点**：
- `tool_registration.py`：`_guard_perception_result` 入口读 `perception_guard_enabled`，False 跳过
- `subagent_entry.py`：`_heal_perception_by_script` 入口读 `perception_heal_enabled`
- `start_agent.py`：LLM 初始化改为——`default_llm_provider` 策略 → providers 表行 → 兜底原 get_param/env 链
- `action_classifier.py`（经 start_agent）：引导语文案/超时/view_context 注入从策略表读
- 回答风格三项拼进 system prompt 构建处（orchestrator-core 加载时读）

## 4. 技能 tab（skills）

**展示**：技能卡片（icon+name+description+脚本数+启用开关+查看）。查看 = SKILL.md 在线编辑（复用身份文件编辑器：git 快照+历史回滚，白名单扩为 `skills/*/SKILL.md` 动态发现）+ scripts/ 文件树只读。

**禁用/启用**：目录改名 `skills/<name>.disabled/`——skill_view 按 `skills/*/SKILL.md` 发现，改名即消失，零框架改动。

**新建**（向导）：选归属（主智能体 skills/ 或子智能体 skills/）→ 填 name/description + 选脚本骨架（空/参数解析模板）→ 落盘 `SKILL.md + scripts/main.py` → git 快照。技能名限 `[a-z0-9-]`。

**市场**（内置模板库，模板真身 `shared/skill_templates/` 随仓库走，只读）：

| 模板 | 归属建议 | 内容 |
|---|---|---|
| 法规查询技能 | 主智能体 | SKILL.md（调 Fetch MCP），无脚本 |
| 报表生成技能 | 处置执行 | SKILL.md + main.py（jinja2 日报/周报） |
| 新监测点接入 | 主智能体 | SKILL.md + main.py（向导式接入） |
| 数据导出技能 | 数据感知 | SKILL.md + main.py（导出 CSV） |
| 知识库检索技能 | 规则推理 | SKILL.md + main.py（grep 知识库返回命中） |
| 自定义空白技能 | 任意 | 纯骨架 |

安装 = 从模板库拷到目标实体 skills/ + git 快照；同名冲突提示不覆盖；删除 = 二次确认 + git 快照。

## 5. MCP tab

**底层**：Hermes 原生 `tools/mcp_tool.py`（stdio/HTTP/SSE、工具发现、注册进工具表），配置 `~/.hermes/config.yaml` 的 `mcp_servers` 段。本系统只做配置管理+边界+测试连接，不写协议代码。

**管理 UI**：接入列表（server 名+transport 徽标+边界摘要+测试状态+启用开关+编辑/删除）；表单按 transport 分字段（stdio: command/args/env；HTTP: url/headers；SSE: url）+ 通用 timeout/connect_timeout + env 脱敏；测试连接 = 后端临时 MCP 客户端握手 + `tools/list` 计数。

**写入**：原子写 config.yaml 的 mcp_servers 段（保留其他段）+ .bak 时间戳备份 + 标注需重启 agent。

**运行边界**：单工具调用 timeout（默认 120s）+ connect_timeout；Filesystem 只开 `shared/knowledge/`（绝不开项目根）；env 鉴权值页面脱敏。

**首批预置 4 个**（一键安装=写配置）：

| MCP | transport | 用途 | 边界 |
|---|---|---|---|
| Fetch | stdio npx | 法规/标准网页抓取 | timeout 60s，无鉴权 |
| InfluxDB | stdio（社区包） | 即席时序查询 | 只读 token，timeout 120s |
| Filesystem | stdio npx | 知识库读写 | 只开 shared/knowledge/ |
| Memory | stdio npx | 知识图谱跨会话记忆 | timeout 60s |

**agent 启用**：主智能体 `enabled_toolsets` 加 `"mcp"`（6→8 工具）；子智能体默认不开（保持 HERMES_HOME 作用域防瞎逛）。

## 6. 供应商 tab（providers）

**表**：`llm_providers`（id/name/base_url/api_key/model/enabled/tested_ok/updated_at）。预置：ctgu-vlm（启用）、LongCat-2.0（禁用）。

**UI**：卡片列表（名称/model/base_url/测试徽标）+ CRUD（api_key password+脱敏回显）+ 测试连接（复用 `/agents/config/llm/test`，按行测，成功回写 tested_ok）。

**strategy 联动**（用户指定流程）：「默认模型供应商」下拉只列 `tested_ok=true`；保存 → 需重启 → start_agent 读取链：策略 `default_llm_provider` → providers 表行 → 兜底 get_param/env。providers 行被删且被引用 → strategy 标红提示重选。

**安全**：GET 脱敏 `sk-***尾4`、PUT 明文、不进 git、前端不缓存明文。

## 7. 错误处理

| 场景 | 处理 |
|---|---|
| 策略 DB 不可用 | 读取方静默走内置默认，strategy 页显示"DB 不可用" |
| 技能名非法/冲突 | 前端 `[a-z0-9-]` 校验 + 后端 400；同名不覆盖 |
| 市场模板缺失 | 列表标灰"模板不存在"；安装先校验后拷贝，失败回滚 |
| config.yaml 写坏 | 原子写 + 写前 .bak；测试连接失败不落盘 |
| MCP 启动失败 | 测试连接返回明确错误；mcp_tool 可选依赖，失败降级不拖垮主智能体 |
| 默认 provider 被删/失效 | start_agent 兜底 get_param 链 + 日志 warning |
| 高危操作（删技能/关守卫） | 二次确认 + git 快照可回滚 |

## 8. 测试

- **单测**：strategy 读写+默认值；providers CRUD+tested_ok 联动；技能白名单动态发现；SKILL.md frontmatter 解析；禁用改名往返；config.yaml mcp_servers 段原子读写（不破坏其他段）
- **集成**：新建技能→skill_view 发现；MCP 测试连接对 Fetch 真握手；provider 测试对 ctgu-vlm 真请求
- **E2E（扩展 scripts/e2e_agent_config.py）**：六 tab URL 同步；策略保存生效标注；新建技能落盘+git 快照；市场安装；provider 测试+设默认；MCP 预置安装；无 JS 错误
- **手工验收**：关守卫→/chat 验证跳过；新建技能→子智能体可见；provider 切换重启后 /health 显示新 model

## 9. 兼容

- V1 四能力（身份文件/厂区/参数/服务）组件与接口原样保留；params tab 并入 strategy 但 `/agents/config/params` 接口保留（向后兼容）
- `llm_*` 三参数保留为兜底链末端；provider 表是新增上游来源
- 子智能体不自动获得 MCP（防瞎逛设计不变）；需要时后续单独开
