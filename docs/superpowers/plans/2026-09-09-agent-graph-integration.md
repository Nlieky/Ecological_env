# 智能体集成（子项目 3/4）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 规则推理知识消费改图谱查询（脚本替换+LLM 查图双路）+ 研判结论写回图谱成案例——图谱开始参与推理并越用越厚。

**Architecture:** 三阶段独立交付——A 脚本内替换（GraphKnowledgeSource 统一入口，图不可用回退硬编码字典且回退可统计）/ B 研判写回（挂事件采集器）/ C LLM 主动查图（graph-query 技能+可靠性实测，不达标不合并）。每阶段可独立验证、独立回退。

**Tech Stack:** Python 3.12 + SQLite（WAL，现有 GraphStore）/ pytest / 真实 LLM 端到端（ctgu-vlm）

**Spec:** `docs/superpowers/specs/2026-09-09-agent-graph-integration-design.md`

---

## 工程约定（执行前必读）

- Python：`/e/project/Ecological_env/ecological_env/Scripts/python.exe`（$PY）。pytest 项目根跑。
- 子智能体脚本可 import shared.*（PYTHONPATH=项目根，call_subagent.py:282-287 已设；run_anomaly_detection_simple.py 有先例）。
- 提交中文 + 前缀 + 结尾 `Co-Authored-By: Claude <noreply@anthropic.com>`。
- 真实基线：6 个含 rule_reasoning_result.json 的 session（`ls sessions/*/rule_reasoning_result.json` 找齐），改造前先固化输出快照。
- 服务：backend :8000 / agent :8642 / Vite :5173 运行中（无 --reload，改 agent 侧代码需重启 8642）。
- 退路：`backup/pre-subproject3` 分支随时可回。

## 关键背景事实（实现者必读）

1. **改造对象**：`subagents/rule-reasoning-agent/skills/rule-reasoning-core/scripts/` 下 run_rule_reasoning.py（主入口，:33-40 import 三个同目录模块）+ expert_reasoner.py（:41-113 硬编码 5 模式 `_load_expert_rules`、:115-139 硬编码 3 案例 `_load_case_library`、:216-244 `_extract_features`、:246-265 `_match_patterns`、:353-392 `_match_cases`）+ regulation_matcher.py（:44-80 硬编码 `_load_regulations`，:36 有个从未使用的 regulations_dir 死变量；:102-136 match()；**当前真实行为：run_rule_reasoning.py:359 调 match(anomalies) 不传 data，走 :148-175 的 score>0.8 退化分支**）。
2. **run_rule_reasoning.py:176-184 INDICATOR_MAP**：中文指标名→英文键映射（复用它，别重定义）。
3. **图谱契约**：GraphStore(db_path) 构造即建空库（不存在则创建文件——注意 GraphKnowledgeSource 要**先检查文件存在**再构造，别用 GraphStore 建出空库）；节点 id 形如 `pattern:secret_pipe`/`indicator:AN`/`regulation:water_law_s39`；模式节点 label 是中文（"暗管偷排"）；limits 边 `indicator→regulation:gb18918` props={value:"50 mg/L"}；indicates 边 pattern→regulation；case 节点 props={timestamp,confidence,reasoning,violation_types}。
4. **写回挂载点**：backend/services/event_service.py collect_from_session :89-149（事件 db.add 后 commit 成功的位置；_parse_plant_id 已有；写回 try/except 独立）。
5. **knowledge-search 删除**：subagents/rule-reasoning-agent/skills/knowledge-search/ 整目录；seed_importer SKILLS 表引用它（"knowledge-search" 条目）需同步删；守卫测试不受影响。
6. **skill 目录结构惯例**：SKILL.md（frontmatter: name/description + 正文用法）+ scripts/main.py 或具体脚本；子智能体技能经 HERMES_HOME/skills/ 被 skill_view 发现。
7. **LLM 可靠性历史坑**：子智能体曾"读 SKILL.md 不执行"（ctgu-vlm 非确定性）；subagent_entry.py 有 perception 的自愈兜底但 rule-reasoning 没有；trace 在 sessions/_subagent_traces/<task_id>_<subagent>.log。

---

### Task 1（阶段 A）：GraphKnowledgeSource 统一入口

