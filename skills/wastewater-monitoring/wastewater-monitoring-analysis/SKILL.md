---
name: wastewater-monitoring-analysis
description: Complete wastewater monitoring data analysis pipeline — data perception, anomaly detection, rule reasoning, and alert/disposition for influent and effluent wastewater indicators (pH, COD, TN, NH3-N, TP, flow).
category: wastewater-monitoring
triggers:
  - "出水监测"
  - "进水监测"
  - "违规检测"
  - "异常分析"
  - "预警工单"
  - "pH"
  - "COD"
  - "TN"
  - "NH3-N"
  - "TP"
  - "是否超标"
  - "去除效率"
---

# Wastewater Monitoring Analysis Skill

## Trigger Conditions

- User requests analysis of influent/effluent monitoring data
- User asks about violations, anomalies, compliance, or alerts
- User says "分析最近N小时监测数据", "是否违规", "检测异常", "生成预警工单"
- Any query involving wastewater indicators: pH, COD, TN, NH3-N, TP, flow rate

---

## Task Classification and Subagent Routing

```
用户查询
    ↓
[1] 需要数据吗？→ multi-dimensional-data-perception
    ↓
[2] 需要异常检测吗？→ anomaly-detection
    ↓
[3] 需要违规判定吗？→ rule-reasoning
    ↓
[4] 需要预警/工单吗？→ disposition-execution
    ↓
[5] 整合结果，生成报告
```

**Full pipeline (违规检测任务)**: All 4 subagents in sequence.
**Analysis-only**: data-perception + anomaly-detection.
**Compliance check**: data-perception + rule-reasoning.
**Alert response**: disposition-execution only.

---

## Execution Steps

### Step 1: Data Perception

Call the subagent first — it returns structured influent + effluent data (records with timestamp, indicators, flow, discharge_volume) + metadata:

```
call_subagent(
    subagent_name="multi-dimensional-data-perception",
    task="获取最近24小时出水监测数据...",
    context={data_paths, time_window, indicators}
)
```

**Fallback on Timeout** — The subagent has a 600s timeout and may occasionally fail. When it does, do NOT retry blindly. Fall back to direct pandas processing:
1. Data location: `shared/data/pollution_water_out.csv` (effluent), `shared/data/pollution_water_in.csv` (influent), or `data/*.csv` relative to project root.
2. CSV processing: `encoding='utf-8-sig'`, `engine='python'`, `dtype=str` then `pd.to_numeric(..., errors='coerce')`.
3. Column mapping: 监测时间→timestamp, pH值→pH, 化学需氧量浓度（毫克/升）→COD, 总氮浓度（毫克/升）→TN, 氨氮浓度（毫克/升）→NH3_N, 总磷浓度（毫克/升）→TP, 流量（升/秒）→flow, 悬浮物浓度（毫克/升）→SS.
4. For "last 24 hours", filter: `timestamp >= latest_time - timedelta(hours=24)` where `latest_time` is the max timestamp in the data (NOT the system clock).
5. Do NOT describe the timeout as a "system failure" to the user — just proceed with direct analysis.

### Step 2: Anomaly Detection

**Call the subagent** — it runs isolation forest, LOF, HBOS and returns scored anomalies:

```
call_subagent(
    subagent_name="anomaly-detection",
    task="对最近24小时出水数据进行异常检测...",
    context={effluent_summary, influent_summary, key_patterns}
)
```

The subagent returns `anomalies[]` (with type, score, indicator, timestamp, votes) + `summary` (counts by type/indicator/data_type). Score > 2.0 = high severity.

**Key anomaly checks** (what the subagent evaluates):

| Check | Method | Threshold | Violation Type |
|-------|--------|-----------|----------------|
| Constant value | Sliding window std | std < 0.05 for 2+ hours | Bottle interference (插瓶干扰) |
| Overall variance | Global std | std < 0.1 | Suspect for pH, TP |
| Spike | Z-score | \|z\| > 2.5 | Point anomaly |
| Trend | Linear regression slope | Relative change > 10% | Trend anomaly |
| Over-smoothing | Polynomial R² | R² > 0.99 | Artificial fitting (人工拟合) |
| Data completeness | Missing rate | > 20% | Malicious evasion (恶意逃避) |
| Multi-indicator sync | 5 indicators constant | 3+ indicators with low std | Combined anomaly |

### Step 3: Rule Reasoning

Call the subagent:

```
call_subagent(
    subagent_name="rule-reasoning",
    task="基于检测结果进行规则推理...",
    context={anomalies, statistics, violations, removal_efficiency}
)
```

