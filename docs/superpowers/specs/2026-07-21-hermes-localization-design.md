# Hermes 框架整体本地化（vendor）设计

> 状态：设计待评审
> 日期：2026-07-21
> 范围：智能体"架构乱/脆弱"工作流（工作流①）。工作流②（子智能体执行可靠性）、③（可观测性）见末尾"非目标"，后续独立 spec。

## 1. 背景：为什么要做

调研发现智能体"架构乱/脆弱"的根因是 **hermes 框架两份副本 + 运行时混血**：

- `hermes-agent` 0.16.0 以 **editable 安装**（`__editable__.hermes_agent-0.16.0.pth` + finder）指向 **`D:\Hermes\hermes-agent\`**。venv 里所有顶级导入 `agent.*`、`tools.*`、`model_tools`、`providers` 等都解析到 D:\Hermes。
- 项目内的"优化版" `shared/framework/hermes_agent/`（下划线）是**不完整副本**：只有 `run_agent.py`、`utils.py`、`hermes_constants.py`、`__init__.py` 和 `agent/` 的 **8/89** 个文件，**没有 `tools/`**。
- `start_agent.py` 显式 `from shared.framework.hermes_agent.run_agent import AIAgent` 拿到优化版 run_agent；但 run_agent 内部 `from agent.conversation_loop import run_conversation` 跳回 D:\Hermes（editable）。

**实测结论（缝合怪）**：
- `AIAgent`（run_agent.py）→ shared/framework（优化版，5358 行，仅比 D:\Hermes 多 14 行）✅
- `agent.conversation_loop`（真正在跑的循环）→ **D:\Hermes**（原版）❌
- `tools.*`（33 个工具 + 签名错误的 `orchestrator_tool.py`）→ **D:\Hermes** ❌

后果：
1. 对 `shared/framework/hermes_agent/agent/` 的优化**根本没生效**（跑的是 D:\Hermes 的）。
2. D:\Hermes 的 `tools/orchestrator_tool.py` 的 handler 签名 bug（`**kwargs` vs dispatch 的 `handler(args, **kwargs)`）一直在捣乱，迫使项目用 `register_orchestrator_tools` 的 override 补丁对抗。
3. 行为难预测（hybrid）→ "不可信"；优化没生效 → "不可观测"；两份副本 → "架构乱"。

## 2. 目标 / 非目标

**目标**
- 项目内**一份完整、canonical 的 hermes**，editable 安装指向它，`D:\Hermes` 彻底退役。
- 现有优化（run_agent.py +14 行、agent/ 8 文件）fold 进 vendored 副本。
- 拆除 `register_orchestrator_tools` 的 override 补丁；`orchestrator_tool.py` 在本地直接修签名。
- vendored 树 **gitignore**（轻），用 **vendor 脚本 + 补丁**（进 git）保证可复现。

**非目标（本 spec 不做，后续独立 spec）**
- 工作流②：子智能体执行可靠性（超时/迭代限制/SKILL.md 合规/结构化输出强校验）。
- 工作流③：可观测性（把 call_subagent 的执行记进 `SubAgentExecutionLog`，让 trace/审计页可见）。

## 3. 方案：整体 vendor + 重指安装

### 3.1 目录结构
- 新位置：`shared/framework/hermes-agent/`（连字符，匹配 hermes 自身包布局）。
- 旧 `shared/framework/hermes_agent/`（下划线、部分副本）合并后删除。
- vendored 树整体 `.gitignore`；vendor 脚本 + 补丁文件进 git。

### 3.2 拷贝范围（运行时 Python，排除非运行时）
**拷**：`agent/`(89)、`tools/`(83)、`model_tools.py`、`providers/`、`plugins/`、`gateway/`、`hermes_cli/`、`acp_adapter/`、`acp_registry/`、`hermes_bootstrap.py`、`hermes_state.py`、`hermes_logging.py`、`hermes_time.py`、`hermes_constants.py`、`pyproject.toml`，以及 run_agent.py 实际 import 到的其它顶级模块（实现时按导入闭包核定）。

**排除**：`docs/ tests/ web/ website/ ui-tui/ tui_gateway/ node_modules/ venv/ locales/ docker/ packaging/ assets/ infographic/ datagen-config-examples/ optional-mcps/ optional-skills/ apps/ scripts/ plans/ __pycache__/ *.egg-info`。

### 3.3 vendor 脚本 + 补丁（进 git）
- `scripts/vendor_hermes.py`（或 `.sh`）：
  1. 参数：`--src`（默认 `D:\Hermes\hermes-agent`，可配）、`--dst=shared/framework/hermes-agent`。
  2. 按白名单拷运行时目录/文件，按黑名单排除。
  3. 应用补丁：`shared/framework/hermes-agent/patches/*.patch`。
- 补丁文件（git 内，小而可 review）：
  - `run_agent.patch`：那 14 行优化 diff。
  - `agent/*.patch`：8 个 agent 文件的定制 diff（实现时逐个 diff vs D:\Hermes 生成；纯拷贝无定制的免补丁）。
  - `orchestrator_tool.patch`：4 个 handler 签名修正（`def _x_handler(**kwargs)` → `def _x_handler(args=None, **kwargs)`，从 `args or kwargs` 取参）。

> 复现方式：新机器 `python scripts/vendor_hermes.py --src <本地hermes源>` → `pip install -e shared/framework/hermes-agent`。

### 3.4 fold 现有优化
- run_agent.py：5358 vs 5348 行，仅 14 行 diff → 直接应用 `run_agent.patch`。
- agent/ 8 文件：逐个 `diff` vs D:\Hermes；有定制 → 生成 `.patch`；纯拷贝 → vendored 副本已含，免补丁。

### 3.5 重指 editable 安装
```
pip uninstall -y hermes-agent
pip install -e shared/framework/hermes-agent
```
- 验证：`python -c "import tools.registry, agent.conversation_loop; print(tools.registry.__file__, agent.conversation_loop.__file__)"` → 两个都指向 `shared/framework/hermes-agent/...`。
- 验证：`sys.path` 无 `D:\Hermes`；启动日志不再加载 `D:\Hermes\.env`。

### 3.6 orchestrator 整合（本地化后）
- `orchestrator_tool.py` 现在在项目内 → `orchestrator_tool.patch` 直接修 4 个 handler 签名（dispatch 的 `handler(args, **kwargs)` 能正确传入）。
- `workspace/skills/orchestrator-core/scripts/tool_registration.py`：**移除** override 注册块（不再需要对抗 D:\Hermes）；保留"把 4 个 schema 灌进 `agent.tools`"的逻辑（让 LLM 看见工具）。
- 验证 call_subagent 端到端：`/api/query` → LLM 调 call_subagent → 子智能体 entry.py → 结构化结果回流，无 "takes 0 positional arguments"。

### 3.7 清理
- 用户删 `D:\Hermes`（或保留作源，但 sys.path 不再依赖它）。
- 删旧 `shared/framework/hermes_agent/`（下划线部分副本）。
- 更新 `CLAUDE.md` / 相关文档：hermes 位置改为 `shared/framework/hermes-agent`（vendor），复现用 vendor 脚本。

## 4. 验收标准
- [ ] `import tools.registry`、`agent.conversation_loop`、`run_agent` 全解析到 `shared/framework/hermes-agent/`。
- [ ] agent 服务启动正常，`sys.path` 无 `D:\Hermes`，启动日志不再加载 `D:\Hermes\.env`。
- [ ] `/api/query` 触发的 call_subagent → 子智能体 → 结构化结果回流，无签名错误、无 override 补丁。
- [ ] `register_orchestrator_tools` 不再含 override 块；`orchestrator_tool.py` handler 签名正确。
- [ ] vendor 脚本可从源重新生成 vendored 树 + 应用补丁；vendored 树被 gitignore。
- [ ] 删掉 D:\Hermes 后系统仍正常运行。

## 5. 风险与对策
- **拷贝量大**（几百文件）：机械拷贝，脚本化；gitignore 避免 repo 膨胀。
- **导入闭包漏项**（少拷一个包 → import error）：以 run_agent/agent/tools/model_tools 的 `from X import` 为起点核定白名单；验证步骤抓 import error，缺啥补啥。
- **editable 重指失败**（pyproject 路径假设）：用 hermes 自带 pyproject.toml；若其有绝对路径/额外依赖，按报错调整。
- **fold 优化遗漏**（14 行 + 8 文件）：补丁从 `diff shared/framework vs D:\Hermes` 精确生成；验证后对比 agent 行为是否与优化意图一致。
- **可复现性**（换机器无 D:\Hermes）：vendor 脚本 `--src` 可指向任意 hermes-agent 0.16.0 源（含 GitHub 下载）；文档说明。

## 6. Self-Review
- 占位符：无 TBD；补丁文件名在实现时按实际 diff 生成（已说明规则）。
- 内部一致：目标/结构/验证/清理相互对齐；vendor 脚本+补丁+gitignore 三者关系自洽。
- 范围：聚焦 localization（工作流①），②③ 明确划为后续独立 spec。
- 歧义："运行时闭包"以实测 import 为准（已给验证方法）。
