# 根因分析（子项目 4/4）设计文档

- 日期：2026-09-11
- 状态：待用户审阅
- 前置：子项目 1（图谱核心）/ 2（事件真实化）/ 3（智能体集成）均已完成
- 依赖：图谱边语义（17 种）+ alert_events + system/status

## 目标

让图谱从"结构展示"变成"故障推演工具"（用户最初对图谱价值的质疑在此完全兑现）：

1. **影响面推演**：点任何服务/智能体节点 → 双向推演（波及面高亮 + 根因候选）
2. **服务健康活图**：六服务全探测，服务真挂图上自动红
3. **事件关联链路**：点事件/案例 → 高亮它涉及的厂→模式→法条链路（图谱页 + 事件中心双入口）

## 已确认的设计决策

| 决策点 | 结论 |
|---|---|
| 影响面方向 | **双向推演**：按边类型分方向处理（hosts 顺边=承载者挂→被承载者挂；calls/reads/orchestrates/uses/invokes 逆边=被依赖方挂→依赖方受影响）；正向答"波及谁"、反向答"根因候选是谁" |
| 健康探测 | **六服务全探**：现 3 项（backend/agent/influxdb）+ 新增 frontend（HTTP HEAD :5173）/ llm（轻量 models 列表请求）/ sqlite（本地文件存在+可写试触） |
| 事件链路入口 | **双入口**：图谱页点 case 节点高亮链路 + 事件中心详情抽屉"关联链路"区块（可跳图谱页） |

## 第 1 部分：影响面推演（后端）

### GraphStore.impact()（spec 一直承诺、本期实现）

```python
def impact(self, node_id: str, direction: str = "both") -> dict:
    """故障影响面双向推演。

    按边类型分方向的依赖语义（审计过的 17 种边中，故障传播相关的 7 种）：
      顺边（src 挂 → dst 挂）:  hosts（承载）
      逆边（dst 挂 → src 受影响）: calls / reads / orchestrates / uses / invokes / mounts
      （employs 弱依赖不入推演；领域边 monitors/detects/indicates/cites/involves/limits/belongs_to 不参与）

    direction: downstream=只推波及面 / upstream=只推根因候选 / both
    返回 {downstream: [节点...], upstream: [节点...], node: {...}}
    downstream = "这个点挂了，谁受影响"（沿上述方向从故障点向外辐射，depth≤3）
    upstream   = "这个点异常了，可能是谁引起的"（反方向收集它的依赖者）
    """
```

实现要点：
- 复用 `neighbors` 的递归 CTE，但**按边类型分别指定 direction**——分两批查询合并（顺边集合用 out、逆边集合用 in），而非 neighbors 的一次双向
- depth ≤ 3（服务拓扑直径小，4 跳会漏到领域知识区无意义）
- 返回节点带 depth 与所属边类型（前端展示"经什么关系受影响"）
- 排除领域边后，推演只在拓扑子图内流动，不会串到违规模式/法规

### API 端点

`GET /api/v1/knowledge/impact/{node_id}?direction=both` → `{success, node, downstream, upstream}`；节点不存在 404。

## 第 2 部分：六服务健康探测（后端）

### get_system_status 扩展（backend/api/v1/system/routes.py）

现有 3 项不动，追加：
- `frontend`：httpx HEAD `http://localhost:5173/`（timeout 2s；注意生产/Docker 下前端域名不同——从 settings 可配 `FRONTEND_URL` 读取，默认 localhost:5173）
- `llm`：httpx GET `{LLM_BASE_URL}/models`（timeout 3s；OpenAI 兼容端点轻请求，不耗 token）
- `sqlite_logs`：本地文件 `shared/data/ecological_logs.db` 存在 + `PRAGMA quick_check` 试触（毫秒级）

**性能**：现在每请求实时探测 3 项 ~几百 ms（agent/influxdb 是真网络探）；加 3 项后最坏 ~1s+。改为**模块级缓存 10s**（探测结果+时间戳，10s 内复用）——SystemStatusView 本来 15s 轮询，KG 页也可放心叠加。

### 图谱 live 叠加扩展（backend/api/v1/knowledge/routes.py）

`_overlay_live_status` 补 service 分支：`props.health = "up"|"down"`、`props.health_checked_at`（来自 get_system_status 缓存）。子项目 1 spec 承诺的"服务健康叠加"欠账在此还清。

## 第 3 部分：前端——图谱页推演交互

### 新增"推演模式"（服务拓扑 tab 专属）

