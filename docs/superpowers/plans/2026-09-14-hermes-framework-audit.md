# Hermes 框架全面评估 · 执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按已批准的设计（`docs/superpowers/specs/2026-09-14-hermes-framework-audit-design.md`）完成 Hermes Agent 框架的四层审查 + LLM 调用最小实证，产出带文件:行号证据的评估报告、真实架构图、双路线裁决书和 P0/P1/P2 路线图。

**Architecture:** 评估型项目——报告骨架先建、逐层填充、按任务提交；唯一的新代码是 LLM 调用计数 wrapper（TDD，放 /tmp 用完即弃）；对项目源码全程只读。调查任务均给出精确命令与预期产出形态，禁止无出处结论。

**Tech Stack:** bash/grep/diff（审计）、Python 3.12（`Ecological_env/ecological_env/bin/python`，探测脚本）、mermaid（架构图）、Markdown（报告）。

**约定（全计划通用）：**
- 命令均从 `Ecological_env/` 仓库根执行：`cd /home/NYJ2025/Ecological_env`
- 中间产物目录：`/tmp/hermes-audit/`（脚本、diff 输出、日志），不进 git
- 报告文件：`docs/superpowers/specs/2026-09-14-hermes-framework-audit-report.md`（逐任务追加，逐任务提交）
- 提交信息格式：`docs(audit): <层名/内容>`（Conventional Commits，中文摘要）
- 框架三目录简称：`FR=shared/framework`，上游=`$FR/hermes-agent`，包副本=`$FR/hermes_agent`，改装层=`$FR/hermes-overlays`
- 只读红线：不修改 `shared/`、`backend/`、`workspace/`、`middleware/`、`subagents/` 下任何文件

---

### Task 1: 基线快照与报告骨架

**Files:**
- Create: `docs/superpowers/specs/2026-09-14-hermes-framework-audit-report.md`
- Create: `/tmp/hermes-audit/`（工作目录，不进 git）

- [ ] **Step 1: 建工作目录与基线快照**

```bash
mkdir -p /tmp/hermes-audit
cd /home/NYJ2025/Ecological_env
git rev-parse HEAD > /tmp/hermes-audit/baseline-commit.txt
git status -s > /tmp/hermes-audit/baseline-status.txt
find shared/framework -type f -name "*.py" | sort > /tmp/hermes-audit/framework-py-manifest.txt
wc -l < /tmp/hermes-audit/framework-py-manifest.txt
```

预期：输出文件总数（探索时为 626）；baseline-commit.txt 记录当前 commit（应为 `348a55e` 或其后续）。

- [ ] **Step 2: 钉死三个目录的关系基事实**

```bash
cd /home/NYJ2025/Ecological_env
echo "== 上游根目录:" && ls shared/framework/hermes-agent/ | head -30
echo "== 包副本目录:" && ls shared/framework/hermes_agent/
echo "== 上游内是否也有 hermes_agent 包:" && ls -d shared/framework/hermes-agent/hermes_agent 2>/dev/null || echo "无"
echo "== overlays:" && find shared/framework/hermes-overlays -type f
```

预期：弄清「包副本 `hermes_agent/`」与「上游目录」的镜像关系（哪个是哪个的拷贝）。把输出原样存入 `/tmp/hermes-audit/dir-relation.txt`（命令末尾加 `| tee /tmp/hermes-audit/dir-relation.txt` 的等价形式）。

- [ ] **Step 3: 识别上游版本**

```bash
cd /home/NYJ2025/Ecological_env
grep -m2 'version\|name' shared/framework/hermes-agent/pyproject.toml
ls -d shared/framework/hermes-agent/.git 2>/dev/null && (cd shared/framework/hermes-agent && git log --oneline -3) || echo "无 git 元数据"
head -5 shared/framework/hermes-agent/CHANGELOG.md 2>/dev/null
```

预期：得到版本号或「无法识别」结论。若无法识别，在报告 L2 开头标注「版本不明，以下 diff 以目录内副本互为基线」。

- [ ] **Step 4: 创建报告骨架**

写入 `docs/superpowers/specs/2026-09-14-hermes-framework-audit-report.md`：

