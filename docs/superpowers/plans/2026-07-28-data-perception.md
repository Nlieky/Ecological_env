# 数据感知子智能体 Implementation Plan(Plan 1/5)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 数据感知子智能体重构为"忠实取数 + 标记缺失 + HRT标注 + 零分析";身份文件对齐实际;去掉自愈 hack(全局 4 子智能体回归 LLM 驱动失败重试)。

**Architecture:** `get_data.py` 加 metadata(`hrt_hours`/`missing_points`,零分析不清洗);SOUL/AGENTS/SKILL 对齐实际职责;`subagent_entry.py` 去自愈。

**Tech Stack:** Python 3.12(InfluxDB client / pandas),hermes subagent_entry,pytest。

**Spec:** `docs/superpowers/specs/2026-07-28-data-perception-design.md`

---

## File Structure

| 文件 | 责任 | 动作 |
|---|---|---|
| `subagents/multi-dimensional-data-perception-agent/SOUL.md` | 身份/职责 | 改(删数据治理承诺,改忠实取数+标记缺失+零分析) |
| `subagents/.../AGENTS.md` | 执行规范 | 改(修 3 处过时:预加载→skill_view、CSV→InfluxDB、skill_view 禁令) |
| `subagents/.../skills/data-perception-core/SKILL.md` | 技能说明 | 改(注明 HRT=2h) |
| `subagents/.../skills/data-perception-core/scripts/get_data.py` | 取数脚本 | 改(metadata 加 hrt_hours/missing_points) |
| `workspace/skills/orchestrator-core/scripts/subagent_entry.py` | 子智能体共享入口 | 改(去自愈,全局 4 子智能体) |
| `tests/unit/test_get_data.py` | 单元测试 | 新建 |

---

## Task 1: SOUL.md 改职责(删数据治理,改忠实取数)

**Files:** Modify `subagents/multi-dimensional-data-perception-agent/SOUL.md`

- [ ] **Step 1: 改 "Your Role" 段**

把(第 15-23 行)的:
```
你是**多维数据感知子智能体**（Multi-Dimensional Data Perception）。使命：
> 获取多维时序监测数据，做清洗、标准化与时间对齐，为异常检测和规则推理提供高质量数据基础。
### Work Philosophy
- **严谨**：每一个缺失值都要记录，每一次插值都要说明理由，质量报告必须真实。
- **可靠**：稳定输出高质量数据；宁可报错，也不返回问题数据；流程可追溯。
- **多源整合**：统一进水 / 出水多指标（pH、COD、TN、NH3-N、TP、SS…）的格式与时空一致性。
```
改为:
```
你是**多维数据感知子智能体**（Multi-Dimensional Data Perception）。使命：
> **忠实取数**：获取多维时序监测数据（进水/出水多指标），保留原始（含缺失、异常值），标记缺失与 HRT，为异常检测和规则推理提供**未篡改**的数据基础。
### Work Philosophy
- **忠实**：异常值和缺失值是监控对象本身，绝不清洗/插值/标准化——保留原始，交下游分析。
- **标注**：标记哪些时间点缺数据（客观事实）、标注 HRT（当前工艺 2h），不改数据。
- **零分析**：不做异常检测、不判物理错误、不判违规——那是下游的活。
```

- [ ] **Step 2: 改 "Data Quality Standards" 段(第 25-33 行)**

删掉整个"Data Quality Standards"表格(完整性<5%/准确性<1% 等是清洗义,违背监控),替换为:
```
### 数据原则（监控理念）
- 异常值、缺失值是**监控对象**，绝不清洗/补齐。
- 缺失 = 数据质量问题（客观标记），不是要补的数。
- 标准化交给异常检测按算法需要自己做。
```

- [ ] **Step 3: 改 "Time Alignment" 段(第 34-40 行)**

改为(只标注 HRT，不做对齐):
```
### Time Alignment
- **水力停留时间(HRT)**：2 小时（当前工艺领域常量，标注进 metadata，对齐交下游）。
- **不做时间对齐**：进/出水各自忠实取，不预设因果对齐（下游按需用 HRT 自己对齐）。
- **时区**：UTC+8。
```

- [ ] **Step 4: 检查改动**

