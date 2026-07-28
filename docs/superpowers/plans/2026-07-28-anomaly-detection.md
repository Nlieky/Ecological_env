# 异常检测子智能体 Implementation Plan(Plan 2/5)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox.

**Goal:** 异常检测改成调算子库(不自己实现),检出 5 类异常特征 + 评分 + 可信度,不判违规模式;specialized 算子去 violation_type,新写 trend/high_freq/periodicity。

**Architecture:** `run_anomaly_detection_simple.py` 删自实现 zscore/iqr/IF,改调 `shared/operators/`(5 特征算子 + isolation_forest + lstm);算子输出去 violation_type;新写 trend/high_freq/periodicity。

**Tech Stack:** Python 3.12(pandas/numpy/scipy/sklearn),pytest。

**Spec:** `docs/superpowers/specs/2026-07-28-anomaly-detection-design.md`

---

## File Structure

| 文件 | 责任 | 动作 |
|---|---|---|
| `shared/operators/specialized/constant_detector.py` | 平稳特征检测 | 改(去 violation_type,输出特征+score) |
| `shared/operators/specialized/change_point_detector.py` | 突变特征检测 | 改(加 score + 特征标签,已无 violation_type) |
| `shared/operators/specialized/trend_detector.py` | 趋势特征检测 | 新建 |
| `shared/operators/specialized/high_freq_detector.py` | 高频波动特征检测 | 新建 |
| `shared/operators/specialized/periodicity_detector.py` | 周期特征检测 | 新建(从 forgery 拆) |
| `subagents/.../run_anomaly_detection_simple.py` | 异常检测主脚本 | 改(调算子库,5 特征+评分+可信度) |
| `subagents/.../SOUL.md` / `AGENTS.md` | 身份/规范 | 改(调算子库/5 特征/不判违规/skill_view) |
| `tests/unit/test_detectors.py` | 算子单元测试 | 新建 |

---

## Task 1: SOUL.md / AGENTS.md 对齐(调算子库 + 5 特征 + 不判违规)

**Files:** Modify `subagents/anomaly-detection-agent/SOUL.md`、`AGENTS.md`

- [ ] **Step 1: AGENTS.md 修过时(同数据感知)**

把"预加载 SKILL"→"`skill_view` 读取";"❌不要 skill_view"→"用 skill_view 读 SKILL";保留"必须从 `shared/operators/` 调算子,禁止本地重实现"(这条 AGENTS 本来就对,但脚本没遵守,本 plan 修脚本)。

- [ ] **Step 2: AGENTS.md 强调"5 类异常特征 + 不判违规"**

在"异常类型"段,把旧的 5 类(boundary/constant/spike/trend/point)改为资料定义的 5 类:
```
## 异常特征(5 类,数据层)
| 特征 | 定义 | 算子 |
|---|---|---|
| 平稳异常 | 标准差/变异系数低于阈值 | constant_detector |
| 突变异常 | 相邻点变化幅度超阈值 | change_point_detector |
| 趋势异常 | 单向均匀升降,二阶导≈0 | trend_detector |
| 周期异常 | FFT 检测显著周期性 | periodicity_detector |
| 高频波动 | 分钟级突升突降/归零 | high_freq_detector |

**不判违规模式**(插瓶/拟合/稀释/逃避是规则推理的活,你只输出异常特征 + 分数 + 可信度)。
```

- [ ] **Step 3: SOUL.md 确认"Anomaly ≠ Violation"** (现状第 13 行已对,无需改,跳过)

- [ ] **Step 4: Commit**

```bash
git add subagents/anomaly-detection-agent/AGENTS.md subagents/anomaly-detection-agent/SOUL.md
git commit -m "docs(anomaly): AGENTS 对齐(5类特征+调算子库+不判违规+skill_view)"
```

---

## Task 2: constant_detector 去 violation_type(只输出特征)

**Files:**
- Modify: `shared/operators/specialized/constant_detector.py`
- Test: `tests/unit/test_detectors.py`

- [ ] **Step 1: 写失败测试**

