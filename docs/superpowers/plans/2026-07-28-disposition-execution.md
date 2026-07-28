# 处置执行子智能体 Implementation Plan(Plan 4/5)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox.

**Goal:** 处置执行废弃预警级别(一般/较重/严重)+ 融合共识,直接消费规则推理的嫌疑等级(高/中/低/无)→ 处置行动,工单带证据。

**Architecture:** `run_disposition` 删 ConsensusEngine + 旧预警分级,读 `rule_reasoning_result.suspicion_level` → 处置行动映射;`work_order` 带 `evidence_points`。

**Tech Stack:** Python 3.12,pytest。

**Spec:** `docs/superpowers/specs/2026-07-28-disposition-execution-design.md`

---

## File Structure

| 文件 | 责任 | 动作 |
|---|---|---|
| `subagents/.../run_disposition.py` | 主脚本 | 改(废弃融合/旧预警,读嫌疑→处置) |
| `subagents/.../work_order_generator.py` | 工单生成 | 改(带 evidence_points) |
| `subagents/.../consensus_engine.py` | 融合共识 | 废弃(不再调用) |
| `subagents/.../alert_classifier.py` | 旧预警分级 | 改(嫌疑→处置映射)或废弃 |
| `subagents/.../SOUL.md` / `AGENTS.md` | 身份/规范 | 改(废弃预警3级,改嫌疑4档) |

---

## Task 1: SOUL.md / AGENTS.md(废弃预警 3 级,改嫌疑 4 档 → 处置)

**Files:** Modify `subagents/disposition-execution-agent/AGENTS.md`、`SOUL.md`

- [ ] **Step 1: AGENTS 预警等级段改为嫌疑→处置映射**

把"预警等级(3 级:general/moderate/serious)"段改为:
```
## 嫌疑等级 → 处置行动(消费规则推理结论)
| 嫌疑等级 | 处置行动 | 工单 |
|---|---|---|
| 高 | 立即调查取证 | 出工单(核查+法规+取证) |
| 中 | 现场核查 | 出工单(核查) |
| 低 | 持续监控 | 监控建议 |
| 无 | 无违规 | 正常报告 |

废弃旧预警级别(一般/较重/严重)和融合共识——前两个子智能体已综合,处置执行只消费嫌疑等级。
```

- [ ] **Step 2: 删 AGENTS "融合共识算法"段**

删掉"融合置信度 = anomaly_conf×0.4 + violation_conf×0.6"那段(废弃)。

- [ ] **Step 3: 修过时(预加载→skill_view)** 同前。

- [ ] **Step 4: Commit**

```bash
git add subagents/disposition-execution-agent/AGENTS.md subagents/disposition-execution-agent/SOUL.md
git commit -m "docs(disposition): 废弃预警3级+融合,改嫌疑4档→处置行动"
```

---

## Task 2: run_disposition 废弃融合/旧预警,读嫌疑→处置(核心)

**Files:** Modify `subagents/.../run_disposition.py`

- [ ] **Step 1: 改 main — 删 ConsensusEngine + 旧预警,直接读 suspicion_level**

在 `main`(第 202-247 行附近),把"融合共识 + 预警分级"段:
```python
        # 执行融合共识
        consensus_engine = ConsensusEngine()
        ...
        fusion_result = consensus_engine.fuse_results(...)
        alert_info = alert_classifier.classify_alert(anomaly_result, violation_result)
```
改为(直接读嫌疑等级 → 处置行动):
```python
        # 直接读规则推理的嫌疑等级(废弃融合共识 + 旧预警分级)
        suspicion_level = "none"
        violation_types = []
        evidence_points = []
        if violation_result and "result" in violation_result:
            res = violation_result["result"]
            suspicion_level = res.get("suspicion_level", "none")
            violation_types = res.get("violation_types") or res.get("violation_type_names") or []
            evidence_points = res.get("evidence_points", [])

        # 嫌疑等级 → 处置行动映射
        ACTION_MAP = {
            "high": ("立即调查取证", True),
            "medium": ("现场核查", True),
            "low": ("持续监控", True),
            "none": ("无违规", False),
        }
        action, need_work_order = ACTION_MAP.get(suspicion_level, ("持续监控", True))
```

- [ ] **Step 2: 改 output — 废弃 alert/fusion,改 suspicion/action/work_order**