```markdown
# Hermes Agent 框架评估报告

- 日期：2026-09-14 ｜ 评估基线 commit：（填 baseline-commit.txt 内容）
- 设计文档：docs/superpowers/specs/2026-09-14-hermes-framework-audit-design.md
- 严重度图例：🔴 阻塞（正确性/可用性风险）｜🟡 应修（质量/维护风险）｜🟢 建议

## 0. 执行摘要（最后写）
## 1. L1 活链路追踪（真实架构）
## 2. L2 改装审计
## 3. L3 项目适配审计
## 4. LLM 调用实证
## 5. L4 双路线裁决书
## 6. 路线图 P0/P1/P2
## 附录 A. 触达/未触达文件清单
## 附录 B. 实证原始数据
```

- [ ] **Step 5: 提交**

```bash
cd /home/NYJ2025/Ecological_env
git add docs/superpowers/specs/2026-09-14-hermes-framework-audit-report.md
git commit -m "docs(audit): 报告骨架与评估基线"
```

---

### Task 2: L1 活链路追踪

**Files:**
- Modify: `docs/superpowers/specs/2026-09-14-hermes-framework-audit-report.md`（填充 §1）

- [ ] **Step 1: 通读接入层（唯一活入口）**

```bash
cd /home/NYJ2025/Ecological_env
cat -n backend/services/agent_service.py > /tmp/hermes-audit/agent_service.numbered
grep -n -B2 -A10 'framework\|hermes' backend/api/routes/query.py
wc -l backend/services/agent_service.py
```

预期：207 行全部读完，记录：它 import 了什么（精确 import 语句行号）、暴露什么类/函数、同步还是异步、错误处理方式。这些直接写进报告 §1.1。

- [ ] **Step 2: 钉死 overlay 生效机制（L1.2，最关键）**

```bash
cd /home/NYJ2025/Ecological_env
grep -rn "sys.path" backend/services/agent_service.py shared/framework/__init__.py 2>/dev/null
grep -rn "hermes-overlays\|hermes_overlays\|overlays" backend/ middleware/ --include="*.py" | head -20
grep -rn "hermes" backend/services/agent_service.py | head -20
ls shared/framework/__init__.py && cat shared/framework/__init__.py
```

预期：回答「运行时到底 import 的是 `hermes_agent/` 还是 `hermes-overlays/` 的代码」——判据是 sys.path 插入顺序 / import 字符串 / 复制覆盖。若静态看不出来，执行下一步运行时验证。

- [ ] **Step 3: 运行时验证 import 解析（如有 venv 可用）**

```bash
cd /home/NYJ2025/Ecological_env
./ecological_env/bin/python - <<'EOF'
import sys, importlib.util
spec = importlib.util.find_spec("hermes_agent")
print("hermes_agent 解析到:", spec.origin if spec else "找不到")
for m in ["run_agent", "agent.agent_init"]:
    try:
        s = importlib.util.find_spec(f"hermes_agent.{m.split('.')[-1]}")
        print(f"hermes_agent.{m}:", s.origin if s else "无")
    except Exception as e:
        print(f"hermes_agent.{m}: 异常 {e}")
EOF
```

预期：打印每个同名模块实际解析到的绝对路径（包副本还是 overlays）。若 venv 缺依赖导致失败，改用 `PYTHONPATH=shared/framework python3` 系统解释器重试一次；再失败则记录「运行时验证不可行」并只用静态证据。

- [ ] **Step 4: 配置与 LLM 端点事实**

```bash
cd /home/NYJ2025/Ecological_env
wc -c .hermes/config.yaml 2>/dev/null; cat .hermes/config.yaml
grep -n 'LLM_' .env | sed 's/KEY=.*/KEY=<redacted>/'
cat shared/configs/llm_config.yaml 2>/dev/null | head -30
grep -rn "base_url\|model" shared/configs/llm_config.yaml 2>/dev/null
```

预期：表格化记录「框架从哪个文件拿哪个配置 → 实际 LLM 端点是 ctgu-vlm 还是 LongCat」。注意 key 不写入报告。

- [ ] **Step 5: 触达文件清单（静态 import 图）**

```bash
cd /home/NYJ2025/Ecological_env
# 从活入口出发做两层 grep 传递闭包（够用即可，不求完美）
grep -rhoE "from hermes[_a-z.]* import [a-zA-Z_, ]+|import hermes[_a-z.]*" backend/ middleware/ --include="*.py" | sort -u > /tmp/hermes-audit/imports-from-project.txt
cat /tmp/hermes-audit/imports-from-project.txt
# 触达文件的直接依赖（一层展开）
for f in $(grep -oE "hermes[_a-z.]*" /tmp/hermes-audit/imports-from-project.txt | sort -u); do
  find shared/framework -path "*${f//./\/}*" -name "*.py" 2>/dev/null
done | sort -u > /tmp/hermes-audit/touched-l1.txt
wc -l /tmp/hermes-audit/touched-l1.txt
```