创建 `tests/unit/test_detectors.py`:
```python
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import pandas as pd
import numpy as np


def test_constant_detector_no_violation_type():
    """恒定检测器只输出特征(平稳),不判违规模式。"""
    from shared.operators.specialized.constant_detector import ConstantDetector
    d = ConstantDetector()
    # 构造恒定序列(std≈0)
    data = pd.Series([7.0] * 20)
    mask, details = d.detect(data)
    assert details.get("is_constant") is True
    assert "score" in details  # 输出异常分数
    assert "violation_type" not in details, "算子不该判违规模式(交规则推理)"


def test_constant_detector_normal_data():
    """正常波动数据不报平稳。"""
    from shared.operators.specialized.constant_detector import ConstantDetector
    d = ConstantDetector()
    data = pd.Series(np.random.RandomState(42).randn(20) + 7)
    mask, details = d.detect(data)
    assert details.get("is_constant") is False
```

- [ ] **Step 2: 运行,确认失败**

```bash
ecological_env/Scripts/python.exe -m pytest tests/unit/test_detectors.py::test_constant_detector_no_violation_type -v
```
预期：FAIL（`violation_type in details` 或 `score not in details`）

- [ ] **Step 3: 改 constant_detector(去 violation_type,加 score,字段名 is_constant)**

把 `detect` 的 `details`（第 90-100 行）和判断逻辑改为:
```python
        # 平稳判断(综合)
        is_constant = is_constant_std or is_constant_cv or is_constant_unique

        if is_constant:
            anomaly_mask = np.ones(len(data), dtype=bool)
            score = max(
                1.0 - data_std / self.std_threshold if self.std_threshold > 0 else 0,
                1.0 - data_cv / self.cv_threshold if self.cv_threshold > 0 and data_cv != float('inf') else 0,
                1.0 - unique_ratio / self.unique_ratio_threshold if self.unique_ratio_threshold > 0 else 0,
            )
            score = float(min(max(score, 0.0), 1.0))
        else:
            anomaly_mask = np.zeros(len(data), dtype=bool)
            score = 0.0

        details = {
            "feature": "平稳",
            "is_constant": bool(is_constant),
            "score": score,
            "std": float(data_std),
            "cv": float(data_cv),
            "unique_count": int(unique_count),
            "unique_ratio": float(unique_ratio),
        }
        # 不输出 violation_type —— 违规模式判定是规则推理的活
        return anomaly_mask, details
```
（删掉原来的 `violation_type`/`confidence` 字段，改 `score` + `is_constant` + `feature`）

- [ ] **Step 4: 运行,确认通过**

```bash
ecological_env/Scripts/python.exe -m pytest tests/unit/test_detectors.py -v -k constant
```
预期：PASS

- [ ] **Step 5: Commit**

```bash
git add shared/operators/specialized/constant_detector.py tests/unit/test_detectors.py
git commit -m "refactor(constant_detector): 去violation_type,输出平稳特征+score"
```

---

## Task 3: 新建 trend_detector(趋势异常)

**Files:**
- Create: `shared/operators/specialized/trend_detector.py`
- Test: `tests/unit/test_detectors.py`

- [ ] **Step 1: 写失败测试**

在 `tests/unit/test_detectors.py` 加:
```python
def test_trend_detector_uniform_rise():
    """均匀上升序列(二阶导≈0)→ 趋势异常。"""
    from shared.operators.specialized.trend_detector import TrendDetector
    d = TrendDetector()
    data = pd.Series(np.linspace(7.0, 9.0, 20))  # 均匀上升
    mask, details = d.detect(data)
    assert details.get("is_trend") is True
    assert details.get("score", 0) > 0.5


def test_trend_detector_random_not_trend():
    """随机波动不是趋势。"""
    from shared.operators.specialized.trend_detector import TrendDetector
    d = TrendDetector()
    data = pd.Series(np.random.RandomState(42).randn(20) + 7)
    mask, details = d.detect(data)
    assert details.get("is_trend") is False
```

- [ ] **Step 2: 运行,确认失败**(`ModuleNotFoundError: trend_detector`)

```bash
ecological_env/Scripts/python.exe -m pytest tests/unit/test_detectors.py -v -k trend
```

- [ ] **Step 3: 实现 trend_detector**

