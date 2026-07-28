# 规则推理子智能体 Implementation Plan(Plan 3/5)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox.

**Goal:** 规则推理对标资料:4 类违规 + 4 条工艺规则(资料精确判据)+ 嫌疑矩阵 + 异常特征对接(读异常检测 5 类 features);缺数据(工况/停产)标 missing_data。

**Architecture:** `process_validator` 改 4 条工艺规则判据(标准差+异常特征,非相关性)+ HRT 对齐;`run_rule_reasoning` 读 anomaly features + 嫌疑矩阵;知识库补违规模式特征库。

**Tech Stack:** Python 3.12(pandas/numpy),pytest。

**Spec:** `docs/superpowers/specs/2026-07-28-rule-reasoning-design.md`

---

## File Structure

| 文件 | 责任 | 动作 |
|---|---|---|
| `subagents/.../process_validator.py` | 工艺规则校验 | 改(4 条规则资料判据 + HRT 对齐 + 多指标同步突降) |
| `subagents/.../regulation_matcher.py` | 法规阈值校验 | 改(排放标准阈值) |
| `subagents/.../run_rule_reasoning.py` | 主脚本 | 改(读 anomaly features + 嫌疑矩阵 + missing_data) |
| `shared/knowledge/violation_patterns/violation_patterns.md` | 违规模式特征库 | 改(4 类 ↔ 特征组合) |
| `subagents/.../SOUL.md` / `AGENTS.md` | 身份/规范 | 改(4 类违规 + 4 条规则 + skill_view) |
| `tests/unit/test_process_validator.py` | 单元测试 | 新建 |

---

## Task 1: SOUL.md / AGENTS.md 对齐(4 类违规 + 4 条规则 + 嫌疑矩阵)

**Files:** Modify `subagents/rule-reasoning-agent/AGENTS.md`、`SOUL.md`

- [ ] **Step 1: AGENTS 违规类型改 4 类(对标资料)**

把"违规类型(5 类:bottle_interference/data_dilution/secret_pipe/false_shutdown/formula_tampering)"改为:
```
## 违规模式(4 类,对标资料)
| 模式 | 初版状态 | 主要判据 |
|---|---|---|
| 插瓶干扰 | ✅ 完整 | pH-COD 协同 + 氨氮-总氮转化 |
| 稀释排放 | ✅ 完整 | 质量平衡 + 多指标同步突降 |
| 人工拟合 | ⚠ 简化(缺工况) | 趋势异常(无工况校验) |
| 恶意逃避 | ❌ TODO | 需停产申报数据 |
```

- [ ] **Step 2: AGENTS 工艺规则改 4 条(资料判据)+ 嫌疑矩阵**

替换"工艺机理规则"段为:
```
## 工艺规则(4 条,资料精确判据)
| 规则 | 判据 | 异常特征 | 判向 |
|---|---|---|---|
| pH-COD 协同 | pH std≤0.1 且 COD std≤5.0 mg/L | + 平稳 | 插瓶 |
| 氨氮-总氮转化 | 氨氮突降而总氮基本不变 | + 突变 | 插瓶 |
| 质量平衡 | 去除率偏差 > 0.2 | + 趋势/突变 | 稀释 |
| 多指标同步突降 | 2+ 污染物同步下降 >50% | + 突变 | 稀释 |

质量平衡按 `data_result.metadata.hrt_hours` 做进水出水时间对齐。

## 嫌疑等级矩阵(资料)
| | 工艺违背 | 工艺无违背 |
|---|---|---|
| 法规违规(超阈值) | 高 | 低 |
| 法规未违规 | 中 | 无 |
```

- [ ] **Step 3: 修过时(预加载→skill_view)** 同数据感知 Plan Task 2。

- [ ] **Step 4: Commit**

```bash
git add subagents/rule-reasoning-agent/AGENTS.md subagents/rule-reasoning-agent/SOUL.md
git commit -m "docs(rule-reasoning): AGENTS 对标资料(4类违规+4条规则判据+嫌疑矩阵)"
```

---

