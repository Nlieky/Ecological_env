# 知识图谱核心（子项目 1/4）设计文档

- 日期：2026-09-07
- 状态：待用户审阅
- 上位规划：知识图谱体系共 4 个子项目，本文档只覆盖子项目 1「图谱核心」。完整规划见「项目拆解」一节。

## 背景与动机

用户提出在 `/agents/knowledge` 增设"知识图谱"功能。经澄清，单纯的静态展示没有存在价值（同样的信息配置中心/日志页都有）；知识图谱必须作为**机器可查询的结构化知识层**参与系统推理才有意义。最终确定三个价值方向：

1. **推理底座**：子智能体从 grep markdown 改为图查询，拿到精确关联（模式→算子→法规→案例）
2. **沉淀闭环**：每轮研判结论写回图谱，知识资产滚雪球（子项目 3 实现）
3. **根因分析**：故障影响面遍历与数据血缘（子项目 4 实现，依赖子项目 2 事件中心真实化）

## 已确认的需求决策

| 决策点 | 结论 |
|---|---|
| 受众 | 运维排障 + 领域知识 双视角 |
| 实时性 | 活图（节点带实时状态；完整健康轮询在子项目 4） |
| 价值定位 | 推理底座 + 沉淀闭环 + 根因分析（全选） |
| 范围 | 连事件中心接真数据一起做（子项目 2） |
| 存储 | SQLite 节点表+边表，自写遍历（递归 CTE + BFS） |
| 页面形态 | Tab 切换（领域知识 / 服务拓扑 两个子图） |
| 架构 | 方案 A：shared/ 独立图谱库（第四库），backend 只读路由 + 前端一页 |

## 项目拆解（4 个子项目，按序实施）

1. **图谱核心（本文档）**：SQLite 图谱库 + 种子导入 + 查询服务 + `/agents/knowledge` 页面
2. **事件中心真实化**：处置子智能体 disposition_result（工单/预警）→ events 表 → `/api/events` 换真数据源。独立有价值（修好 mock 页），同时为 3、4 供料
3. **智能体集成**：规则推理子智能体改图查询；研判结论写回图谱。依赖 1
4. **根因分析与活图**：影响面遍历、服务健康接入、审计血缘图。依赖 1+2

## 图谱模型

### 节点类型（8 类）

| 类型 | ID 前缀 | 实例来源 | 关键属性 |
|---|---|---|---|
| `plant` 厂区 | `plant:` | plant-hierarchy.yaml（现 2 厂） | display_name、type、数据新鲜度 |
| `indicator` 指标 | `indicator:` | 动态发现（pH/COD/TN/AN/TP/flow/SS） | 单位、进出水角色 |
| `violation_pattern` 违规模式 | `pattern:` | violation_patterns.md（6 种，含暗管偷排/虚假停产） | 特征描述、实现状态（4 主类已实现/恶意逃避 TODO/人工拟合降级） |
| `operator` 算子 | `operator:` | operator_config.json（17+） | 类别（统计/ML/DL/专用）、公式摘要 |
| `regulation` 法规 | `regulation:` | regulations/（水污染防治法等） | 条款号、要点 |
| `case` 案例 | `case:` | historical_cases.json 种子 + 研判沉淀追加 | 时间、结论、置信度 |
| `agent` 智能体 | `agent:` | 主 + 4 子智能体 | 角色、技能数 |
| `service` 服务 | `service:` | 前端/Backend/Agent/InfluxDB/SQLite/LLM | 端口、健康状态 |

节点 ID 用英文 slug（如 `pattern:bottle_interference`、`plant:jinqiao_phase1`），中文进 label。

### 边类型（10 种）

| 边 | 方向 | 含义 | 示例 |
|---|---|---|---|
| `monitors` | 厂→指标 | 该厂监测此指标 | 金桥一期 → COD |
| `detects` | 算子→模式 | 该算子检测此违规 | constant_detector → 插瓶干扰 |
| `indicates` | 模式→法规 | 此违规违反此条款 | 稀释排放 → 水污染防治法§83 |
| `cites` | 案例→模式/法规 | 案例引用判定依据 | 金桥0221案 → 插瓶干扰 |
| `employs` | 智能体→算子 | 该智能体使用此算子 | ②异常检测 → 孤立森林 |
| `calls` | 智能体→服务 | 调用此服务 | 主智能体 → LLM |
| `orchestrates` | 主→子 | 编排关系 | 主智能体 → ①感知 |
| `reads` | 智能体→服务 | 读取存储 | ③规则推理 → 知识库 |
| `writes` | 智能体→服务 | 写入存储 | ①感知 → InfluxDB |
| `involves` | 案例→厂/指标 | 案例涉及对象 | 案例 → 金桥一期、氨氮 |

**边渲染规则**：一条边仅当其两端节点类型都在当前显示集合（tab 预设或图例过滤）内时才渲染。算子（operator）同时属于两个 tab 的预设——领域知识 tab 里它是"检测器"，服务拓扑 tab 里它是 shared 算子库成员（使 employs 边可见）。

案例节点是生长点：种子导历史案例，子项目 3 写研判结论继续追加 case 节点与 involves/detects 边。

种子规模估算：约 140 节点 / 260 边。

## 存储结构

库文件：`shared/data/knowledge_graph.db`（独立于 ecological_logs.db）。