服务拓扑 tab 的图例区新增一个开关按钮 **「⚡ 影响推演」**（领域知识 tab 不显示此按钮——领域边不参与推演）：

- **开启后点节点**：不再开详情侧栏，改为触发推演——
  - 该节点**红色描边脉冲**（ECharts emphasis 样式或 itemStyle 边框）
  - **downstream 波及面**：橙色高亮（受影响者）
  - **upstream 根因候选**：紫色高亮
  - 无关节点**灰色淡出**（blur）
  - 相关边高亮、无关节边淡出
  - 顶部浮层摘要条：`故障点 X → 波及 N 节点（②异常检测/③规则推理/...）· 根因候选 M 个`，含「清除推演」按钮
- **关闭或清除**：dispatchAction downplay + 恢复（重渲染即可，现有 notMerge 模式天然支持）
- 实现方式：**重渲染方案**（推演结果并入 toEChartsSeries 的 node itemStyle 状态字段——`state: 'fault'|'affected'|'candidate'|null` → 渲染时着色），不用 dispatchAction highlight（与 emphasis.focus='adjacency' 的交互冲突难调和，重渲染更可控且模式已有）
- store 新增：`impactMode: boolean`、`impactResult: {nodeId, downstream, upstream} | null`、`runImpact(nodeId)`（调 API）、`clearImpact()`

### 服务健康红点

- 图数据加载时 service 节点 props 已带 health（第 2 部分叠加）
- 渲染：health=down 的 service 节点**红色实心 + 标签红**（不受推演模式影响，常态显示）
- 不做自动轮询（用户点刷新/切 tab 自然重载；SystemStatusView 已有 15s 轮询页）——spec 说"完整实时轮询在子项目 4"，此处折中：**KG 页 60s 慢轮询**只刷 health（轻量：调 /stats 或 /graph?node_types=service 拿叠加），图不整体重载

## 第 4 部分：前端——事件关联链路（双入口）

### 入口 A：图谱页点 case 节点高亮链路

点 case 节点（推演模式关闭时）保持现详情侧栏行为，**详情顶部加「高亮链路」按钮**：
- 点击 → case 节点 + involves 的厂 + cites 的模式 + 模式 indicates 的法条 全链高亮（同推演的着色机制，蓝色系），其余淡出
- 一跳邻居数据已在 selectedNeighbors（现详情就有），法条二跳调 `/node/{id}` 拿或前端从 allEdges 过滤——**用 allEdges 过滤**（图数据已全量在前端，无需新请求）

### 入口 B：事件中心详情抽屉"关联链路"区块

EventCenterView 详情抽屉（现有区块尾部）新增：
- 从 `evidence` 提取关联图谱元素：expert_pattern 的 `pattern_key` → 模式节点；violation_types 中文 → 模式（label 反查，前端已拿全量图数据？**事件中心页没加载图数据**——改为调 `/api/v1/knowledge/node/{case:事件id}`：研判写回时同事件已有 case 节点，直接查它的邻居）
  - `source_event` 桥：详情抽屉已知 event_id → 查 `case:{event_id}` 节点 → 404 时（研判未写回或 none 级）显示"该事件无图谱关联（研判沉淀缺失）"
- 展示：链路元素列表（厂→模式→法条，各带类型色点）+ **「在图谱中查看」按钮** → 路由跳 `/agents/knowledge`（带 query `?focus=case:xxx`，图谱页 mounted 时解析 query 自动开该节点详情——小改动）

## 验证策略

| 层 | 手段 |
|---|---|
| 后端单测 | impact() 双向推演正确性（构造小图：hosts/calls/orchestrates 混合，断言 downstream/upstream 集合与方向）；六探测各 up/down 两态；live 叠加 service 分支 |
| API 测 | /impact/{id} 三 direction × 存在/不存在；/graph 的 service 节点含 health |
| 前端 Vitest | store 的 impact 状态机（runImpact/clearImpact/模式切换重置）；着色映射纯函数（state→itemStyle） |
| 端到端 | 停掉 agent 服务 → KG 页拓扑 tab agent 节点变红 → 开推演点它 → 波及面正确（master/4子/研判管线）→ 恢复服务变绿；事件中心点最近事件 → 关联链路显示 → 跳图谱页聚焦 |

## 明确出界（不做）

审计血缘图（llm_call_logs 时序链——spec 提过但价值密度低，单独排期）；影响面的历史事件自动关联（"此故障历史上发生过几次"——数据不足）；推演结果落库/生成事件；网络拓扑探测（只探已知 6 服务，不做端口扫描）
