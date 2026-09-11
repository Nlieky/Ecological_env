# 根因分析（子项目 4/4）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 图谱变故障推演工具——impact() 双向影响推演 + 六服务健康探测（图谱自动红）+ 事件关联链路双入口。

**Architecture:** 后端三件（GraphStore.impact 按边类型分方向遍历 / get_system_status 六探测+10s 缓存 / knowledge 路由 impact 端点+service 健康叠加）；前端两件（图谱页推演模式重渲染着色 / 事件中心关联链路+图谱页 focus query）。重渲染着色方案（不用 dispatchAction）。

**Tech Stack:** SQLite 递归 CTE（复用）/ httpx 探测 / Vue3+ECharts / pytest+Vitest

**Spec:** `docs/superpowers/specs/2026-09-11-root-cause-analysis-design.md`

---

## 工程约定（执行前必读）

- Python：`/e/project/Ecological_env/ecological_env/Scripts/python.exe`（$PY）。pytest 项目根跑。
- 前端：`cd frontend && npm test`；type-check `npx vue-tsc --noEmit`（存量 3 错别碰）。
- 服务：backend :8000 / agent :8642 / Vite :5173 运行中。改动需重启对应服务验证。
- 提交中文 + 前缀 + 结尾 `Co-Authored-By: Claude <noreply@anthropic.com>`。

## 关键背景事实（探索报告核实）

1. **GraphStore**（shared/knowledge_graph/graph_store.py）：无 impact()；neighbors(node_id, edge_types, direction=out|in|both, depth≤4) 递归 CTE 已具备方向化能力；MAX_DEPTH=4。**impact 分两批调 neighbors**（顺边集 out / 逆边集 in）合并即可，不用写新 CTE。
2. **边语义**（故障传播 7 种）：顺边=[hosts]（承载者挂→被承载者挂）；逆边=[calls, reads, orchestrates, uses, invokes, mounts]（被依赖方挂→依赖方受影响）；employs 弱依赖与 9 种领域边不参与。
3. **get_system_status**（backend/api/v1/system/routes.py:16-74）：现探 3 项每请求实时跑（agent httpx /health 3s、influxdb 试连）；backend 硬编码 up。加 3 项后必须 10s 缓存。
4. **_overlay_live_status**（backend/api/v1/knowledge/routes.py:33-55）：只叠 plant 的 last_data_ts/live_status；service 无叠加——本期补 `props.health` + `health_checked_at`。
5. **前端**：KnowledgeGraphView onNodeClick→openNode 详情侧栏（L259-261）；渲染走 toEChartsSeries→setOption(notMerge)（L238）——重渲染着色天然兼容；store（stores/knowledge.ts）无高亮态，需加 impactMode/impactResult/runImpact/clearImpact。dispatchAction 可用但选重渲染方案（与 emphasis.focus='adjacency' 冲突）。
6. **事件桥**：研判写回的 case 节点 id = `case:{event_id}`（event_service.py:112），props.source_event=event_id；查 `/api/v1/knowledge/node/case:{event_id}` 得 involves/cites 邻居。事件中心页未加载图数据——用 API 查而非前端过滤。
7. **图谱页路由**：`/agents/knowledge` 无 query 解析——加 `?focus=<node_id>` 支持（mounted 时 openNode）。
8. **llm 探测**：`GET {LLM_BASE_URL}/models` 轻请求（OpenAI 兼容，不耗 token）；LLM_BASE_URL 从 .env / get_param 已有链路。frontend 探测 URL 可配（settings 加 FRONTEND_URL，默认 http://localhost:5173）。

---

### Task 1（后端）：impact() + 六探测 + API 端点

**Files:**
- Modify: `shared/knowledge_graph/graph_store.py`（加 impact）
- Modify: `backend/api/v1/system/routes.py`（六探测+缓存）
- Modify: `backend/core/config.py`（FRONTEND_URL 设置）
- Modify: `backend/api/v1/knowledge/routes.py`（/impact 端点 + service 健康叠加）
- Test: `tests/knowledge_graph/test_impact.py`、`tests/system/test_health_probe.py`

- [ ] **Step 1: 写失败的 impact 测试**