读一遍 SOUL.md，确认：① 无"清洗/插值/标准化/质量报告(清洗义)"字样；② 有"忠实取数/标记缺失/HRT标注/零分析"。

- [ ] **Step 5: Commit**

```bash
git add subagents/multi-dimensional-data-perception-agent/SOUL.md
git commit -m "refactor(data-perception): SOUL 改为忠实取数+标记缺失+零分析(去数据治理承诺)"
```

---

## Task 2: AGENTS.md 修 3 处过时

**Files:** Modify `subagents/multi-dimensional-data-perception-agent/AGENTS.md`

- [ ] **Step 1: 修"预加载"→"skill_view"**

把(第 11 行):
```
主智能体通过**共享入口 `subagent_entry.py`** 以 subprocess 调起你：你的 SOUL/AGENTS/MEMORY + SKILL.md 已被预加载进 prompt，任务以用户消息形式送达。
```
改为:
```
主智能体通过**共享入口 `subagent_entry.py`** 以 subprocess 调起你：你的 SOUL/AGENTS/MEMORY 已加载，任务以用户消息形式送达。你用 hermes 原生 **`skill_view`** 读取自己的 `SKILL.md`。
```

- [ ] **Step 2: 修"❌不要 skill_view"→"用 skill_view"**

把"执行纪律"下的:
```
- ❌ 不要 `skill_view` / `skills_list` / `memory` 探索
```
改为:
```
- ✅ 用 `skill_view('data-perception-core')` 读取技能说明，然后 `terminal` 跑脚本
- ❌ 不要翻 `scripts/` 别的脚本、不要 `memory` 探索
```

- [ ] **Step 3: 修"CSV 取数"→"InfluxDB"**

把 "Responsibilities" 段(第 35 行):
```
- 从 `shared/data/pollution_water_in.csv`、`shared/data/pollution_water_out.csv` 取数
- 缺失值处理、异常值过滤、时间戳解析
```
改为:
```
- 从 **InfluxDB**(`monitoring-data` bucket)取进水/出水数据
- **忠实取数**：保留原始(含缺失/异常值)，标记缺失时间点，**不做清洗/插值/标准化**
```

- [ ] **Step 4: Commit**

```bash
git add subagents/multi-dimensional-data-perception-agent/AGENTS.md
git commit -m "docs(data-perception): AGENTS 修 3 处过时(预加载→skill_view、CSV→InfluxDB)"
```

---

## Task 3: SKILL.md 注明 HRT

**Files:** Modify `subagents/.../skills/data-perception-core/SKILL.md`

- [ ] **Step 1: 在 SKILL.md 顶部(frontmatter 后)加 HRT 注明**

在 `# 数据获取技能` 标题下加一段:
```
## 工艺领域常量

**水力停留时间(HRT)= 2 小时**(当前工艺)。脚本会把 `hrt_hours=2` 标进 `data_result.json` 的 metadata，供下游(规则推理)按需做进水出水时间对齐。数据感知本身不做对齐。
```

- [ ] **Step 2: Commit**

```bash
git add subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/SKILL.md
git commit -m "docs(data-perception): SKILL 注明 HRT=2h 领域常量"
```

---

## Task 4: get_data.py metadata 加 hrt_hours(TDD)

**Files:**
- Modify: `subagents/.../skills/data-perception-core/scripts/get_data.py`
- Test: `tests/unit/test_get_data.py`

- [ ] **Step 1: 写失败测试**

创建 `tests/unit/test_get_data.py`:
```python
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# 项目根上 1 层（tests/unit/ → 项目根）
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
# get_data.py 路径
GD = ROOT / "subagents" / "multi-dimensional-data-perception-agent" / "skills" / "data-perception-core" / "scripts"
sys.path.insert(0, str(GD))


def test_metadata_has_hrt_hours(tmp_path, monkeypatch):
    """data_result.result.metadata 必须含 hrt_hours=2(领域常量)。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("get_data", GD / "get_data.py")
    gd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gd)

    # mock InfluxDB,返回最小数据
    fake_records = [{"timestamp": "2026-07-14 00:00:00", "pH": 7.4, "COD": 68.0}]
    monkeypatch.setenv("INFLUXDB_TOKEN", "fake-token")
    monkeypatch.setenv("SESSION_DIR", str(tmp_path))

    with patch.object(gd, "InfluxDBClient") as MockClient, \
         patch.object(gd, "_fetch_df") as mock_fetch:
        mock_fetch.return_value = MagicMock(rename=MagicMock(return_value=MagicMock(empty=False, tail=MagicMock(return_value=[]), iteritems=lambda: [])))
        # 直接测 metadata 构造（绕过复杂 mock，测常量）
        # 这里改成测 metadata dict 构造
        pass

    # 简化：直接断言常量
    from get_data import _HRT_HOURS  # 期望脚本定义此常量
    assert _HRT_HOURS == 2
```

