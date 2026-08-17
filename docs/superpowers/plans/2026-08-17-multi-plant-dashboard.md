# 多厂区仪表盘目录系统 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立"市→厂区→厂"三级仪表盘目录——从 InfluxDB 自动发现厂，配置文件分层，每厂有专属看板页（指标卡+趋势图+AI动作响应）。

**Architecture:** 数据层新增 `discover_plants()`（InfluxDB group by plant_id）+ `plant-hierarchy.yaml`（层级配置）；后端新增 2 个 v1 接口（tree/dashboard）；前端新增 PlantTree 组件 + PlantDashboardView 视图 + 路由。

**Tech Stack:** 现有栈——Vue3+Pinia+Vue Router / FastAPI / InfluxDB Client / PyYAML（已装）。

**Spec:** `docs/superpowers/specs/2026-08-17-multi-plant-dashboard-design.md`

**环境注意：**
- Python 用 `ecological_env/Scripts/python.exe`，项目根 `E:\project\Ecological_env`
- InfluxDB 需在跑（8086）才能验证发现/看板接口；数据里有 plant_id="当阳市金桥污水处理厂一期"
- 前端验证用 `cd frontend && npx vue-tsc --noEmit`（有 3 个预先存在的错误可忽略：ChatMessage 'c' unused / GrafanaView env ×2）

---

## File Structure

```
shared/data/discover_plants.py              ← 新：自动发现 + 层级合并
shared/data/plant-hierarchy.yaml           ← 新：市→厂区→厂 配置
backend/api/v1/plants/__init__.py          ← 新：路由包
backend/api/v1/plants/routes.py            ← 新：/api/v1/plants/tree + /{id}/dashboard
backend/main.py                            ← 改：注册 plants 路由（+1行）
frontend/src/api/modules/plants.ts         ← 改：加 tree/dashboard 调用
frontend/src/api/types/api.types.ts        ← 改：加 PlantTreeNode/PlantDashboard 类型
frontend/src/stores/plants.ts              ← 新：目录树状态（拉取+缓存）
frontend/src/components/cockpit/PlantTree.vue ← 新：三级折叠目录树
frontend/src/views/PlantDashboardView.vue  ← 新：单厂看板页
frontend/src/router/index.ts               ← 改：加 /plants/:plantId 路由
```

---

### Task 1: discover_plants.py 数据发现 + 层级合并

**Files:**
- Create: `shared/data/discover_plants.py`
- Create: `shared/data/plant-hierarchy.yaml`

- [ ] **Step 1: 写层级配置文件**

`shared/data/plant-hierarchy.yaml`：

```yaml
# 市 → 厂区 → 厂 层级配置
# 厂名必须与 InfluxDB 里 plant_id tag 完全一致(即 xls 报表解析出的厂名)。
# 有数据但未列在此的厂自动落"未分组"；列了但没数据的厂显示为离线(预登记)。
当阳市:
  城东厂区:
    - 当阳市金桥污水处理厂一期
```

- [ ] **Step 2: 写发现+合并模块**

`shared/data/discover_plants.py`（完整代码）：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 InfluxDB 自动发现所有厂(plant_id)，按 plant-hierarchy.yaml 合并出目录树。