## Task 2: process_validator 改 4 条工艺规则(资料判据 + HRT 对齐)— 核心

**Files:**
- Modify: `subagents/.../process_validator.py`
- Test: `tests/unit/test_process_validator.py`

- [ ] **Step 1: 写失败测试**

创建 `tests/unit/test_process_validator.py`:
```python
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import pandas as pd
import numpy as np


def test_ph_cod_bottle_interference():
    """pH std≤0.1 且 COD std≤5.0 + 平稳异常 → 插瓶。"""
    from subagents.rule_reasoning_agent.skills.rule_reasoning_core.scripts.process_validator import ProcessValidator
    v = ProcessValidator()
    # pH 几乎恒定, COD 几乎恒定
    influent = pd.DataFrame({"pH值": [7.0]*20, "化学需氧量浓度（毫克/升）": [50.0]*20})
    anomalies = [{"features": ["平稳"], "indicator": "pH"}, {"features": ["平稳"], "indicator": "COD"}]
    result = v.validate(anomalies, {}, {}, data=influent)
    types = [p.get("pattern") for p in result.get("matched_patterns", [])]
    assert "插瓶干扰" in types or "bottle_interference" in types


def test_multi_indicator_dilution():
    """2+ 污染物同步突降 >50% + 突变 → 稀释。"""
    from subagents.rule_reasoning_agent.skills.rule_reasoning_core.scripts.process_validator import ProcessValidator
    v = ProcessValidator()
    effluent = pd.DataFrame({
        "化学需氧量浓度（毫克/升）": [100]*10 + [40]*10,   # 突降 60%
        "氨氮浓度（毫克/升）": [5]*10 + [2]*10,             # 突降 60%
    })
    anomalies = [{"features": ["突变"], "indicator": "COD"}, {"features": ["突变"], "indicator": "氨氮"}]
    result = v.validate(anomalies, {}, {}, data=effluent)
    types = [str(p.get("pattern")) for p in result.get("matched_patterns", [])]
    assert any("稀释" in t for t in types)
```

- [ ] **Step 2: 运行,确认失败**(`pytest -k process` FAIL,判据不对)

```bash
ecological_env/Scripts/python.exe -m pytest tests/unit/test_process_validator.py -v
```

- [ ] **Step 3: 改 process_validator 的判据(资料精确判据)**

在 `ProcessValidator.validate` 里,按资料判据实现 4 条规则。核心改动:
```python
    def validate(self, anomalies, correlation_results, trend_results, data=None, hrt_hours=2):
        """4 条工艺规则(资料判据)。data: effluent df(中文列名)。"""
        matched_patterns = []
        feature_set = set()
        for a in anomalies:
            feature_set.update(a.get("features", []))

        if data is None or data.empty:
            return {"matched_patterns": [], "violations_count": 0}

        df = data

        # 规则1: pH-COD 协同(插瓶) — pH std≤0.1 且 COD std≤5.0 + 平稳异常
        ph_col = "pH值"
        cod_col = "化学需氧量浓度（毫克/升）"
        if ph_col in df.columns and cod_col in df.columns and "平稳" in feature_set:
            ph_std = float(df[ph_col].std())
            cod_std = float(df[cod_col].std())
            if ph_std <= 0.1 and cod_std <= 5.0:
                matched_patterns.append({"pattern": "插瓶干扰", "rule": "pH-COD协同",
                                         "ph_std": ph_std, "cod_std": cod_std})

        # 规则2: 氨氮-总氮转化(插瓶) — 氨氮突降而总氮基本不变 + 突变
        nh3_col = "氨氮浓度（毫克/升）"
        tn_col = "总氮浓度（毫克/升）"
        if nh3_col in df.columns and tn_col in df.columns and "突变" in feature_set:
            nh3_drop = self._max_drop_ratio(df[nh3_col])
            tn_change = self._max_drop_ratio(df[tn_col])
            if nh3_drop > 0.3 and tn_change < 0.1:  # 氨氮突降, 总氮不变
                matched_patterns.append({"pattern": "插瓶干扰", "rule": "氨氮-总氮转化"})

        # 规则3: 多指标同步突降(稀释) — 2+ 污染物同步下降 >50% + 突变
        if "突变" in feature_set:
            pollutant_cols = ["化学需氧量浓度（毫克/升）", "氨氮浓度（毫克/升）",
                              "总磷浓度（毫克/升）", "悬浮物浓度（毫克/升）"]
            sync_drop = []
            for col in pollutant_cols:
                if col in df.columns:
                    drop = self._max_drop_ratio(df[col])
                    if drop > 0.5:
                        sync_drop.append((col, drop))
            if len(sync_drop) >= 2:
                matched_patterns.append({"pattern": "稀释排放", "rule": "多指标同步突降",
                                         "sync_indicators": sync_drop})

        # 规则4: 质量平衡(稀释) — 去除率偏差 > 0.2 + 趋势/突变
        # 需进水出水 + HRT 对齐; 若无进水数据则跳过
        # (实现时从 anomalies/data 推; 此处简化, 后续按 hrt_hours 对齐)

        return {"matched_patterns": matched_patterns,
                "violations_count": len(matched_patterns)}

    @staticmethod
    def _max_drop_ratio(series) -> float:
        """序列中最大突降比例(0~1)。"""
        s = series.dropna()
        if len(s) < 2:
            return 0.0
        before = s.iloc[:len(s)//2].mean()
        after = s.iloc[len(s)//2:].mean()
        if before <= 0:
            return 0.0
        return float(max(0.0, (before - after) / before))
```

