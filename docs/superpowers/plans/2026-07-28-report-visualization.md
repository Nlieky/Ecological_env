# 报告可视化 Implementation Plan(Plan 5/5)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox.

**Goal:** 报告自动带数据曲线(进水/出水双线)+ 异常 markPoint。`build_chart` 共享工具 + get_data/run_anomaly 调用 + query.py 收集 + 前端 ECharts 渲染。

**Architecture:** `shared/viz/build_chart_data(records, anomalies)` → ECharts option 列表;get_data/run_anomaly 调它存 `result.chartData`;`query.py` 收集本轮 chartData → `QueryResponse.chartData`;`ChatMessage.vue` 渲染。

**Tech Stack:** Python 3.12(pandas),Vue3 + ECharts,pytest。

**Spec:** `docs/superpowers/specs/2026-07-28-report-visualization-design.md`

> **前置:** Plan 1(get_data 改造完)+ Plan 2(run_anomaly 改造完)已完成,本 plan 给它们加 build_chart 调用 + query/前端。

---

## File Structure

| 文件 | 责任 | 动作 |
|---|---|---|
| `shared/viz/build_chart.py` | 构造 ECharts 配置 | 新建 |
| `shared/viz/__init__.py` | 包标识 | 新建 |
| `subagents/.../get_data.py` | 数据感知 | 改(调 build_chart,存 result.chartData) |
| `subagents/.../run_anomaly_detection_simple.py` | 异常检测 | 改(调 build_chart 带异常,存 result.chartData) |
| `backend/api/routes/query.py` | 查询接口 | 改(收集 chartData → QueryResponse.chartData) |
| `frontend/src/components/aiops/ChatMessage.vue` | 消息渲染 | 改(chartData → ECharts) |
| `tests/unit/test_build_chart.py` | 单元测试 | 新建 |

---

## Task 1: 新建 build_chart.py(build_chart_data,TDD)

**Files:**
- Create: `shared/viz/__init__.py`、`shared/viz/build_chart.py`
- Test: `tests/unit/test_build_chart.py`

- [ ] **Step 1: 写失败测试**

创建 `tests/unit/test_build_chart.py`:
```python
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def test_build_chart_no_anomalies():
    """无异常时,输出每指标一个 ECharts option(进水/出水双线,无 markPoint)。"""
    from shared.viz.build_chart import build_chart_data
    records = {
        "influent": [{"timestamp": "2026-07-14 00:00:00", "pH": 7.4, "COD": 68.0},
                     {"timestamp": "2026-07-14 01:00:00", "pH": 7.5, "COD": 70.0}],
        "effluent": [{"timestamp": "2026-07-14 00:00:00", "pH": 7.3, "COD": 33.0},
                     {"timestamp": "2026-07-14 01:00:00", "pH": 7.35, "COD": 34.0}],
    }
    charts = build_chart_data(records, indicators=["pH", "COD"])
    assert len(charts) == 2  # pH + COD 两个子图
    assert charts[0]["title"] == "pH 趋势"
    opt = charts[0]["option"]
    assert len(opt["series"]) == 2  # 进水 + 出水双线
    assert "xAxis" in opt


def test_build_chart_with_anomalies_markpoint():
    """有异常时,pH 图的进水 series 含 markPoint。"""
    from shared.viz.build_chart import build_chart_data
    records = {
        "influent": [{"timestamp": "2026-07-14 00:00:00", "pH": 7.4},
                     {"timestamp": "2026-07-14 01:00:00", "pH": 9.5}],  # 异常点
        "effluent": [],
    }
    anomalies = [{"indicator": "pH", "data_type": "influent",
                  "timestamp": "2026-07-14 01:00:00", "features": ["突变"]}]
    charts = build_chart_data(records, indicators=["pH"], anomalies=anomalies)
    opt = charts[0]["option"]
    # 进水 series(index 0)含 markPoint
    infl_series = opt["series"][0]
    assert "markPoint" in infl_series
    assert len(infl_series["markPoint"]["data"]) >= 1
```

