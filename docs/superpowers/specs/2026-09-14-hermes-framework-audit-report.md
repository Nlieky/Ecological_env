# Hermes Agent 框架评估报告

- 日期：2026-09-14 ｜ 评估基线 commit：`b0db9af4ef8377d32f9e7db6fa8e11794fda384a`（内容见 0.5 节）
- 设计文档：docs/superpowers/specs/2026-09-14-hermes-framework-audit-design.md
- 严重度图例：🔴 阻塞（正确性/可用性风险）｜🟡 应修（质量/维护风险）｜🟢 建议

## 0. 执行摘要（最后写）

## 0.5 基线事实

评估启动时钉死的事实，后续各节结论均以此为基准。核心证据已随报告入库：`docs/superpowers/specs/2026-09-14-hermes-audit-evidence/`（baseline-commit.txt、upstream-version.txt、dir-relation.txt）；大体积产物（baseline-status.txt、framework-py-manifest.txt）留存在本机 `/tmp/hermes-audit/`。

### 0.5.1 基线快照

- 基线 commit：`b0db9af4`（`git rev-parse HEAD`）。注：计划探索时记录的 `609a867` 在当前仓库中不存在（`git cat-file -t 609a867` 无此对象，历史可能已改写）；以实际 HEAD 为准。
- 工作区状态：存在大量未提交改动（frontend/node_modules、subagents/、workspace/、CHANGELOG.md、CLAUDE.md 等），完整快照见 baseline-status.txt。评估全程只读，不触碰这些改动。
- `shared/framework` 下 Python 文件清单：**626 个**（framework-py-manifest.txt）。

### 0.5.2 三目录关系（证据：dir-relation.txt，命令输出 + 逐文件 diff）

| 目录 | 角色 | 证据 |
|---|---|---|
| `shared/framework/hermes-agent/` | 上游仓库根的 vendored 完整副本 | 含 pyproject.toml、Dockerfile、flake.nix、uv.lock、gateway/、plugins/ 等，顶层条目共 **51** 个（`ls … \| wc -l`，dir-relation.txt 补证段）；无 `.git` 元数据；入库提交 `f446f413`（完整 subject："chore: 把 vendored hermes 框架纳入仓库(部署需要)"） |
| `shared/framework/hermes_agent/`（下划线） | 从上游抽取的**精简包副本**，仅 7 个 .py：`__init__.py`、`run_agent.py`、`utils.py`、`agent/{__init__,agent_init,process_bootstrap,identity_loader}.py` | `find` 输出；`__init__.py` 自述"从 https://github.com/NousResearch/hermes-agent 复制并修改，修改内容：扩展身份文件读取支持" |
| `shared/framework/hermes-overlays/` | 覆盖层：`run_agent.py`、`agent/agent_init.py`（与下划线副本逐字节一致）+ 独有 `tools/orchestrator_tool.py`（废水监测主智能体的子智能体调用工具，文件头注释） | `find` + `diff` 输出 |

关键细节：

1. **上、下划线目录不是整体镜像**：上游目录内部无 `hermes_agent/` 包（`ls -d .../hermes-agent/hermes_agent` → 无）；下划线包是「上游顶层 `run_agent.py`、`utils.py` + `agent/` 子集」的部分拷贝，目的应是使其可作为 `hermes_agent` Python 包导入（`process_bootstrap.py` 中出现 `from shared.framework.hermes_agent.utils import ...` 的 fallback 导入）。
2. **逐字节一致**（副本 vs 上游）：`run_agent.py`、`agent/agent_init.py`（cmp 比对 exit 0，dir-relation.txt 补证段）、`agent/__init__.py`（diff 无输出）。即 `run_agent.py` 与 `agent_init.py` 各自在三处（上游目录、`hermes_agent/`、`hermes-overlays/`）存有完全相同的拷贝。
3. **本地改动**（副本 vs 上游 diff）：
   - `utils.py`：3 处差异，副本为 `os.sync(f.fileno())`，上游为 `os.fsync(f.fileno())`（行 134/192/259）。语义影响留待 L2 审计判定。
   - `agent/process_bootstrap.py`：副本的 import 增加 try/except fallback（失败时改从 `shared.framework.hermes_agent.utils` 导入）。
   - `agent/identity_loader.py`：**本地新增**，上游无此文件（即 `__init__.py` 所述"扩展身份文件读取支持"）。