Key validations:
- GB 18918-2002 limits: pH 6-9, COD ≤100, TN ≤20, NH3-N ≤15, TP ≤1.0
- Removal efficiency: COD >70%, TN >70%, NH3-N >60%, TP >80%
- Process mechanism: NH3-N/TN correlation ≥0.3, flow-concentration coupling

### Step 4: Alert and Disposition

Call the subagent — it fuses anomaly confidence + rule-reasoning confidence into a final score:

```
call_subagent(
    subagent_name="disposition-execution",
    task="综合研判并生成三级预警...",
    context={anomaly_count, rule_reasoning_result, compliance_status}
)
```

The subagent returns:
- `fusion.fused_confidence`: Weighted blend of anomaly confidence and rule-reasoning confidence (default 50/50 weights)
- `alert.level_cn`: 严重(红) / 较重(橙) / 一般(黄)
- `alert.action_cn`: Disposition action (e.g., "现场核查")
- `work_order.id`: Unique ticket number (e.g., WO-YYYYMMDD-NNN-xxxxx)
- `work_order.inspection_points[]`: Structured list — each with `{location, action, priority: high|low}`
- `work_order.recommended_actions[]`: Immediate + medium-term action items
- `work_order.legal_references[]`: Applicable laws/regulations
- `work_order.data_traceback`: Time range, affected indicators, data source for audit trail

Alert level thresholds:
- 🔴 **严重 (Critical)**: Fused suspicion ≥ 0.8, multi-indicator anomaly
- 🟠 **较重 (Medium)**: Fused suspicion 0.5-0.8, single indicator anomaly or mechanism violation
- 🟢 **一般 (Low)**: Fused suspicion 0.2-0.5, borderline cases

### Step 5: Report Integration

**Conclusion-first format** (user prefers concise, actionable output):

```
🌊 完整违规研判报告
━━━━━━━━━━━━━━━━━━━
一、数据感知 — Statistics table + data quality
二、异常检测 — Anomaly summary table (count, types, high-score items)
三、规则推理 — 违规类型 + 置信度 + 机理违规 + 合规状态
四、处置工单 — 工单号 + 预警等级 + 融合置信度 + 核查要点
五、综合研判 — 结论一句话 + 核心证据链(3-4条) + 建议
━━━━━━━━━━━━━━━━━━━
流程耗时: ~X秒（4个子智能体）
```

**Critical rule**: When violation is detected, lead with the **core evidence chain** — the 3-4 concrete observations (e.g., "出水pH 01:00-08:00恒定7.03", "流量断崖下跌293→56", "NH3-N/TN相关系数0.257<0.3") that connect data → anomaly → rule → alert. Do NOT bury these in tables alone — state them as bullet points in the conclusion.

Standard report structure (if user requests detail):
1. 数据感知 — Statistics table + data quality
2. 异常检测 — Anomaly list with types, times, confidence
3. 规则推理 — Compliance check + process validation + pattern matching
4. 综合研判 — Alert level + core judgment logic
5. 处置建议 — Immediate actions + medium-term follow-up + legal references

**⚠ "达标 ≠ 清白的" (Compliance ≠ No Fraud)** — When ALL effluent indicators are numerically within limits but anomaly/rule subagents still return a violation (e.g., 暗管偷排 with constant values, flow drops, or mechanism violations), this is NOT a false positive. "Too clean" data is itself a fraud indicator. Report must explicitly state: Section 1 shows compliance ✅, but Sections 2-4 explain why compliance is SUSPECT (constant values, flow-concentration decoupling, mechanism violations). Final conclusion: "虽然数值达标，但数据模式异常 → 疑似违规". See `references/compliance_fraud_patterns.md` for a real session case study.

---

## Pitfalls

1. **Subagent timeout is occasional, not default** — `multi-dimensional-data-perception` has a 600s timeout. In practice it returns structured data reliably. Always have the fallback pandas path ready, but do NOT skip the subagent call preemptively.

2. **CSV encoding** — Files have BOM + Chinese headers. Use `encoding='utf-8-sig'` and `engine='python'`. Reading without BOM handling produces garbled first column.

3. **Type coercion** — Some CSV rows may have concatenated string values in numeric columns. Always use `pd.to_numeric(..., errors='coerce')` and verify no unexpected NaN after conversion.

4. **Effluent vs Influent schema difference** — Effluent has `SS` (悬浮物) column; influent does not. Handle with `errors='ignore'` when dropping/renaming.