> 说明：InfluxDB mock 较重，这里用"断言脚本定义了 `_HRT_HOURS=2` 常量"作最小测试。完整集成在 Task 7 端到端跑。

简化测试为:
```python
def test_hrt_constant():
    import importlib.util
    spec = importlib.util.spec_from_file_location("get_data", GD / "get_data.py")
    gd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gd)
    assert gd._HRT_HOURS == 2
```

- [ ] **Step 2: 运行测试,确认失败**

```bash
ecological_env/Scripts/python.exe -m pytest tests/unit/test_get_data.py::test_hrt_constant -v
```
预期：FAIL（`AttributeError: module 'get_data' has no attribute '_HRT_HOURS'`）

- [ ] **Step 3: 实现 — 在 get_data.py 加常量 + metadata**

在 `get_data.py` 顶部（`_KEEP_FIELDS` 后，约第 43 行）加:
```python
# 当前工艺的水力停留时间(小时)。标注进 metadata，供下游按需做进水出水时间对齐。
# 数据感知本身不做对齐(零分析)。
_HRT_HOURS = 2
```

在 `main()` 的 `result["result"]["metadata"]`（第 143-147 行）加 `hrt_hours`:
```python
            "metadata": {
                "time_range": time_range_str,
                "indicators": ["pH", "COD", "TN", "NH3-N", "TP", "SS", "flow_rate", "discharge_volume"],
                "hrt_hours": _HRT_HOURS,
                "data_source": "influxdb",
            },
```

- [ ] **Step 4: 运行测试,确认通过**

```bash
ecological_env/Scripts/python.exe -m pytest tests/unit/test_get_data.py::test_hrt_constant -v
```
预期：PASS

- [ ] **Step 5: Commit**

```bash
git add subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/get_data.py tests/unit/test_get_data.py
git commit -m "feat(data-perception): get_data metadata 加 hrt_hours=2 标注"
```

---

## Task 5: get_data.py 计算 missing_points(TDD)

**Files:**
- Modify: `subagents/.../skills/data-perception-core/scripts/get_data.py`
- Test: `tests/unit/test_get_data.py`

- [ ] **Step 1: 写失败测试**

在 `tests/unit/test_get_data.py` 加:
```python
def test_compute_missing_points_range():
    """range 模式：期望 start~end 每小时一条，实际缺的算 missing。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("get_data", GD / "get_data.py")
    gd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gd)

    # 实际只有 00:00 和 02:00，缺 01:00
    records = [
        {"timestamp": "2026-07-14 00:00:00"},
        {"timestamp": "2026-07-14 02:00:00"},
    ]
    missing = gd._compute_missing_points(records, use_range=True,
                                         start="2026-07-14", end="2026-07-14 02:00:00",
                                         hours_back=0)
    assert "2026-07-14 01:00:00" in missing


def test_compute_missing_points_hours():
    """hours 模式：以最新时间为准往前 N 小时，缺的算 missing。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("get_data", GD / "get_data.py")
    gd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gd)

    records = [
        {"timestamp": "2026-07-14 00:00:00"},
        {"timestamp": "2026-07-14 02:00:00"},
    ]
    missing = gd._compute_missing_points(records, use_range=False, start=None, end=None,
                                         hours_back=3)
    assert "2026-07-14 01:00:00" in missing
```

- [ ] **Step 2: 运行测试,确认失败**

```bash
ecological_env/Scripts/python.exe -m pytest tests/unit/test_get_data.py -v -k missing
```
预期：FAIL（`AttributeError: ... _compute_missing_points`）

- [ ] **Step 3: 实现 — 加 `_compute_missing_points` 函数**