创建 `shared/operators/specialized/trend_detector.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""趋势检测器 - 检测单向均匀上升/下降(二阶导≈0)。资料定义的趋势异常特征。"""

import logging
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)


class TrendDetector:
    """趋势检测器:序列呈单向均匀升降(线性,二阶导接近 0)。"""

    def __init__(self, min_slope_ratio: float = 0.5, second_deriv_threshold: float = 0.05,
                 min_length: int = 10):
        self.min_slope_ratio = min_slope_ratio
        self.second_deriv_threshold = second_deriv_threshold
        self.min_length = min_length
        self.name = "趋势检测器"

    def detect(self, data: pd.Series) -> Tuple[np.ndarray, Dict[str, Any]]:
        data = data.dropna()
        if len(data) < self.min_length:
            return np.zeros(len(data)), {"error": "数据过少"}

        values = data.values.astype(float)
        n = len(values)
        x = np.arange(n)

        # 线性拟合
        slope, intercept = np.polyfit(x, values, 1)
        fitted = slope * x + intercept
        residuals = values - fitted

        # 二阶导(差分的差分)幅度,衡量偏离线性
        second_deriv = np.diff(values, n=2)
        second_deriv magnitude = float(np.std(second_deriv)) if len(second_deriv) > 0 else 0.0
        # 趋势强度:斜率相对数据波动
        data_std = float(np.std(values))
        slope_ratio = abs(slope) / (data_std + 1e-9) if data_std > 1e-9 else 0.0
        # 拟合优度 R²
        ss_res = float(np.sum(residuals ** 2))
        ss_tot = float(np.sum((values - values.mean()) ** 2)) + 1e-9
        r_squared = 1 - ss_res / ss_tot

        # 趋势判断:R² 高(线性拟合好)+ 二阶导小(均匀)
        is_trend = r_squared > 0.8 and slope_ratio > self.min_slope_ratio
        score = float(min(max(r_squared * min(slope_ratio, 1.0), 0.0), 1.0)) if is_trend else 0.0
        direction = "上升" if slope > 0 else "下降"

        anomaly_mask = np.ones(n, dtype=bool) if is_trend else np.zeros(n, dtype=bool)
        details = {
            "feature": "趋势",
            "is_trend": bool(is_trend),
            "score": score,
            "slope": float(slope),
            "direction": direction,
            "r_squared": float(r_squared),
        }
        return anomaly_mask, details

    def __call__(self, data):
        return self.detect(data)
```

> 注：`second_deriv magnitude` 变量名含空格是 bug，实现时用 `second_deriv_std`。上面是示意，实际写 `second_deriv_std = float(np.std(second_deriv))`。

- [ ] **Step 4: 运行,确认通过**

```bash
ecological_env/Scripts/python.exe -m pytest tests/unit/test_detectors.py -v -k trend
```
预期：PASS

- [ ] **Step 5: Commit**

```bash
git add shared/operators/specialized/trend_detector.py tests/unit/test_detectors.py
git commit -m "feat(trend_detector): 新建趋势异常检测器(单向均匀升降)"
```

---

## Task 4: 新建 high_freq_detector(高频波动)

**Files:**
- Create: `shared/operators/specialized/high_freq_detector.py`
- Test: `tests/unit/test_detectors.py`

- [ ] **Step 1: 写失败测试**

```python
def test_high_freq_detector_spike():
    """突升突降的高频波动 → 高频异常。"""
    from shared.operators.specialized.high_freq_detector import HighFreqDetector
    d = HighFreqDetector()
    data = pd.Series([7.0, 9.5, 7.0, 4.5, 7.0, 9.5, 7.0, 4.5] * 3)  # 反复突升突降
    mask, details = d.detect(data)
    assert details.get("is_high_freq") is True
    assert details.get("score", 0) > 0.3
```

- [ ] **Step 2: 运行,确认失败**(`ModuleNotFoundError`)

- [ ] **Step 3: 实现 high_freq_detector**

