# Hermes Agent 框架评估报告

- 日期：2026-09-14 ｜ 评估基线 commit：`b0db9af4ef8377d32f9e7db6fa8e11794fda384a`（内容见 0.5 节）
- 设计文档：docs/superpowers/specs/2026-09-14-hermes-framework-audit-design.md
- 严重度图例：🔴 阻塞（正确性/可用性风险）｜🟡 应修（质量/维护风险）｜🟢 建议

## 0. 执行摘要（最后写）

## 0.5 基线事实

评估启动时钉死的事实，后续各节结论均以此为基准。原始证据存于 `/tmp/hermes-audit/`（baseline-commit.txt、baseline-status.txt、framework-py-manifest.txt、dir-relation.txt、upstream-version.txt）。

### 0.5.1 基线快照

- 基线 commit：`b0db9af4`（`git rev-parse HEAD`）。注：计划探索时记录的 `609a867` 在当前仓库中不存在（`git cat-file -t 609a867` 无此对象，历史可能已改写）；以实际 HEAD 为准。
- 工作区状态：存在大量未提交改动（frontend/node_modules、subagents/、workspace/、CHANGELOG.md、CLAUDE.md 等），完整快照见 baseline-status.txt。评估全程只读，不触碰这些改动。
- `shared/framework` 下 Python 文件清单：**626 个**（framework-py-manifest.txt）。

### 0.5.2 三目录关系（证据：dir-relation.txt，命令输出 + 逐文件 diff）

| 目录 | 角色 | 证据 |
|---|---|---|
| `shared/framework/hermes-agent/` | 上游仓库根的 vendored 完整副本 | 含 pyproject.toml、Dockerfile、flake.nix、uv.lock、gateway/、plugins/ 等 50+ 顶层条目；无 `.git` 元数据；入库提交 `f446f413`（"把 vendored hermes 框架纳入仓库"） |
| `shared/framework/hermes_agent/`（下划线） | 从上游抽取的**精简包副本**，仅 7 个 .py：`__init__.py`、`run_agent.py`、`utils.py`、`agent/{__init__,agent_init,process_bootstrap,identity_loader}.py` | `find` 输出；`__init__.py` 自述"从 https://github.com/NousResearch/hermes-agent 复制并修改，修改内容：扩展身份文件读取支持" |
| `shared/framework/hermes-overlays/` | 覆盖层：`run_agent.py`、`agent/agent_init.py`（与下划线副本逐字节一致）+ 独有 `tools/orchestrator_tool.py`（废水监测主智能体的子智能体调用工具，文件头注释） | `find` + `diff` 输出 |

关键细节：

1. **上、下划线目录不是整体镜像**：上游目录内部无 `hermes_agent/` 包（`ls -d .../hermes-agent/hermes_agent` → 无）；下划线包是「上游顶层 `run_agent.py`、`utils.py` + `agent/` 子集」的部分拷贝，目的应是使其可作为 `hermes_agent` Python 包导入（`process_bootstrap.py` 中出现 `from shared.framework.hermes_agent.utils import ...` 的 fallback 导入）。
2. **逐字节一致**（副本 vs 上游）：`run_agent.py`、`agent/agent_init.py`、`agent/__init__.py`。`hermes-overlays/` 中的 `run_agent.py`、`agent/agent_init.py` 与下划线副本也逐字节一致（同一文件的第三份拷贝）。
3. **本地改动**（副本 vs 上游 diff）：
   - `utils.py`：3 处差异，副本为 `os.sync(f.fileno())`，上游为 `os.fsync(f.fileno())`（行 134/192/259 附近）。语义影响留待 L2 审计判定。
   - `agent/process_bootstrap.py`：副本的 import 增加 try/except fallback（失败时改从 `shared.framework.hermes_agent.utils` 导入）。
   - `agent/identity_loader.py`：**本地新增**，上游无此文件（即 `__init__.py` 所述"扩展身份文件读取支持"）。

### 0.5.3 上游版本（证据：upstream-version.txt）

- **版本：hermes-agent 0.16.0**，作者 Nous Research。来源：`shared/framework/hermes-agent/pyproject.toml`（`name = "hermes-agent"` / `version = "0.16.0"`），与 `hermes_agent.egg-info/PKG-INFO`（Name/Version/Author）互相佐证。
- 局限：上游目录无 `.git` 元数据、无 CHANGELOG.md，故无法核对 0.16.0 对应的上游 commit 或本地是否在上游之上有过改动；该问题留待 L2 改装审计处理。

## 1. L1 活链路追踪（真实架构）

## 2. L2 改装审计

## 3. L3 项目适配审计

## 4. LLM 调用实证

## 5. L4 双路线裁决书

## 6. 路线图 P0/P1/P2

## 附录 A. 触达/未触达文件清单

## 附录 B. 实证原始数据