```sql
nodes(id TEXT PRIMARY KEY,      -- "type:slug"
      type TEXT NOT NULL,
      label TEXT NOT NULL,
      props_json TEXT)

edges(id INTEGER PRIMARY KEY AUTOINCREMENT,
      src TEXT NOT NULL, dst TEXT NOT NULL,
      type TEXT NOT NULL,
      props_json TEXT,
      UNIQUE(src, dst, type))

meta(key TEXT PRIMARY KEY, value TEXT)   -- schema_version / last_seeded_at
```

src/dst/type 建索引。库开 WAL 模式。

## 查询 API（graph_store.py，7 个方法）

| 方法 | 用途 | 主要消费者 |
|---|---|---|
| `upsert_node` / `upsert_edge` | 幂等写入 | 种子导入、子项目 3 研判写回 |
| `get_node(id)` | 单点详情 | 前端详情侧栏 |
| `neighbors(id, edge_types, direction, depth)` | 递归 CTE 多跳邻居 | 子智能体推理（子项目 3） |
| `subgraph(node_types, edge_types)` | 按类型取子图 | 前端整图渲染 |
| `shortest_path(a, b)` | BFS 两点寻路 | 根因分析（子项目 4） |
| `impact(id)` | 故障影响面辐射遍历 | 子项目 4 |
| `stats()` | 类型计数 | 前端概览 |

原则：多跳邻居用递归 CTE（推理场景），寻路用 Python BFS（带终止条件），各用所长。depth 硬上限 4 跳。

## 种子导入

`seed_importer.py`，数据源全部来自项目已有真实文件：

| 导入源 | 产出 |
|---|---|
| plant-hierarchy.yaml | 2 厂节点 + 层级属性（市/厂区） |
| InfluxDB 字段发现（`shared/data/influxdb_query.py` 或 operator 侧字段契约；InfluxDB 不可达时回退固定 7 指标清单：pH/COD/TN/AN/TP/flow/SS） | 指标节点 + monitors 边 |
| violation_patterns.md/.py | 6 模式节点（含实现状态标注） |
| operator_config.json | 算子节点 |
| 硬编码映射表（~40 行，seed_importer.py 内） | detects / indicates / employs / orchestrates / reads / writes / calls 边 |
| historical_cases.json | 案例节点 + cites / involves 边 |
| 智能体与服务目录 | 5 智能体 + 6 服务节点 |

设计决策：

1. **关系映射用硬编码表而非解析散文**：md 文档给人看，代码抓关系脆弱不可靠；显式表可查可改，将来可升级为配置中心管理的 yaml。
2. **种子幂等可重跑**：节点 upsert、边 UNIQUE 去重；研判沉淀的 case 不在种子里不受影响。新厂接入/算子新增后重跑即进图。

运行方式：`ecological_env\Scripts\python.exe shared\knowledge_graph\seed_importer.py`。

## 后端 API

`backend/api/v1/knowledge/routes.py`，挂 `/api/v1/knowledge`，3 个只读端点：

| 端点 | 返回 | 说明 |
|---|---|---|
| `GET /graph?node_types=&edge_types=` | `{nodes, edges, stats, seeded}` | 整图/按类型过滤；类型计数 |
| `GET /node/{id}` | `{node, neighbors}` | 节点详情 + 一跳邻居分组 |
| `GET /stats` | 类型计数 + 最近写入 case | 概览徽标 |

活图（子项目 1 范围内）：`/graph` 返回时由 backend 现查 `/v1/system/status`，把各厂数据新鲜度与服务健康**叠加**到对应节点属性上（查时合并，不落库）。完整实时轮询在子项目 4。

## 前端页面

路由 `/agents/knowledge`，侧栏归"智能助手"组，名称"知识图谱"。

- 顶部 Tab 切换：**领域知识**（plant/indicator/pattern/operator/regulation/case）与**服务拓扑**（agent/service + orchestrates/calls/reads 边），复用大屏 tab 交互习惯
- 左侧图例复选框过滤节点类型；主区 ECharts graph series 力导向布局，categories 按 8 类着色
- 底部/侧边详情栏：点节点展示属性表 + 一跳邻居列表（可点击跳转）
- 顶部统计徽标：节点数/边数/案例数
- 渲染失败兜底：try/catch 包 setOption，降级为节点列表表格（吸取 ECharts 树摇静默失败的教训）

技术：ECharts Graph 组件已在 `src/lib/echarts.ts` 注册，零构建改动；新视图 + 可选 store，不引新依赖。

## 错误处理

| 场景 | 处理 |
|---|---|
| knowledge_graph.db 不存在 | 路由返回空图 + `seeded:false`，前端显示引导卡片（运行 seed_importer.py 初始化）；不自动建库 |
| 种子源文件缺失 | seed_importer 单源失败跳过并警告，其余继续；退出码 0，打印各源统计 |
| 邻居查询深度失控 | depth 硬上限 4，超限拒绝 |
| SQLite 并发写 | WAL + 短事务 |
| 前端渲染失败 | 降级节点列表表格 |

## 测试

pytest，`tests/knowledge_graph/`：

1. 存储层单测：upsert 幂等、neighbors 多跳、subgraph 过滤、shortest_path
2. 种子导入集成测：临时目录跑种子 → 断言节点数 >120、10 种边齐全、`pattern:bottle_interference` 有 detects 入边、重跑第二遍边数不变
3. API 路由测：TestClient 三端点——空库、种子后、类型过滤三场景
4. 前端：Vitest 测 store 数据转换（nodes/edges → ECharts series）；页面人工验收

## 明确出界（本期不做）

图算法库（networkx）、Neo4j、实时健康轮询（子项目 4）、研判写回（子项目 3）、事件中心真实化（子项目 2）。