**Files:**
- Create: `shared/knowledge_graph/graph_query.py`
- Test: `tests/knowledge_graph/test_graph_query.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/knowledge_graph/test_graph_query.py
"""GraphKnowledgeSource：优先图谱、不可用回退、回退可观测。"""
import json
from pathlib import Path

import pytest

from shared.knowledge_graph.graph_query import GraphKnowledgeSource
from shared.knowledge_graph import seed_importer


@pytest.fixture(scope="module")
def seeded_db(tmp_path_factory):
    db = tmp_path_factory.mktemp("gq") / "kg.db"
    seed_importer.run_seed(db_path=db)
    return db


def test_patterns_from_graph(seeded_db):
    src = GraphKnowledgeSource(db_path=seeded_db)
    pats = src.get_patterns()
    assert src.available is True
    labels = {p["label"] for p in pats}
    assert {"插瓶干扰", "暗管偷排", "稀释排放", "人工拟合"} <= labels
    # 审计修正后的字段：恶意逃避 desc 是数据缺失型定义
    me = next(p for p in pats if p["label"] == "恶意逃避")
    assert "缺失" in me["desc"]


def test_cases_from_graph(seeded_db):
    src = GraphKnowledgeSource(db_path=seeded_db)
    cases = src.get_cases()
    assert len(cases) >= 2  # 种子 2 条历史案例
    assert all("timestamp" in c and "violation_types" in c for c in cases)


def test_indicator_limits(seeded_db):
    src = GraphKnowledgeSource(db_path=seeded_db)
    lim = src.get_indicator_limits()
    assert lim.get("COD") and "50" in lim["COD"]["value"]
    assert lim.get("AN") and "5" in lim["AN"]["value"]


def test_pattern_laws_dual_anchor(seeded_db):
    # 审计修正后：篡改类双锚 §39+§83
    src = GraphKnowledgeSource(db_path=seeded_db)
    laws = src.get_pattern_laws("插瓶干扰")
    articles = {l["article"] for l in laws}
    assert "第三十九条" in articles and "第八十三条" in articles


def test_pattern_id_by_label(seeded_db):
    src = GraphKnowledgeSource(db_path=seeded_db)
    assert src.pattern_id_by_label("暗管偷排") == "pattern:secret_pipe"
    assert src.pattern_id_by_label("不存在") is None


def test_db_missing_fallback_observed(tmp_path):
    # DB 不存在 → available=False，回退调用方字典，回退被记录
    src = GraphKnowledgeSource(db_path=tmp_path / "nope.db")
    assert src.available is False
    fallback_data = [{"label": "兜底模式"}]
    pats = src.get_patterns(fallback=fallback_data)
    assert pats == fallback_data
    assert len(src.fallback_log) == 1
    assert src.fallback_log[0]["reason"] == "db_missing"


def test_empty_graph_fallback(tmp_path):
    # 文件存在但未种子（空图）→ 回退
    db = tmp_path / "empty.db"
    from shared.knowledge_graph.graph_store import GraphStore
    g = GraphStore(db)  # 构造即建空库
    g.close()
    src = GraphKnowledgeSource(db_path=db)
    pats = src.get_patterns(fallback=[{"label": "兜底"}])
    assert pats == [{"label": "兜底"}]
    assert src.fallback_log[-1]["reason"] == "empty_or_no_patterns"


def test_query_exception_fallback(seeded_db, monkeypatch):
    # 查询抛异常 → 回退不炸
    src = GraphKnowledgeSource(db_path=seeded_db)
    def boom():
        raise RuntimeError("boom")
    monkeypatch.setattr(src._store, "subgraph", boom)
    pats = src.get_patterns(fallback=[{"label": "兜底"}])
    assert pats == [{"label": "兜底"}]
    assert src.fallback_log[-1]["reason"].startswith("error")


def test_usage_report(seeded_db):
    src = GraphKnowledgeSource(db_path=seeded_db)
    src.get_patterns()
    src.get_cases()
    report = src.usage_report()
    assert report["used_graph"] is True
    assert report["queries"] == 2
    assert report["fallbacks"] == 0
```

- [ ] **Step 2: 跑测试确认失败**（ModuleNotFoundError）

- [ ] **Step 3: 实现** `shared/knowledge_graph/graph_query.py`：