> 注：`validate` 签名加 `hrt_hours=2`(从 data_result.metadata 读)。规则 4 质量平衡需进水出水 + HRT 对齐,实现时若上游传了进水 df 则按 HRT 偏移对齐后算去除率偏差。

- [ ] **Step 4: 运行,确认通过**

```bash
ecological_env/Scripts/python.exe -m pytest tests/unit/test_process_validator.py -v
```
预期：PASS

- [ ] **Step 5: Commit**

```bash
git add subagents/rule-reasoning-agent/skills/rule-reasoning-core/scripts/process_validator.py tests/unit/test_process_validator.py
git commit -m "refactor(process_validator): 4条工艺规则资料判据+HRT对齐+多指标同步突降"
```

---

## Task 3: regulation_matcher 法规阈值校验

**Files:** Modify `subagents/.../regulation_matcher.py`

- [ ] **Step 1: 确认法规匹配逻辑(超排放标准阈值 → 违规)**

读 `regulation_matcher.py`，确认它从 `shared/knowledge/regulations/排放标准.md` 读阈值，对 anomalies 的值做超阈值校验。若已实现则跳过；若判据不对，改为:
```python
# 排放标准阈值(示例, 实际从知识库读)
LIMITS = {"COD": 50, "TN": 15, "氨氮": 5, "TP": 1.0, "pH": (6, 9)}
# 对每个异常点的 indicator+value, 超阈值 → 法规违规
```

- [ ] **Step 2: Commit(若有改动)**

```bash
git add subagents/rule-reasoning-agent/skills/rule-reasoning-core/scripts/regulation_matcher.py
git commit -m "refactor(regulation_matcher): 排放标准阈值校验"
```

---

## Task 4: run_rule_reasoning 读 anomaly features + 嫌疑矩阵 + missing_data

**Files:** Modify `subagents/.../run_rule_reasoning.py`

- [ ] **Step 1: 改 normalize_anomalies → 读 features**

把 `normalize_anomalies`(把旧 type 归一化)改为直接用 anomaly 的 `features` 字段(异常检测新输出):
```python
def extract_features(anomalies):
    """从异常检测结果提取 features 集合(供工艺规则组合判定)。"""
    feature_set = set()
    for a in anomalies:
        feature_set.update(a.get("features", []))
    return feature_set
```
在 main 调 process_validator 时,传 anomalies(含 features)。

- [ ] **Step 2: 实现嫌疑矩阵**