预期：得到项目→框架的直接 import 面（应很小）。对触达文件再递归一层（对 touched-l1.txt 中文件 grep `from hermes_agent\|import hermes_agent`），合并为触达全集。全集与 manifest 差集 = 未触达（附录 A）。

- [ ] **Step 6: 画真实架构图并写入报告 §1**

在报告 §1 插入 mermaid：`query.py → agent_service → (overlay 机制标注) → 框架核心模块 → LLM 端点`，节点标注真实文件路径。附「与专利六层架构的映射/偏差」小节（对照 CLAUDE.md 的六层描述逐层标 ✅对应/⚠️偏差/❌缺失）。

- [ ] **Step 7: 提交**

```bash
git add docs/superpowers/specs/2026-09-14-hermes-framework-audit-report.md
git commit -m "docs(audit): L1 活链路追踪完成"
```

---

### Task 3: L2 改装审计（diff 逐块归类）

**Files:**
- Modify: `docs/superpowers/specs/2026-09-14-hermes-framework-audit-report.md`（填充 §2）

- [ ] **Step 1: 生成三组 diff 基线数据**

```bash
cd /home/NYJ2025/Ecological_env
# 组1: overlays/run_agent.py vs 上游
diff -u shared/framework/hermes-agent/run_agent.py shared/framework/hermes-overlays/run_agent.py > /tmp/hermes-audit/diff-run-agent.patch || true
# 组2: overlays/agent_init vs 包副本（上游同名物）
diff -u shared/framework/hermes_agent/agent/agent_init.py shared/framework/hermes-overlays/agent/agent_init.py > /tmp/hermes-audit/diff-agent-init.patch || true
# 组3: 包副本 vs 上游（验证"扩展身份文件读取"自述）
diff -rq shared/framework/hermes_agent shared/framework/hermes-agent/hermes_agent > /tmp/hermes-audit/diff-pkg-copy.txt 2>/dev/null || diff -rq shared/framework/hermes_agent/agent shared/framework/hermes-agent 2>/dev/null | head -30 > /tmp/hermes-audit/diff-pkg-copy.txt
wc -l /tmp/hermes-audit/*.patch /tmp/hermes-audit/diff-pkg-copy.txt
```

预期：三个文件都有内容（若组3路径不存在，按 Task1 Step2 钉死的真实关系改路径重跑）。预期 diff-run-agent.patch 为数千行量级。

- [ ] **Step 2: diff 统计与分块**

```bash
grep -c '^+[^+]' /tmp/hermes-audit/diff-run-agent.patch   # overlays 新增行数
grep -c '^-[^-]' /tmp/hermes-audit/diff-run-agent.patch   # overlays 删除行数
# 按 hunk 列出修改热点（上下文头）
grep -n '^@@' /tmp/hermes-audit/diff-run-agent.patch | head -40
```

预期：新增/删除行数 + hunk 列表。把 hunk 逐个归类到四分类（身份文件扩展/编排改动/项目特化/无法解释），方法：读每个 hunk 的上下文（`sed -n` 按 hunk 行号抽读），判据：出现 SOUL/IDENTITY/MEMORY/身份 → 身份扩展；出现 orchestrat/subagent/schedule → 编排；出现废水/influx/监测中文词 → 项目特化；其余 → 待解释。

- [ ] **Step 3: 精读 orchestrator_tool.py 全文（193 行）**

```bash
cat -n shared/framework/hermes-overlays/tools/orchestrator_tool.py > /tmp/hermes-audit/orchestrator-tool.numbered
```

预期：写清它注册了什么工具、参数 schema、被谁调用（回查 agent_init/run_agent 中的引用行号）。

- [ ] **Step 4: 逐项评分并填报告 §2**

对每个归类块填四属性表（动机可推断性/正确性风险/上游同步冲突面/松耦合替代方案）。替代方案判据参考：上游若已有 hook/配置/子类点（在上游目录 grep `hook\|register\|plugin`），标注「本可用 X 而不必改源码」。