### 0.5.3 上游版本（证据：upstream-version.txt）

- **版本：hermes-agent 0.16.0**，作者 Nous Research。来源：`shared/framework/hermes-agent/pyproject.toml`（`name = "hermes-agent"` / `version = "0.16.0"`），与 `hermes_agent.egg-info/PKG-INFO`（Name/Version/Author）互相佐证。
- 局限：上游目录无 `.git` 元数据、无 CHANGELOG.md，故无法核对 0.16.0 对应的上游 commit 或本地是否在上游之上有过改动；该问题留待 L2 改装审计处理。

### 0.5.4 对设计文档 §1.1 的修正

基线 diff 实证推翻了设计文档「1.1 已确认的事实基础（探索阶段结论）」中的两处结论，后续章节以本节为准（Task 2+ 执行者请勿再按设计文档原文理解）：

1. **「改装集中在 overlays 层且规模重大」不成立**（设计 §1.1 事实表第 2 行）：`hermes-overlays/run_agent.py`（5358 行）与 `hermes-overlays/agent/agent_init.py`（1763 行）与上游对应文件逐字节一致（cmp exit 0，见 0.5.2），是上游文件的原样拷贝而非改装产物；overlays 中真正的本地文件只有 `tools/orchestrator_tool.py`（193 行）。实际的本地改动位于 `hermes_agent/` 包副本内：`utils.py`（3 处 os.sync/os.fsync 差异）、`agent/process_bootstrap.py`（fallback import）、`agent/identity_loader.py`（本地新增）。L2 检查项 2.1 的审计对象需据此重新聚焦。
2. **「hermes-agent/ 626 个 py」计数归属有误**（设计 §1.1 事实表第 1 行）：626 是整个 `shared/framework/` 的 .py 总数；拆分为 `hermes-agent/` 615、`hermes_agent/` 7、`hermes-overlays/` 3、`shared/framework/__init__.py` 1（合计 626，framework-py-manifest.txt 按前缀计数）。检查项 1.3 的覆盖率测算应按此口径分列。

## 1. L1 活链路追踪（真实架构）

<!-- 覆盖设计文档 §3 L1 检查项 1.1–1.5（1.2 overlay 生效机制须先行钉死；1.3 覆盖率按 0.5.4 修正口径分列） -->

核心证据随报告入库：`docs/superpowers/specs/2026-09-14-hermes-audit-evidence/l1-runtime-findspec.txt`（venv 内 15 条 import 解析实证）、`l1-untouched-strict.txt`（严格未触达清单）。大体积产物（touched-all.txt 451 行、pyc-evidence.txt、untouched.txt）在本机 `/tmp/hermes-audit/`。

### 1.1 入口链：活入口是 start_agent.py，不是（只是）backend/services/agent_service.py

设计假设「唯一活入口 = backend/services/agent_service.py」**部分不成立**：存在两条并行入口，import 目标相同，但当前活链路走 HTTP 转发那条。

**活链路（用户查询的真实路径）**：

```
前端 → backend/api/routes/query.py POST /api/query（backend/main.py:122 挂载，uvicorn :8000，scripts/start_backend.sh:6）
     → HTTP requests.post（query.py:77-84）→ AGENT_SERVICE_URL=http://localhost:8642（backend/core/config.py:28）
     → scripts/start_agent.py（uvicorn :8642，start_agent.py:376/508-515）
     → start_agent.py:38  from shared.framework.hermes_agent.run_agent import AIAgent
```