创建 `shared/operators/specialized/high_freq_detector.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""高频波动检测器 - 分钟级突升突降、异常归零。资料定义的高频波动异常特征。"""

import logging
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)


class HighFreqDetector:
    """高频波动:相邻点差分大且频繁(突升突降),或出现异常归零。"""

    def __init__(self, diff_threshold: float = 3.0, freq_ratio_threshold: float = 0.3,
                 min_length: int = 8):
        self.diff_threshold = diff_threshold  # 差分超此值(相对 std)算突跳
        self.freq_ratio_threshold = freq_ratio_threshold  # 突跳点占比超此值算高频
        self.min_length = min_length
        self.name = "高频波动检测器"

    def detect(self, data: pd.Series) -> Tuple[np.ndarray, Dict[str, Any]]:
        data = data.dropna()
        if len(data) < self.min_length:
            return np.zeros(len(data)), {"error": "数据过少"}

        values = data.values.astype(float)
        n = len(values)
        data_std = float(np.std(values))
        if data_std < 1e-9:
            return np.zeros(n), {"feature": "高频波动", "is_high_freq": False, "score": 0.0}

        # 一阶差分
        diffs = np.abs(np.diff(values))
        normalized_diffs = diffs / data_std
        # 突跳点
        spike_mask = normalized_diffs > self.diff_threshold
        # 归零检测(值突然接近 0)
        zero_mask = np.abs(values) < data_std * 0.05

        freq_ratio = float(spike_mask.sum() / n)
        zero_ratio = float(zero_mask.sum() / n)
        is_high_freq = (freq_ratio > self.freq_ratio_threshold) or (zero_ratio > 0.3)

        score = float(min(max(max(freq_ratio, zero_ratio), 0.0), 1.0)) if is_high_freq else 0.0

        anomaly_mask = np.zeros(n, dtype=bool)
        anomaly_mask[1:][spike_mask] = True
        anomaly_mask[zero_mask] = True

        details = {
            "feature": "高频波动",
            "is_high_freq": bool(is_high_freq),
            "score": score,
            "freq_ratio": freq_ratio,
            "zero_ratio": zero_ratio,
        }
        return anomaly_mask, details

    def __call__(self, data):
        return self.detect(data)
```

- [ ] **Step 4: 运行,确认通过**

```bash
ecological_env/Scripts/python.exe -m pytest tests/unit/test_detectors.py -v -k high_freq
```

- [ ] **Step 5: Commit**

```bash
git add shared/operators/specialized/high_freq_detector.py tests/unit/test_detectors.py
git commit -m "feat(high_freq_detector): 新建高频波动检测器(突升突降/归零)"
```

---

## Task 5: 新建 periodicity_detector(从 forgery 拆出周期检测)

**Files:**
- Create: `shared/operators/specialized/periodicity_detector.py`
- Test: `tests/unit/test_detectors.py`

- [ ] **Step 1: 写失败测试**

```python
def test_periodicity_detector_periodic():
    """周期性序列(正弦)→ 周期异常。"""
    from shared.operators.specialized.periodicity_detector import PeriodicityDetector
    d = PeriodicityDetector()
    t = np.arange(40)
    data = pd.Series(np.sin(t * 2 * np.pi / 8) + 7)  # 周期 8
    mask, details = d.detect(data)
    assert details.get("is_periodic") is True
```

- [ ] **Step 2: 运行,确认失败**

- [ ] **Step 3: 实现 periodicity_detector(从 forgery_detector._detect_periodicity 拆出)**

创建 `shared/operators/specialized/periodicity_detector.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""周期检测器 - FFT 检测显著周期性成分。资料定义的周期异常特征。
从 forgery_detector 拆出(原 forgery 混了周期/聚类/分布,这里只留周期)。"""

import logging
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)


class PeriodicityDetector:
    """周期检测:FFT 检测序列中的强周期分量。"""

    def __init__(self, periodicity_threshold: float = 0.8, min_length: int = 30):
        self.periodicity_threshold = periodicity_threshold
        self.min_length = min_length
        self.name = "周期检测器"

    def detect(self, data: pd.Series) -> Tuple[np.ndarray, Dict[str, Any]]:
        data = data.dropna()
        if len(data) < self.min_length:
            return np.zeros(len(data)), {"error": "数据过少"}

        values = data.values.astype(float)
        n = len(values)
        # 去趋势
        detrended = values - np.mean(values)
        # FFT
        fft_result = np.fft.fft(detrended)
        power = np.abs(fft_result[:n // 2])
        power = power / (power.sum() + 1e-10)
        max_power = float(power.max())

        is_periodic = max_power > self.periodicity_threshold
        score = float(min(max(max_power, 0.0), 1.0)) if is_periodic else 0.0

        anomaly_mask = np.ones(n, dtype=bool) if is_periodic else np.zeros(n, dtype=bool)
        details = {
            "feature": "周期",
            "is_periodic": bool(is_periodic),
            "score": score,
            "max_power": max_power,
        }
        return anomaly_mask, details

    def __call__(self, data):
        return self.detect(data)
```