```python
"""GraphKnowledgeSource——规则推理的知识源（子项目3 阶段A）。

优先图谱查询；DB 缺失/空图/异常时回退调用方提供的硬编码字典（兜底可统计：
fallback_log 记录每次回退的时间/原因/调用方，usage_report 汇总写进研判结果
metadata.graph_usage——用户要求观察线上回退频率，几乎不触发则移除兜底）。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from shared.knowledge_graph.graph_store import GraphStore

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DB = _PROJECT_ROOT / "shared" / "data" / "knowledge_graph.db"


class GraphKnowledgeSource:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else _DEFAULT_DB
        self.fallback_log: list[dict] = []
        self._query_count = 0
        self._store: Optional[GraphStore] = None
        self.available = False
        if self.db_path.exists():
            try:
                self._store = GraphStore(self.db_path)
                self.available = True
            except Exception as e:
                logger.warning(f"[graph-query] GraphStore 初始化失败: {e}")
        else:
            logger.info(f"[graph-query] 图谱不存在({self.db_path})，回退模式")

    # ---------- 内部 ----------
    def _fallback(self, caller: str, reason: str, data):
        self.fallback_log.append({"time": datetime.now().isoformat(timespec="seconds"),
                                  "caller": caller, "reason": reason})
        return data

    def _subgraph(self, node_types):
        """查询子图；空结果/异常返回 None（调用方走回退）。"""
        if not self.available:
            return None
        try:
            sg = self._store.subgraph(node_types=node_types)
            self._query_count += 1
            return sg if sg["nodes"] else None
        except Exception as e:
            logger.warning(f"[graph-query] 查询失败({node_types}): {e}")
            self._store = None
            self.available = False  # 后续查询直接回退，不反复撞
            return None

    # ---------- 对外查询（fallback 参数=调用方的硬编码字典） ----------
    def get_patterns(self, fallback=None) -> list:
        reason = "db_missing" if not self.db_path.exists() else None
        sg = self._subgraph(["violation_pattern"]) if reason is None else None
        if sg is None:
            why = reason or ("empty_or_no_patterns" if self.db_path.exists() else "db_missing")
            if fallback is None and sg is None and self.available is False and not self.db_path.exists():
                why = "db_missing"
            return self._fallback("get_patterns", why, list(fallback or []))
        return [{"id": n["id"], "label": n["label"],
                 "desc": n["props"].get("desc", ""),
                 "status": n["props"].get("status", "")}
                for n in sg["nodes"]]

    def get_cases(self, fallback=None) -> list:
        sg = self._subgraph(["case"])
        if sg is None:
            return self._fallback("get_cases",
                                  "db_missing" if not self.db_path.exists() else "empty_or_no_cases",
                                  list(fallback or []))
        return [{"id": n["id"], "label": n["label"], **n["props"]} for n in sg["nodes"]]

    def get_indicator_limits(self, fallback=None) -> dict:
        """limits 边：indicator→gb18918。返回 {英文键: {value, standard}}"""
        sg = self._subgraph(["indicator", "regulation"])
        if sg is None:
            return self._fallback("get_indicator_limits",
                                  "db_missing" if not self.db_path.exists() else "empty",
                                  dict(fallback or {}))
        node_by_id = {n["id"]: n for n in sg["nodes"]}
        out = {}
        for e in sg["edges"]:
            if e["type"] != "limits":
                continue
            ind = node_by_id.get(e["src"])
            reg = node_by_id.get(e["dst"])
            if ind and reg and "gb18918" in reg["id"]:
                out[ind["props"].get("field", ind["id"].split(":", 1)[1])] = {
                    "value": e["props"].get("value", ""),
                    "standard": reg["label"],
                }
        return out or self._fallback("get_indicator_limits", "no_limits_edges", dict(fallback or {}))

    def get_pattern_laws(self, pattern_label: str, fallback=None) -> list:
        """indicates 边：模式(中文label)→法规 [{article, note, anchor}]"""
        pid = self.pattern_id_by_label(pattern_label)
        if pid is None:
            return self._fallback("get_pattern_laws", "pattern_not_found",
                                  list(fallback or []))
        try:
            nb = self._store.neighbors(pid, edge_types=["indicates"], direction="out", depth=1)
            self._query_count += 1
        except Exception as e:
            logger.warning(f"[graph-query] 法条查询失败: {e}")
            return self._fallback("get_pattern_laws", f"error:{e}", list(fallback or []))
        out = []
        for n in nb["nodes"]:
            out.append({"article": n["props"].get("article", n["label"]),
                        "note": n["props"].get("note", ""),
                        "anchor": n["label"]})
        return out

    def pattern_id_by_label(self, label: str) -> Optional[str]:
        if not self.available:
            return None
        try:
            node = None
            sg = self._subgraph(["violation_pattern"])
            for n in (sg or {}).get("nodes", []):
                if n["label"] == label:
                    node = n
                    break
            return node["id"] if node else None
        except Exception:
            return None

    # ---------- 观测 ----------
    def usage_report(self) -> dict:
        return {"used_graph": self.available,
                "queries": self._query_count,
                "fallbacks": len(self.fallback_log),
                "fallback_detail": self.fallback_log}
```

注意点：
- 构造前先 `db_path.exists()` 检查——**不要**让 GraphStore 建出空库文件（污染"图不存在"语义）
- `get_patterns` 的 reason 分支逻辑写干净（上面草稿里的嵌套 if 有点绕，实现时理顺：先判 available/db 存在，再查，三层清晰）
- pattern_id_by_label 会多查一次 subgraph——可以缓存 patterns 结果（首次查询后缓存，后续 O(1)；写回侧也用它）

- [ ] **Step 4: 跑测试全绿**（9 个）；全套无回归

- [ ] **Step 5: 提交**

```bash
git add shared/knowledge_graph/graph_query.py tests/knowledge_graph/test_graph_query.py
git commit -m "feat(graph): GraphKnowledgeSource知识源——优先图谱/回退可观测(用户要求线上统计回退频率)"
```

---

### Task 2（阶段 A）：三个模块图查询替换 + 基线对比

**Files:**
- Modify: `subagents/rule-reasoning-agent/skills/rule-reasoning-core/scripts/expert_reasoner.py`
- Modify: `subagents/rule-reasoning-agent/skills/rule-reasoning-core/scripts/regulation_matcher.py`
- Modify: `subagents/rule-reasoning-agent/skills/rule-reasoning-core/scripts/run_rule_reasoning.py`
- Create: `tests/rule_reasoning/test_baseline_compare.py`

- [ ] **Step 1: 固化基线快照（改造前）**