- [ ] **Step 5: 提交**

```bash
git add docs/superpowers/specs/2026-09-14-hermes-framework-audit-report.md
git commit -m "docs(audit): L2 改装审计完成"
```

---

### Task 4: L3 项目适配审计

**Files:**
- Modify: `docs/superpowers/specs/2026-09-14-hermes-framework-audit-report.md`（填充 §3）

- [ ] **Step 1: agent_service.py 逐行问题清单**

基于 Task2 Step1 的编号读档，检查五项并逐条记录（文件:行号）：异常处理（有无裸 except/吞错）、超时与重试（LLM 调用有无 deadline）、同步阻塞（是否 async、会不会卡死 FastAPI worker）、配置硬编码、日志与可观测性。

- [ ] **Step 2: 四子代理身份文件齐全度矩阵**

```bash
cd /home/NYJ2025/Ecological_env
for d in subagents/*/; do
  echo "== $d"; for f in IDENTITY.md AGENTS.md SOUL.md TOOLS.md MEMORY.md; do
    [ -f "$d$f" ] && echo "  ✓ $f" || echo "  ✗ $f 缺失"
  done; ls "$d" | head -8
done | tee /tmp/hermes-audit/subagent-identity-matrix.txt
```

预期：4×5 矩阵 + 各目录技能/scripts 概览。

- [ ] **Step 3: 业务闭环证据链（关键）**

```bash
cd /home/NYJ2025/Ecological_env
for kw in influxdb perception anomaly rule disposition; do
  echo "== $kw 在活链路文件中的引用:"; grep -rn "$kw" backend/services/agent_service.py shared/framework/hermes-overlays/ 2>/dev/null | head -5
done
ls subagents/*/skills/*/scripts/*.py 2>/dev/null | head -20
grep -rn "import\|subprocess\|exec" shared/framework/hermes-overlays/tools/orchestrator_tool.py | head -10
```

预期：对「influxdb→感知→异常→规则→处置」五环节逐个给出：在框架链路中被谁、在哪行调用（或「找不到证据」）。找不到证据的环节标 🔴 并注明「业务断链」。

- [ ] **Step 4: workspace 身份文件加载一致性**

```bash
cd /home/NYJ2025/Ecological_env
ls workspace/*.md; grep -n "SOUL\|IDENTITY\|MEMORY\|AGENTS\|USER\|TOOLS\|HEARTBEAT" shared/framework/hermes-overlays/agent/agent_init.py | head -20
grep -rn "identity_loader\|load_identity" shared/framework/hermes_agent/agent/identity_loader.py | head -10
```

预期：对照表——workspace 每个 .md ↔ 框架是否真的读（读的代码行号）/被忽略。

- [ ] **Step 5: 测试覆盖盘点**

```bash
cd /home/NYJ2025/Ecological_env
find tests -name "*.py" | xargs grep -ln "agent_service\|hermes" 2>/dev/null | tee /tmp/hermes-audit/tests-framework.txt
find tests -name "*.py" | xargs grep -ln "orchestrator-core\|execution_control\|orchestrator_core" 2>/dev/null | tee /tmp/hermes-audit/tests-legacy.txt
echo "框架链路测试: $(wc -l < /tmp/hermes-audit/tests-framework.txt) 个; 脚本链路测试: $(wc -l < /tmp/hermes-audit/tests-legacy.txt) 个"
```

预期：两份清单，回答「测试押在哪条链路上」。

- [ ] **Step 6: 填报告 §3 并提交**

```bash
git add docs/superpowers/specs/2026-09-14-hermes-framework-audit-report.md
git commit -m "docs(audit): L3 项目适配审计完成"
```

---

### Task 5: LLM 调用计数 wrapper（TDD，唯一代码任务）

**Files:**
- Create: `/tmp/hermes-audit/llm_probe.py`（不进 git）
- Test: `/tmp/hermes-audit/test_llm_probe.py`（不进 git）

- [ ] **Step 1: 写失败测试**

`/tmp/hermes-audit/test_llm_probe.py`：