- [ ] **Step 2: 运行,确认失败**(`ModuleNotFoundError: shared.viz`)

```bash
ecological_env/Scripts/python.exe -m pytest tests/unit/test_build_chart.py -v
```

- [ ] **Step 3: 实现 build_chart.py**

创建 `shared/viz/__init__.py`(空)和 `shared/viz/build_chart.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""报告可视化:原始数据 + 异常点 → ECharts option 列表(每指标一个子图)。

每图:进水/出水双线 + 异常 markPoint(按指标+时间匹配)。
供 get_data.py(无异常)和 run_anomaly(带异常)调用,构造 chartData。
"""

from typing import List, Dict, Any, Optional
import pandas as pd

# data_result 英文字段 → 中文标题(标题用,series 名用进水/出水)
_INDICATOR_TITLE = {"pH": "pH", "COD": "COD", "TN": "TN", "NH3-N": "氨氮",
                    "TP": "总磷", "SS": "悬浮物"}


def build_chart_data(records: dict, indicators: Optional[List[str]] = None,
                     anomalies: Optional[List[dict]] = None) -> List[Dict[str, Any]]:
    """records = {influent: [{timestamp, pH, COD,...}], effluent: [...]}
    返回 [{"title": "pH 趋势", "option": <ECharts option>}, ...]
    """
    if indicators is None:
        # 从 records 推断指标(排除 timestamp)
        sample = (records.get("influent") or records.get("effluent") or [{}])[0]
        indicators = [k for k in sample if k != "timestamp"]

    infl = records.get("influent") or []
    effl = records.get("effluent") or []
    xs_in = [r.get("timestamp", "")[5:16] for r in infl]   # MM-DD HH:mm
    xs_out = [r.get("timestamp", "")[5:16] for r in effl]

    charts = []
    for ind in indicators:
        title = f"{_INDICATOR_TITLE.get(ind, ind)} 趋势"
        series_in = {"name": "进水", "type": "line", "smooth": True,
                     "data": [_num(r.get(ind)) for r in infl]}
        series_out = {"name": "出水", "type": "line", "smooth": True,
                      "data": [_num(r.get(ind)) for r in effl]}

        # 异常 markPoint(按指标 + data_type 匹配到对应 series)
        if anomalies:
            for side, series in (("influent", series_in), ("effluent", series_out)):
                pts = [{"name": a.get("features", ["异常"])[0],
                        "value": _num(_val_at(records, side, ind, a.get("timestamp"))),
                        "xAxis": (a.get("timestamp", "")[5:16]),
                        "yAxis": _num(_val_at(records, side, ind, a.get("timestamp")))}
                       for a in anomalies
                       if a.get("indicator") in (ind, _to_cn(ind)) and a.get("data_type") == side]
                if pts:
                    series["markPoint"] = {"data": pts}

        # xAxis 用进水/出水时间并集(简化:进水时间)
        option = {
            "title": {"text": title, "left": "center", "textStyle": {"fontSize": 12}},
            "tooltip": {"trigger": "axis"},
            "legend": {"data": ["进水", "出水"], "top": 18},
            "xAxis": {"type": "category", "data": xs_in or xs_out},
            "yAxis": {"type": "value"},
            "series": [series_in, series_out],
        }
        charts.append({"title": title, "option": option})
    return charts


def _num(v):
    try:
        return None if v is None else round(float(v), 2)
    except (TypeError, ValueError):
        return None


def _val_at(records, side, ind, ts):
    """在 records[side] 里找 timestamp==ts 的 ind 值。"""
    for r in records.get(side, []):
        if r.get("timestamp") == ts:
            return r.get(ind, r.get(_to_en(ind)))
    return None


def _to_cn(ind):
    return {"NH3-N": "氨氮", "TP": "总磷", "SS": "悬浮物"}.get(ind, ind)


def _to_en(ind_cn):
    return {"氨氮": "NH3-N", "总磷": "TP", "悬浮物": "SS"}.get(ind_cn, ind_cn)
```

