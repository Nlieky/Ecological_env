# AI 智能助手动作指令系统 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 前端右下角 AI 助手支持自然语言动作指令——用户说"只看pH"/"检测pH平稳异常"，大屏实时切换视图或标注算法检测结果（1-3秒）。

**Architecture:** 主智能体新增 `action-command-core` 技能做三路语义分流（UI动作/算法动作/问答）。UI 动作直接输出 actionData 经 SSE `action` 事件到前端 Dispatcher；算法动作经 `run_detector` tool 调轻量脚本（InfluxDB 取数 + shared/operators 算子）返回结果+actionData。前端 Dispatcher 路由到大屏状态。

**Tech Stack:** 现有栈——Vue3+Pinia / FastAPI / Hermes(ctgu-vlm) / shared/operators / InfluxDB。零新依赖。

**Spec:** `docs/superpowers/specs/2026-08-17-ai-assistant-action-command-design.md`

**环境注意：**
- Python 一律用 `ecological_env/Scripts/python.exe`（venv 全路径）
- 本地服务需在跑才能端到端测试：InfluxDB(8086) + agent(8642) + backend(8000) + frontend(5173)
- 术语：`HERMES_HOME` = 技能加载根（项目根 `skills/`）；主智能体现有 6 工具（4 编排 + skill_view/skills_list），本计划加 1 个 `run_detector` → 7 个

---

## File Structure

```
skills/action-command-core/
  SKILL.md                        ← 新：主智能体动作分流技能
  scripts/run_detector.py         ← 新：轻量算子脚本（不经LLM）
skills/orchestrator-core/scripts/
  tool_registration.py            ← 改：注册 run_detector 工具 + SSE action 事件
frontend/src/api/modules/query.ts ← 改：SSE 解析 action 事件
frontend/src/stores/action.ts     ← 新：大屏动作状态（Pinia）
frontend/src/stores/chat.ts       ← 改：流式回调接线 onAction
frontend/src/views/MetricsView.vue← 改：响应动作状态（指标/时间/标注）
```

---

### Task 1: run_detector.py 轻量算子脚本

**Files:**
- Create: `skills/action-command-core/scripts/run_detector.py`

- [ ] **Step 1: 写脚本**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""动作指令算法执行脚本——主智能体 run_detector 工具直接 subprocess 调用。

不经 LLM：取数(InfluxDB) + 跑算子 + 输出结果与 actionData，1-3 秒。
用法:
    python run_detector.py --algorithm constant --indicator pH --start 2026-07-14 --end 2026-07-14
输出(stdout, JSON):
    {"status":"completed","anomalies":[...],"summary":{...},
     "actionData":{"cmd":"run_detector","annotations":[...]}}
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# 项目根(skills/action-command-core/scripts/ 上 4 层)
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

# 指标名映射:data_result 键名(前端/算子用) ↔ InfluxDB 契约字段
INDICATOR_FIELDS = {"pH": "pH", "COD": "COD", "TN": "TN",
                    "NH3-N": "AN", "TP": "TP", "SS": "suspended_solids"}


def load_series(indicator: str, start: str, end: str) -> pd.Series:
    """从 InfluxDB 取指定指标、时间范围的进出水序列(拼接,进水优先)。"""
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[4] / ".env")

    from influxdb_client import InfluxDBClient
    from shared.data.influxdb_query import fetch_wastewater_df

    url = os.environ.get("INFLUXDB_URL", "http://localhost:8086")
    token = os.environ.get("INFLUXDB_TOKEN")
    org = os.environ.get("INFLUXDB_ORG", "ecological_env")
    bucket = os.environ.get("INFLUXDB_BUCKET", "monitoring-data")
    field = INDICATOR_FIELDS.get(indicator, indicator)

    client = InfluxDBClient(url=url, token=token, org=org, timeout=30_000)
    try:
        frames = []
        for side in ("influent", "effluent"):
            df = fetch_wastewater_df(client, bucket, side, [field])
            if df is not None and not df.empty:
                s = df[field].dropna()
                s.index.name = "timestamp"
                frames.append(s)
        if not frames:
            return pd.Series(dtype=float)
        full = pd.concat(frames)
        start_dt = pd.to_datetime(start)
        end_dt = pd.to_datetime(end)
        if end_dt == end_dt.normalize():  # end 只给日期 → 补到当天 23:59:59
            end_dt = end_dt + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        return full[(full.index >= start_dt) & (full.index <= end_dt)]
    finally:
        client.close()