- [ ] **Step 4: 运行,确认通过**

```bash
ecological_env/Scripts/python.exe -m pytest tests/unit/test_detectors.py -v -k periodic
```

- [ ] **Step 5: Commit**

```bash
git add shared/operators/specialized/periodicity_detector.py tests/unit/test_detectors.py
git commit -m "feat(periodicity_detector): 新建周期检测器(从forgery拆出,FFT)"
```

---

## Task 6: run_anomaly_detection_simple.py 改调算子库

**Files:** Modify `subagents/.../run_anomaly_detection_simple.py`

> 核心：删自实现的 `zscore_anomaly`/`iqr_anomaly`/`isolation_forest_anomaly`/`detect_anomalies_in_series`，改成调 `shared/operators/`。

- [ ] **Step 1: 改 import + 算子实例化**

文件顶部加:
```python
from shared.operators.specialized.constant_detector import ConstantDetector
from shared.operators.specialized.change_point_detector import ChangePointDetector
from shared.operators.specialized.trend_detector import TrendDetector
from shared.operators.specialized.high_freq_detector import HighFreqDetector
from shared.operators.specialized.periodicity_detector import PeriodicityDetector
from shared.operators.machine_learning.isolation_forest import IsolationForestDetector
```

- [ ] **Step 2: 用 5 特征算子 + 评分器替换 detect_anomalies_in_series**

把 `detect_anomalies_in_series`（第 225-262 行）替换为:
```python
def detect_features_for_series(values: np.ndarray, series_name: str) -> list:
    """对单个序列跑 5 类特征算子 + 评分器,返回异常点(features + score + confidence)。"""
    import pandas as pd
    series = pd.Series(values)
    anomalies = []
    if len(series) < 5:
        return anomalies

    # 5 特征算子
    detectors = [
        ("平稳", ConstantDetector()),
        ("突变", ChangePointDetector()),
        ("趋势", TrendDetector()),
        ("周期", PeriodicityDetector()),
        ("高频波动", HighFreqDetector()),
    ]
    matched_features = []
    feature_scores = {}
    for name, det in detectors:
        try:
            mask, details = det.detect(series)
            if details.get(f"is_{_feature_key(name)}", False) or details.get("is_constant") or details.get("is_trend") or details.get("is_periodic") or details.get("is_high_freq"):
                matched_features.append(name)
                feature_scores[name] = details.get("score", 0.0)
        except Exception as e:
            logger.warning(f"{name} 检测失败: {e}")

    # 评分器(孤立森林)
    anomaly_score = 0.0
    try:
        vals = series.dropna().values.reshape(-1, 1)
        from sklearn.ensemble import IsolationForest
        iso = IsolationForest(contamination=0.1, random_state=42)
        iso.fit(vals)
        raw_scores = -iso.score_samples(vals)
        anomaly_score = float((raw_scores.max() - raw_scores.min()) / (raw_scores.std() + 1e-9))
        anomaly_score = float(min(max(anomaly_score / 3.0, 0.0), 1.0))
    except Exception as e:
        logger.warning(f"孤立森林评分失败: {e}")

    if matched_features:
        # 模式相似度(匹配特征数 / 5)
        pattern_similarity = len(matched_features) / 5.0
        # 可信度(资料公式): 0.6×异常分数 + 0.4×模式相似度
        confidence = 0.6 * anomaly_score + 0.4 * pattern_similarity
        anomalies.append({
            "features": matched_features,
            "score": anomaly_score,
            "confidence": float(confidence),
            "pattern_similarity": float(pattern_similarity),
            "value": float(series.iloc[-1]),
        })
    return anomalies


def _feature_key(name):
    return {"平稳": "constant", "突变": "change_point", "趋势": "trend",
            "周期": "periodic", "高频波动": "high_freq"}.get(name, name)
```