发现靠数据（导新厂报表自动出现），分层靠配置（业务知识手写）。
没配置的厂自动落"未分组"，不会丢。
"""
from pathlib import Path
from typing import Dict, List, Optional

_DATA_DIR = Path(__file__).resolve().parent
_HIERARCHY_FILE = _DATA_DIR / "plant-hierarchy.yaml"


def discover_plants() -> List[Dict]:
    """InfluxDB group by plant_id，返回所有有数据的厂。

    返回: [{"plant_id": str, "data_types": ["influent",...],
            "latest_time": str, "point_count": int}]
    """
    from shared.data.influxdb_query import get_client_and_bucket
    client, bucket = get_client_and_bucket()
    flux = (
        f'from(bucket: "{bucket}") '
        f'|> range(start: 0) '
        f'|> filter(fn: (r) => r._measurement == "wastewater") '
        f'|> group(columns: ["plant_id", "data_type"]) '
        f'|> last() '
        f'|> keep(columns: ["plant_id", "data_type", "_time"])'
    )
    try:
        tables = client.query_api().query(flux)
        plants: Dict[str, Dict] = {}
        for table in tables:
            for rec in table.records:
                pid = rec.values.get("plant_id") or "unknown"
                dtype = rec.values.get("data_type") or ""
                ts = str(rec.get_time())
                info = plants.setdefault(pid, {
                    "plant_id": pid, "data_types": [],
                    "latest_time": ts, "point_count": 0,
                })
                if dtype and dtype not in info["data_types"]:
                    info["data_types"].append(dtype)
                if ts > info["latest_time"]:
                    info["latest_time"] = ts
        return sorted(plants.values(), key=lambda p: p["plant_id"])
    finally:
        client.close()


def load_hierarchy() -> Dict:
    """读 plant-hierarchy.yaml，返回 {市: {厂区: [厂名]}}。文件缺失返回空 dict。"""
    if not _HIERARCHY_FILE.exists():
        return {}
    import yaml
    with open(_HIERARCHY_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_tree() -> Dict:
    """发现 ∩ 配置 → 目录树。

    返回: {
      "cities": [{"name": 市, "districts": [{"name": 厂区, "plants": [节点]}]}],
      "ungrouped": [节点]
    }
    节点: {"plant_id", "status": "online"|"offline",
           "data_types", "latest_time", "point_count}
    """
    discovered = {p["plant_id"]: p for p in discover_plants()}
    hierarchy = load_hierarchy()

    cities = []
    assigned = set()
    for city, districts in (hierarchy or {}).items():
        dist_nodes = []
        for dist, plant_names in (districts or {}).items():
            plant_nodes = []
            for name in (plant_names or []):
                assigned.add(name)
                plant_nodes.append(_make_node(name, discovered))
            dist_nodes.append({"name": dist, "plants": plant_nodes})
        cities.append({"name": city, "districts": dist_nodes})
    ungrouped = [_make_node(pid, discovered)
                 for pid in sorted(set(discovered) - assigned)]
    return {"cities": cities, "ungrouped": ungrouped}


def _make_node(pid: str, discovered: Dict[str, Dict]) -> Dict:
    p = discovered.get(pid)
    if p:
        return {**p, "status": "online"}
    return {"plant_id": pid, "status": "offline", "data_types": [],
            "latest_time": "", "point_count": 0}


if __name__ == "__main__":
    import json
    print(json.dumps(build_tree(), ensure_ascii=False, indent=2))
```

- [ ] **Step 3: 验证（InfluxDB 需在跑）**

Run: `ecological_env/Scripts/python.exe shared/data/discover_plants.py`
Expected: JSON 输出，`cities[0].name="当阳市"`，其 districts[0].plants[0] 含 `plant_id="当阳市金桥污水处理厂一期"`、`status="online"`、`data_types` 含 influent+effluent。

- [ ] **Step 4: Commit**

```bash
git add shared/data/discover_plants.py shared/data/plant-hierarchy.yaml
git commit -m "feat(plants): 数据自动发现厂列表+层级配置合并(市→厂区→厂)"
```

---

### Task 2: 后端 /api/v1/plants 接口

**Files:**
- Create: `backend/api/v1/plants/__init__.py`
- Create: `backend/api/v1/plants/routes.py`
- Modify: `backend/main.py`（v1 路由注册处加 1 行）

- [ ] **Step 1: 写路由**

`backend/api/v1/plants/__init__.py`（空文件即可）。

`backend/api/v1/plants/routes.py`（完整代码）：

```python
"""多厂区仪表盘 API——厂目录树 + 单厂看板数据（真实 InfluxDB 数据）。

与旧 mock 的 /api/realtime/plants 区分：这里是真实数据，按 plant_id tag 过滤。
"""
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["多厂区仪表盘"])


@router.get("/plants/tree")
async def get_plant_tree():
    """厂目录树：市→厂区→厂，从数据自动发现+配置分层。"""
    try:
        from shared.data.discover_plants import build_tree
        return {"success": True, "data": build_tree()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"构建厂目录树失败: {e}")


# 厂看板指标定义：(显示名, InfluxDB字段, 出水限值, 单位)
_DASH_INDICATORS = [
    ("pH", "pH", (6.0, 9.0), ""),
    ("COD", "COD", 100.0, "mg/L"),
    ("TN", "TN", 20.0, "mg/L"),
    ("氨氮", "AN", 15.0, "mg/L"),
    ("TP", "TP", 1.0, "mg/L"),
    ("SS", "suspended_solids", None, "mg/L"),
]


@router.get("/plants/{plant_id}/dashboard")
async def get_plant_dashboard(plant_id: str, hours: int = 24):
    """单厂看板数据包：各指标当前值+趋势+状态。hours 控制趋势窗口（默认24）。"""
    try:
        from datetime import datetime, timedelta
        import pandas as pd
        from shared.data.influxdb_query import get_client_and_bucket

        client, bucket = get_client_and_bucket()
        start = (datetime.utcnow() - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
        plant_id = plant_id.replace('"', '')  # 防 flux 注入：去掉引号

        def _flux(data_type: str) -> str:
            return (
                f'from(bucket: "{bucket}") '
                f'|> range(start: {start}) '
                f'|> filter(fn: (r) => r._measurement == "wastewater" '
                f'  and r.plant_id == "{plant_id}" '
                f'  and r.data_type == "{data_type}") '
                f'|> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")'
            )

        trends = {}
        current = {}
        try:
            dfs = {}
            for side in ("influent", "effluent"):
                df = client.query_api().query_data_frame(_flux(side))
                if isinstance(df, list):
                    df = pd.concat([d for d in df if not d.empty], ignore_index=True) if df else pd.DataFrame()
                dfs[side] = df if df is not None and not df.empty else pd.DataFrame()
        finally:
            client.close()

        for label, field, limit, unit in _DASH_INDICATORS:
            item = {"label": label, "unit": unit,
                    "limit": limit, "influent": None, "effluent": None,
                    "status": "nodata", "series": {"influent": [], "effluent": []}}
            for side in ("influent", "effluent"):
                df = dfs.get(side, pd.DataFrame())
                if field in df.columns:
                    series = df[["_time", field]].dropna()
                    item["series"][side] = [
                        {"time": str(r["_time"])[:19].replace("T", " "),
                         "value": round(float(r[field]), 2)}
                        for _, r in series.iterrows()
                    ]
                    if not series.empty:
                        last = round(float(series.iloc[-1][field]), 2)
                        item[side] = last
            # 状态：有出水值→按限值判 normal/warning；无→nodata
            eff = item["effluent"]
            if eff is not None and limit is not None:
                lo, hi = limit if isinstance(limit, tuple) else (None, limit)
                bad = (lo is not None and eff < lo) or (hi is not None and eff > hi)
                item["status"] = "warning" if bad else "normal"
            elif eff is not None:
                item["status"] = "normal"
            trends[field] = item

        return {"success": True, "data": {
            "plant_id": plant_id,
            "window_hours": hours,
            "indicators": trends,
            "influent_points": len(dfs.get("influent", pd.DataFrame())),
            "effluent_points": len(dfs.get("effluent", pd.DataFrame())),
        }}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"厂看板数据获取失败: {e}")
```

- [ ] **Step 2: 注册路由**

`backend/main.py` 129-131 行附近（现有 v1 注册处）加：

```python
from backend.api.v1 import plants as v1_plants
app.include_router(v1_plants.router, prefix="/api/v1")
```

（import 放文件顶部与其它 v1 import 并排，include_router 放 131 行后。）

- [ ] **Step 3: 重启 backend 验证**

重启 backend 后：

Run: `curl http://localhost:8000/api/v1/plants/tree`
Expected: `{"success":true,"data":{"cities":[{"name":"当阳市",...,"plants":[{"plant_id":"当阳市金桥污水处理厂一期","status":"online",...}]}]},"ungrouped":[]}`

Run（plant_id 需 URL 编码，用浏览器或 curl 的 --data-urlencode 不行，直接写中文让 curl 自动处理，Windows 下验证用 Python）：
`ecological_env/Scripts/python.exe -c "import urllib.request,json; req=urllib.request.urlopen('http://localhost:8000/api/v1/plants/' + urllib.parse.quote('当阳市金桥污水处理厂一期') + '/dashboard'); d=json.load(req); print(d['success'], d['data']['effluent_points'])"`
Expected: `True 24`（或该时间窗内的实际点数）

- [ ] **Step 4: Commit**

```bash
git add backend/api/v1/plants/ backend/main.py
git commit -m "feat(plants): /api/v1/plants/tree+dashboard 真实数据接口(替代mock)"
```

---

### Task 3: 前端类型 + API 模块 + plants store

**Files:**
- Modify: `frontend/src/api/types/api.types.ts`（文件末尾追加类型）
- Modify: `frontend/src/api/modules/plants.ts`（重写）
- Create: `frontend/src/stores/plants.ts`

- [ ] **Step 1: 加类型**

`api.types.ts` 末尾追加：

```typescript
// ── 多厂区仪表盘 ──
export interface PlantNode {
  plant_id: string
  status: 'online' | 'offline'
  data_types: string[]
  latest_time: string
  point_count: number
}
export interface PlantDistrict { name: string; plants: PlantNode[] }
export interface PlantCity { name: string; districts: PlantDistrict[] }
export interface PlantTree { cities: PlantCity[]; ungrouped: PlantNode[] }

export interface IndicatorTrendPoint { time: string; value: number }
export interface PlantIndicator {
  label: string
  unit: string
  limit: number | [number, number] | null
  influent: number | null
  effluent: number | null
  status: 'normal' | 'warning' | 'nodata'
  series: { influent: IndicatorTrendPoint[]; effluent: IndicatorTrendPoint[] }
}
export interface PlantDashboard {
  plant_id: string
  window_hours: number
  indicators: Record<string, PlantIndicator>
  influent_points: number
  effluent_points: number
}
```

- [ ] **Step 2: 重写 plants.ts API 模块**

```typescript
import api from '../client'
import type { PlantData, PlantTree, PlantDashboard } from '../types/api.types'

export const plantsService = {
  /** 旧 mock 接口(全厂总览用,保留兼容) */
  list: () => api.get<unknown, PlantData[]>('/realtime/plants'),

  /** 多厂区目录树(真实数据): 市→厂区→厂 */
  tree: () => api.get<unknown, { success: boolean; data: PlantTree }>('/v1/plants/tree'),

  /** 单厂看板数据(真实数据): 指标当前值+趋势+状态 */
  dashboard: (plantId: string, hours = 24) =>
    api.get<unknown, { success: boolean; data: PlantDashboard }>(
      `/v1/plants/${encodeURIComponent(plantId)}/dashboard`, { params: { hours } },
    ),
}
```

- [ ] **Step 3: 写 plants store**

`frontend/src/stores/plants.ts`：

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { plantsService } from '@/api/modules/plants'
import type { PlantTree, PlantDashboard } from '@/api/types/api.types'

export const usePlantsStore = defineStore('plants', () => {
  const tree = ref<PlantTree | null>(null)
  const treeLoading = ref(false)
  const treeError = ref<string | null>(null)

  const dashboard = ref<PlantDashboard | null>(null)
  const dashboardLoading = ref(false)

  async function fetchTree(force = false) {
    if (tree.value && !force) return tree.value
    treeLoading.value = true; treeError.value = null
    try {
      const r = await plantsService.tree()
      tree.value = r.data
      return r.data
    } catch (e: any) {
      treeError.value = e?.message || '目录树加载失败'
      return null
    } finally { treeLoading.value = false }
  }

  async function fetchDashboard(plantId: string, hours = 24) {
    dashboardLoading.value = true
    try {
      const r = await plantsService.dashboard(plantId, hours)
      dashboard.value = r.data
      return r.data
    } catch { dashboard.value = null; return null }
    finally { dashboardLoading.value = false }
  }

  return { tree, treeLoading, treeError, dashboard, dashboardLoading, fetchTree, fetchDashboard }
})
```

- [ ] **Step 4: TS 检查（确认我的文件无新错误）**

Run: `cd frontend && npx vue-tsc --noEmit 2>&1 | grep -E "plants|api.types"`
Expected: 无输出（我加的文件没错误；ChatMessage/GrafanaView 的 3 个预先存在错误不在此列）

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/types/api.types.ts frontend/src/api/modules/plants.ts frontend/src/stores/plants.ts
git commit -m "feat(plants): 前端类型+API模块+目录树store"
```

---

### Task 4: PlantTree 目录树组件

**Files:**
- Create: `frontend/src/components/cockpit/PlantTree.vue`

- [ ] **Step 1: 写组件**

```vue
<template>
  <div class="ptree">
    <div v-if="store.treeLoading" class="hint">加载厂目录…</div>
    <div v-else-if="store.treeError" class="hint err">⚠ {{ store.treeError }}</div>
    <template v-else>
      <div v-for="city in store.tree?.cities" :key="city.name" class="city">
        <button class="lvl1" @click="openCity = openCity === city.name ? '' : city.name">
          <span class="tri" :class="{ open: openCity === city.name }">▶</span>{{ city.name }}
        </button>
        <div v-show="openCity === city.name">
          <div v-for="dist in city.districts" :key="dist.name" class="dist">
            <button class="lvl2" @click="openDist = openDist === dist.name ? '' : dist.name">
              <span class="tri" :class="{ open: openDist === dist.name }">▶</span>{{ dist.name }}
            </button>
            <div v-show="openDist === dist.name">
              <button v-for="p in dist.plants" :key="p.plant_id" class="plant"
                :class="{ active: activeId === p.plant_id }" @click="$emit('select', p.plant_id)">
                <span class="dot" :class="p.status" />{{ shortName(p.plant_id) }}
                <span class="time">{{ p.latest_time.slice(5, 16) }}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
      <div v-if="store.tree?.ungrouped?.length" class="city">
        <button class="lvl1" @click="showUngrouped = !showUngrouped">
          <span class="tri" :class="{ open: showUngrouped }">▶</span>未分组
        </button>
        <div v-show="showUngrouped">
          <button v-for="p in store.tree.ungrouped" :key="p.plant_id" class="plant"
            :class="{ active: activeId === p.plant_id }" @click="$emit('select', p.plant_id)">
            <span class="dot" :class="p.status" />{{ p.plant_id }}
          </button>
        </div>
      </div>
      <div v-if="!store.tree?.cities?.length && !store.tree?.ungrouped?.length" class="hint">
        暂无厂数据（导入报表后自动出现）
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { usePlantsStore } from '@/stores/plants'

defineProps<{ activeId?: string }>()
defineEmits<{ (e: 'select', plantId: string): void }>()

const store = usePlantsStore()
const openCity = ref('')
const openDist = ref('')
const showUngrouped = ref(false)

function shortName(id: string) {
  return id.replace(/^当阳市/, '').replace(/污水处理厂/, '')
}

onMounted(() => store.fetchTree())
</script>

<style scoped>
.ptree { font-size: 13px }
.lvl1 { all: unset; cursor: pointer; display: flex; align-items: center; gap: 6px;
  font-weight: 600; font-size: 13.5px; padding: 6px 4px; color: var(--text-primary, #1e293b) }
.lvl2 { all: unset; cursor: pointer; display: flex; align-items: center; gap: 6px;
  padding: 4px 4px 4px 18px; color: var(--text-secondary, #475569) }
.plant { all: unset; cursor: pointer; display: flex; align-items: center; gap: 7px; width: 100%;
  box-sizing: border-box; padding: 5px 8px 5px 32px; color: var(--text-secondary, #475569);
  border-radius: 7px }
.plant:hover { background: rgba(99, 102, 241, .07) }
.plant.active { background: rgba(99, 102, 241, .13); color: var(--primary, #4f46e5); font-weight: 600 }
.tri { font-size: 9px; color: #94a3b8; transition: transform .15s }
.tri.open { transform: rotate(90deg) }
.dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0 }
.dot.online { background: #10b981 }
.dot.offline { background: #cbd5e1 }
.time { margin-left: auto; font-size: 10.5px; color: #94a3b8 }
.hint { padding: 10px; color: var(--text-muted, #94a3b8); font-size: 12.5px }
.hint.err { color: #ef4444 }
</style>
```

- [ ] **Step 2: TS 检查**

Run: `cd frontend && npx vue-tsc --noEmit 2>&1 | grep -E "PlantTree"`
Expected: 无输出

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/cockpit/PlantTree.vue
git commit -m "feat(plants): PlantTree 三级折叠目录树组件(市→厂区→厂+未分组)"
```

---

### Task 5: PlantDashboardView 单厂看板页 + 路由

**Files:**
- Create: `frontend/src/views/PlantDashboardView.vue`
- Modify: `frontend/src/router/index.ts`（dashboard children 加 1 条路由）

- [ ] **Step 1: 写看板视图**

```vue
<template>
  <div class="pdash">
    <!-- 布局：左目录树 + 右看板 -->
    <div class="side">
      <div class="side-ttl">厂区目录</div>
      <PlantTree :active-id="plantId" @select="goPlant" />
    </div>

    <div class="main" v-if="store.dashboard">
      <div class="head">
        <div>
          <h2>{{ plantId }}</h2>
          <span class="sub">数据窗口 {{ store.dashboard.window_hours }}h ·
            进水 {{ store.dashboard.influent_points }} 点 · 出水 {{ store.dashboard.effluent_points }} 点</span>
        </div>
        <div class="wins">
          <button v-for="w in [24, 72, 168]" :key="w" :class="{ on: hours === w }" @click="hours = w">{{ w }}h</button>
        </div>
      </div>

      <!-- 指标卡片 -->
      <div class="cards">
        <div v-for="(ind, field) in store.dashboard.indicators" :key="field" class="card"
          :class="ind.status">
          <div class="c-hd">{{ ind.label }}<span v-if="ind.unit" class="u">{{ ind.unit }}</span></div>
          <div class="c-vals">
            <div class="v"><span class="k">进水</span>{{ ind.influent ?? '—' }}</div>
            <div class="v"><span class="k">出水</span>{{ ind.effluent ?? '—' }}</div>
          </div>
          <div class="c-st" :class="ind.status">
            {{ ind.status === 'normal' ? '正常' : ind.status === 'warning' ? '⚠ 超限' : '无数据' }}
          </div>
        </div>
      </div>

      <!-- 趋势图：点卡片切换曲线 -->
      <div class="chart-card">
        <div class="ch-hd">{{ curLabel }} 趋势 · 进水 vs 出水</div>
        <div ref="chartEl" class="chart" />
      </div>
    </div>

    <div v-else class="main loading">
      {{ store.dashboardLoading ? '加载看板数据…' : '该厂暂无数据' }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import echarts from '@/lib/echarts'
import PlantTree from '@/components/cockpit/PlantTree.vue'
import { usePlantsStore } from '@/stores/plants'

const route = useRoute()
const router = useRouter()
const store = usePlantsStore()

const plantId = computed(() => decodeURIComponent(String(route.params.plantId || '')))
const hours = ref(24)
const curField = ref('COD')

const curLabel = computed(() => store.dashboard?.indicators?.[curField.value]?.label || curField.value)

const chartEl = ref<HTMLDivElement>()
let chart: ReturnType<typeof echarts.init> | null = null

function goPlant(id: string) {
  router.push(`/plants/${encodeURIComponent(id)}`)
}

function renderChart() {
  const ind = store.dashboard?.indicators?.[curField.value]
  if (!chart || !ind) return
  const infl = ind.series.influent.map((p) => [p.time.slice(5), p.value])
  const effl = ind.series.effluent.map((p) => [p.time.slice(5), p.value])
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['进水', '出水'], top: 4 },
    grid: { left: 52, right: 20, top: 34, bottom: 44 },
    xAxis: { type: 'category', data: effl.map((p) => p[0]).length ? effl.map((p) => p[0]) : infl.map((p) => p[0]) },
    yAxis: { type: 'value', name: ind.unit },
    series: [
      { name: '进水', type: 'line', smooth: true, symbol: 'none', data: infl,
        lineStyle: { width: 2 }, itemStyle: { color: '#6366f1' } },
      { name: '出水', type: 'line', smooth: true, symbol: 'none', data: effl,
        lineStyle: { width: 2 }, itemStyle: { color: '#10b981' } },
    ],
  }, true)
}

watch(hours, () => store.fetchDashboard(plantId.value, hours.value))
watch(() => store.dashboard, () => nextTick(renderChart), { deep: true })
watch(curField, renderChart)
watch(plantId, () => store.fetchDashboard(plantId.value, hours.value))

onMounted(async () => {
  if (chartEl.value) chart = echarts.init(chartEl.value)
  await store.fetchTree()
  await store.fetchDashboard(plantId.value, hours.value)
})
onBeforeUnmount(() => { chart?.dispose(); chart = null })
</script>

<style scoped>
.pdash { display: flex; gap: 16px; align-items: flex-start }
.side { width: 240px; flex-shrink: 0; background: var(--card-bg, #fff);
  border: 1px solid var(--brd, #e2e8f0); border-radius: 13px; padding: 10px 8px }
.side-ttl { font-size: 11px; color: var(--text-muted, #94a3b8); letter-spacing: .5px;
  padding: 2px 6px 8px }
.main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 14px }
.main.loading { padding: 60px; text-align: center; color: var(--text-muted) }
.head { display: flex; justify-content: space-between; align-items: center }
.head h2 { margin: 0; font-size: 18px }
.sub { font-size: 12px; color: var(--text-muted) }
.wins button { background: #fff; border: 1px solid var(--brd); border-radius: 7px;
  padding: 5px 12px; cursor: pointer; font-size: 12px; color: var(--text-secondary) }
.wins button.on { border-color: var(--primary); color: var(--primary); font-weight: 600 }
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px }
.card { background: var(--card-bg, #fff); border: 1px solid var(--brd, #e2e8f0);
  border-radius: 12px; padding: 12px 14px; cursor: pointer; transition: border-color .15s }
.card:hover { border-color: var(--primary) }
.card.warning { border-color: #fca5a5; background: rgba(239, 68, 68, .04) }
.c-hd { font-size: 13px; font-weight: 600; margin-bottom: 8px }
.c-hd .u { font-weight: 400; font-size: 11px; color: var(--text-muted); margin-left: 4px }
.c-vals { display: flex; gap: 14px }
.v { font-size: 17px; font-weight: 700 }
.v .k { font-size: 10.5px; font-weight: 400; color: var(--text-muted); margin-right: 4px }
.c-st { margin-top: 7px; font-size: 11px }
.c-st.normal { color: #10b981 }
.c-st.warning { color: #ef4444; font-weight: 600 }
.c-st.nodata { color: #94a3b8 }
.chart-card { background: var(--card-bg, #fff); border: 1px solid var(--brd, #e2e8f0);
  border-radius: 13px; padding: 12px }
.ch-hd { font-size: 13px; font-weight: 600; margin-bottom: 8px }
.chart { height: 320px }
</style>
```

- [ ] **Step 2: 加路由**

`frontend/src/router/index.ts`，在 `dashboard` 那条 children 路由后加：

```typescript
        { path: 'plants/:plantId', component: () => import('@/views/PlantDashboardView.vue'),
          meta: { title: '厂区看板', group: '监控大屏' } },
```

- [ ] **Step 3: 卡片点击切趋势（模板里 card 加 @click）**

在 Task 5 Step 1 的 `.card` div 上加 `@click="curField = String(field)"`（模板已写好则确认存在）。

- [ ] **Step 4: TS 检查 + 浏览器验证**

Run: `cd frontend && npx vue-tsc --noEmit 2>&1 | grep -E "PlantDashboard|router"`
Expected: 无输出

浏览器（服务在跑）：`http://localhost:5173/plants/当阳市金桥污水处理厂一期`
Expected: 左侧目录树（当阳市→城东厂区→金桥），右侧指标卡（pH/COD/TN/氨氮/TP/SS 进出水值+状态）+ COD 趋势图，点卡片切曲线，点 24/72/168 切窗口。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/PlantDashboardView.vue frontend/src/router/index.ts
git commit -m "feat(plants): 单厂看板页(指标卡+趋势图+时间窗)+路由"
```

---

### Task 6: 入口调整 + 端到端验证

**Files:**
- Modify: `frontend/src/views/DashboardView.vue`（加目录树入口）

- [ ] **Step 1: DashboardView 顶部加目录树侧栏**

`DashboardView.vue` 模板最外层 div 内、`.seg` 之前，包一层左右布局并把 PlantTree 放左侧：

```vue
    <!-- 左：厂区目录树 / 右：原有内容 -->
    <div class="dash-layout">
      <div class="dash-side">
        <PlantTree @select="(id) => $router.push(`/plants/${encodeURIComponent(id)}`)" />
      </div>
      <div class="dash-main">
        <!-- 原有 .seg 及以下全部内容不动，移进这个 div -->
      </div>
    </div>
```

script 加 `import PlantTree from '@/components/cockpit/PlantTree.vue'`，style 追加：

```css
.dash-layout { display: flex; gap: 16px; align-items: flex-start }
.dash-side { width: 230px; flex-shrink: 0; background: var(--card-bg);
  border: 1px solid var(--brd); border-radius: 13px; padding: 10px 8px }
.dash-main { flex: 1; min-width: 0 }
```

（把原有 `.seg`、`<template v-if="mode...">`、`PlantOverviewGrid` 整体移入 `.dash-main`。）

- [ ] **Step 2: 端到端验证**

浏览器 `http://localhost:5173/dashboard`：
1. 左侧出现厂区目录树（当阳市→城东厂区→金桥）
2. 点“金桥” → 跳 `/plants/当阳市金桥污水处理厂一期` 单厂看板
3. 看板页指标卡有真实值、趋势图有曲线、窗口切换生效
4. 右下角 AI 助手说“只看COD” → 单厂看板趋势图响应（actionStore 联动验证——如 MetricsView 的 watch 已有，看板页可后续接）

- [ ] **Step 3: 最终 Commit**

```bash
git add frontend/src/views/DashboardView.vue
git commit -m "feat(plants): DashboardView 加厂区目录树侧栏,端到端验证通过"
```

---

## Self-Review 结论

- **Spec 覆盖**：自动发现+配置分层（Task1）→ spec 数据层；tree/dashboard API（Task2）→ 后端；目录树/看板页/入口（Task4/5/6）→ 前端三块全覆盖。
- **占位符**：无 TBD。Task 6 Step 1 的"移入这个 div"是对现有代码的重排指令（保留原有内容不动），非占位。
- **类型一致**：PlantNode/PlantTree/PlantDashboard 类型（Task 3 定义）与后端返回结构（Task 2）、store（Task 3）、视图消费（Task 5）字段一致；discover_plants 返回的 plant_id/status/data_types/latest_time/point_count 贯穿前后端。