在生成结论处(第 405-410 行附近),按资料矩阵定 suspicion_level:
```python
regulation_violation = len(regulation_matches.get("violations", [])) > 0
process_violation = process_validation.get("violations_count", 0) > 0
if regulation_violation and process_violation:
    suspicion_level = "high"
elif not regulation_violation and process_violation:
    suspicion_level = "medium"
elif regulation_violation and not process_violation:
    suspicion_level = "low"
else:
    suspicion_level = "none"
has_violation = suspicion_level in ("high", "medium", "low")
```

- [ ] **Step 3: 输出 missing_data**

在 result 加:
```python
"missing_data": ["工况数据(人工拟合降级)", "停产申报数据(恶意逃避 TODO)"]
```

- [ ] **Step 4: 传 hrt_hours 给 process_validator**

从 `data_result.metadata.hrt_hours` 读 HRT,传给 `process_validator.validate(..., hrt_hours=hrt)`:
```python
hrt_hours = data_result.get("result", {}).get("metadata", {}).get("hrt_hours", 2)
process_validation = process_validator.validate(anomalies, correlation_results, trend_results, data=effluent_df, hrt_hours=hrt_hours)
```

- [ ] **Step 5: 语法检查 + Commit**

```bash
ecological_env/Scripts/python.exe -m py_compile subagents/rule-reasoning-agent/skills/rule-reasoning-core/scripts/run_rule_reasoning.py && echo OK
git add subagents/rule-reasoning-agent/skills/rule-reasoning-core/scripts/run_rule_reasoning.py
git commit -m "refactor(run_rule_reasoning): 读anomaly features+嫌疑矩阵+missing_data+HRT"
```

---

## Task 5: 知识库 — 违规模式特征库

**Files:** Modify `shared/knowledge/violation_patterns/violation_patterns.md`

- [ ] **Step 1: 写 4 类违规模式 ↔ 特征组合**

```markdown
# 违规模式特征库

| 违规模式 | 异常特征组合 | 工艺规则 |
|---|---|---|
| 插瓶干扰 | 平稳(+突变) | pH-COD 协同 / 氨氮-总氮转化 |
| 稀释排放 | 突变(+趋势) | 质量平衡 / 多指标同步突降 |
| 人工拟合 | 趋势 | (需工况数据增强) |
| 恶意逃避 | — | (需停产申报数据 TODO) |
```

- [ ] **Step 2: Commit**

```bash
git add shared/knowledge/violation_patterns/violation_patterns.md
git commit -m "docs(knowledge): 违规模式特征库(4类↔特征组合)"
```

---

## Task 6: 端到端验证

- [ ] **Step 1: 跑全链路,检查 rule_reasoning_result**

```bash
ecological_env/Scripts/python.exe -c "
import json, glob, os
sd = sorted(glob.glob(r'sessions/session_*'), key=os.path.getmtime, reverse=True)[0]
r = json.load(open(os.path.join(sd,'rule_reasoning_result.json'), encoding='utf-8'))
res = r.get('result',{})
print('suspicion_level=', res.get('suspicion_level'))
print('violation_types=', res.get('violation_types'))
print('missing_data=', res.get('missing_data'))
assert 'missing_data' in res, '缺 missing_data'
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
- ✅ 4 类违规:Task 1 AGENTS + Task 5 知识库
- ✅ 4 条工艺规则资料判据:Task 2 process_validator
- ✅ HRT 对齐:Task 2(质量平衡)+ Task 4(传 hrt_hours)
- ✅ 嫌疑矩阵:Task 4
- ✅ 异常特征对接:Task 4(读 features)
- ✅ missing_data:Task 4
- ⏸ 质量平衡规则完整(进水出水 HRT 对齐):Task 2 规则 4 简化,实现时按 hrt_hours 对齐

**Placeholder scan:** Task 2 规则 4(质量平衡)标了"实现时按 hrt 对齐"——执行时需补进水出水对齐逻辑。

**Type consistency:** anomaly features(异常检测输出)→ process_validator 读 features → matched_patterns(pattern 名)。一致。