```python
import sys; sys.path.insert(0, "/tmp/hermes-audit")
from llm_probe import CountingProxy, Waterfall

class FakeClient:
    def __init__(self): self.calls = 0
    def chat(self, prompt, **kw):
        self.calls += 1
        return f"resp{self.calls}"

def test_proxy_counts_and_records():
    fake = FakeClient()
    proxy = CountingProxy(fake, stage="L1-解析")
    proxy.chat("第一问"); proxy.chat("第二问", model="x")
    wf = Waterfall()
    wf.add("L1-解析", proxy.usage)
    assert proxy.usage["calls"] == 2
    assert wf.total_calls() == 2
    assert wf.rows()[0][0] == "L1-解析" and wf.rows()[0][1] == 2
```

- [ ] **Step 2: 运行验证失败**

```bash
/home/NYJ2025/Ecological_env/ecological_env/bin/python -m pytest /tmp/hermes-audit/test_llm_probe.py -v 2>&1 | tail -3
```

预期：FAIL（ModuleNotFoundError: llm_probe 或 ImportError）。

- [ ] **Step 3: 最小实现**

`/tmp/hermes-audit/llm_probe.py`：

```python
"""LLM 调用计数 wrapper：包装任意 client 对象，记录调用数与 token（若响应带 usage）。"""
import time, json

class CountingProxy:
    def __init__(self, inner, stage="未标记"):
        self._inner = inner; self.stage = stage
        self.usage = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "seconds": 0.0}

    def __getattr__(self, name):  # 透传其余属性
        return getattr(self._inner, name)

    def _record(self, fn, *a, **kw):
        t0 = time.time()
        out = fn(*a, **kw)
        dt = time.time() - t0
        u = self.usage
        u["calls"] += 1; u["seconds"] += dt
        for pt, ct in (("prompt_tokens","completion_tokens"),("input_tokens","output_tokens")):
            src = getattr(out, "usage", None) or (out.get("usage") if isinstance(out, dict) else None)
            if src:
                u["prompt_tokens"] += getattr(src, pt, 0) or (src.get(pt, 0) if isinstance(src, dict) else 0)
                u["completion_tokens"] += getattr(src, ct, 0) or (src.get(ct, 0) if isinstance(src, dict) else 0)
        return out

    def chat(self, *a, **kw):  return self._record(self._inner.chat, *a, **kw)
    def complete(self, *a, **kw): return self._record(self._inner.complete, *a, **kw)
    def invoke(self, *a, **kw):  return self._record(self._inner.invoke, *a, **kw)

class Waterfall:
    def __init__(self): self._rows = []
    def add(self, stage, usage): self._rows.append((stage, usage["calls"], usage["prompt_tokens"], usage["completion_tokens"], round(usage["seconds"],1)))
    def rows(self): return self._rows
    def total_calls(self): return sum(r[1] for r in self._rows)
    def markdown(self):
        head = "| 阶段 | 调用数 | prompt_tok | completion_tok | 秒 |\n|---|---|---|---|---|"
        return head + "\n" + "\n".join(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} |" for r in self._rows)
```

- [ ] **Step 4: 运行验证通过**

```bash
/home/NYJ2025/Ecological_env/ecological_env/bin/python -m pytest /tmp/hermes-audit/test_llm_probe.py -v 2>&1 | tail -3
```

预期：PASS（2 passed 或 1 passed）。

- [ ] **Step 5: 接入活链路跑一轮实证**

方法（按 L1 钉死的机制二选一，均不修改项目文件）：
- 首选 monkey-patch：写 `/tmp/hermes-audit/run_probe.py`——`sys.path` 按活链路配置 → `import` agent_service 及其 LLM client 工厂 → 用 `CountingProxy` 包住 client 单例 → 调用 `agent_service` 的主入口函数（入参用 `tests/integration/` 现成用例的数据或 `stream/` 的单条模拟数据）→ 结束打印 `Waterfall.markdown()` 存 `/tmp/hermes-audit/waterfall.md`
- 降级 A（无法 import）：跑 `tests/integration/` 中最接近框架链路的用例，`PYTHONSTARTUP`/sitecustomize 方式注入 patch
- 降级 B（E4，完全跑不通）：在报告 §4 写明跑不通的原因（缺什么），改为静态推演：grep 活链路中所有 LLM 调用点行号，数出「每轮理论调用数」，显著标注「⚠️ 未实证，静态推演」

验收：`waterfall.md` 有真实数字；总调用数与 CLAUDE.md 记载「~12 次/流程」对照，偏差给解释（如身份文件逐次重读导致倍增）。

- [ ] **Step 6: 填报告 §4 + 附录 B 并提交**