- query.py:1-5 docstring 自述「重构后：通过HTTP请求转发到Agent服务(localhost:8642)，不再直接创建AIAgent实例」；:46 给出架构「FastAPI → HTTP转发 → Agent服务 → AIAgent(主智能体)」。服务不可用时直接 503（:67-74）。流式端点 /query/stream（路由 :236）经 httpx.AsyncClient 流式转发（import :11，调用 :258-262）。
- scripts/start_agent.py（523 行）自带独立的 `AgentService` 类（:64，**与 backend/services/agent_service.py 同名不同类**）：master_agent 单例 + threading.Lock 串行化（:87-91），initialize() 创建 AIAgent（:97-103，identity_path="workspace"，max_iterations=15 :106-108），会话缓存/查询缓存/跨轮 session 目录续传（:72-84）。

**并行入口（进程内，当前非主路径）**：backend/services/agent_service.py（207 行，全读，/tmp/hermes-audit/agent_service.numbered）：

- import：`from shared.framework.hermes_agent.run_agent import AIAgent`（:13，try/except，失败 fallback 裸 `from run_agent import AIAgent` :20，再失败 AIAgent=None :22）；`from backend.models.query import QueryResponse`（:24）。
- 暴露：类 `AgentService`（:30），方法 `get_agent`（:71，env 读 LLM_* 默认值 :95-98，实例缓存）与 `process_query`（:129，调 `agent.run_conversation(user_message, conversation_history=None)` :163）。
- 全同步（无 async）；错误处理：导入期 try/except 降级（:12-22），查询期 broad except 记日志后 re-raise（:203-207）。
- 引用方仅两处：backend/services/__init__.py:3（re-export）与 backend/main.py:181-183（**启动自检**：实例化一次打日志，不接任何路由）。query.py 不 import 它——活查询流量不经过此文件。

**子智能体入口（第三条，同款 import）**：skills/orchestrator-core/scripts/subagent_entry.py:38 `from shared.framework.hermes_agent.run_agent import AIAgent`（「与主智能体同款路径」，:33 注释）。

三条入口的 import 字符串完全一致 ⇒ 1.2 的 overlay 结论对全链路统一成立。

### 1.2 overlay 生效机制：venv 可编辑安装把裸 import 钉到 vendored 树，overlays 目录运行时零参与

**一句话结论：运行时是「精简包 run_agent（全限定名）+ vendored hermes-agent 全家桶（裸顶层名，经 venv 可编辑安装）」的混合体；hermes-overlays/ 从不被 import——它是构建期覆盖源，由 scripts/vendor_hermes.py 拷进 vendored 树。**

机制三件套（证据链）：

1. **全限定 import 无歧义**：`shared.framework.hermes_agent.run_agent` 经 `shared/framework/__init__.py`（纯 docstring，无 sys.path 操作）作普通包解析到精简包副本。venv 实证（l1-runtime-findspec.txt）：`shared.framework.hermes_agent.run_agent → shared/framework/hermes_agent/run_agent.py`。
2. **裸 import 经可编辑安装落到 vendored 树**：run_agent.py 内部全是上游风格的裸顶层 import（:65 `from hermes_constants import…`、:98 `from agent.process_bootstrap import…`、:123 `from model_tools import…`、:129-131 `from tools.… import…`）。venv = `/home/NYJ2025/Ecological_env/ecological_env`（Python 3.12.12，sys.executable 实测值已入 l1-runtime-findspec.txt）；启动脚本用裸 `python`（`start_agent.py` shebang `#!/usr/bin/env python`、`start_backend.sh` `python -m uvicorn`），实际解析到哪个解释器取决于 PATH 激活——本节全部结论以该 venv 为前提。其 site-packages 存在 `__editable__.hermes_agent-0.16.0.pth` + finder，`dist-info/direct_url.json` = `file:///home/NYJ2025/Ecological_env/shared/framework/hermes-agent`（editable）。find_spec 实证（Python 模块解析探针，importlib.util.find_spec，只查加载路径不执行模块代码）：`agent`、`agent.process_bootstrap`、`tools.registry`、`model_tools`、`hermes_constants`、`utils`、`hermes_cli`、裸 `run_agent` **全部解析到 `shared/framework/hermes-agent/`**；裸 `hermes_agent` 反而 NONE（不可导入）。
3. **overlays 是构建期机制**：scripts/vendor_hermes.py:62-78 `apply_overlays()` 把 `hermes-overlays/` 全部文件按相对路径 copy2 进 `hermes-agent/`（DST，:18），再打两个文本 patch（:83-111：model_metadata OpenRouter 超时 10→1；system_prompt 注入身份文件加载块）。目录名带连字符 ⇒ Python 语法上不可能被 import；全仓 grep 无任何 sys.path 注入/importlib 加载指向它。