在 `get_data.py`（`get_data_by_range` 后，`main` 前）加:
```python
def _compute_missing_points(records, use_range, start, end, hours_back):
    """计算缺失的时间点（期望每小时一条，实际记录里没有的）。

    数据感知只标记缺失（客观事实），不补齐（缺失是异常信号，交下游）。
    """
    import pandas as pd
    if not records:
        return []
    timestamps = [r["timestamp"] for r in records if r.get("timestamp")]
    if not timestamps:
        return []
    ts = pd.to_datetime(timestamps)
    actual = set(ts)
    if use_range and start and end:
        start_dt = pd.to_datetime(start)
        end_dt = pd.to_datetime(end)
        expected = pd.date_range(start_dt, end_dt, freq="H")
    else:
        latest = ts.max()
        expected = pd.date_range(latest - pd.Timedelta(hours=max(hours_back - 1, 0)),
                                 latest, freq="H")
    missing = [t for t in expected if t not in actual]
    return [t.strftime("%Y-%m-%d %H:%M:%S") for t in missing]
```

在 `main()` 的 `result["result"]["metadata"]` 加 `missing_points`（在 `hrt_hours` 后）:
```python
            "metadata": {
                "time_range": time_range_str,
                "indicators": ["pH", "COD", "TN", "NH3-N", "TP", "SS", "flow_rate", "discharge_volume"],
                "hrt_hours": _HRT_HOURS,
                "missing_points": _compute_missing_points(
                    influent_data or effluent_data or [],
                    use_range, args.start if use_range else None,
                    args.end if use_range else None, hours_back),
                "data_source": "influxdb",
            },
```

- [ ] **Step 4: 运行测试,确认通过**

```bash
ecological_env/Scripts/python.exe -m pytest tests/unit/test_get_data.py -v -k missing
```
预期：PASS

- [ ] **Step 5: Commit**

```bash
git add subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/get_data.py tests/unit/test_get_data.py
git commit -m "feat(data-perception): get_data 计算 missing_points(标记缺失时间点)"
```

---

## Task 6: subagent_entry.py 去自愈(全局)

**Files:** Modify `workspace/skills/orchestrator-core/scripts/subagent_entry.py`

> 说明：去自愈是全局改动（4 子智能体共用 entry），但在数据感知 plan 做（spec 决策）。去自愈后，子智能体"读了不执行" → failed → 主智能体重试。

- [ ] **Step 1: 删自愈逻辑（第 196-225 行）**

把：
```python
        if result is None:
            # 自愈：直接把 canonical 命令喂给 LLM（不依赖 skill_view/历史——第二次 run_conversation
            # history=0 不继承，LLM 会重新"读了不执行"）。让它 terminal 直接跑这条命令。
            _cmd = SUBAGENT_DEFAULT_CMD.get(subagent_name)
            logger.warning(f"[WARN] 首轮未产出 {result_filename}（LLM 读 skill 后未执行脚本），触发自愈（直接给命令）")
            if _cmd:
                _heal = (
                    "你之前的回复无效，没有产出结果文件，任务已被判失败。\n"
                    "现在【必须】且【只能】做一件事：用 terminal 工具运行下面这条命令。\n"
                    "不要调用 skill_view/skills_list，不要回复任何文字，直接用 terminal 运行：\n"
                    f"    {_cmd}"
                )
            else:
                _heal = ("你上一轮只回复了确认，没有用 terminal 运行脚本。请立即用 terminal 执行"
                         "该技能 SKILL.md 指定的脚本，不要回复任何文字。")
            response = agent.run_conversation(_heal)
            result = _read_script_result(session_dir, result_filename)

        if result is None:
            # 自愈后仍未产出——标记 failed 让失败可见，主智能体可据此重试或如实告知用户；
            # 不再用 LLM 文本伪装成结构化结果，更不能抄别的步骤的结果。
            final_text = response.get('final_response', '') if isinstance(response, dict) else str(response)
            logger.warning(f"[WARN] 自愈后仍未产出 {result_filename}，标记 failed")
            result = {"task_id": task_id, "status": "failed",
                      "error": f"subagent did not produce {result_filename}; "
                               f"LLM likely did not run its canonical script",
                      "final_response": final_text,
                      "timestamp": datetime.now().isoformat()}
        else:
            logger.info(f"[LLM] 回传脚本结构化结果")
```