```bash
mkdir -p tests/rule_reasoning/baselines
$PY -X utf8 - << 'EOF'
import json, shutil
from pathlib import Path
# 找全部含 rule_reasoning_result.json 的 session，复制输入(anomaly/data/task)与输出到 baselines
roots = sorted(Path("sessions").glob("*/rule_reasoning_result.json"))
n = 0
for rr in roots:
    sd = rr.parent
    if not (sd / "anomaly_result.json").exists():
        continue  # 没输入的没对比价值
    dst = Path("tests/rule_reasoning/baselines") / sd.name
    dst.mkdir(parents=True, exist_ok=True)
    for f in ("anomaly_result.json", "data_result.json", "task.json", "rule_reasoning_result.json"):
        if (sd / f).exists():
            shutil.copy2(sd / f, dst / f)
    n += 1
print(f"固化 {n} 个基线 session")
EOF
git add tests/rule_reasoning/baselines && git commit -m "test(rule-reasoning): 固化改造前基线快照(6个真实session输入输出)"
```

- [ ] **Step 2: 写对比测试** `tests/rule_reasoning/test_baseline_compare.py`：

```python
# tests/rule_reasoning/test_baseline_compare.py
"""基线对比：同输入下改造前后 rule_reasoning 的关键结论一致（子3 阶段A 验收门）。

判定标准（spec）：suspicion_level/has_violation 一致率 100%；
violation_types 允许差异（知识源变化的目的）但需打印供人审。
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "subagents/rule_reasoning_agent_placeholder"  # 占位防抄错，下行是真实路径
SCRIPT = ROOT / "subagents" / "rule-reasoning-agent" / "skills" / "rule-reasoning-core" / "scripts" / "run_rule_reasoning.py"
BASELINES = Path(__file__).parent / "baselines"

CASES = sorted([d for d in BASELINES.iterdir() if d.is_dir()]) if BASELINES.exists() else []


@pytest.mark.parametrize("case_dir", CASES, ids=lambda d: d.name)
def test_conclusion_consistency(case_dir, tmp_path):
    # 复制输入到临时目录跑改造后脚本
    work = tmp_path / "s"
    work.mkdir()
    for f in ("anomaly_result.json", "data_result.json", "task.json"):
        src = case_dir / f
        if src.exists():
            shutil_copy = open(src, "rb").read()
            (work / f).write_bytes(shutil_copy)
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--session-dir", str(work), "--anomaly-result", str(work / "anomaly_result.json")],
        capture_output=True, text=True, timeout=300, cwd=str(ROOT),
        env={**__import__("os").environ})
    assert r.returncode == 0, r.stderr[-800:]
    new = json.loads((work / "rule_reasoning_result.json").read_text(encoding="utf-8"))
    old = json.loads((case_dir / "rule_reasoning_result.json").read_text(encoding="utf-8"))
    # 关键结论必须一致
    assert new["result"]["suspicion_level"] == old["result"]["suspicion_level"], \
        f"suspicion 不一致: old={old['result']['suspicion_level']} new={new['result']['suspicion_level']}"
    assert new["result"]["has_violation"] == old["result"]["has_violation"]
    # violation_types 差异打印（不 assert——知识源变会带来合理差异）
    if new["result"].get("violation_types") != old["result"].get("violation_types"):
        print(f"[人审] {case_dir.name} violation_types: "
              f"old={old['result'].get('violation_types')} new={new['result'].get('violation_types')}")
    # graph_usage 观测字段在（新行为）
    gu = new.get("metadata", {}).get("graph_usage")
    assert gu is not None and "used_graph" in gu
```

（注意：`shutil_copy` 变量名是故意的直白复制，实现时用 `import shutil; shutil.copy2` 正常写；SCRIPT 第一行占位防抄错，第二行才是真的——只保留第二行。）

- [ ] **Step 3: 改造前先跑一次对比测试**——应该全绿（自己 vs 自己一致），确认基线机制本身工作

- [ ] **Step 4: 改造 expert_reasoner.py**

- `_load_expert_rules`（:41-113）：函数体改为——构造 GraphKnowledgeSource，`get_patterns(fallback=原硬编码字典)`。原 5 模式字典**原样保留**作为 fallback 参数（移到模块级常量 `_FALLBACK_PATTERNS`，内容不动）
- `_load_case_library`（:115-139）：同理，`get_cases(fallback=原3案例)`；原列表保留为 `_FALLBACK_CASES`
- `_match_patterns`/`_match_cases` 的匹配逻辑**不动**（它们消费的数据形状保持兼容——get_patterns 返回的 dict 要有匹配逻辑要的键：读 _match_patterns 用了哪些键，缺的在 GraphKnowledgeSource 侧补齐映射，如 label/desc/characteristics。**关键**：图里模式节点 props 有 desc/status 但没有匹配逻辑可能需要的特征关键词——如果匹配靠中文关键词（"恒定"/"多指标"），desc 里得有这些词，否则匹配率骤降。实现时先读 _match_patterns/_calculate_pattern_match 的实际取键逻辑，GraphKnowledgeSource 返回的数据必须满足；若图 desc 不含关键词，把 fallback 模式字典的特征字段并入图结果（图优先、字典补充字段））
- 模块级持有 GraphKnowledgeSource 实例供 run_rule_reasoning 取 usage_report

- [ ] **Step 5: 改造 regulation_matcher.py**