**逐文件裁决（md5 + find_spec + pyc 三重证据）**：

| 文件 | 三份拷贝关系 | 运行时生效者 | 判定 |
|---|---|---|---|
| `run_agent.py` | 三份逐字节一致（md5 3fb3838d…：hermes_agent/ = hermes-overlays/ = hermes-agent/） | `hermes_agent/run_agent.py`（全限定名加载） | ✅活；因逐字节一致，「谁生效」对本文件无差别 |
| `agent/agent_init.py` | 三份一致（8db8566c…） | `hermes_agent/agent/agent_init.py`（run_agent.py:416 懒加载 `from shared.framework.hermes_agent.agent.agent_init import init_agent`） | ✅活；vendored 的 agent_init.py 反而是严格未触达（无 pyc、无 import 边） |
| `agent/identity_loader.py` | 仅精简包有（本地新增） | `hermes_agent/agent/identity_loader.py`（agent_init.py:1747 引用 + vendored system_prompt.py:112 的 vendor-patch 反向引用） | ✅活——精简包存在的核心理由 |
| `utils.py` | 精简包≠vendored（os.sync×3 vs os.fsync，0.5.2） | **vendored 副本**（裸 `utils` → hermes-agent/utils.py） | 🔴 **精简包的 os.sync 改动是运行时死代码**（该文件无 pyc、无任何全限定 import 引用） |
| `agent/process_bootstrap.py` | 精简包≠vendored（fallback import，0.5.2） | **vendored 副本**（裸 `agent.process_bootstrap` → hermes-agent/） | 🔴 精简包的 fallback 改动同样死代码（vendored 版 :31 只有裸 `from utils import…`，且裸 utils 永远可导入成功，fallback 永不触发） |
| `hermes-overlays/`（3 文件） | — | 无人 import、无 pyc | 构建期源，运行时零参与 |

**对 0.5.4 结论的再修正**：0.5.4 把 L2 审计对象重聚焦到 `hermes_agent/` 副本的三个本地改动；本节实证其中 **只有 identity_loader.py 在活链路上**，utils.py 与 process_bootstrap.py 两处改动运行时不可达（修复它们的正确姿势是重跑 vendor 或改 overlays+patch，而不是改精简包——L2/L4 采纳）。

**已发生的构建期漂移（无运行时影响但须记录）**：`overlays/tools/orchestrator_tool.py` 的 PROJECT_ROOT 用 `parents[4]` 相对推导（:13），vendored 副本仍硬编码 `Path("E:/project/Ecological_env")`（Windows 路径，diff 唯一差异行）⇒ overlays 修正后**未重跑 vendor_hermes.py**。漂移之所以无害：tool_registration.py:279-283 判定 vendored 自带 orchestrator_tool 为「多处损坏的桥接」，用 override=True 以本项目 handler 覆盖（见 1.5），两份 orchestrator_tool 均不在调度路径上。

### 1.3 触达清单数据（静态 import 闭包 + pyc 运行时证据）

方法：从 4 个入口 import 语句作种子（start_agent.py:38、subagent_entry.py:38、agent_service.py:13、tool_registration.py:283；含并行入口 agent_service.py——其模块级 import 于 backend 启动时执行，只是不接查询流量），按与运行时一致的解析规则（1.2 三件套；顶层名清单取自 vendored `hermes_agent.egg-info/top_level.txt`；含缩进的懒加载 import）BFS 求传递闭包（从入口 import 逐层展开到不再新增文件）；运行时证据取 `find shared/framework -name "*.pyc"`（cpython-312，与 venv 3.12.12 一致）。