```python
# tests/knowledge_graph/test_impact.py
"""impact() 双向影响推演：按边类型分方向、排除领域边、depth 截断。"""
from pathlib import Path
import pytest
from shared.knowledge_graph.graph_store import GraphStore


def make_store(tmp_path: Path) -> GraphStore:
    return GraphStore(tmp_path / "kg.db")


@pytest.fixture
def topo(tmp_path):
    """混合边拓扑:
    agent_service --hosts--> master --orchestrates--> perception --reads--> influxdb
    backend --calls--> agent_service ; frontend --calls--> backend
    master --invokes--> call_subagent(工具)
    领域边: plant --monitors--> COD（不应进推演）
    """
    g = make_store(tmp_path)
    N = [
        ("service:frontend", "service"), ("service:backend", "service"),
        ("service:agent_service", "service"), ("service:influxdb", "service"),
        ("agent:master", "agent"),
        ("agent:multi-dimensional-data-perception", "agent"),
        ("tool:call_subagent", "tool"),
        ("plant:jinqiao", "plant"), ("indicator:COD", "indicator"),
    ]
    for nid, ntype in N:
        g.upsert_node(nid, ntype, nid.split(":")[1], {})
    E = [
        ("service:agent_service", "agent:master", "hosts"),
        ("agent:master", "agent:multi-dimensional-data-perception", "orchestrates"),
        ("agent:multi-dimensional-data-perception", "service:influxdb", "reads"),
        ("service:backend", "service:agent_service", "calls"),
        ("service:frontend", "service:backend", "calls"),
        ("agent:master", "tool:call_subagent", "invokes"),
        ("plant:jinqiao", "indicator:COD", "monitors"),  # 领域边
    ]
    for s, d, t in E:
        g.upsert_edge(s, d, t)
    return g


def test_impact_influxdb_downstream(topo):
    """InfluxDB 挂 → 逆边波及: perception(直接) → master → agent_service → backend → frontend"""
    r = topo.impact("service:influxdb", direction="downstream")
    ids = {n["id"] for n in r["downstream"]}
    assert "agent:multi-dimensional-data-perception" in ids
    assert "agent:master" in ids          # 经 orchestrates 逆边
    assert "service:backend" in ids        # 经 calls 逆边
    assert "service:frontend" in ids
    assert r["upstream"] == []


def test_impact_influxdb_upstream(topo):
    """InfluxDB 的根因候选 = 无（没人承载它——它是叶）"""
    r = topo.impact("service:influxdb", direction="upstream")
    assert r["upstream"] == []
    assert r["downstream"] == []


def test_impact_frontend_downstream(topo):
    """frontend 挂 → 波及空（没人依赖它——calls 是它调别人）"""
    r = topo.impact("service:frontend", direction="downstream")
    assert r["downstream"] == []
    # 但根因候选视角：frontend 异常可能是 backend/agent 引起
    r2 = topo.impact("service:frontend", direction="upstream")
    up_ids = {n["id"] for n in r2["upstream"]}
    assert "service:backend" in up_ids and "service:agent_service" in up_ids


def test_impact_agent_service_hosts_direction(topo):
    """agent_service 挂 → hosts 顺边: master 被承载也挂（downstream 含 master）"""
    r = topo.impact("service:agent_service", direction="downstream")
    ids = {n["id"] for n in r["downstream"]}
    assert "agent:master" in ids          # hosts 顺边
    assert "service:frontend" in ids      # calls 逆边


def test_impact_excludes_domain_edges(topo):
    """plant 挂不推 COD（monitors 领域边不参与）"""
    r = topo.impact("plant:jinqiao")
    assert r["downstream"] == [] and r["upstream"] == []


def test_impact_404_node(topo):
    with pytest.raises(KeyError):
        topo.impact("nope:xxx")


def test_impact_carries_edge_type(topo):
    """波及节点带 via 字段说明经什么关系受影响"""
    r = topo.impact("service:influxdb")
    perc = next(n for n in r["downstream"] if n["id"].startswith("agent:multi"))
    assert perc.get("via") == "reads"
```

- [ ] **Step 2: 跑测试确认失败**（AttributeError: no impact）

- [ ] **Step 3: 实现 impact()**（graph_store.py，neighbors 后追加）

