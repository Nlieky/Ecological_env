# Hermes 框架整体本地化（vendor）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 D:\Hermes\hermes-agent 整体 vendor 进项目 `shared/framework/hermes-agent/`，editable 安装重指向它，仅 fold 4 个小定制文件 + 本地修 orchestrator_tool 签名，使所有 hermes 导入解析到项目内、退役 D:\Hermes。

**Architecture:** vendor 脚本从源（默认 D:\Hermes\hermes-agent）拷运行时 Python（排除 docs/tests/web/node_modules 等）到 `shared/framework/hermes-agent/`（gitignore），再用 git 内的 `shared/framework/hermes-overlays/`（4 个小定制文件 + 修好的 orchestrator_tool）覆盖。然后 `pip install -e` 重指 editable 安装。子智能体依赖的完整 conversation_loop（含 terminal 工具）保留 D:\Hermes 新版，不覆盖——避免断编排。

**Tech Stack:** Python 3.12（venv `ecological_env`）、pip editable 安装、Git Bash（Windows）。
**分支:** `frontend-refactor`（继续）。
**环境约定:** 命令里 `PY=ecological_env/Scripts/python.exe`；路径用正斜杠；`D:\Hermes\hermes-agent` 在 bash 里是 `/d/Hermes/hermes-agent`。
**验证策略:** 本期为 vendor/基建，无纯逻辑可 TDD；用"导入解析检查 + agent 启动 + /api/query 端到端"作为验证关卡。

---

## File Structure

**新建:**
- `scripts/vendor_hermes.py` — vendor 脚本（拷贝 + 覆盖），可重复运行。
- `shared/framework/hermes-overlays/run_agent.py` — 小定制（+14 行），从旧 `shared/framework/hermes_agent/` 迁入。
- `shared/framework/hermes-overlays/hermes_constants.py` — 小定制（25 行 diff），迁入。
- `shared/framework/hermes-overlays/agent/__init__.py` — 小定制（11 行 diff），迁入。
- `shared/framework/hermes-overlays/agent/agent_init.py` — 小定制（22 行 diff），迁入。
- `shared/framework/hermes-overlays/tools/orchestrator_tool.py` — 签名修正版（新建，覆盖基线以修 handler 签名）。
- `shared/framework/hermes-agent/` — vendored 完整 hermes（**gitignore**，脚本生成）。

**修改:**
- `.gitignore`（加 `shared/framework/hermes-agent/`）
- `workspace/skills/orchestrator-core/scripts/tool_registration.py`（删除 override 注册块）
- `CLAUDE.md`（更新 hermes 位置说明）

**删除:**
- `shared/framework/hermes_agent/`（旧下划线部分副本；小定制已迁入 overlays）

> 关键决策（已与用户确认）：**只 fold 4 个小定制文件**。大差异文件（conversation_loop 4483 行、prompt_builder 3138、utils 752、system_prompt 842、process_bootstrap 338、runtime_cwd 124、identity_loader）**一律用 D:\Hermes 完整新版**——因为 shared/framework 的精简 conversation_loop 对非 orchestrator 工具返回 "not implemented"，会让子智能体丢 terminal 工具、断编排。

---

## Task 1: 建立 overlays 目录（迁入小定制 + 建修正版 orchestrator_tool）

**Files:**
- Create: `shared/framework/hermes-overlays/run_agent.py`
- Create: `shared/framework/hermes-overlays/hermes_constants.py`
- Create: `shared/framework/hermes-overlays/agent/__init__.py`
- Create: `shared/framework/hermes-overlays/agent/agent_init.py`
- Create: `shared/framework/hermes-overlays/tools/orchestrator_tool.py`

- [ ] **Step 1: 迁入 4 个小定制文件**（从旧 shared/framework/hermes_agent/ 拷到 overlays/）

```bash
mkdir -p shared/framework/hermes-overlays/agent shared/framework/hermes-overlays/tools
cp shared/framework/hermes_agent/run_agent.py shared/framework/hermes-overlays/run_agent.py
cp shared/framework/hermes_agent/hermes_constants.py shared/framework/hermes-overlays/hermes_constants.py
cp shared/framework/hermes_agent/agent/__init__.py shared/framework/hermes-overlays/agent/__init__.py
cp shared/framework/hermes_agent/agent/agent_init.py shared/framework/hermes-overlays/agent/agent_init.py
```

- [ ] **Step 2: 建修正版 orchestrator_tool.py**（拷 D:\Hermes 基线 + 改 4 个 handler 签名）

```bash
cp /d/Hermes/hermes-agent/tools/orchestrator_tool.py shared/framework/hermes-overlays/tools/orchestrator_tool.py
```