- `_load_regulations`：`get_indicator_limits(fallback=原限值字典)` + 法条部分 `get_pattern_laws`（match() 输出里法规引用的来源换成图——读 match() 实际怎么用 regulations 字典再对齐）
- 删 :36 死变量 regulations_dir
- **保持当前真实行为**：match(anomalies) 不传 data 走 score>0.8 分支的路径不能变（这是现状，不要"顺手修复"——超范围）

- [ ] **Step 6: run_rule_reasoning.py 接 usage_report**

- 结果 JSON 的 metadata 加 `"graph_usage": source.usage_report()`（expert_reasoner/regulation_matcher 共用一个 GraphKnowledgeSource 实例，从模块取）
- import shared 的 sys.path 处理：脚本顶部已有 find_project_root——加 `sys.path.insert(0, str(root))`（若未有）

- [ ] **Step 7: 跑基线对比测试**——全部 suspicion/has_violation 一致；violation_types 差异打印出来人工审（预期：案例更多来自图谱、法条引用变化为 §39/§83 体系——这些是"变好"的差异）

- [ ] **Step 8: 全套测试 + 提交**

```bash
$PY -m pytest tests/ -q   # 全绿（基线对比新增 6 个参数化用例）
git add subagents/rule-reasoning-agent/ tests/rule_reasoning/
git commit -m "feat(rule-reasoning): 知识消费改图谱查询(阶段A)——专家模式/案例/限值法条三模块接入GraphKnowledgeSource,硬编码字典降级为回退,基线对比6session关键结论100%一致"
```

---

### Task 3（阶段 B）：研判写回图谱

**Files:**
- Modify: `backend/services/event_service.py`
- Test: `tests/events/test_writeback.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/events/test_writeback.py
"""研判写回图谱：事件入库时同步写案例节点+involves/cites边；幂等；图缺失静默。"""
import json
from pathlib import Path

import pytest

from shared.knowledge_graph.graph_store import GraphStore
from shared.knowledge_graph import seed_importer


@pytest.fixture
def env(tmp_path, monkeypatch):
    """独立 events 库 + 独立图谱库 + 伪造 session。"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import backend.database.base as base
    import backend.services.event_service as es
    engine = create_engine(f"sqlite:///{tmp_path}/ev.db", connect_args={"check_same_thread": False})
    base.Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    monkeypatch.setattr(es, "SessionLocal", TestSession)
    # 独立图谱（种子过，含模式节点供 cites）
    kg = tmp_path / "kg.db"
    seed_importer.run_seed(db_path=kg)
    svc = es.EventService(sessions_root=tmp_path)
    monkeypatch.setattr(es, "_graph_db_path", kg)  # 写回用的图路径（实现里抽成模块级可 patch）
    # 伪造 medium session
    sd = tmp_path / "session_wb1"
    sd.mkdir()
    (sd / "disposition_result.json").write_text(json.dumps({
        "task_id": "t1", "status": "completed",
        "result": {"suspicion_level": "medium", "suspicion_level_cn": "中风险",
                   "violation_types": ["暗管偷排"], "action": "现场核查",
                   "confidence": 0.9, "work_order": None, "report": None,
                   "evidence_points": []},
        "metadata": {"timestamp": "2026-09-09T10:00:00"}}, ensure_ascii=False), encoding="utf-8")
    (sd / "task.json").write_text(json.dumps(
        {"task": "查询当阳市金桥污水处理厂一期数据研判", "task_id": "t1"}, ensure_ascii=False), encoding="utf-8")
    yield svc, sd.name, kg
    engine.dispose()


def test_writeback_creates_case_node(env):
    svc, session_name, kg = env
    ev = svc.collect_from_session(session_name)
    assert ev is not None
    g = GraphStore(kg)
    node = g.get_node(f"case:{ev['id']}")
    assert node is not None
    assert node["props"]["plant_id"] == "当阳市金桥污水处理厂一期"
    assert node["props"]["severity"] == "medium"
    # involves → 厂
    nb = g.neighbors(f"case:{ev['id']}", edge_types=["involves"], direction="out", depth=1)
    assert {n["id"] for n in nb["nodes"]} == {"plant:当阳市金桥污水处理厂一期"}
    # cites → 模式（中文→slug 反查）
    nb2 = g.neighbors(f"case:{ev['id']}", edge_types=["cites"], direction="out", depth=1)
    assert "pattern:secret_pipe" in {n["id"] for n in nb2["nodes"]}
    g.close()


def test_writeback_idempotent(env):
    svc, session_name, kg = env
    svc.collect_from_session(session_name)   # 事件采集幂等：第二次 None
    assert svc.collect_from_session(session_name) is None
    g = GraphStore(kg)
    n = g.subgraph(node_types=["case"])["nodes"]
    # 种子 2 + 写回 1 = 3（第二次采集没发生，无重复节点）
    assert len(n) == 3
    g.close()


def test_writeback_unknown_pattern_skips_cites(env):
    # 违规类型反查不到模式节点 → cites 跳过但节点仍写
    svc, sd, kg = env
    import json as j
    d = j.loads((svc.sessions_root / sd / "disposition_result.json").read_text(encoding="utf-8"))
    d["result"]["violation_types"] = ["不存在的类型"]
    (svc.sessions_root / sd / "disposition_result.json").write_text(j.dumps(d, ensure_ascii=False), encoding="utf-8")
    ev = svc.collect_from_session(sd)
    g = GraphStore(kg)
    assert g.get_node(f"case:{ev['id']}") is not None
    nb = g.neighbors(f"case:{ev['id']}", edge_types=["cites"], direction="out", depth=1)
    assert nb["nodes"] == []
    g.close()


def test_writeback_graph_missing_silent(tmp_path, monkeypatch):
    """图谱 DB 不存在 → 事件照常入库，写回静默跳过。"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import backend.database.base as base
    import backend.services.event_service as es
    engine = create_engine(f"sqlite:///{tmp_path}/ev2.db", connect_args={"check_same_thread": False})
    base.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(es, "SessionLocal", sessionmaker(bind=engine))
    monkeypatch.setattr(es, "_graph_db_path", tmp_path / "nope.db")
    sd = tmp_path / "session_wb2"
    sd.mkdir()
    (sd / "disposition_result.json").write_text(json.dumps({
        "task_id": "t", "status": "completed",
        "result": {"suspicion_level": "high", "violation_types": ["插瓶干扰"],
                   "action": "立即调查取证", "confidence": 0.9,
                   "work_order": None, "report": None, "evidence_points": []},
        "metadata": {"timestamp": "2026-09-09T11:00:00"}}, ensure_ascii=False), encoding="utf-8")
    (sd / "task.json").write_text(json.dumps(
        {"task": "查询金桥数据", "task_id": "t"}, ensure_ascii=False), encoding="utf-8")
    svc = es.EventService(sessions_root=tmp_path)
    ev = svc.collect_from_session("session_wb2")  # 不抛
    assert ev is not None  # 事件照常
    engine.dispose()
```