```python
    # ── 影响面推演（子项目4）────────────────────────────────────────
    # 故障传播 7 边按方向分两批：hosts 顺边（承载者挂→被承载者挂）；
    # 其余 6 种逆边（被依赖方挂→依赖方受影响）。领域边/employs 不参与。
    _IMPACT_FORWARD = ["hosts"]  # 顺边传播
    _IMPACT_REVERSE = ["calls", "reads", "orchestrates", "uses", "invokes", "mounts"]

    def impact(self, node_id: str, direction: str = "both") -> Dict:
        """故障影响面双向推演。

        downstream=该点挂了谁受影响（顺边沿 out + 逆边沿 in 各推 ≤3 跳）
        upstream=该点异常可能是谁引起的（两个方向都反过来）
        返回 {node, downstream:[{id,type,label,depth,via}], upstream:[...]}
        节点不存在 raise KeyError。via=首跳边类型（"经什么关系"）。
        """
        if self.get_node(node_id) is None:
            raise KeyError(f"节点不存在: {node_id}")
        if direction not in ("both", "downstream", "upstream"):
            raise ValueError("direction 必须是 both/downstream/upstream")

        def _spread(seed: str, edge_types: List[str], dirn: str) -> Dict:
            return self.neighbors(seed, edge_types=edge_types,
                                  direction=dirn, depth=3)

        def _merge(a: Dict, b: Dict) -> List[Dict]:
            best: Dict[str, Dict] = {}
            for n in (a.get("nodes", []) + b.get("nodes", [])):
                if n["id"] not in best or n["depth"] < best[n["id"]]["depth"]:
                    best[n["id"]] = dict(n)
            return sorted(best.values(), key=lambda x: x["depth"])

        downstream: List[Dict] = []
        upstream: List[Dict] = []
        if direction in ("both", "downstream"):
            # 顺边类型沿 out 方向 + 逆边类型沿 in 方向 = 故障向外辐射
            f = _spread(node_id, self._IMPACT_FORWARD, "out")
            r = _spread(node_id, self._IMPACT_REVERSE, "in")
            downstream = _merge(f, r)
        if direction in ("both", "upstream"):
            # 反推：顺边类型沿 in（谁承载着它）+ 逆边类型沿 out（它在依赖谁）
            f2 = _spread(node_id, self._IMPACT_FORWARD, "in")
            r2 = _spread(node_id, self._IMPACT_REVERSE, "out")
            upstream = _merge(f2, r2)
        # via=首跳边类型：从 edges 里找故障点与该节点(或其首跳前驱)的关系
        edge_type_by_node = self._impact_via(node_id, downstream + upstream)
        for n in downstream + upstream:
            n["via"] = edge_type_by_node.get(n["id"], "")
        node = self.get_node(node_id) or {}
        return {"node": node, "downstream": downstream, "upstream": upstream}

    def _impact_via(self, seed: str, reached: List[Dict]) -> Dict[str, str]:
        """为推演到的节点标注首跳边类型（故障点直接邻居看得到；多跳的标首跳类型）。"""
        out: Dict[str, str] = {}
        for e in self._conn.execute(
                "SELECT src, dst, type FROM edges WHERE src=? OR dst=?",
                (seed, seed)).fetchall():
            other = e["dst"] if e["src"] == seed else e["src"]
            if other not in out:
                out[other] = e["type"]
        # 多跳节点：沿 depth=1 的邻居再查一跳（近似——足够展示"经什么关系"）
        return out
```

注意：via 只标直接邻居（一跳）——多跳节点 via 留空可接受（摘要条只列直接关系），测试 `test_impact_carries_edge_type` 断言的就是一跳。**实现时先跑测试再调整**——如果 _merge 后 depth 语义与 neighbors 返回一致（含起点排除），测试应该绿。

- [ ] **Step 4: 六探测 + 缓存（system/routes.py）**

```python
# 模块级缓存（10s）：六探测含 3 个真网络探（agent 3s/influxdb/llm 3s），
# 每请求实时跑最坏 1s+；SystemStatusView 15s 轮询 + KG 页叠加都会打这里。
_STATUS_CACHE: dict = {"ts": 0.0, "data": None}
_STATUS_TTL = 10.0
```