然后编辑 `shared/framework/hermes-overlays/tools/orchestrator_tool.py`，把 4 个 handler 的签名从 `(**kwargs)` 改成 `(args=None, **kwargs)` 并从 `args or kwargs` 取参。逐一替换：

`_call_subagent_handler`：
```python
# 旧
def _call_subagent_handler(**kwargs):
    """延迟调用 call_subagent"""
    call_subagent_fn, _, _, _ = _get_subagent_tools()
    result = call_subagent_fn(
        kwargs.get("subagent_name"),
        kwargs.get("task"),
        kwargs.get("context")
    )
    return {"result": result}
```
```python
# 新
def _call_subagent_handler(args=None, **kwargs):
    """延迟调用 call_subagent（hermes dispatch 把工具参数 dict 作第 1 个位置参数传入）"""
    a = args or kwargs or {}
    call_subagent_fn, _, _, _ = _get_subagent_tools()
    result = call_subagent_fn(a.get("subagent_name"), a.get("task"), a.get("context"))
    return {"result": result}
```

`_create_session_handler`：
```python
# 旧
def _create_session_handler(**kwargs):
    """延迟调用 create_session"""
    _, create_session_fn, _, _ = _get_subagent_tools()
    session_id = create_session_fn()
    return {"result": {"session_id": session_id}}
```
```python
# 新
def _create_session_handler(args=None, **kwargs):
    """延迟调用 create_session"""
    _, create_session_fn, _, _ = _get_subagent_tools()
    session_id = create_session_fn()
    return {"result": {"session_id": session_id}}
```

`_list_subagents_handler`：
```python
# 旧
def _list_subagents_handler(**kwargs):
    """延迟调用 list_subagents"""
    _, _, list_subagents_fn, _ = _get_subagent_tools()
    return {"result": list_subagents_fn()}
```
```python
# 新
def _list_subagents_handler(args=None, **kwargs):
    """延迟调用 list_subagents"""
    _, _, list_subagents_fn, _ = _get_subagent_tools()
    return {"result": list_subagents_fn()}
```

`_read_result_handler`：
```python
# 旧
def _read_result_handler(**kwargs):
    """延迟调用 read_result"""
    _, _, _, read_result_fn = _get_subagent_tools()
    return {"result": read_result_fn(kwargs.get("result_file"))}
```
```python
# 新
def _read_result_handler(args=None, **kwargs):
    """延迟调用 read_result"""
    a = args or kwargs or {}
    _, _, _, read_result_fn = _get_subagent_tools()
    return {"result": read_result_fn(a.get("result_file"))}
```

- [ ] **Step 3: 校验 overlays 编译**

```bash
PY=ecological_env/Scripts/python.exe
for f in shared/framework/hermes-overlays/run_agent.py shared/framework/hermes-overlays/hermes_constants.py shared/framework/hermes-overlays/agent/__init__.py shared/framework/hermes-overlays/agent/agent_init.py shared/framework/hermes-overlays/tools/orchestrator_tool.py; do $PY -m py_compile "$f" && echo "OK $f"; done
```
Expected: 5 个 `OK`。

- [ ] **Step 4: Commit**

```bash
git add shared/framework/hermes-overlays
git commit -m "feat: hermes overlays (4 small customizations + fixed orchestrator_tool signatures)"
```

---

## Task 2: 写 vendor 脚本

**Files:**
- Create: `scripts/vendor_hermes.py`

- [ ] **Step 1: 写 `scripts/vendor_hermes.py`**