```bash
git add docs/superpowers/specs/2026-09-14-hermes-framework-audit-report.md
git commit -m "docs(audit): LLM 调用实证完成"
```

---

### Task 6: L4 双路线裁决

**Files:**
- Modify: `docs/superpowers/specs/2026-09-14-hermes-framework-audit-report.md`（填充 §5）

- [ ] **Step 1: git 时间线取证**

```bash
cd /home/NYJ2025/Ecological_env
echo "== orchestrator-core 首末次提交:"; git log --format="%ad %h %s" --date=short -- workspace/skills/orchestrator-core | tail -1; git log --format="%ad %h %s" --date=short -- workspace/skills/orchestrator-core | head -1
echo "== framework 首末次提交:"; git log --format="%ad %h %s" --date=short -- shared/framework | tail -1; git log --format="%ad %h %s" --date=short -- shared/framework | head -1
echo "== agent_service 首末次提交:"; git log --format="%ad %h %s" --date=short -- backend/services/agent_service.py
```

预期：两条路线的先后与活跃期，佐证谁是事实标准。

- [ ] **Step 2: 职责矩阵与重复度**

对照 CLAUDE.md 的 orchestrator-core 流水线描述与 L1 实测的框架链路，填 5×3 矩阵（任务解析/子代理调度/结果解释/身份文件/工具脚本调用 × 框架链路 / 脚本链路 / 重复？）。重复度结论必须引用两侧文件:行号。

- [ ] **Step 3: 外部参照分析（材料已在手）**

用已完成的 pi-subagents / OpenClaw 调研结论（`~/pi-subagent-tutorial.md`、`~/openclaw/docs/tools/subagents.md`）映射到废水场景，各写一段「若采用其模式，本系统哪些痛点消失/哪些代价出现」。只作参照，不引入新依赖。

- [ ] **Step 4: 写裁决书（三选一，禁止和稀泥）**

格式：`结论：继续用并加固 / 收缩为库 / 替换` + 三段论据（架构收益、实证数据、维护成本）+ 过渡步骤（被裁方处置：归档/抽取可复用件/立即删除的顺序）。

- [ ] **Step 5: 提交**

```bash
git add docs/superpowers/specs/2026-09-14-hermes-framework-audit-report.md
git commit -m "docs(audit): L4 双路线裁决书完成"
```

---

### Task 7: 汇总、路线图与验收自检

**Files:**
- Modify: `docs/superpowers/specs/2026-09-14-hermes-framework-audit-report.md`（§0 执行摘要、§6 路线图、附录 A）

- [ ] **Step 1: 汇总所有发现并分级**

通读报告全文，把 L1-L4 全部发现抽成总表（每行：编号/严重度/一句话/证据行号/所属层），据此填 §6 路线图：
- P0 立即修 = 全部 🔴（正确性/断链风险）
- P1 短期 1-2 周 = 🟡 中影响维护/成本的项
- P2 方向演进 = 裁决书 + 外部参照的可借鉴机制清单（每条注明借鉴对象与落点）

- [ ] **Step 2: 写执行摘要 §0**

格式：一段话结论（框架对不对的直接回答）+ 三个最重要的数字（改装规模、活链路触达率、实测 LLM 调用数）+ 裁决结论 + P0 数量。

- [ ] **Step 3: 附录 A 落盘**

```bash
cp /tmp/hermes-audit/touched-l1.txt /tmp/hermes-audit/waterfall.md /tmp/hermes-audit/subagent-identity-matrix.txt /dev/null 2>/dev/null # 确认存在
```

把触达/未触达清单精简后（触达全列、未触达按顶层目录聚合统计）写入附录 A；附录 B 贴 `waterfall.md` 原文。

- [ ] **Step 4: 对照设计文档 §7 验收标准逐条自检**

5 条验收标准逐条打勾（证据/裁决/实证/路线图可执行/检查项全覆盖无留白），不满足的回前面任务补。自检结果写进报告末尾「验收记录」小节。

- [ ] **Step 5: 终版提交**

```bash
cd /home/NYJ2025/Ecological_env
git add docs/superpowers/specs/2026-09-14-hermes-framework-audit-report.md
git commit -m "docs(audit): 评估报告终版（摘要/路线图/验收记录）"
git log --oneline -7
```

预期：7 个审计相关 commit（骨架+五层+终版）。