- get_system_status 开头：缓存新鲜直接返回缓存 data（.deepcopy 防外改）
- 追加三探测（各自 try/except 不互相拖垮，单探失败该服务 down 不影响其他）：
  - frontend：`httpx.head(settings.FRONTEND_URL, timeout=2)`（settings 加 `FRONTEND_URL: str = "http://localhost:5173"`；.env 可覆盖）
  - llm：`httpx.get(f"{llm_base}/models", timeout=3)`——llm_base 从 `agent_params.get_param("llm_base_url")` 或 settings.LLM_BASE_URL（读现有链路）
  - sqlite_logs：Path 存在 + `sqlite3.connect(...).execute("PRAGMA quick_check")` 试触
- services 数组保持现形状 `{name, title, status}`（SystemStatusView 兼容）

- [ ] **Step 5: knowledge 路由加 /impact 端点 + service 健康叠加**

```python
@router.get("/knowledge/impact/{node_id}")
async def get_impact(node_id: str, direction: str = "both"):
    store = _get_store()
    if store is None:
        raise HTTPException(404, "知识图谱未初始化")
    try:
        r = store.impact(node_id, direction=direction)
    except KeyError:
        raise HTTPException(404, f"节点不存在: {node_id}")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"success": True, **r}
```

_overlay_live_status 补 service 分支：调 get_system_status（有缓存不打爆），service 节点按 name 匹配（node id `service:agent_service` ↔ status 数组 name `agent`——**写显式映射表** `{"agent_service": "agent", "backend": "backend", "influxdb": "influxdb", "frontend": "frontend", "llm": "llm", "sqlite_logs": "sqlite_logs"}`），叠加 `props.health` + `props.health_checked_at`。

- [ ] **Step 6: 测试 + 提交**

`tests/system/test_health_probe.py`：mock httpx 六服务 up/down 阵列断言（fixture 清缓存）；10s 缓存命中（两次调用探测函数只跑一次——计数 mock）。

```bash
$PY -m pytest tests/knowledge_graph/test_impact.py tests/system/ -v
$PY -m pytest tests/ -q   # 全套
git add shared/knowledge_graph/graph_store.py backend/api/v1/system/routes.py backend/core/config.py backend/api/v1/knowledge/routes.py tests/
git commit -m "feat(impact): 影响面双向推演+六服务探测+图谱健康叠加——按边类型分方向(hosts顺/calls等逆),10s探测缓存"
```

---

### Task 2（前端）：图谱页推演模式 + 健康红点

**Files:**
- Modify: `frontend/src/stores/knowledge.ts`（impactMode/impactResult/runImpact/clearImpact + 着色纯函数）
- Modify: `frontend/src/views/KnowledgeGraphView.vue`（推演开关/点击分流/着色渲染/摘要条/健康红/60s 慢轮询/focus query）
- Test: `frontend/src/stores/__tests__/knowledge.impact.spec.ts`

- [ ] **Step 1: 写失败的 store 测试**

```typescript
// frontend/src/stores/__tests__/knowledge.impact.spec.ts
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useKnowledgeStore, impactNodeStyle } from '@/stores/knowledge'

describe('impact store 状态机', () => {
  beforeEach(() => { setActivePinia(createPinia()) })

  it('runImpact 存结果并标记模式', async () => {
    const store = useKnowledgeStore()
    const mock = vi.fn().mockResolvedValue({
      node: { id: 'service:influxdb' },
      downstream: [{ id: 'agent:perception', type: 'agent', label: '感知', depth: 1, via: 'reads' }],
      upstream: [],
    })
    store._impactApi = mock
    await store.runImpact('service:influxdb')
    expect(store.impactMode).toBe(true)
    expect(store.impactResult?.nodeId).toBe('service:influxdb')
    expect(store.impactResult?.downstream).toHaveLength(1)
  })

  it('clearImpact 重置', async () => {
    const store = useKnowledgeStore()
    store.impactResult = { nodeId: 'x', downstream: [], upstream: [], node: null as any }
    store.impactMode = true
    store.clearImpact()
    expect(store.impactMode).toBe(false)
    expect(store.impactResult).toBeNull()
  })

  it('切 tab 清推演', async () => {
    const store = useKnowledgeStore()
    store.impactMode = true
    store.setTab('domain')
    expect(store.impactMode).toBe(false)  // 领域 tab 无推演
  })
})

describe('impactNodeStyle 着色纯函数', () => {
  const result = {
    nodeId: 'svc:a',
    downstream: [{ id: 'n:down' }, { id: 'n:down2' }],
    upstream: [{ id: 'n:up' }],
  } as any

  it('故障点/波及/根因/无关四种状态', () => {
    expect(impactNodeStyle('svc:a', result).state).toBe('fault')
    expect(impactNodeStyle('n:down', result).state).toBe('affected')
    expect(impactNodeStyle('n:up', result).state).toBe('candidate')
    expect(impactNodeStyle('n:other', result).state).toBe('unrelated')
    expect(impactNodeStyle('n:other', null).state).toBe('normal')  // 无推演=正常态
  })
})
```