| 口径 | hermes-agent/（615） | hermes_agent/（7） | hermes-overlays/（3） | 合计（626） |
|---|---|---|---|---|
| 静态 import 闭包 | 448（72.8%） | 3（42.9%：run_agent、agent_init、identity_loader） | 0 | **451（72.0%）** |
| pyc 编译证据（至少被加载过一次） | 382（含闭包外 100 个动态加载，其中 plugins/ 系 79 个经插件扫描动态 import，静态 regex 不可见） | 5（含闭包外 2 个 `__init__.py`） | 0 | 388（另含 shared/framework/__init__.py，父包加载证据） |
| 闭包 ∪ pyc | 548 | 5 | 0 | **554（88.5%）** |
| 严格未触达（无静态边且无 pyc） | 67 | **2（utils.py、process_bootstrap.py）** | **3（全部）** | **72** |

注意事项：

- 闭包内 166 个文件无 pyc（hermes-agent 侧；hermes_cli 系占 67）：静态可达但从未真正执行——try/except 可选依赖（bedrock/gemini 等适配器）或从未走到的懒加载分支。**静态闭包是「静态可见 import 集」的上界、必经集的近似上界（未排除动态必经加载，精确界由 §4 E1 判定）**；pyc 是历史执行证据（含冒烟/手工运行），两者都不是「单次 /api/query 必经集合」。另：闭包按 import 语句追踪，不含父包 `__init__.py`（如 shared/framework/__init__.py 有 pyc 无静态边），故并集口径略偏低估。
- pyc ∖ 闭包 = 103 个，证明存在静态 grep 不可见的动态加载（插件扫描为主）。口径辨析：554/626=88.5% 是「**非死重量**（静态可达 ∪ 历史执行）」口径的下界；若按「执行覆盖」口径，下界是 388/626=62.0%（仅有历史执行证据者）。
- 数据落盘：/tmp/hermes-audit/{touched-l1,touched-all,untouched,untouched-strict,pyc-evidence}.txt + 构建脚本 build_touched.py；严格未触达 72 个见 l1-untouched-strict.txt（附录 A 素材）。

### 1.4 配置与 LLM 端点事实

| 配置源 | 活链路是否读取 | 证据 | 要点 |
|---|---|---|---|
| `.env`（项目根） | ✅ **唯一真源** | start_agent.py:29 load_dotenv → :95-97 os.getenv；call_subagent.py:260-267 透传子进程（含 OPENAI_API_KEY/OPENAI_BASE_URL 映射） | `LLM_BASE_URL=http://172.16.12.41:30000/v1`（.env:9）、`LLM_MODEL=ctgu-vlm`（:11）、`LLM_API_KEY`=<已脱敏>（:10）、`HERMES_TOTAL_TIMEOUT=300`（:33） |
| `$HERMES_HOME/config.yaml`（hermes 自身配置） | ❌ 文件不存在 | hermes_constants.py:423-428（config 路径=HERMES_HOME/config.yaml）+ start_agent.py:33（HERMES_HOME=项目根）+ `ls config.yaml`→无 | hermes 的 yaml 配置整体缺席，框架参数全靠 env 与构造参数 |
| `.hermes/config.yaml` | ❌ 不存在 | `wc -c` 无输出 | — |
| `workspace/config.yaml` | ❌ 非活链路（陈旧） | 内容为 LongCat-2.0 @ api.longcat.chat（旧端点）；HERMES_HOME 指向项目根而非 workspace；AIAgent 的 base_url/model 由构造参数显式传入（start_agent.py:97-103） | 遗留文件，若哪天有人「按注释」把 HERMES_HOME 指回 workspace 会引入错误端点——🟡 建议清理（L3） |
| `shared/configs/llm_config.yaml` | ❌ 零读取 | grep backend/ scripts/ skills/ subagents/ framework 无命中 | 端点描述与 .env 一致，纯文档性质 |
| `backend/core/config.py` | ✅ 仅 backend 侧 | :28 AGENT_SERVICE_URL、:30 AGENT_TIMEOUT=600 | 不含 LLM 密钥 |