- [ ] **Step 2: 确认失败**（写回不存在）

- [ ] **Step 3: 实现写回**

event_service.py 改动（保持现有结构）：
- 模块级 `_graph_db_path = _PROJECT_ROOT / "shared" / "data" / "knowledge_graph.db"`（可 patch）
- `collect_from_session` 里事件 commit 成功后：

```python
            # 研判写回图谱（子项目3 阶段B）：案例节点+involves厂+cites模式。
            # 独立 try/except——图谱写失败只记日志，不影响事件已入库。
            try:
                _writeback_case_to_graph(ev, db_path=_graph_db_path)
            except Exception as wb_err:
                logger.warning(f"[events] 图谱写回失败(不影响事件): {wb_err}")
```

- `_writeback_case_to_graph(ev_dict, db_path)` 模块级函数：
  - db 不存在 → logger.info 后 return（静默跳过）
  - GraphStore(db_path)；upsert_node(f"case:{ev['id']}", "case", f"案例 {ev['timestamp'][:10]}", {timestamp/plant_id/severity/violation_types/confidence/action/source_event: ev['id']})
  - involves 边：`case:{id}` → f"plant:{ev['plantId']}"（图上厂节点 id 就是中文 plant_id；厂节点不存在也要写边吗？——**先 get_node 检查**，不存在跳过该边记日志，防悬挂边（审计教训））
  - cites 边：中文类型 → pattern_id_by_label 反查（GraphKnowledgeSource 或直查图 label）；反查不到跳过记日志
  - 完成后 logger.info 一行（节点/边写入摘要）

- [ ] **Step 4: 跑测试全绿**（4 个新 + events 全套 + 全套回归）

- [ ] **Step 5: 提交**

```bash
git add backend/services/event_service.py tests/events/test_writeback.py
git commit -m "feat(events): 研判结论写回图谱(阶段B)——案例节点+involves厂+cites模式,幂等/图缺失静默/防悬挂边"
```

---

### Task 4（阶段 C）：graph-query 技能 + 删 knowledge-search

**Files:**
- Create: `subagents/rule-reasoning-agent/skills/graph-query/SKILL.md`
- Create: `subagents/rule-reasoning-agent/skills/graph-query/scripts/query_graph.py`
- Delete: `subagents/rule-reasoning-agent/skills/knowledge-search/`（整目录）
- Modify: `subagents/rule-reasoning-agent/skills/rule-reasoning-core/SKILL.md`（可选查图步骤）
- Modify: `shared/knowledge_graph/seed_importer.py`（SKILLS 表删 knowledge-search 条目）
- Test: `tests/knowledge_graph/test_graph_query_tool.py`（query_graph.py 脚本级测试）

- [ ] **Step 1: 写 query_graph.py 脚本测试**