（store 里 `_impactApi` 可注入（默认用 knowledgeService.impact）——测试不打真网络。`impactNodeStyle(nodeId, result)` 返回 `{state, color?}` 纯函数：fault=#ef4444 描边、affected=#f97316、candidate=#8b5cf6、unrelated 降透明、normal 原色。）

- [ ] **Step 2: api module 补 impact**（frontend/src/api/modules/knowledge.ts）

```typescript
  impact: (id: string, direction = 'both') =>
    api.get<unknown, { success: boolean; node: KGNode; downstream: any[]; upstream: any[] }>(
      `/v1/knowledge/impact/${encodeURIComponent(id)}`, { params: { direction } }),
```

- [ ] **Step 3: store 实现**

- state：`impactMode` / `impactResult: {nodeId, node, downstream, upstream} | null`
- `_impactApi` 可注入（默认 knowledgeService.impact）
- `runImpact(id)`：调 API 存结果（失败 ElMessage 提示并退回 normal 点击）
- `clearImpact()`；`setTab` 里清（切 tab 重置推演）
- `toggleImpactMode()`（开→关时清结果）
- 导出 `impactNodeStyle(nodeId, result)` 纯函数
- **toEChartsSeries 增强不在此做**——着色在视图层渲染时按 impactResult 叠加（store 保持纯数据）

- [ ] **Step 4: 视图改造（KnowledgeGraphView.vue）**

1. **图例区**（topology tab 时）加开关按钮「⚡ 影响推演」（class kg-tool 复用，激活态 on）
2. **onNodeClick 分流**：impactMode 时 `store.runImpact(id)`（不开详情）；否则原 openNode
3. **renderChart 着色**：data 映射时对每个节点算 `impactNodeStyle` + service health——
   - state=fault：itemStyle 边框 #ef4444 3px + symbolSize 放大
   - affected：#f97316 / candidate：#8b5cf6（覆盖类型色）
   - unrelated：opacity 0.15
   - service 节点 props.health==='down'：红色实心 + label 红（不受推演影响，常态）
   - 相关边高亮（两端都在 impact 集内的边 width 2 橙），其余边 opacity 0.1
4. **摘要条**：impactResult 非空时图区顶部浮层（absolute）——`故障点 {label} → 波及 {N}（前几个 label…）· 根因候选 {M}` + 清除按钮
5. **60s 慢轮询 health**：impactMode 关闭时 setInterval 60s 调 `store.refreshHealth()`（新增 action：只调 knowledgeService.graph(null, true) 拿 service 节点更新 allNodes 的 health——轻量；onUnmounted 清）
6. **focus query**：onMounted 解析 `route.query.focus` → 存在则 openNode(focus)（事件中心跳转入口）

- [ ] **Step 5: 测试 + type-check + 提交**

```bash
cd frontend && npm test && npx vue-tsc --noEmit 2>&1 | grep -iE "impact|knowledge"
git add frontend/src/stores/knowledge.ts frontend/src/views/KnowledgeGraphView.vue frontend/src/api/modules/knowledge.ts frontend/src/stores/__tests__/knowledge.impact.spec.ts
git commit -m "feat(impact): 图谱页推演模式——点节点双向波及着色+摘要条+服务健康红点+60s慢轮询+focus query"
```

---

### Task 3（前端）：事件关联链路双入口

**Files:**
- Modify: `frontend/src/views/KnowledgeGraphView.vue`（case 详情"高亮链路"按钮 + 链路着色）
- Modify: `frontend/src/views/EventCenterView.vue`（详情抽屉"关联链路"区块）
- Modify: `frontend/src/stores/knowledge.ts`（caseLink 状态：`highlightCase(id)` 用 allEdges 过滤链路节点集）
- Test: `frontend/src/stores/__tests__/knowledge.impact.spec.ts` 追加 caseLink 用例