**LLM 端点事实**：全链路（主+4 子智能体）唯一活端点 = **`http://172.16.12.41:30000/v1`，模型 `ctgu-vlm`**（内网 vLLM，OpenAI 兼容）；OpenAI SDK 经 process_bootstrap 懒加载（`from openai import OpenAI`，_load_openai_cls）。`.env` 同时保留 LongCat 注释行（:14）为备用端点说明，未启用。

### 1.5 子智能体注册与调用机制（谁把 4 个子智能体变成框架可调用的）

注册主体 = `skills/orchestrator-core/scripts/tool_registration.py`（446 行），由 start_agent.py:113-119 在 master_agent 初始化后经 `importlib.util.spec_from_file_location` 按文件路径加载并调用 `register_orchestrator_tools(agent)`（失败仅告警不阻断，:121-127）。两层注册（:214-283，注释自证 2026-07-21 端到端验证）：

1. **schema 层**：把 4 个工具 schema（call_subagent / list_subagents / create_session / read_result，:231-258）灌进 `agent.tools`——conversation_loop 只读 agent.tools 喂给 LLM；同时裁剪工具表，仅保留编排 4 件套 + skill_view/skills_list（:265-272），砍掉 terminal/browser 等分心工具。
2. **registry 层**：handler 以 `override=True` 注册进 hermes 全局 `tools.registry`（:283 `from tools.registry import registry` → vendored 树），取代 vendored 自带且被判定损坏的 tools/orchestrator_tool.py（:279-283）。dispatch 走全局 registry，故覆盖必须发生在这里。

调用链（LLM 决策 → 子智能体结果回传）：

```
主智能体 LLM 决策调 call_subagent（enum 限定 4 个子智能体名，tool_registration.py:242）
→ _call_subagent_handler → orchestrator_core_bridge.py（importlib 桥接，解决目录名连字符不可 import）
→ call_subagent.py:291-296  subprocess.run([sys.executable, subagent_entry.py], env=LLM_*/OPENAI_* 透传（:260-267）+PYTHONPATH=项目根, cwd=subagents/<x>, timeout=600)
→ subagent_entry.py:38  AIAgent（= 又一个完整 hermes 会话：HERMES_HOME=subagents/<x>、max_iterations=6、toolsets=[skills,terminal]，:174-177）
→ 子智能体 LLM 经 skill_view 读自己的技能 → terminal 跑 canonical 脚本 → 结果 JSON 落 SESSION_DIR
→ read_result 读文件 / _compact_result_for_master 紧凑摘要回主智能体（铁律「LLM 绝不读原始数据」，:138-141）
```

- 4 个子智能体映射：`SUBAGENT_PATHS`（call_subagent.py:26-36）：multi-dimensional-data-perception / anomaly-detection / rule-reasoning / disposition-execution → `subagents/<名>-agent/`（目录实存，各含 SOUL.md/AGENTS.md/MEMORY.md/skills/，ls 实证）。
- 进度流：tool_registration 模块级 `_current_progress_queue`（:46，`_emit_progress` :49 起）由 start_agent 的 /query/stream 注入（:117-118 保留模块引用），子智能体各阶段事件（evidence/chartData）实时推给前端。
- 观测性：子智能体 subprocess 全量 stdout/stderr 落盘 `sessions/_subagent_traces/`（call_subagent.py:304-310）。

### 1.6 真实运行时架构图