```python
#!/usr/bin/env python3
"""把 hermes-agent 运行时 vendor 进项目 shared/framework/hermes-agent/。

用法:
    python scripts/vendor_hermes.py [--src D:\\Hermes\\hermes-agent]

步骤:
1. 从 src 拷运行时 Python 到 dst（排除 docs/tests/web/node_modules 等非运行时）。
2. 用 shared/framework/hermes-overlays/ 里的文件覆盖（小定制 + 修正版 orchestrator_tool）。

dst 整体被 .gitignore；本脚本 + overlays 进 git，保证可复现。
"""
import argparse
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DST = REPO / "shared" / "framework" / "hermes-agent"
OVERLAYS = REPO / "shared" / "framework" / "hermes-overlays"

# 非运行时目录/文件（拷贝时排除）
EXCLUDE_DIRS = {
    "docs", "tests", "web", "website", "ui-tui", "tui_gateway", "node_modules",
    "venv", "locales", "docker", "packaging", "assets", "infographic",
    "datagen-config-examples", "optional-mcps", "optional-skills", "apps",
    "scripts", "plans", "__pycache__", ".git", ".github",
}
EXCLUDE_SUFFIXES = (".egg-info",)
EXCLUDE_FILES = {".gitignore", ".gitattributes"}


def _ignore(directory, names):
    ignored = set()
    for n in names:
        p = Path(directory) / n
        if n in EXCLUDE_DIRS:
            ignored.add(n)
        elif p.is_dir() and any(n.endswith(s) for s in EXCLUDE_SUFFIXES):
            ignored.add(n)
        elif n in EXCLUDE_FILES:
            ignored.add(n)
        elif n.endswith(".pyc"):
            ignored.add(n)
    return ignored


def copy_runtime(src: Path) -> None:
    if DST.exists():
        shutil.rmtree(DST)
    print(f"[vendor] copying {src} -> {DST}")
    shutil.copytree(src, DST, ignore=_ignore, dirs_exist_ok=False)
    print(f"[vendor] copied runtime (excluded: {len(EXCLUDE_DIRS)} dir patterns)")


def apply_overlays() -> int:
    if not OVERLAYS.exists():
        print("[vendor] no overlays dir; skipping")
        return 0
    n = 0
    for p in OVERLAYS.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(OVERLAYS)
        target = DST / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
        n += 1
        print(f"[vendor] overlay: {rel}")
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=r"D:\Hermes\hermes-agent", help="hermes-agent 源目录")
    args = ap.parse_args()
    src = Path(args.src)
    if not src.exists():
        raise SystemExit(f"source not found: {src}")
    copy_runtime(src)
    n = apply_overlays()
    print(f"[vendor] done. overlays applied: {n}. vendored at {DST}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 校验脚本语法**

```bash
ecological_env/Scripts/python.exe -m py_compile scripts/vendor_hermes.py && echo "OK"
```
Expected: `OK`。

- [ ] **Step 3: Commit**

```bash
git add scripts/vendor_hermes.py
git commit -m "feat: vendor_hermes.py (copy runtime + apply overlays, reproducible)"
```

---

## Task 3: gitignore vendored 树 + 运行 vendor

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: gitignore vendored 树**

在 `.gitignore` 末尾追加：
```
# vendored hermes（脚本生成，不入库；用 scripts/vendor_hermes.py 复现）
shared/framework/hermes-agent/
```

- [ ] **Step 2: 运行 vendor**

```bash
ecological_env/Scripts/python.exe scripts/vendor_hermes.py --src /d/Hermes/hermes-agent
```
Expected: 打印 `copying ... -> shared/framework/hermes-agent`、若干 `overlay:` 行、`done`。

- [ ] **Step 3: 确认 vendored 树关键目录在**

```bash
ls -d shared/framework/hermes-agent/agent shared/framework/hermes-agent/tools shared/framework/hermes-agent/providers 2>&1
ls shared/framework/hermes-agent/agent/*.py | wc -l
ls shared/framework/hermes-agent/tools/*.py | wc -l
```
Expected: agent/tools/providers 都存在；agent ~89 个 .py；tools ~83 个 .py。
> 若缺关键目录（如 providers/plugins）：它们被 EXCLUDE 误删了？检查 EXCLUDE_DIRS，移除误判项，重跑 Step 2。

- [ ] **Step 4: 确认 gitignore 生效（vendored 不进 git）**

```bash
git status --short shared/framework/hermes-agent | head
```
Expected: 空（被 gitignore）。overlays + vendor 脚本已在前两 Task 提交。

- [ ] **Step 5: Commit .gitignore**

```bash
git add .gitignore
git commit -m "chore: gitignore vendored hermes tree"
```

---

## Task 4: 重指 editable 安装 + 验证导入本地化

**Files:** （无文件改动；venv 安装重指）

- [ ] **Step 1: 卸载旧 editable 安装（指向 D:\Hermes 的）**

```bash
ecological_env/Scripts/python.exe -m pip uninstall -y hermes-agent
```
Expected: `Successfully uninstalled hermes-agent-0.16.0`。

- [ ] **Step 2: 从项目内 vendored 树重装（editable）**

```bash
ecological_env/Scripts/python.exe -m pip install -e shared/framework/hermes-agent
```
Expected: `Successfully installed hermes-agent-0.16.0`（editable，指向 `shared/framework/hermes-agent`）。
> 若报 pyproject/build 错（如缺 build 后端、路径假设）：查看 `shared/framework/hermes-agent/pyproject.toml` 的 build-system + packages；按报错最小调整（如补 `--no-build-isolation` 或修 packages 列表）。改动若有，回填 overlays/vendor 流程或单独提交。

- [ ] **Step 3: 验证导入全部解析到项目内**

```bash
ecological_env/Scripts/python.exe -c "
import tools.registry, agent.conversation_loop
from shared.framework.hermes_agent.run_agent import AIAgent  # 旧路径应仍可导入(下划线副本还在)
import run_agent
print('tools.registry ->', tools.registry.__file__)
print('agent.conversation_loop ->', agent.conversation_loop.__file__)
print('run_agent ->', run_agent.__file__)
"
```
Expected: 三个路径都含 `shared/framework/hermes-agent`，**不含 `D:\Hermes`**。
> 若某导入报 ModuleNotFoundError（vendored 缺该包）：该包被 EXCLUDE 误删或源里本就缺。补到 EXCLUDE 排除项之外（若是运行时依赖），或确认源路径正确，重跑 Task 3 Step 2 + 本 Step。

- [ ] **Step 4: 验证 sys.path 无 D:\Hermes**

```bash
ecological_env/Scripts/python.exe -c "import sys; print([p for p in sys.path if 'Hermes' in p or 'hermes' in p])"
```
Expected: 只剩 `shared/framework/hermes-agent` 相关条目（editable finder 指向它），无 `D:\Hermes`。

> 本 Task 无代码提交（仅 venv 状态变化）。

---

## Task 5: 简化 tool_registration.py（拆 override 补丁）

**Files:**
- Modify: `workspace/skills/orchestrator-core/scripts/tool_registration.py`

> 背景：orchestrator_tool.py 现在 vendored 在本地、签名已修（Task 1 的 overlay），hermes dispatch 能正确调到它。不再需要项目侧的 override 注册块对抗 D:\Hermes。保留"把 4 个 schema 灌进 agent.tools"（让 LLM 看见工具）的逻辑。

- [ ] **Step 1: 删除 override 注册块**

在 `register_orchestrator_tools` 中，删除从 `# 覆盖注册到 hermes 全局 registry` 注释起到该 try/except 结束的整块（即 `_hg.register(... override=True ...)` 那段）。**保留**前面"把 _ORCH_SCHEMAS 灌进 agent.tools"的循环。

删除的块（整段移除）：
```python
    # 覆盖注册到 hermes 全局 registry（修正 hermes 自带 tools/orchestrator_tool.py 的 handler 签名 bug）。
    # ...（整段 try/except，含 _hg.register(... override=True ...)）
```

- [ ] **Step 2: 校验编译 + 导入**

```bash
ecological_env/Scripts/python.exe -m py_compile workspace/skills/orchestrator-core/scripts/tool_registration.py && echo "compile OK"
```
Expected: `compile OK`。

- [ ] **Step 3: Commit**

```bash
git add workspace/skills/orchestrator-core/scripts/tool_registration.py
git commit -m "refactor: remove orchestrator override hack (hermes now vendored+fixed locally)"
```

---

## Task 6: 端到端验证（agent 启动 + /api/query → 子智能体）

**Files:** （无）

- [ ] **Step 1: 重启 agent 服务（拾取 vendored hermes）**

```bash
# 杀旧 8642
netstat -ano | grep -E "LISTENING" | grep -E ":8642 " | awk '{print $5}' | sort -u | while read pid; do taskkill //PID $pid //F; done
sleep 2
# 重启
ecological_env/Scripts/python.exe scripts/start_agent.py  # 后台跑
```

- [ ] **Step 2: 等 + 查启动日志**

```bash
sleep 12
curl -s -m 5 http://localhost:8642/health   # Expected: {"status":"healthy","agent_initialized":true}
```
确认日志含 `✅ Orchestrator工具注册成功`，且**不再加载 `D:\Hermes\.env`**（grep 启动日志无 `D:\Hermes`）。

- [ ] **Step 3: 发真实查询触发子智能体**

```bash
printf '{"query":"调用数据感知子智能体获取最近12小时出水COD并算均值"}' > /tmp/qv.json
curl -s -X POST http://localhost:8000/api/query -H "Content-Type: application/json; charset=utf-8" --data-binary @/tmp/qv.json --max-time 200 -o /tmp/ans.json -w "http=%{http_code} time=%{time_total}s\n"
```
Expected: `http=200`，耗时 ~30-120s（子智能体跑 LLM）。

- [ ] **Step 4: 确认子智能体真跑（无签名错误、结构化结果）**

```bash
# agent 日志：call_subagent completed（非 error、无 "takes 0 positional"）
grep -iE "call_subagent completed|takes 0 positional|dispatch error" <agent日志路径> | tail -3
# sessions 目录有 task.json + *_result.json
ls -td sessions/session_* | head -1 | xargs ls
```
Expected: 有 `call_subagent completed (Xs, N chars)`；无 `takes 0 positional`；session 目录含 task.json + data_result.json（结构化）。

- [ ] **Step 5: 无代码提交（仅验证）**

---

## Task 7: 清理 + 文档

**Files:**
- Delete: `shared/framework/hermes_agent/`（旧下划线部分副本）
- Modify: `CLAUDE.md`

- [ ] **Step 1: 删除旧部分副本**（小定制已迁入 overlays；其余大差异文件不再用）

```bash
git rm -r shared/framework/hermes_agent
```
> 先确认无代码再 import 这个旧路径：`grep -rn "shared.framework.hermes_agent" --include=*.py .`。唯一引用是 `scripts/start_agent.py:29 from shared.framework.hermes_agent.run_agent import AIAgent`——改成从 vendored 导入（见 Step 2）。

- [ ] **Step 2: 改 start_agent.py 导入源**

`scripts/start_agent.py:29`：
```python
# 旧
from shared.framework.hermes_agent.run_agent import AIAgent
```
```python
# 新（vendored hermes；run_agent 现在是顶级可导入模块）
from run_agent import AIAgent
```
> vendored 安装后 `run_agent` 是顶级模块（`pip install -e` 后 `import run_agent` 解析到 shared/framework/hermes-agent/run_agent.py，即 overlays 覆盖后的小定制版）。

- [ ] **Step 3: 更新 CLAUDE.md**

把 Hermes 框架位置说明从 `shared/framework/hermes_agent`（下划线部分副本）改为：vendored 在 `shared/framework/hermes-agent/`（gitignore，`scripts/vendor_hermes.py` 复现）；editable 安装指向它；不再依赖 `D:\Hermes`。

- [ ] **Step 4: 验证 start_agent 改动后 agent 仍能起**

```bash
netstat -ano | grep -E "LISTENING" | grep -E ":8642 " | awk '{print $5}' | sort -u | while read pid; do taskkill //PID $pid //F; done
sleep 2
ecological_env/Scripts/python.exe scripts/start_agent.py  # 后台
sleep 12
curl -s -m 5 http://localhost:8642/health
```
Expected: healthy。

- [ ] **Step 5: Commit**

```bash
git add scripts/start_agent.py CLAUDE.md
git commit -m "refactor: import AIAgent from vendored hermes; remove old partial copy + D:\\Hermes dep"
```

---

## 验收标准（vendor 完成）
- [ ] `import tools.registry` / `agent.conversation_loop` / `run_agent` 全解析到 `shared/framework/hermes-agent/`，无 `D:\Hermes`。
- [ ] agent 启动日志不再加载 `D:\Hermes\.env`；`/api/query` → call_subagent → 子智能体 → 结构化结果回流，无签名错误。
- [ ] `register_orchestrator_tools` 不含 override 块；vendored `orchestrator_tool.py` handler 签名正确。
- [ ] `scripts/vendor_hermes.py` 可从源重生成 vendored 树；vendored 树被 gitignore；overlays + 脚本在 git。
- [ ] 旧 `shared/framework/hermes_agent/` 已删；`start_agent.py` 从 vendored 导入。
- [ ] （用户侧）删 `D:\Hermes` 后系统仍正常运行。

## Self-Review
- **Spec 覆盖**：spec §3.1 结构（Task 1/3）、§3.2 拷贝范围（Task 2 EXCLUDE + Task 3 验证）、§3.3 vendor 脚本（Task 2）、§3.4 fold 优化（Task 1，仅小定制——已与用户确认调整 spec 的"全部 fold"）、§3.5 重指安装（Task 4）、§3.6 orchestrator 整合（Task 1 overlay + Task 5 拆 override）、§3.7 清理（Task 7）、§4 验收（Task 6 + 验收清单）均有对应 Task。
- **占位符**：无 TBD；EXCLUDE 列表 + 4 个 handler 改写 + vendor 脚本均为完整代码；导入闭包漏项给出了"验证→补→重跑"的明确处置。
- **类型/命名一致**：overlays 路径（`shared/framework/hermes-overlays/`）在 Task 1/2/3 一致；`run_agent` 顶级导入在 Task 4 验证 + Task 7 改 start_agent 一致。
- **已知风险已处理**：①大差异文件不 fold（避免断子智能体）——Task 1 仅迁 4 小文件；②导入闭包漏项——Task 4 Step 3 处置；③editable 重指失败——Task 4 Step 2 处置；④start_agent 旧导入——Task 7 Step 2 改。
