# 智能体配置中心设计（/agents/config 重建）

> 日期：2026-08-27
> 状态：设计已与用户逐项确认
> 前置：现 /agents/config 仅静态展示硬编码 JSON（/query/capabilities），与真实配置完全脱节

## 1. 目标

把 /agents/config 从"静态展示页"升级为**智能体配置中心**：在线管理智能体的身份、厂区接入、运行参数与服务生命周期。配置真相源不变（文件仍是文件），管理入口搬到网页。

**四大能力（用户确认全上）**：

| # | 能力 | 真相源 | 生效时机 |
|---|---|---|---|
| 1 | 身份文件编辑（主 7 + 子各 3） | workspace/*.md、subagents/*/SOUL/AGENTS/MEMORY.md | 立即（下次会话加载） |
| 2 | 厂区配置（层级/报表映射/别名） | shared/data/plant-hierarchy.yaml + plant_aliases 段 | 立即（读取方实时读） |
| 3 | 运行参数 + LLM 切换 | SQLite `agent_runtime_params` 表 | 分参数标注（立即/需重启） |
| 4 | agent 服务重启 | 后端托管（kill 8642 → detached 新进程） | 即时 |

## 2. 信息架构（左实体右内容）

```
/agents/config
├─ 左栏：实体树
│   ├─ 🧠 主智能体
│   ├─ 📊 多维数据感知
│   ├─ 🔍 异常检测
│   ├─ ⚖️ 规则推理
│   └─ 🚨 研判预警与处置
└─ 右侧内容区（按选中实体）
    ├─ Tab1 概览（角色/位置/身份文件清单/技能清单——真实读取）
    ├─ Tab2 身份文件（列表→编辑器：textarea+diff预览+保存git快照+历史回滚）
    ├─ Tab3 技能（只读 SKILL.md 内容展示，与身份文件同编辑器但默认只读）
    └─ Tab4 运行参数（主智能体专属：参数表+LLM配置+测试连接+重启按钮）
        厂区配置为独立入口（左栏底部"⚙ 厂区配置"），不挂在实体下
```

## 3. 后端设计

### 3.1 新增路由 `backend/api/v1/agents/config/routes.py`

**身份文件（8 个接口理念，合并为 5 个）**：

```
GET  /api/v1/agents/config/entities
     → 实体清单（主+4子）：name/label/icon/identity_files[]/skills[]/location
GET  /api/v1/agents/config/files?entity=master&file=SOUL.md
     → {path, content, size, mtime}（路径白名单校验，防穿越）
PUT  /api/v1/agents/config/files   body: {entity, file, content, message?}
     → 校验→写文件→git add+commit（自动快照）→返回 {commit}
GET  /api/v1/agents/config/files/history?entity=master&file=SOUL.md
     → git log 该文件最近 20 条：[{commit, date, author, message, short_diff}]
POST /api/v1/agents/config/files/revert   body: {entity, file, commit}
     → git checkout <commit> -- <file> → 返回恢复后内容
```

**厂区配置**：

```
GET  /api/v1/agents/config/plants          → yaml 全量（层级+report_name_map+plant_configs+plant_aliases）
PUT  /api/v1/agents/config/plants          → 校验（厂名与 InfluxDB plant_id 对齐提示）→ 原子写（tmp+rename）→ git 快照
POST /api/v1/agents/config/plants/validate → 不落盘，仅校验（别名重复/层级引用不存在的厂/格式）
```

**运行参数**：

```
GET  /api/v1/agents/config/params          → 全部参数+当前值+默认值+生效说明
PUT  /api/v1/agents/config/params          body: {key: value, ...} 批量更新
POST /api/v1/agents/config/llm/test        body: {base_url?, model?, api_key?}
     → 发最小 chat 请求（1 token）测连通，返回 {ok, latency_ms, error?}
```

**服务管理**：

```
POST /api/v1/agents/config/service/restart → kill 占 8642 端口进程 → detached 启动新 agent
     → {ok, old_pid, new_pid}
GET  /api/v1/agents/config/service/status  → agent 存活 + 版本 + 启动时间
```

### 3.2 参数注册表（核心设计）

`backend/services/agent_params.py` 定义**参数目录**——每参数含 key/默认值/读取方/生效级别：

| key | 默认 | 读取方 | 生效 |
|---|---|---|---|
| `hermes_total_timeout` | 300 | start_agent.py | 需重启 |
| `subagent_timeout` | 600 | call_subagent.py | 需重启（subprocess 读） |
| `agent_timeout` | 300 | backend→agent HTTP | 立即（每请求读） |
| `master_max_iterations` | 15 | start_agent.py | 需重启 |
| `subagent_max_iterations` | 8 | subagent_entry.py | 需重启 |
| `llm_base_url` / `llm_model` / `llm_api_key` | env | start_agent + entry | 需重启 |

读取方改造：`os.getenv` 处包一层 `get_param(key)`——DB 有值用 DB，否则 env/代码默认。密钥类参数 GET 时脱敏（`sk-***abcd`），PUT 明文写入。

**SQLite 表**（复用现有 SQLAlchemy 基类）：

```python
class AgentRuntimeParam(Base):
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)          # 字符串存储，读取方按类型转
    updated_at: Mapped[datetime]
```

### 3.3 agent 服务重启（后端托管）

Windows 下三步（backend/api/v1/agents/config/service_control.py）：

1. `psutil`（或 netstat 解析）找占 8642 的 PID → `terminate()`，等 5s 兜底 `kill()`
2. `subprocess.Popen([venv_python, "scripts/start_agent.py"], creationflags=DETACHED_PROCESS|CREATE_NEW_CONSOLE, cwd=项目根, env=带 .env 变量)`——独立控制台窗口，日志仍可见
3. 轮询 `/health` 最多 60s，成功返回 new_pid + 健康确认