- [ ] **Step 4: 运行,确认通过**

```bash
ecological_env/Scripts/python.exe -m pytest tests/unit/test_build_chart.py -v
```
预期：PASS

- [ ] **Step 5: Commit**

```bash
git add shared/viz/__init__.py shared/viz/build_chart.py tests/unit/test_build_chart.py
git commit -m "feat(viz): 新建 build_chart_data(records+anomalies→ECharts option 列表)"
```

---

## Task 2: get_data.py 调 build_chart(存 result.chartData)

**Files:** Modify `subagents/.../get_data.py`

- [ ] **Step 1: 在 main 产出 result 后调 build_chart_data**

在 `main` 的 `result` 构造后(存 data_result.json 前)加:
```python
    # 报告可视化:构造 chartData(无异常标注,纯数据曲线)
    try:
        import sys as _sys
        _root = Path(__file__).resolve().parents[5]
        if str(_root) not in _sys.path:
            _sys.path.insert(0, str(_root))
        from shared.viz.build_chart import build_chart_data
        result["result"]["chartData"] = build_chart_data(
            {"influent": influent_data, "effluent": effluent_data})
    except Exception as e:
        logger.warning(f"build_chart 失败(忽略,不影响取数): {e}")
```

- [ ] **Step 2: 语法检查 + Commit**

```bash
ecological_env/Scripts/python.exe -m py_compile subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/get_data.py && echo OK
git add subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/get_data.py
git commit -m "feat(data-perception): get_data 调 build_chart 存 result.chartData"
```

---

## Task 3: run_anomaly 调 build_chart(带异常 markPoint)

**Files:** Modify `subagents/.../run_anomaly_detection_simple.py`

- [ ] **Step 1: 在 main 产出 anomaly_result 后调 build_chart_data(带 anomalies)**

在 `main` 构造 output 后(存 anomaly_result.json 前)加:
```python
    # 报告可视化:构造 chartData(带异常 markPoint)
    try:
        from shared.viz.build_chart import build_chart_data
        # records 从 data_result 读(链式);若没有则空
        records = data.get("records") if isinstance(data, dict) else {}
        output["result"]["chartData"] = build_chart_data(
            records, anomalies=detection_result.get("anomalies"))
    except Exception as e:
        logger.warning(f"build_chart 失败(忽略): {e}")
```

> 注：`records` 需从 data_result 取(influent/effluent 原始数据)。实现时若 run_anomaly 没持有原始 records,则从 `SESSION_DIR/data_result.json` 读 `result.influent/effluent`。

- [ ] **Step 2: Commit**

```bash
git add subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/run_anomaly_detection_simple.py
git commit -m "feat(anomaly): run_anomaly 调 build_chart 存 result.chartData(带异常标注)"
```

---

## Task 4: query.py 收集 chartData → QueryResponse.chartData

**Files:** Modify `backend/api/routes/query.py`

- [ ] **Step 1: 阻塞 /api/query 收集 chartData**

在 `execute_query`(阻塞)拿到 agent 响应后,从 trace/结果收集 chartData:
```python
    # 收集本轮 chartData(异常检测优先,带标注;否则数据感知)
    chart_data = None
    for sc in subagent_calls:  # 优先异常检测的 chartData
        if sc.get("subagent_name") == "anomaly-detection":
            chart_data = sc.get("chartData")
            break
    if chart_data is None:
        for sc in subagent_calls:
            if sc.get("subagent_name") == "multi-dimensional-data-perception":
                chart_data = sc.get("chartData")
                break
```
在 `return QueryResponse(...)` 加 `chartData=chart_data`(QueryResponse 模型已有 chartData 字段)。