5. **"Last 24 hours" is data-relative, not system-clock-relative** — Current data ends at 2024-12-31. The window is `max_timestamp - 24h`, not `now - 24h`.

6. **Session directory for shared data** — Create via `create_session()`, then save intermediate results as JSON under `sessions/session_YYYYMMDD_HHMMSS/`.

7. **Anomaly-detection subagent is reliable** — Call it for full pipeline runs. It returns scored anomalies (type, score, votes) from isolation forest, LOF, and HBOS models. Use pandas fallback only if the subagent times out or when doing quick exploratory checks.

8. **Fusion confidence from disposition-execution** — The subagent fuses anomaly confidence and rule-reasoning confidence (default 50/50 weights) into `fused_confidence`. Use this final score, not individual subagent scores, for alert level classification. Example: anomaly 0.73 + rule 0.855 → fused 0.792 → "较重 (橙色)".

9. **"Too clean" data is a red flag** — If all effluent indicators are well below limits (COD < 50 when limit is 100, TN < 10 when limit is 20), this is NOT a clean bill of health. Combined with constant values, flow drops, or mechanism violations (e.g., NH3-N/TN correlation 0.257 < 0.3), it strongly suggests 暗管偷排 or other fraud. Do NOT conclude "全部达标，无违规" just because numbers are within limits.

10. **Pass context between subagents** — Chain results: data-perception → anomaly-detection (with structured data summary) → rule-reasoning (with anomaly details) → disposition-execution (with rule reasoning). Each `context` parameter should summarize the prior subagent's key findings as JSON-like key-value pairs.

11. **Full pipeline execution time** — All 4 subagents sequentially (data-perception + anomaly-detection + rule-reasoning + disposition-execution) typically completes in **~2 minutes**. Each subagent is an **LLM-driven agent** (subprocess → shared `subagent_entry.py` → AIAgent session → LLM reads preloaded SKILL.md → runs canonical script via terminal). Anti-wandering guardrails: SKILL.md preloaded into prompt + terminal-only tools + `max_iterations=4`. If a single subagent takes >120s, suspect a timeout — check `call_subagent` error handling.

12. **Alert level discrepancy (规则推理 vs 处置执行)** — The rule-reasoning subagent reports its own `suspicion_level` (e.g., "critical") based on `confidence` (e.g., 0.855). The disposition-execution subagent **fuses** this with anomaly confidence and produces a potentially **different** `alert.level_cn` (e.g., 0.792 → "较重/橙色" instead of "严重/红色"). **Always report both**: rule-reasoning confidence + fused confidence + final alert level. Do NOT conflate the two — the fused score is the authoritative one for work order classification.

13. **Flow-volume mismatch is the strongest 暗管偷排 indicator** — When effluent flow_rate drops >50% while influent flow_rate remains stable (e.g., effluent 290→56 vs influent 319→340), this is the primary evidence chain for secret pipe detection. Always highlight the 进水流量 vs 出水流量 comparison in the report.

14. **`call_subagent` context parameter** — Accepts both JSON-serialized strings and Python dicts (auto-serialized by the framework). Pass concise key-value summaries: counts, ranges, timestamps, constant-value segments. Do NOT pass pandas DataFrames, numpy arrays, or file handles — they will fail silently or produce garbled output.

15. **First subagent call needs no context; subsequent calls chain on prior results** — `multi-dimensional-data-perception` is the pipeline entry point and operates standalone. Each downstream subagent (anomaly-detection → rule-reasoning → disposition-execution) needs the prior subagent's key findings in `context`. Skipping context breaks the chain.

16. **Actual pipeline timing** — Full 4-subagent pipeline observed at **~15 seconds** (2026-07-23, confirmed): data-perception ~3s, anomaly-detection ~5s, rule-reasoning ~11s, disposition-execution ~2s. Well within the 15-70s documented range.

---

## See Also

- `references/regulatory_limits.md` — GB 18918-2002 detailed limits and penalty provisions
- `references/violation_patterns.md` — 5 violation types (插瓶干扰, 稀释排放, 人工拟合, 恶意逃避, 暗管偷排) + "达标但欺诈" composite pattern with detection thresholds and evidence patterns
- `references/compliance_fraud_patterns.md` — Case study: "达标但欺诈" pattern (all indicators compliant yet fraud detected, from 2026-07-23 session)
- `scripts/analyze_effluent_24h.py` — Standalone 24h effluent analysis script (fallback when subagent pipeline unavailable)