```python
# tests/knowledge_graph/test_graph_query_tool.py
"""graph-query 技能脚本：三种查询模式+紧凑JSON输出+图缺失优雅退出。"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "subagents" / "rule-reasoning-agent" / "skills" / "graph-query" / "scripts" / "query_graph.py"


def run(args, env_db):
    import os
    return subprocess.run([sys.executable, str(SCRIPT)] + args,
                          capture_output=True, text=True, timeout=60, cwd=str(ROOT),
                          env={**os.environ, "KNOWLEDGE_GRAPH_DB": str(env_db)})


def test_pattern_query(seeded_db_module):
    r = run(["--pattern", "插瓶干扰"], seeded_db_module)
    assert r.returncode == 0
    d = json.loads(r.stdout.strip().splitlines()[-1])
    assert d["label"] == "插瓶干扰"
    assert any("第三十九条" in str(l) for l in d["laws"])
    assert "detects" in d  # 关联算子
    assert "cases" in d    # 关联案例（含写回的）


def test_cases_query(seeded_db_module):
    r = run(["--cases"], seeded_db_module)
    d = json.loads(r.stdout.strip().splitlines()[-1])
    assert len(d["cases"]) >= 2


def test_law_query(seeded_db_module):
    r = run(["--law", "人工拟合"], seeded_db_module)
    d = json.loads(r.stdout.strip().splitlines()[-1])
    assert len(d["laws"]) >= 2  # §39+§83 双锚


def test_missing_db_exit_clean(tmp_path):
    r = run(["--pattern", "插瓶干扰"], tmp_path / "nope.db")
    assert r.returncode == 0  # 不崩——输出 {"error": "graph_unavailable"}
    d = json.loads(r.stdout.strip().splitlines()[-1])
    assert d.get("error") == "graph_unavailable"


def test_output_compact(seeded_db_module):
    """输出是单行紧凑 JSON（LLM 上下文友好，<2000 字符）。"""
    r = run(["--pattern", "插瓶干扰"], seeded_db_module)
    last_line = r.stdout.strip().splitlines()[-1]
    assert len(last_line) < 2000
```

（fixture seeded_db_module 复用 test_graph_query.py 的种子库 fixture——或独立建。）

- [ ] **Step 2: 确认失败**

- [ ] **Step 3: 实现 query_graph.py**

要点：
- argparse：`--pattern <中文名>` / `--cases [--plant <厂名>]` / `--law <模式名>`（互斥，必选其一）；`--db`（默认 env KNOWLEDGE_GRAPH_DB 或 _DEFAULT_DB）
- 输出**单行紧凑 JSON**（ensure_ascii=False, separators=(',',':')），长字段截断（desc 截 80 字、evidence 不输出）
- --pattern 返回 {label, desc, status, laws:[{article,note,anchor}], detects:[算子名], cases:[{label,severity,timestamp}]}（案例查 cites 反向）
- --cases 返回全部 case（可按厂过滤 involves）
- 图缺失/参数错 → {"error": "..."} + exit 0（**不崩**——LLM 环境要稳）

- [ ] **Step 4: SKILL.md（graph-query 技能）**

frontmatter（name/description 对齐 hermes skill 发现惯例——参照 rule-reasoning-core/SKILL.md 的 frontmatter 格式）+ 正文：
- 用途一句话：查知识图谱拿违规模式/历史案例/法条关联
- 用法：一条命令示例（`python <脚本> --pattern 暗管偷排`，解释器全路径同其他技能惯例）
- 输出：单行 JSON 字段说明
- 反瞎逛条款：一次查询一种模式；禁止读 DB 文件本身

- [ ] **Step 5: rule-reasoning-core/SKILL.md 加可选步骤**

在"调脚本 → 确认完成"流程后加（措辞谨慎——鼓励非强制）：

```markdown
## 可选增强：查图谱补充上下文（鼓励，非必须）
脚本完成后，如需回答"该厂历史上有无类似情况""该模式关联哪些法条/算子"，
可用 graph-query 技能查询（最多 1 次）。不查不影响研判正确性；
查了可让结论引用真实历史案例与准确法条。
```

**不动**现有反瞎逛条款与三步流程（保守——先观察 LLM 是否稳定使用）。

- [ ] **Step 6: 删 knowledge-search**

```bash
git rm -r subagents/rule-reasoning-agent/skills/knowledge-search/
```
seed_importer SKILLS 表删 ("knowledge-search","agent:rule-reasoning","知识四库检索") 条目；守卫测试跑一遍（不涉主智能体技能，应全绿）。

- [ ] **Step 7: 测试 + 提交**

```bash
$PY -m pytest tests/ -q   # 全绿
git add subagents/rule-reasoning-agent/skills/ shared/knowledge_graph/seed_importer.py tests/knowledge_graph/test_graph_query_tool.py
git commit -m "feat(rule-reasoning): graph-query技能(阶段C)——模式/案例/法条紧凑JSON查询+SKILL可选查图步骤;删knowledge-search(从未生效)"
```

---

### Task 5（阶段 C）：LLM 可靠性实测（≥10 轮端到端）

**Files:**
- Create: `tests/rule_reasoning/reliability_report.md`（实测记录，入库）
- （无代码改动——本任务是验证与调优循环）

- [ ] **Step 1: 重启 agent 服务**（:8642，带 Task4 的 SKILL 改动）

- [ ] **Step 2: ≥10 轮端到端实测**

脚本化跑（每轮新 session_id，问题混合）：
- 5 轮研判类："查询当阳市金桥污水处理厂一期 2026年7月14日 数据并研判"（标准链路）
- 3 轮历史类："金桥一期历史上有没有暗管偷排的案例"（诱导查图）
- 2 轮混合："查洗舱站最近数据研判，这个厂之前有类似违规吗"