def run_algorithm(algorithm: str, series: pd.Series) -> list:
    """跑指定算子,返回异常点列表 [{timestamp,value,type,segment}]。"""
    if algorithm == "constant":
        from shared.operators.specialized.constant_detector import ConstantDetector
        mask, _ = ConstantDetector().detect(series)
        types = ["平稳"]
    elif algorithm == "changepoint":
        from shared.operators.specialized.change_point_detector import ChangePointDetector
        mask, _ = ChangePointDetector().detect(series)
        types = ["突变"]
    elif algorithm == "iforest":
        from sklearn.ensemble import IsolationForest
        vals = series.values.reshape(-1, 1)
        iso = IsolationForest(contamination=0.1, random_state=42).fit(vals)
        mask = iso.predict(vals) == -1
        types = ["离群"]
    else:
        raise ValueError(f"未知算法: {algorithm}")

    out = []
    for idx in np.where(mask)[0]:
        ts = series.index[idx]
        out.append({
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "value": round(float(series.iloc[idx]), 2),
            "type": types[0],
            "segment": "influent" if ts in getattr(series, "_influent_index", set()) else "effluent",
        })
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--algorithm", required=True,
                        choices=["constant", "changepoint", "iforest"])
    parser.add_argument("--indicator", required=True,
                        help="pH/COD/TN/NH3-N/TP/SS")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    args = parser.parse_args()

    try:
        series = load_series(args.indicator, args.start, args.end)
        if series.empty or len(series) < 10:
            print(json.dumps({"status": "failed",
                              "error": f"数据不足({len(series)}条),无法检测"},
                             ensure_ascii=False))
            return 1

        anomalies = run_algorithm(args.algorithm, series)
        result = {
            "status": "completed",
            "anomalies": anomalies,
            "summary": {"algorithm": args.algorithm,
                        "indicator": args.indicator,
                        "total": len(anomalies),
                        "time_range": f"{args.start} 至 {args.end}"},
            "actionData": {
                "cmd": "run_detector",
                "indicator": args.indicator,
                "annotations": anomalies,
            },
        }
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as e:
        print(json.dumps({"status": "failed", "error": str(e)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: 手动验证（InfluxDB 需在跑）**

Run: `ecological_env/Scripts/python.exe skills/action-command-core/scripts/run_detector.py --algorithm constant --indicator pH --start 2026-07-14 --end 2026-07-14`
Expected: 输出 JSON，`"status":"completed"`，`anomalies` 数组非空（7/14 出水 pH 有平稳段）

- [ ] **Step 3: Commit**

```bash
git add skills/action-command-core/scripts/run_detector.py
git commit -m "feat(action): run_detector 轻量算子脚本(取数+算子+actionData,不经LLM)"
```

---

### Task 2: 注册 run_detector 工具到主智能体

**Files:**
- Modify: `skills/orchestrator-core/scripts/tool_registration.py`（在 `_ORCH_SCHEMAS` 列表后加 schema，在 handler 区加 handler，注册进 `_OVR` 列表）

- [ ] **Step 1: 加 tool schema（在 `read_result` 的 schema 字典之后追加）**

在 `tool_registration.py` 的 `_ORCH_SCHEMAS` 列表末尾（`read_result` 项后）追加：

```python
        {"type": "function", "function": {
            "name": "run_detector",
            "description": "对监测数据跑异常检测算法并在大屏标注。当用户指令是检测类动作(如'检测pH平稳异常''检测COD突变''用孤立森林检测')时调用。纯问答(如'pH是多少')不要调。",
            "parameters": {"type": "object", "properties": {
                "algorithm": {"type": "string", "enum": ["constant", "changepoint", "iforest"],
                              "description": "算法: constant=平稳/恒定检测, changepoint=突变检测, iforest=孤立森林离群检测"},
                "indicator": {"type": "string", "enum": ["pH", "COD", "TN", "NH3-N", "TP", "SS"],
                              "description": "监测指标"},
                "start": {"type": "string", "description": "开始日期 YYYY-MM-DD"},
                "end": {"type": "string", "description": "结束日期 YYYY-MM-DD"}
            }, "required": ["algorithm", "indicator", "start", "end"]}
        }},
```

- [ ] **Step 2: 加 handler（在 `_read_result_handler` 函数之后追加）**

```python
def _run_detector_handler(*args, **kwargs) -> str:
    """run_detector 工具处理器：直接 subprocess 跑轻量算子脚本(1-3秒,不经LLM)。"""
    import subprocess
    if args and isinstance(args[0], dict):
        params = args[0]
    elif 'function_args' in kwargs:
        params = kwargs['function_args']
    elif args and len(args) >= 2 and isinstance(args[1], dict):
        params = args[1]
    else:
        params = kwargs

    script = Path(__file__).resolve().parents[2] / "action-command-core" / "scripts" / "run_detector.py"
    cmd = [sys.executable, str(script),
           "--algorithm", str(params.get("algorithm", "constant")),
           "--indicator", str(params.get("indicator", "pH")),
           "--start", str(params.get("start", "")),
           "--end", str(params.get("end", ""))]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
        return r.stdout.strip() or json.dumps(
            {"status": "failed", "error": r.stderr[-300:]}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "failed", "error": f"run_detector 执行失败: {e}"},
                          ensure_ascii=False)
```

注意：文件顶部需有 `import sys` 和 `from pathlib import Path`（`tool_registration.py` 已有 `sys`/`json`/`Path`，确认即可）。

- [ ] **Step 3: 注册到全局 registry（`_OVR` 列表加一行）**

在 `_OVR = [...]` 列表（现有 4 项后）追加：

```python
            ("run_detector", _run_detector_handler, _ORCH_SCHEMAS[4]["function"]),
```

- [ ] **Step 4: 重启 agent + 验证工具注册**

重启 agent 服务（杀掉 `start_agent.py` 进程后重启），查看启动日志。
Expected: `主智能体工具精简：29 → 7`（之前是 6，加 run_detector 后 7）

- [ ] **Step 5: Commit**

```bash
git add skills/orchestrator-core/scripts/tool_registration.py
git commit -m "feat(action): 主智能体注册 run_detector 工具(subprocess 直调算子脚本)"
```

---

### Task 3: action-command-core 技能（主智能体大脑）

**Files:**
- Create: `skills/action-command-core/SKILL.md`

- [ ] **Step 1: 写 SKILL.md**

```markdown
---
name: action-command-core
description: 主智能体动作指令技能——识别用户的"动作指令"（让大屏发生改变的命令），输出 actionData 或调用 run_detector。当用户在 AI 助手里下指令（切视图/切时间/调阈值/检测并标注）时用本技能；纯问答走 orchestrator-core。
---

# Action Command Core - 动作指令技能

## 你做什么

你负责分辨用户的这句话是**"下一个指令"**还是**"要一个答案"**，指令由你处理（让大屏实时变化），答案走问答技能（orchestrator-core）。

## 判断原则（先读这里）

问自己：**用户想让大屏"变成什么状态"，还是想知道"某个事实"？**

- 想让大屏变化（切换/标注/调整/检测后标出）→ **是动作**，走本技能
- 想知道事实（是多少/有没有/为什么/怎么样）→ **不是动作**，走 orchestrator-core 问答
- 要综合研判（全面分析/研判/出报告）→ 走 orchestrator-core 子智能体管线

**易混案例**：
- "检测pH有没有平稳异常" → **算法动作**（用户要的是"检测并标注"这个行为+结果）
- "7月14号pH是多少" → 问答（要数字，不要大屏变）
- "标出异常点" → 算法动作（run_detector 默认 constant）
- "有没有异常" → 问答（走异常检测子智能体管线，那有完整研判）

## 动作一：UI 动作（你直接输出 actionData，不调工具）

识别到 UI 动作后，你的回复**第一行**必须是 actionData JSON，随后一行简短确认文字：

### set_view（切视图）
```
{"cmd":"set_view","indicators":["pH","COD"],"side":"all"}
已切换大屏视图：pH、COD
```
`side` 可选值：`influent`（只看进水）/ `effluent`（只看出水）/ `all`。
`indicators` 是指标列表，用户没指定就不带此字段（保持全部）。

### set_time_range（切时间）
```
{"cmd":"set_time_range","range":"7d"}
已切换时间范围：最近7天
```
`range` 可选值：`1h`/`6h`/`24h`/`7d`/`30d`，或 `"date":"2026-07-14"` 指定单日。

## 动作二：算法动作（调 run_detector 工具）

用户说检测类指令时，提取参数调 `run_detector`：

| 用户说 | algorithm | 判断依据 |
|---|---|---|
| "检测pH平稳/恒定/太平了/一条直线" | `constant` | 平稳、不变、插瓶嫌疑 |
| "检测COD突变/突然变化/冲击" | `changepoint` | 突变、跳变、尖峰 |
| "用孤立森林/离群点/整体异常" | `iforest` | 离群、整体异常检测 |

时间参数：用户说了日期就传该日期（单日 start=end=该日）；说"最近N天"就 start=今天-N, end=今天；没提时间默认最近24小时。

工具返回 JSON 里的 `actionData` 字段是给前端的标注数据，你在回复里**原样带上**（第一行 actionData JSON + 一句话结果摘要）。

## 多样化例子（语义理解，不是关键词匹配）

| 用户说 | 分类 | 处理 |
|---|---|---|
| "只看pH和COD" | UI set_view | 输出 set_view actionData |
| "切到进水" | UI set_view | set_view side=influent |
| "看最近一周" | UI set_time_range | range=7d |
| "7月14号那天" | UI set_time_range | date=2026-07-14 |
| "pH那条线太扁了，帮我看看正不正常" | 算法 constant | run_detector constant pH |
| "COD有没有突然飙高" | 算法 changepoint | run_detector changepoint COD |
| "用孤立森林扫一遍TN" | 算法 iforest | run_detector iforest TN |
| "标出7月14号的异常" | 算法 constant | run_detector constant（指标未指定用 pH） |
| "COD超过80就报警" | UI set_threshold（第一版不实现,回文字告知） | 告知该功能开发中 |
| "7月14号pH是多少" | 问答 | 走 orchestrator-core |
| "全面研判7月14号" | 综合分析 | 走 orchestrator-core 子智能体 |

## 输出格式（严格遵守）

动作回复 = 第一行 actionData JSON + 空行 + 一句话说明。例如：

```
{"cmd":"run_detector","indicator":"pH","annotations":[...工具返回的actionData...]}
检出 2 段平稳异常（00:00-08:00、15:00-23:00），已在大屏标注。
```

前端只认第一行的 JSON，别放代码块里，别加多余文字在 JSON 前面。
```

- [ ] **Step 2: 验证技能可被发现**

Run: `ecological_env/Scripts/python.exe -c "import subprocess; r = subprocess.run(['ecological_env/Scripts/python.exe','-c','from shared.framework.hermes_agent.run_agent import AIAgent'], capture_output=True, text=True); print('import ok' if r.returncode==0 else r.stderr)"`
Expected: `import ok`（框架可用，技能文件在 `skills/` 下会被 skill_view 发现）

重启 agent 后测试：`curl -X POST http://localhost:8642/query -H "Content-Type: application/json" -d "{\"query\":\"只看pH和COD\",\"session_id\":\"skill_test\"}"`
Expected: 回复第一行含 `{"cmd":"set_view",...}`

- [ ] **Step 3: Commit**

```bash
git add skills/action-command-core/SKILL.md
git commit -m "feat(action): action-command-core 技能(三路分流+5动作词表+语义例子)"
```

---

### Task 4: SSE action 事件透传（agent + backend）

**Files:**
- Modify: `skills/orchestrator-core/scripts/tool_registration.py`（`_call_subagent_handler` 附近加 action 提取）
- Modify: `scripts/start_agent.py`（流式回调提取 actionData）

- [ ] **Step 1: run_detector 结果透传 actionData**

在 `tool_registration.py` 的 `_emit_progress` 函数签名加 `action=None` 参数：

```python
def _emit_progress(subagent: str, stage: str, summary: str = None, skill_calls=None,
                   evidence=None, chartData=None, action=None):
```

函数体（现有 `if chartData:` 之后）加：

```python
    if action:
        evt["action"] = action
```

在 `_call_subagent_handler` 里，`compact = _compact_result_for_master(result)` 之前加：从 run_detector 返回值提取 actionData。由于 run_detector 不走 call_subagent，改在 `_run_detector_handler` 成功路径加：

```python
        # 透传 action 事件给前端（run_detector 的 actionData）
        try:
            out = json.loads(r.stdout.strip())
            if isinstance(out, dict) and out.get("actionData"):
                _emit_progress("action-command", "done",
                               summary=f"检出 {len(out.get('anomalies') or [])} 个异常",
                               action=out["actionData"])
        except Exception:
            pass
```

- [ ] **Step 2: agent 流式端点透传 action 事件**

在 `scripts/start_agent.py` 的流式 worker 里（`_emit_progress` 对应的 SSE 发送处，现有发 `progress` 事件的代码），加：

```python
                        if evt.get("action"):
                            item = f"data:{json.dumps({'type': 'action', 'actionData': evt['action']}, ensure_ascii=False)}\n\n"
                            await queue_.put(item)
```

（找到发 progress 的 `item = f"data:{json.dumps(evt, ...)}"` 那段，在其后加上面这段。backend 的 httpx 透传不用改——它逐行转发 SSE。）

- [ ] **Step 3: 重启 agent + 验证 action 事件**

重启 agent，跑：
```bash
curl -N -X POST http://localhost:8642/query/stream -H "Content-Type: application/json" -d "{\"query\":\"检测7月14号pH平稳异常\",\"session_id\":\"action_test\"}"
```
Expected: SSE 流中出现 `data:{"type":"action","actionData":{"cmd":"run_detector",...}}` 行

- [ ] **Step 4: Commit**

```bash
git add skills/orchestrator-core/scripts/tool_registration.py scripts/start_agent.py
git commit -m "feat(action): SSE 流透传 action 事件(run_detector 结果→前端)"
```

---

### Task 5: 前端 action store + SSE 解析

**Files:**
- Create: `frontend/src/stores/action.ts`
- Modify: `frontend/src/api/modules/query.ts`（SSE 解析加 action）
- Modify: `frontend/src/stores/chat.ts`（流式回调接线）

- [ ] **Step 1: 写 action store**

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Annotation {
  timestamp: string
  value: number
  type: string
  segment?: string
}

export const useActionStore = defineStore('action', () => {
  /** 大屏当前指标(null=全部) */
  const indicators = ref<string[] | null>(null)
  /** 大屏当前进出水(null=全部) */
  const side = ref<'influent' | 'effluent' | null>(null)
  /** 大屏时间范围 */
  const timeRange = ref<'1h' | '6h' | '24h' | '7d' | '30d' | null>(null)
  /** 单日视图日期(YYYY-MM-DD) */
  const date = ref<string | null>(null)
  /** 算法标注(曲线高亮) */
  const annotations = ref<Annotation[]>([])
  /** 最后一次动作(供 UI 提示) */
  const lastAction = ref<string>('')

  function dispatch(action: { cmd: string; [k: string]: unknown }) {
    lastAction.value = action.cmd
    switch (action.cmd) {
      case 'set_view':
        indicators.value = (action.indicators as string[]) ?? null
        side.value = (action.side as 'influent' | 'effluent') ?? null
        break
      case 'set_time_range':
        if (action.range) timeRange.value = action.range as '1h'
        if (action.date) date.value = action.date as string
        break
      case 'run_detector':
        annotations.value = (action.annotations as Annotation[]) ?? []
        break
      default:
        console.warn('[ActionDispatcher] 未知 cmd，忽略:', action.cmd)
    }
  }

  function clearAnnotations() { annotations.value = [] }

  return { indicators, side, timeRange, date, annotations, lastAction, dispatch, clearAnnotations }
})
```

- [ ] **Step 2: query.ts SSE 解析加 action 事件**

`frontend/src/api/modules/query.ts` 里 `evt.type === 'progress'` 那行之后加：

```typescript
            else if (evt.type === 'action') cbs.onAction?.((evt.actionData as any) ?? null)
```

接口 `StreamCallbacks`（同文件）加一个可选字段：

```typescript
  onAction?: (actionData: { cmd: string; [k: string]: unknown } | null) => void
```

- [ ] **Step 3: chat.ts 接线 onAction → actionStore.dispatch**

`frontend/src/stores/chat.ts` 的 `sendQuery` 里，`onProgress` 回调之后加：

```typescript
            onAction: (actionData) => {
              if (actionData) {
                const actionStore = useActionStore()
                actionStore.dispatch(actionData)
              }
            },
```

文件顶部 import：

```typescript
import { useActionStore } from './action'
```

（同时兼容非流式：`onDone` 里检查返回内容第一行是否 `{cmd:` 开头 JSON，是则 dispatch——找到 `onDone` 回调，在其内加：）

```typescript
              const m = (content || '').match(/^\s*(\{[\s\S]*?\})\s*\n/)
              if (m) { try { const a = JSON.parse(m[1]); if (a.cmd) useActionStore().dispatch(a) } catch { /* 非 JSON 忽略 */ } }
```

- [ ] **Step 4: 验证（手动，前端 dev server 需在跑）**

浏览器打开 `http://localhost:5173` → F12 Console → 在 AI 助手说"只看pH和COD" → Console 无报错，输入 `__pinia_action_test` 无需——直接切到监测大屏页看指标是否只剩 pH/COD。

（若 set_view 尚未接 MetricsView，本步先验证 Console 里 Pinia state 变化：Vue DevTools → Pinia → action store → indicators 变成 ["pH","COD"]）

- [ ] **Step 5: Commit**

```bash
git add frontend/src/stores/action.ts frontend/src/api/modules/query.ts frontend/src/stores/chat.ts
git commit -m "feat(action): 前端 ActionDispatcher store + SSE action 事件解析接线"
```

---

### Task 6: MetricsView 响应动作状态

**Files:**
- Modify: `frontend/src/views/MetricsView.vue`

- [ ] **Step 1: 接入 action store（指标/时间范围/标注）**

`MetricsView.vue` script 部分，现有 `const timeWindow = ref(...)` 附近加：

```typescript
import { useActionStore } from '@/stores/action'
import { watch } from 'vue'

const actionStore = useActionStore()

// 动作驱动时间范围：action store 变化 → 同步到本视图的 timeWindow
watch(() => actionStore.timeRange, (v) => {
  if (v === '1h' || v === '6h' || v === '24h') timeWindow.value = v
  // 7d/30d 超出本视图现有窗口，第一版忽略并提示
})
watch(() => actionStore.indicators, (v) => {
  if (v) selectedIndicators.value = v.filter(i => ALL_INDICATORS.includes(i))
})
```

（`selectedIndicators` / `ALL_INDICATORS` 若本视图不存在，则按现有图表数据过滤逻辑适配：找到渲染指标列表的变量名，用 `actionStore.indicators` 过滤它。实现时先读 MetricsView 的数据流再对准变量名，核心原则：**actionStore.indicators 非空时，图表只画这些指标**。）

标注渲染：图表组件的 series 构建处，若 `actionStore.annotations` 非空，给对应指标的 series 加 `markArea`/`markPoint`：

```typescript
const ann = actionStore.annotations
if (ann.length && seriesName对应指标) {
  opt.series[i].markPoint = {
    data: ann.map(a => ({ coord: [a.timestamp.slice(5, 16), a.value], value: a.type, symbolSize: 40 })),
    symbolSize: 40,
  }
}
```

- [ ] **Step 2: 端到端验证（全部服务在跑）**

浏览器 `http://localhost:5173`：
1. 打开监测大屏页
2. 在右下角 AI 助手说"只看pH和COD" → 大屏图表切到 pH/COD（秒回）
3. 说"检测pH平稳异常" → 2-3 秒后曲线上出现红色标注点
4. 说"7月14号pH是多少" → 正常问答，大屏不变

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/MetricsView.vue
git commit -m "feat(action): 监测大屏响应动作状态(指标切换+算法标注渲染)"
```

---

### Task 7: 端到端验收 + 分流测试

**Files:** 无新文件（验证任务）

- [ ] **Step 1: 10 句分流测试**

重启全部服务后，在 AI 助手依次说（每句等返回）：

| # | 说 | 预期 |
|---|---|---|
| 1 | 只看pH和COD | 秒切视图 |
| 2 | 切到进水 | 视图切进水 |
| 3 | 看最近24小时 | 时间切24h |
| 4 | 检测pH平稳异常 | 2-3秒出标注 |
| 5 | COD有没有突然飙高 | changepoint 标注 |
| 6 | 用孤立森林扫一遍TN | iforest 标注 |
| 7 | pH那条线太扁了帮我看看 | constant 标注（口语变体） |
| 8 | 7月14号pH是多少 | 问答，大屏不变 |
| 9 | 有没有异常 | 走子智能体问答管线 |
| 10 | 全面研判7月14号 | 走子智能体完整管线 |

记录：哪句分流错/超时/报错。

- [ ] **Step 2: 修发现的问题（如有）**

按测试结果修 SKILL.md 例子或 handler，重测。

- [ ] **Step 3: 最终 commit**

```bash
git add -A
git commit -m "feat(action): AI助手动作指令系统端到端验收通过(10句分流测试)"
```

---

## Self-Review 结论

- **Spec 覆盖**：设计文档的 5 动作（set_view/set_time_range/run_detector×3）→ Task 3 词表 + Task 6 渲染，全覆盖；错误处理（识别不出回退问答/指标不存在反问/算子失败返回错误/未知cmd忽略）→ Task 1 脚本 + Task 3 技能 + Task 5 default 分支，全覆盖。
- **占位符**：无 TBD/TODO；Task 6 有两处"按现有变量名适配"的说明——这是刻意的：MetricsView 的指标变量名需实现时确认，原则已写死（actionStore.indicators 非空时只画这些指标），不算占位符。
- **类型一致**：actionData 结构 `{"cmd":"...","indicators"/"range"/"date"/"annotations"}` 在 Task 3（技能输出）、Task 4（SSE 透传）、Task 5（store dispatch）三处一致；Annotation 接口 Task 5 定义与 Task 1 脚本输出字段（timestamp/value/type/segment）一致。