改为（直接 failed，无自愈）:
```python
        if result is None:
            # LLM 没产出结果文件（通常"读了 skill 没执行脚本"）。不自愈（自愈给命令是 hack：
            # hermes 第二轮 run_conversation history=0 不继承，且时间窗不准）。直接 failed，
            # 让主智能体决定重试或如实告知用户。
            final_text = response.get('final_response', '') if isinstance(response, dict) else str(response)
            logger.warning(f"[WARN] 未产出 {result_filename}（LLM 可能读了 skill 没执行脚本），标记 failed")
            result = {"task_id": task_id, "status": "failed",
                      "error": f"subagent did not produce {result_filename}; "
                               f"LLM likely did not run its canonical script",
                      "final_response": final_text,
                      "timestamp": datetime.now().isoformat()}
        else:
            logger.info(f"[LLM] 回传脚本结构化结果")
```

- [ ] **Step 2: 删 `SUBAGENT_DEFAULT_CMD` 映射（不再用）**

删掉 `subagent_entry.py` 里定义 `SUBAGENT_DEFAULT_CMD = {...}` 的整段（约第 60-69 行附近，注释含"自愈兜底用"）。

- [ ] **Step 3: 语法检查**

```bash
ecological_env/Scripts/python.exe -m py_compile workspace/skills/orchestrator-core/scripts/subagent_entry.py && echo OK
```
预期：输出 `OK`

- [ ] **Step 4: Commit**

```bash
git add workspace/skills/orchestrator-core/scripts/subagent_entry.py
git commit -m "refactor(subagent-entry): 去自愈给命令(全局),失败交主智能体重试"
```

---

## Task 7: 端到端验证

**Files:** 无（运行验证）

- [ ] **Step 1: 重启 agent 服务**

```bash
# 停旧 agent（如有），重启
ecological_env/Scripts/python.exe scripts/start_agent.py
```

- [ ] **Step 2: 触发数据感知查询，验证 metadata**

发一个查询（如"最近24小时进水数据"），然后检查最新 session 的 `data_result.json`：
```bash
ls -t sessions/session_* | head -1
# 读该 session 的 data_result.json，确认 result.metadata 含 hrt_hours=2 和 missing_points
```
或写个临时验证脚本：
```bash
ecological_env/Scripts/python.exe -c "
import json, glob, os
sd = sorted(glob.glob(r'sessions/session_*'), key=os.path.getmtime, reverse=True)[0]
d = json.load(open(os.path.join(sd, 'data_result.json'), encoding='utf-8'))
md = d.get('result', {}).get('metadata', {})
print('hrt_hours =', md.get('hrt_hours'))
print('missing_points =', md.get('missing_points'))
assert md.get('hrt_hours') == 2, 'hrt_hours missing'
print('OK')
"
```

- [ ] **Step 3: 运行冒烟测试（确认去自愈后链路通）**

```bash
ecological_env/Scripts/python.exe scripts/smoke_test.py
```
预期：PASS（去自愈后，若 LLM 正常执行则通过；若偶发"读了不执行"则主智能体重试）

- [ ] **Step 4: Commit（若有验证脚本残留则清理，无则跳过）**

```bash
# 无代码改动，跳过 commit
```

---

## Self-Review

**Spec coverage：**
- ✅ 忠实取数(不清洗)：get_data 现状已不清洗(NaN→None)，spec 确认
- ✅ 标记缺失：Task 5 `_compute_missing_points`
- ✅ HRT 标注：Task 4 `_HRT_HOURS` + metadata
- ✅ 零分析：Task 1 SOUL 改职责
- ✅ 不清洗/插值/标准化：Task 1 SOUL + 现状不清洗
- ✅ AGENTS 过时修：Task 2（3 处）
- ✅ 去自愈：Task 6
- ⏸ build_chart 调用：可视化 plan（Plan 5）做，本 plan 不含
- ⏸ InfluxDB range 性能：数据小(~4900条)，影响小，后续优化（spec 已标性能项）

**Placeholder scan：** 无 TBD/TODO，每步有具体代码/命令。

**Type consistency：** `_HRT_HOURS`（Task 4 定义）→ metadata `hrt_hours`（Task 4/5 用）；`_compute_missing_points`（Task 5 定义）→ metadata `missing_points`。一致。