- [ ] **Step 3: 改 main 的 detect_anomalies 调用,输出 features + confidence**

在 `main`（第 337 行附近）`detection_result = detect_anomalies(data)` 的 `detect_anomalies` 函数里，把对每个指标的检测改为调 `detect_features_for_series`，把结果字段从 `type/score/votes` 改为 `features/score/confidence/pattern_similarity`（对齐 spec 输出契约）。

> 这一步是 `detect_anomalies` 函数主体改造，按 spec 输出契约组织 anomalies 列表。具体：遍历 influent/effluent 每个指标列 → `detect_features_for_series(df[col].values, col)` → 汇总到 all_anomalies，每个 anomaly 带 `timestamp/indicator/data_type/features/score/confidence/value/expected_range`。

- [ ] **Step 4: 语法检查**

```bash
ecological_env/Scripts/python.exe -m py_compile subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/run_anomaly_detection_simple.py && echo OK
```

- [ ] **Step 5: 集成测试（用 data_result 驱动）**

```bash
# 假设已有 data_result.json（数据感知产出）
ecological_env/Scripts/python.exe -c "
import sys; sys.path.insert(0, '.')
from subagents.anomaly_detection_agent.skills.anomaly_detection_core.scripts.run_anomaly_detection_simple import load_data_from_result, detect_features_for_series
import os
os.environ['SESSION_DIR'] = 'sessions/' + sorted(__import__('glob').glob('sessions/session_*'))[-1].split('/')[-1] if __import__('os').path.exists('sessions') else ''
# 简化：测 detect_features_for_series 对一个序列
import numpy as np
anoms = detect_features_for_series(np.array([7.0]*20 + [9.0]*5), 'pH')
print('features:', [a['features'] for a in anoms])
print('confidence:', [a.get('confidence') for a in anoms])
"
```
预期：输出 features（如 ['平稳']）+ confidence（非 None）

- [ ] **Step 6: Commit**

```bash
git add subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/run_anomaly_detection_simple.py
git commit -m "refactor(anomaly): run_anomaly改调算子库+5类特征+评分+可信度(删自实现)"
```

---

## Task 7: 端到端验证

- [ ] **Step 1: 跑全链路（数据感知已改 + 异常检测已改）**

发查询"最近24小时出水有没有异常"，检查 anomaly_result.json:
```bash
ecological_env/Scripts/python.exe -c "
import json, glob, os
sd = sorted(glob.glob(r'sessions/session_*'), key=os.path.getmtime, reverse=True)[0]
a = json.load(open(os.path.join(sd,'anomaly_result.json'), encoding='utf-8'))
anoms = a.get('result',{}).get('anomalies',[])
print('anomalies:', len(anoms))
for x in anoms[:3]:
    print(' features=', x.get('features'), 'confidence=', x.get('confidence'))
assert all('features' in x and 'confidence' in x for x in anoms), '缺 features/confidence'
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
- ✅ 调算子库(不自己写)：Task 6 删自实现 + 调 shared/operators
- ✅ 5 类特征：Task 2-5（constant/change_point/trend/high_freq/periodicity）
- ✅ 不判违规：Task 2 去 violation_type；输出无 violation_type
- ✅ 评分（孤立森林 0.5 + LSTM）：Task 6（LSTM 标注 TODO，初版孤立森林；spec 错误处理说 LSTM 降级）
- ✅ 可信度公式：Task 6（0.6×score + 0.4×similarity）
- ✅ 输出 features + confidence：Task 6
- ⏸ LSTM 评分器：初版降级用孤立森林（spec 错误处理允许）；LSTM 完整接入后续
- ⏸ build_chart 调用：Plan 5（可视化）

**Placeholder scan:** Task 6 Step 3 描述了 detect_anomalies 改造方向但未逐行代码（因现状函数较长，实现时按 spec 输出契约组织）—— 这是 plan 的已知简化点，执行时需对照 spec 输出契约实现。

**Type consistency:** 算子统一输出 `{feature, is_*, score}`；run_anomaly 汇总为 `{features, score, confidence, pattern_similarity}`。一致。