```mermaid
flowchart TD
    FE["前端 frontend/"] -->|"POST /api/query"| Q["backend/api/routes/query.py:46<br/>(uvicorn :8000, scripts/start_backend.sh:6)"]
    Q -->|"HTTP requests.post query.py:77-84<br/>AGENT_SERVICE_URL=localhost:8642 (config.py:28)"| SA["scripts/start_agent.py :8642<br/>AgentService 单例+线程锁 (:64,:355)"]
    SA -->|"全限定 import :38"| RA["shared/framework/hermes_agent/run_agent.py<br/>(AIAgent 入口, 精简包)"]
    RA -->|"懒加载 :416 全限定"| AI["hermes_agent/agent/agent_init.py"]
    AI --> IDL["hermes_agent/agent/identity_loader.py<br/>(本地新增, 精简包唯一活改动)"]
    RA -->|"裸 import :65-183<br/>agent.* / tools.* / model_tools /<br/>hermes_constants / hermes_cli.* / utils"| VEND["shared/framework/hermes-agent/ (vendored 0.16.0, 615 py)<br/>经 venv __editable__.hermes_agent-0.16.0.pth 生效"]
    VEND -->|"system_prompt.py:112<br/>vendor-patch 反向引用"| IDL
    SA -->|"importlib 加载 :114-119"| TR["skills/orchestrator-core/scripts/tool_registration.py<br/>两层注册: agent.tools + registry.override"]
    TR -->|"from tools.registry :283"| VEND
    TR --> BR["orchestrator_core_bridge.py → call_subagent.py"]
    BR -->|"subprocess :291-296<br/>env LLM_*/OPENAI_* 透传"| SUB["subagents/×4-agent<br/>(HERMES_HOME=各自目录)"]
    SUB -->|"subagent_entry.py:38 同款全限定 import"| RA
    SA -.->|"workspace/ 身份文件<br/>identity_path= :101"| WS["workspace/ (7 身份文件)"]
    RA -->|"OpenAI 兼容<br/>process_bootstrap 懒加载 openai"| LLM["LLM 端点: http://172.16.12.41:30000/v1<br/>模型 ctgu-vlm (.env:9-11, 唯一真源)"]
    SUB --> LLM
    OV["shared/framework/hermes-overlays/ (3 py)<br/>构建期覆盖源, 运行时零 import"] -.->|"vendor_hermes.py:62-78<br/>构建期拷入(当前已漂移)"| VEND
    AGS["backend/services/agent_service.py<br/>(并行进程内入口, 仅 main.py:181 启动自检引用)"] -.->|"同款 import :13"| RA
    SUBDB["InfluxDB :8086 monitoring-data<br/>(backend/core/config.py:47-52)"] -.->|"数据感知子智能体 get_data.py 拉取"| SUB
```

要点：框架代码实际由两个目录共同构成（精简包 3 个活文件 + vendored 448 个静态可达文件（∪ 历史执行 548））；「身份文件→system_prompt 注入」是精简包与 vendored 树之间唯一的反向依赖（system_prompt.py:112）。

### 1.7 与专利六层架构的映射/偏差（对照仓库根 CLAUDE.md）