把 output 的 `result`(第 254-286 行)改为:
```python
                "suspicion_level": suspicion_level,
                "violation_types": violation_types,
                "action": action,
                "confidence": violation_result.get("result", {}).get("confidence", 0.0) if violation_result else 0.0,
                "work_order": work_order_generator.generate_work_order(
                    {"suspicion_level": suspicion_level, "violation_types": violation_types,
                     "action": action}, data_context) if need_work_order else None,
                "report": alert_report.to_dict() if need_work_order else None,
                "evidence_points": evidence_points,
```
（删掉 `alert`(旧预警 level)/`fusion`(共识)字段）

- [ ] **Step 3: 删 consensus_engine/alert_classifier 的调用**

确保 `main` 不再 `import`/实例化 `ConsensusEngine`/`AlertClassifier`(或保留文件但 main 不调用)。

- [ ] **Step 4: 语法检查**

```bash
ecological_env/Scripts/python.exe -m py_compile subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/run_disposition.py && echo OK
```

- [ ] **Step 5: Commit**

```bash
git add subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/run_disposition.py
git commit -m "refactor(run_disposition): 废弃融合/旧预警,读嫌疑等级→处置行动"
```

---

## Task 3: work_order_generator 工单带 evidence_points

**Files:** Modify `subagents/.../work_order_generator.py`

- [ ] **Step 1: 确认 work_order 含核查要点 + 法规引用 + 处置建议**

读 `work_order_generator.py`,确认 `generate_work_order` 输出含 `inspection_points`/`legal_references`/`recommended_actions`。若缺,补:
```python
def generate_work_order(self, alert_info, data_context):
    return {
        "id": f"WO_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "alert_level": alert_info.get("suspicion_level"),
        "violation_types": alert_info.get("violation_types", []),
        "inspection_points": [...],  # 来自 data_context(异常时间段/指标)
        "legal_references": [...],   # 来自 evidence_points 的法规
        "recommended_actions": [...], # 按 suspicion_level 映射
    }
```

- [ ] **Step 2: 在 run_disposition 传 evidence_points 给 work_order_generator**

(若 work_order_generator 需 evidence 生成 legal_references,在 Task 2 Step 2 的 generate_work_order 调用里传 evidence_points)

- [ ] **Step 3: Commit(若有改动)**

```bash
git add subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/work_order_generator.py
git commit -m "feat(work_order): 工单带核查要点+法规引用(evidence_points)"
```

---

## Task 4: 废弃 consensus_engine / alert_classifier(标注,不删文件)

**Files:** `subagents/.../consensus_engine.py`、`alert_classifier.py`

- [ ] **Step 1: 在文件顶部加废弃说明**

在 `consensus_engine.py` 和 `alert_classifier.py` 顶部 docstring 加:
```python
"""[已废弃] 规则推理已综合 anomaly+violation 成嫌疑等级,处置执行直接消费嫌疑等级,
不再需要融合共识(ConsensusEngine)和旧预警分级(AlertClassifier)。
保留文件供参考,run_disposition 不再调用。"""
```

- [ ] **Step 2: Commit**

```bash
git add subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/consensus_engine.py subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/alert_classifier.py
git commit -m "chore(disposition): 标注consensus_engine/alert_classifier废弃"
```

---

## Task 5: 端到端验证

- [ ] **Step 1: 跑全链路,检查 disposition_result**

```bash
ecological_env/Scripts/python.exe -c "
import json, glob, os
sd = sorted(glob.glob(r'sessions/session_*'), key=os.path.getmtime, reverse=True)[0]
d = json.load(open(os.path.join(sd,'disposition_result.json'), encoding='utf-8'))
res = d.get('result',{})
print('suspicion_level=', res.get('suspicion_level'))
print('action=', res.get('action'))
print('work_order=', bool(res.get('work_order')))
assert 'alert' not in res, '旧预警 alert 应废弃'
assert 'fusion' not in res, '融合 fusion 应废弃'
assert 'suspicion_level' in res and 'action' in res
print('OK')
"
```

- [ ] **Step 2: 冒烟测试**

```bash
ecological_env/Scripts/python.exe scripts/smoke_test.py
```

---

## Self-Review

**Spec coverage:**
- ✅ 废弃预警级别+融合:Task 1/2/4
- ✅ 消费嫌疑等级→处置:Task 2
- ✅ 工单带证据:Task 3
- ✅ AGENTS 改嫌疑 4 档:Task 1
- ⏸ consensus_engine/alert_classifier 废弃:Task 4 标注(保留文件,run_disposition 不调用)

**Placeholder scan:** Task 3 work_order 内容若现状已实现则跳过,否则补——执行时读 work_order_generator 确认。

**Type consistency:** rule_reasoning_result.suspicion_level(high/medium/low/none)→ run_disposition 读 → ACTION_MAP 映射。一致。