**安全**：重启接口加简单确认机制（body 带 `confirm: true` 才执行）；backend 自身绝不被此接口 kill。

### 3.4 git 快照策略

- 只 `git add` 被编辑的目标文件（身份文件/yaml），**绝不碰工作区其他未提交改动**
- commit message 格式：`config(web): {entity}/{file} — {用户填的message或"在线编辑"}`
- 回滚 = `git checkout <commit> -- <path>`，同样只动这一个文件
- git 不可用（如 .git 损坏）时降级为时间戳 .bak 备份（同目录 backups/，保最近 10 份）

### 3.5 路径白名单（安全边界）

实体→可编辑文件集合**服务端硬编码白名单**：

```python
ENTITY_FILES = {
  "master": ["IDENTITY.md","SOUL.md","AGENTS.md","MEMORY.md","USER.md","TOOLS.md","HEARTBEAT.md"],
  "multi-dimensional-data-perception": ["SOUL.md","AGENTS.md","MEMORY.md"],
  ... 4 个子智能体
}
# + 各实体 skills/*/SKILL.md（只读展示，可解锁编辑）
```

任何 entity/file 参数不在白名单 → 400。杜绝 `../../.env` 穿越读密钥。

## 4. 前端设计（AgentConfigView 重写）

```
src/views/AgentConfigView.vue        ← 骨架：左树+右内容+路由 tab
src/api/modules/agentConfig.ts       ← 新 API 模块
src/components/agents/config/
  ├─ EntityTree.vue        左栏实体树（复用 PlantTree 交互模式）
  ├─ EntityOverview.vue    概览 tab：身份文件卡+技能卡（真实清单）
  ├─ IdentityFileEditor.vue 编辑器：文件列表+textarea(等宽)+diff预览+保存/回滚
  ├─ ParamsPanel.vue       参数表+LLM卡（测试连接+脱敏显示）
  ├─ PlantsConfigPanel.vue 厂区配置：层级树编辑+别名表+报表映射表
  └─ ServiceControl.vue    重启按钮+状态+确认弹窗
```

**交互要点**：
- 编辑器保存流程：改内容 → 点保存 → 出 diff 弹窗（红删绿增）→ 确认 → git 快照 → toast 提示 commit hash
- 未保存切换文件/实体时拦截提示
- 参数改动按生效级别分组显示；"需重启"参数保存后顶部黄条提示 + 一键重启入口
- LLM api_key 输入框 password 型，已存值显示 `sk-***尾4位`，留空=不修改
- 厂区配置 yaml 用结构化表单（不是裸 yaml 编辑）：层级树增删、每厂卡片（display_name/type/limits/aliases）
- 主题沿用现有浅色 admin 风格（var(--card-bg) 等既有 token）

## 5. 错误处理

| 场景 | 处理 |
|---|---|
| git 不可用/仓库损坏 | 降级 .bak 备份，UI 标注"快照降级" |
| 保存身份文件时磁盘满/权限 | 原子写（tmp+rename）失败返回 500，原文件不动 |
| 重启时 kill 失败（权限） | 返回 {ok:false, error}，不启动新进程（避免双实例） |
| 新 agent 启动后 health 失败 | 返回 ok:true 但 warn 提示 + 新窗口日志位置指引 |
| LLM 测试连接超时 | 10s 超时返回 {ok:false, error:"timeout"} |
| 参数值非法（超时负数等） | PUT 前 schema 校验，400 带字段级错误 |
| 白名单外路径 | 400 "不允许的文件" |
| DB 不可用 | 参数读取走 env 兜底（get_param 不抛错），配置页参数区显示"DB 不可用" |

## 6. 测试

- **单测**：agent_params（get_param DB优先/env兜底/类型转换）、路径白名单校验、yaml 原子写
- **集成**：身份文件 PUT→文件变+git log 多一条→revert 回旧内容；参数 PUT→start_agent 侧 get_param 读到
- **E2E（Playwright，复用现有栈）**：进入页面→编辑 MEMORY.md 加一行→保存→git log 出现快照→回滚→内容还原；参数改 agent_timeout→显示"立即生效"；LLM 测试连接（对 ctgu-vlm 真 http）
- **手工验收**：改 SOUL.md 里的语气描述→在 /chat 新会话问"你是谁"→回答风格变化（身份立即生效验证）

## 7. 兼容与迁移

- 旧 `/query/capabilities` 与 AgentConfigView 的静态展示**保留不动**（其他地方可能引用），新页面完全替换视图层
- `_PLANT_ALIASES`（subagent_entry.py）改为：先读 plant-hierarchy.yaml 的 `plant_aliases` 段，无该段时用内置默认（现有两厂）——**向后兼容，yaml 优先**
- report_name_map 已在 yaml，页面只是暴露读写
- DB 迁移：init_db 加 AgentRuntimeParam 表（create_all 自动建）

## 8. 交付批次

虽四能力一批上，但实现顺序（每步可独立验证）：
1. 后端：参数注册表+DB 表+get_param+读取方接线（4 处 os.getenv 改造）
2. 后端：身份文件读写+git 快照+历史+回滚（含白名单）
3. 后端：厂区配置读写+校验+yaml 原子写
4. 后端：LLM 测试连接+服务重启
5. 前端：骨架+实体树+概览
6. 前端：身份文件编辑器（diff+回滚）
7. 前端：参数面板+LLM+服务控制
8. 前端：厂区配置面板
9. E2E + 手工验收（含 /chat 身份生效验证）