> 注：agent 服务的 trace.subagent_calls 要把 chartData 带回来——需在 `start_agent.py process_query` 收集 subagent_calls 时,从结果文件读 `result.chartData`(或 _extract 类似)。这是 query.py 能拿到 chartData 的前提。

- [ ] **Step 2: 流式 /api/query/stream 同样收集**

在流式 proxy 解析 progress done 时,从结果文件读 chartData,放入 done 事件或单独收集(流式最终返回)。

- [ ] **Step 3: (前提)start_agent.py 收集 chartData 到 trace.subagent_calls**

在 `process_query` 收集 `_subagent_calls` 时,从 `*_result.json` 的 `result.chartData` 读,加到 subagent_calls:
```python
    _subagent_calls.append({...,
        "chartData": <从 result.json 读 result.chartData>})
```

- [ ] **Step 4: 语法检查 + Commit**

```bash
ecological_env/Scripts/python.exe -m py_compile backend/api/routes/query.py scripts/start_agent.py && echo OK
git add backend/api/routes/query.py scripts/start_agent.py
git commit -m "feat(query): 收集本轮 chartData(anomaly优先)→ QueryResponse.chartData"
```

---

## Task 5: ChatMessage.vue 渲染 chartData

**Files:** Modify `frontend/src/components/aiops/ChatMessage.vue`

- [ ] **Step 1: 在消息渲染处加 chartData 渲染(ECharts)**

读 `ChatMessage.vue`,在消息内容后加(若 msg.chartData 或消息含 chartData):
```vue
<template>
  <!-- 既有消息渲染 -->
  <div v-if="charts.length" class="charts">
    <div v-for="(c, i) in charts" :key="i" class="chart-item">
      <div ref="chartRefs" class="chart-canvas"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import echarts from '@/lib/echarts'
const props = defineProps<{ msg: any }>()
const charts = computed(() => props.msg?.chartData?.charts || [])
const chartRefs = ref<HTMLElement[]>([])
watch(charts, async () => {
  await nextTick()
  charts.value.forEach((c, i) => {
    const el = chartRefs.value[i]
    if (el) echarts.init(el).setOption(c.option)
  })
}, { immediate: true })
</script>
```

> 注：`msg.chartData` 需后端返回的消息结构含 chartData(或前端从 response 单独取)。具体接入看 ChatMessage 现有 props。

- [ ] **Step 2: 前端验证**

```bash
cd frontend && npm run dev
# 浏览器发查询"最近24小时出水异常",看消息是否出曲线
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/aiops/ChatMessage.vue
git commit -m "feat(frontend): ChatMessage 渲染 chartData(ECharts 曲线+异常标注)"
```

---

## Task 6: 端到端验证

- [ ] **Step 1: 全链路(5 plan 全部实现后)**

```bash
ecological_env/Scripts/python.exe scripts/smoke_test.py
# 浏览器发"最近24小时出水有没有异常",确认消息出曲线 + 异常 markPoint
```

- [ ] **Step 2: 扩展 smoke_test 断言 chartData**

在 `smoke_test.py` 加(查询返回后):
```python
    if not data.get("chartData"):
        fails.append("查询未返回 chartData(可视化)")
```

---

## Self-Review

**Spec coverage:**
- ✅ build_chart(shared/viz):Task 1
- ✅ get_data 调用:Task 2
- ✅ run_anomaly 调用:Task 3
- ✅ query.py 收集:Task 4
- ✅ 前端渲染:Task 5
- ✅ markPoint + tooltip:Task 1(build_chart)
- ✅ 每指标子图:Task 1

**Placeholder scan:** Task 3/4 标了"records 从 data_result 读"/"start_agent 收集 chartData"——执行时需补这两处数据流(get_data 的 records 给 anomaly、start_agent 读 result.chartData)。

**Type consistency:** build_chart 返回 `[{title, option}]` → result.chartData → QueryResponse.chartData → 前端 charts。一致。