每轮记录（从 sessions/_subagent_traces/ 与审计库取）：
- ③规则推理脚本执行了吗（rule_reasoning_result.json 存在且 completed）
- graph-query 被调用了吗（trace 里 grep query_graph）
- 调用成功吗（输出含合法 JSON 无 error）
- 结论引用了图知识吗（最终回答/结果提及历史案例或 §39/§83）

- [ ] **Step 3: 统计与判定**

| 指标 | 标准 | 不达标动作 |
|---|---|---|
| 脚本执行率 | **100%**（现有能力不许退化） | 立即回查 Task2 改动（回归） |
| graph-query 调用率 | ≥50%（诱导轮 ≥66%） | 调 SKILL.md 措辞重测一轮 5 次 |
| 查询成功率 | 100%（调了就得成） | 查脚本输出长度/JSON 可解析性/trace 错误 |
| 引用率 | 诱导轮 ≥40% | 同上+查 prompt 上下文 |

- [ ] **Step 4: 不顺利深查清单**（用户点名）

逐项排查并记录到 reliability_report.md：
1. SKILL.md 步骤位置（可选步骤是否被"反瞎逛"条款压制——LLM 可能把"最少步骤"理解为禁止查图）
2. 输出 JSON 超长被 LLM 忽略？（控制 <2000 字符验证）
3. skill_view 能发现 graph-query 吗（技能列表/描述是否清晰）
4. trace 里 LLM 的实际行为序列（读了几次 skill、犹豫点在哪）
5. ctgu-vlm 对"可选"指令的遵循度（对比"必须"措辞的 A/B——若"鼓励"不生效试"完成脚本后，运行 graph-query 查一次该厂历史案例"的直白祈使句）

- [ ] **Step 5: 处置**

- 全达标 → 报告归档，子项目 3 完成
- 措辞调优后达标 → 报告记录调优过程，完成
- 调优两轮仍不达标 → **阶段 C 的 SKILL.md 改动 revert**（graph-query 技能与脚本保留——无害），报告如实记录失败模式。脚本替换路（A/B）价值不受影响

- [ ] **Step 6: 提交报告**

```bash
git add tests/rule_reasoning/reliability_report.md
git commit -m "test(rule-reasoning): LLM查图可靠性实测报告(≥10轮端到端)——各指标与调优/处置记录"
```

---

### Task 6: 收尾——全量回归 + CLAUDE.md + 真实写回可视化验证

- [ ] **Step 1: 全量回归**：$PY -m pytest tests/ -q 全绿 + cd frontend && npm test（无前端改动应原样绿）
- [ ] **Step 2: 端到端真问一轮**（Task5 的其中一轮即可）：确认图谱页面 /agents/knowledge 出现新案例节点（seed 数 2 → 3+），点开有 involves 厂/cites 模式边
- [ ] **Step 3: 回退开关验证**：把 shared/data/knowledge_graph.db 临时改名 → 跑一轮研判 → 确认回退生效（graph_usage.used_graph=false, reason=db_missing）且结论一致 → 改回
- [ ] **Step 4: CLAUDE.md 补条目**

```markdown
### 智能体集成（2026-09-09 子项目 3/4）
- `shared/knowledge_graph/graph_query.py`：GraphKnowledgeSource——规则推理知识源（优先图谱/回退硬编码字典/回退可观测 fallback_log+usage_report）
- 规则推理三模块（expert_reasoner/regulation_matcher）知识消费接图查询；process_validator 不动（判定逻辑非知识）
- 研判写回：event_service.collect_from_session 事件入库后同步写 case 节点+involves厂+cites模式（幂等/图缺失静默/防悬挂边）
- graph-query 技能：LLM 可选查图（模式/案例/法条紧凑 JSON）；knowledge-search 已删（从未生效）
- 可靠性实测报告：tests/rule_reasoning/reliability_report.md；回退频率观察：结果 JSON metadata.graph_usage
```

- [ ] **Step 5: 提交 + 汇报**（含回退频率首日数据——用户要观察这个）

---

## Self-Review 记录

- **Spec 覆盖**：GraphKnowledgeSource+回退可观测（Task1）/ 三模块替换+基线对比门（Task2）/ 写回幂等+防悬挂（Task3）/ graph-query 技能+删 knowledge-search（Task4）/ ≥10 轮可靠性+不顺利深查清单+不达标 revert（Task5）/ 回退开关验证+CLAUDE.md（Task6）✓
- **用户三点指示落位**：回退可统计（fallback_log→graph_usage→观察期）Task1/6；删 knowledge-search Task4；graph-query 可靠性加严（100% 执行率红线+深查 5 项清单+两轮调优上限后 revert）Task5 ✓
- **类型一致性**：GraphKnowledgeSource API 在 Task1 定义（get_patterns/get_cases/get_indicator_limits/get_pattern_laws/pattern_id_by_label/usage_report）Task2/3/4 消费一致；_graph_db_path 模块级可 patch 约定 Task3 测试与实现一致
- **已知实现风险标注**：Task2 Step4 的"图模式 desc 不含匹配关键词"风险已在任务内写明处理方案（图优先、字典补字段）；Task2 基线对比的判定标准与 spec 一致（suspicion/has_violation 100%，types 差异人审）