| 专利层 | CLAUDE.md 描述 | 实测（L1） | 判定 |
|---|---|---|---|
| 1 人机交互层 | middleware/ Flask :5000 + Grafana | 活交互 = frontend/ + backend/ FastAPI :8000（main.py:121-126）；`middleware/` 目录**不存在**（全仓 find 仅 backend/middleware/logging_middleware.py，FastAPI 日志中间件，与 Flask 无关） | ❌ 偏差（CLAUDE.md 描述的旧链路整体已删） |
| 2 数据采集层 | stream/dual_data_stream.py 推流模拟 | `stream/` 不存在；活数据源 = InfluxDB localhost:8086 bucket monitoring-data（config.py:47-52），由数据感知子智能体拉取（subagents/…/get_data.py 引用 influxdb） | ❌ 偏差（推流→拉取，双流向单源） |
| 3 主智能体层 | workspace/ 身份文件（IDENTITY/SOUL/AGENTS/MEMORY/USER/TOOLS/HEARTBEAT） | workspace/ 7 个身份文件全部实存且被活链路加载：AIAgent(identity_path="workspace", load_soul_identity=True)（start_agent.py:101-102）→ agent_init → identity_loader；backend 侧另有 _check_identity_files 自检（agent_service.py:46-69） | ✅ 对应（载体从「编排脚本读」换为 hermes AIAgent 读，文件集合不变） |
| 4 任务编排层 | workspace/skills/orchestrator-core/scripts/（task_receiving_and_parsing / execution_control / result_interpretation，~12 次 LLM 调用） | 活编排 = **根目录 skills/**/orchestrator-core（tool_registration + call_subagent + subagent_entry），编排主体是 hermes 主智能体 LLM 决策；CLAUDE.md 所指 workspace/skills/orchestrator-core/scripts/ 仍存在（dynamic_orchestrator/execution_control/resource_matching/task_structuring）但**无任何活代码引用**（直接引用仅 tests/：verify_architecture.py、test_four_layer_architecture.py、integration/test_orchestrator_integration.py；另 skills/ 活副本内 subagent_tools.py:29 有一条 try 链 fallback import，详查归 3.5 盘点）；「~12 次调用」口径对应旧套件，新链路 LLM 调用次数更多（主智能体多轮 + 每子智能体一次完整 AIAgent 会话），量化归 §4 | ⚠️ 偏差（位置 + 机制双变；旧套件成死代码） |
| 5 子智能体层 | subagents/ 4 个专业智能体，各自身份文件+脚本 | 4 个目录实存（含 SOUL/AGENTS/MEMORY + skills/<core>/scripts），enum 硬编码于 call_subagent schema（tool_registration.py:242）；驱动方式从「本地 coordinator 调脚本」变为「每个子智能体=一次完整 hermes AIAgent 会话（subagent_entry.py）」 | ✅ 对应（驱动载体换为 hermes 子进程） |
| 6 数据支撑层 | shared/（data、models、configs、knowledge、operators） | shared/data、knowledge、operators 实存（是否仍被子智能体脚本消费未逐条核证，归 3.2/3.3 待证）；但 `shared/configs/llm_client.py` 不存在（CLAUDE.md 的 LLM 客户端封装已删），配置真源移至 .env（1.4）；framework/ 新增三大目录（0.5.2）不在 CLAUDE.md 描述内 | ⚠️ 偏差（部分失活 + 未收录新增） |

**总判定**：六层中的 3、5 两层在活链路上成立（载体换成 hermes）；1、2 两层的 CLAUDE.md 实现已整体不存在（❌）；4 迁移且留死代码；6 部分失活+未收录新增（⚠️）。CLAUDE.md 本身已落后真实架构一个代差，应随 L4 裁决一并重写（P1 候选）。

## 2. L2 改装审计

<!-- 覆盖设计文档 §3 L2 检查项 2.1–2.6（注意 0.5.4 修正：改装点在 hermes_agent/ 副本而非 overlays，2.1 审计对象据此重聚焦） -->

## 3. L3 项目适配审计

<!-- 覆盖设计文档 §3 L3 检查项 3.1–3.5 -->

## 4. LLM 调用实证

<!-- 覆盖设计文档 §3 E 最小实证 E1–E4（E1 计数 wrapper 仅注入 /tmp；E4 降级时本节须显著标注「未实证」）；对照 CLAUDE.md「~12 次调用/流程」口径 -->

## 5. L4 双路线裁决书

<!-- 覆盖设计文档 §3 L4 检查项 4.1–4.4（4.4 终审三选一，不许和稀泥；含过渡步骤与被裁一方处置） -->

## 6. 路线图 P0/P1/P2

<!-- 覆盖设计文档 §4 输出物「路线图」（P0 立即修/P1 短期/P2 方向性演进，P2 含借鉴 pi-subagents、OpenClaw 的具体机制清单）+ 验收标准 §7-4（P0 项可直接转化为后续修复任务） -->

## 附录 A. 触达/未触达文件清单

## 附录 B. 实证原始数据