- [ ] **Step 1: store 加 caseLink**

- state：`caseLinkNodes: Set<string> | null`（链路节点集）
- `highlightCase(nodeId)`：从 allEdges 过滤——起点 case + 它的 involves/cites 一跳 + 模式节点再沿 indicates 一跳（法条）；存节点集（含 case 自身）
- `clearCaseLink()`
- 着色：renderChart 里 caseLinkNodes 非空时链路节点蓝色系高亮（#3b82f6）其余淡出——**与 impactResult 互斥**（caseLink 优先级低于 impact：impactResult 存在时忽略 caseLink；clearImpact 后恢复）

- [ ] **Step 2: 图谱页 case 详情按钮**

详情侧栏（selectedNode.type==='case' 时）头部加「🔗 高亮链路」按钮 → `store.highlightCase(selectedNode.id)`；再点清除。摘要条复用（显示`案例链路：厂→模式→法条 N 节点`）。

- [ ] **Step 3: 事件中心"关联链路"区块**

EventCenterView 详情抽屉尾部新 d-sec（v-if current.id）：
- 调 `knowledgeService.node('case:' + current.id)`（404 → 显示"该事件无图谱关联（研判沉淀缺失）"）
- 成功 → 展示链路元素列表：厂（绿点）→ 违规模式（红点）→（cites 邻居）+ 「在图谱中查看」按钮 → `router.push('/agents/knowledge?focus=case:' + current.id)`
- 加载态/异常静默（try/catch，区块失败不影响抽屉其他部分）

- [ ] **Step 4: 测试 + 提交**

```bash
npm test
git add frontend/src/views/KnowledgeGraphView.vue frontend/src/views/EventCenterView.vue frontend/src/stores/knowledge.ts
git commit -m "feat(impact): 事件关联链路双入口——图谱case高亮链路+事件中心关联区块跳图谱focus"
```

---

### Task 4：端到端验证（含故障演练）

- [ ] **Step 1: 重启服务**（agent + backend 带新代码）

- [ ] **Step 2: 推演端到端**（Playwright 或 curl）
  - `GET /api/v1/knowledge/impact/service:influxdb` → downstream 含 4 子智能体链（master 经 orchestrates 逆边）+ backend + frontend
  - 前端：开推演模式点 InfluxDB 节点 → 橙色波及面 + 紫色根因（无）+ 摘要条数字对
- [ ] **Step 3: 故障演练（核心验收）**
  - kill agent 服务（:8642）→ 60s 内 KG 页 agent_service 节点变红（health=down）→ SystemStatusView 也 down
  - 推演点 agent_service → 波及 master+4 子+backend+frontend
  - 重启 agent 服务 → 变绿
- [ ] **Step 4: 事件链路端到端**
  - 事件中心点最近事件 → 关联链路区块显示（厂→模式）→ 点"在图谱中查看" → 图谱页自动开该 case 详情 → 点"高亮链路" → 蓝色链路（厂→模式→法条）
- [ ] **Step 5: 全量回归 + 提交（如有修复）**

```bash
$PY -m pytest tests/ -q && cd frontend && npm test
```

---

### Task 5：收尾——CLAUDE.md + 记忆

- [ ] CLAUDE.md Key Files 补条目（impact/探测/推演交互/双入口）
- [ ] 提交 + 汇报（含"四子项目全部完成"总结）

---

## Self-Review 记录

- **Spec 覆盖**：impact 双向+边语义（T1）/六探测+10s缓存+service叠加（T1）/推演模式+着色+摘要+健康红+慢轮询（T2）/双入口 caseLink+focus（T3）/端到端含停服演练（T4）✓
- **占位符扫描**：无 TBD；impact 实现的 via 多跳标注明确"近似可接受"；测试代码完整
- **类型一致性**：store `_impactApi` 注入约定测试与实现一致；impactNodeStyle 返回 {state} 两处一致；case:{event_id} 桥 Task3 与后端 event_service 契约一致
- **已知决策**：着色用重渲染（探索报告证 dispatchAction 与 emphasis 冲突）；60s 慢轮询只刷 health 不整图重载；via 只标一跳（摘要条够用）
