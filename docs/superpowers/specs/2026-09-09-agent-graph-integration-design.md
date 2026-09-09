# 智能体集成（子项目 3/4）设计文档

- 日期：2026-09-09
- 状态：待用户审阅
- 前置：子项目 1（图谱核心，已完成并经语义审计修正——10 错边+8 夸大全整改，守卫测试锁定）；子项目 2（事件中心真实化，已完成）
- 退路：`backup/pre-subproject3` 分支 + tag `sub1-sub2-verified`（用户明确要求：子项目 3 改动现有研判链路，失败可一键回退）

## 背景与目标

图谱（119 节点/157 边）已建成且语义经过审计修正，但还没有任何智能体真正**用**它。子项目 3 让图谱参与研判双向流动：

1. **读**：规则推理子智能体的知识消费改用图查询（现状全是硬编码字典：5 专家模式+3 案例+限值/法条/工艺规则——不是 grep，探索修正了这个认知）
2. **写**：每轮研判结论写回图谱成案例节点——案例库随使用自动增长（"越用越聪明"）

用户明确的风险要求：子项目 3 是唯一改动现有研判链路的子项目，"一旦做不好效果还不如原来"。全设计围绕**可回退、可观测、灰度启用**展开。

## 已确认的设计决策

| 决策点 | 结论 |
|---|---|
| 图查询接入方式 | **双路都做**（用户选定）：脚本内替换（低风险先行）+ LLM 主动查图（高风险灰度后行） |
| 回退兜底 | 图不可用→回退硬编码字典；**做成可统计的**（记录回退次数与原因），上线观察后若几乎不触发则移除（用户指示） |
| knowledge-search | **删除**（从未生效：路径 bug 解析到不存在目录、主链路零调用；功能被 graph-query 替代） |
| graph-query 可靠性 | **重点验证项**（用户点名）：子智能体调技能历史上出过"读了 SKILL.md 不执行"，需多轮实测统计成功率，不顺利要深查原因 |
| 写回时机 | 事件采集器 collect_from_session 内同步写（复用门控/幂等/厂名解析，研判链路零改动） |
| 交付顺序 | 脚本替换先行（可独立验证）→ 写回 → LLM 查图（最后启用） |

## 第 1 部分：脚本内图查询替换

### 改造对象（run_rule_reasoning.py 的三个知识消费模块）

| 模块 | 现状（硬编码） | 改为（图查询） | 回退兜底 |
|---|---|---|---|
| `expert_reasoner._load_expert_rules` | 5 造假模式字典 | 图 `violation_pattern` 6 节点（含审计修正后的特征描述/status）+ `detects` 边关联算子 | 原字典保留为 fallback |
| `expert_reasoner._load_case_library` / `_match_cases` | 3 条硬编码案例 | 图全部 `case` 节点（种子 2 + 研判写回 N 条——**案例库自动增长的核心**） | 原列表 fallback |
| `regulation_matcher._load_regulations` | GB 限值+法条字典 | `limits` 边查指标限值；`indicates` 边查模式→§39/§83 法条（审计修正后的双锚体系） | 原字典 fallback |
| `process_validator` | 4 类工艺规则硬编码 | **不改**——工艺规则是判定逻辑本体（阈值/条件），不是"知识查找"，动了就是重写判定器（超范围） | — |

### 回退机制（可观测设计）

`shared/knowledge_graph/graph_query.py` 新建统一入口：

```python
class GraphKnowledgeSource:
    """规则推理的知识源：优先图谱，图不可用/查询异常回退调用方提供的硬编码字典。

    回退可观测：每次回退记录（时间/原因/调用方）到类属性 fallback_log，
    run_rule_reasoning 把统计写进结果 JSON 的 metadata.graph_usage 字段——
    线上可统计回退频率（用户要求：观察后若几乎不触发则移除兜底）。
    """
    def __init__(self, db_path=None): ...  # 文件不存在/损坏 → self.available=False
    def get_patterns(self) -> list[dict]        # 6 模式节点（label/desc/status）
    def get_cases(self) -> list[dict]           # 全部 case 节点（含研判沉淀）
    def get_indicator_limits(self) -> dict      # indicator→{标准, 限值}
    def get_pattern_laws(self, pattern_label) -> list  # 模式→[{条款, 定性/罚则}]
```

**回退触发条件**（全部记录）：DB 文件不存在 / 连接异常 / 查询结果为空（如图未种子）。**回退不中断研判**——结果 JSON 里 `graph_usage: {used_graph: false, reason: "db_missing"}`。

### 指标名映射

图的指标节点 id 是英文契约字段（`indicator:AN`），expert_reasoner 的特征是中文（"氨氮"）——GraphKnowledgeSource 内置中英映射（复用 run_rule_reasoning.py:176-184 的 INDICATOR_MAP 常量，不重复定义）。

### 中文违规类型 → 模式节点 id

研判输出 violation_types 是中文（"暗管偷排"），模式节点 id 是英文 slug（`pattern:secret_pipe`）。GraphKnowledgeSource 提供 `pattern_id_by_label` 查询（label 反查），供写回与匹配共用。

## 第 2 部分：研判写回图谱

### 挂载点（用户已定：事件采集器内）

`backend/services/event_service.py` 的 `collect_from_session`：事件成功入库后，同函数内同步写图谱（try/except 独立包裹——图谱写失败**只记日志，不影响事件已入库**，更不影响研判链路）：

```
case:<event_id> 节点
  props: {timestamp, plant_id, severity, violation_types(中文), confidence, action, source_event: event_id}
  involves → plant:<中文plant_id>     （厂关联——图谱设计时预留的边，首个真实消费者）
  cites    → pattern:<slug>            （中文类型经 pattern_id_by_label 反查；反查不到的类型跳过该边并记日志）
```

### 幂等与共存

- upsert_node/upsert_edge 天然幂等（同 event 重复采集不产生重复节点——且事件采集本身有 session_id 门控，双保险）
- 种子重灌清边白名单不含 cites/involves（子项目 1 已设计）——研判沉淀永不被种子冲掉
- 图谱未种子（DB 不存在）时写回静默跳过（记日志），与读侧降级对称

### 前端可见

写回的案例节点经子项目 1 的 `/agents/knowledge` 页面自动可见（领域知识 tab 的"案例"类型会随研判增长）——无需前端改动，天然的可视化验证窗口。

## 第 3 部分：LLM 主动查图（graph-query 技能）

### 技能定义

`subagents/rule-reasoning-agent/skills/graph-query/`：
- `SKILL.md`：用途一句话（查图谱拿模式/案例/法条关联）+ 用法（一条命令）+ 输出说明
- `scripts/query_graph.py`：argparse 三种查询模式（--pattern <中文名> / --cases [--plant <名>] / --law <模式名>），输出**紧凑 JSON**（单行、截断长字段）——LLM 上下文友好

### SKILL.md 接入（rule-reasoning-core 的改动）

在现有"调脚本 → 确认完成"流程**之后**加一个可选步骤：

```markdown
## 可选：查图谱补充上下文（鼓励但非必须）
脚本完成后，如果你需要回答"这个厂历史上有无类似情况""该模式关联哪些法条"，
可以运行 graph-query 技能的查询脚本（最多 1 次）。
不查不影响研判结果正确性；查了可以让结论引用真实历史案例。
```

**防瞎逛约束不变**：最多 1 次查询；禁止用 terminal 直接读 DB 文件。

### 可靠性验证（用户点名重点）

子智能体"读了 SKILL.md 不执行"是本项目已知失败模式（记忆：ctgu-vlm 非确定性，2026-07-28 加过 prompt 强化+自愈兜底）。本部分的验收标准因此加严：

1. **多轮实测**：≥10 次端到端调用（真实 LLM、真实研判链路），统计：脚本执行率（必须 100%——这是现有能力不许退化）、graph-query 调用率（LLM 是否愿意用）、查询结果被结论引用率
2. **不顺利深查**：若 graph-query 调用率低或查询失败，逐项排查：SKILL.md 措辞是否明确 / 输出 JSON 是否超长被截 / 与 skill_view 的兼容 / trace 里的实际行为
3. 不达标处置：调整 SKILL.md 措辞重测；仍不达标则该部分**不合并**（脚本替换路已独立交付价值，LLM 查图是增强不是依赖）

### 删除 knowledge-search

`subagents/rule-reasoning-agent/skills/knowledge-search/` 整目录删除（从未生效：路径 bug 解析到 `subagents\shared\knowledge` 不存在路径、返回 0 命中、主链路零调用）。同时：
- seed_importer 的 SKILLS 表如有引用同步清理
- 守卫测试 `test_master_skills_include_installed` 不受影响（那是主智能体技能）

## 验证策略（整体）

| 层 | 手段 |
|---|---|
| 单元 | GraphKnowledgeSource 单测（可用/DB缺失/空图三态、各查询返回形状、回退日志）|
| 基线对比 | 6 个真实 session 的 rule_reasoning_result.json 输入输出快照，改造前后**逐字段对比**（脚本是纯函数）——判定标准：suspicion_level/has_violation 一致率 100%（evidence 明细允许有差异，因为知识源变了这正是目的），差异需逐条人审确认是"变好"（法条引用更准/案例更全） |
| 写回 | 采集器写图谱的专项测试（案例节点/边形状、幂等、图缺失静默） |
| 端到端 | smoke_test.py 全链路 + 手工问一轮验证案例节点出现在图谱页面 |
| LLM 查图 | ≥10 轮实测统计（上文标准） |
| 回退统计 | graph_usage 字段线上可查；观察期后决定移除兜底（用户指示） |

## 分阶段交付（一个 spec、三个独立可验证的阶段）

- **阶段 A**：GraphKnowledgeSource + 三个模块图查询替换 + 回退统计 + 基线对比（不碰 LLM/写回——可独立上线回退）
- **阶段 B**：研判写回（采集器内）+ 图谱页面案例可见
- **阶段 C**：graph-query 技能 + SKILL.md 接入 + ≥10 轮可靠性实测（不达标不合并）+ 删 knowledge-search

## 明确出界（不做）

process_validator 判定逻辑重写 / 主智能体编排改动 / 知识图谱前端新功能 / 飞书推送 / 恶意逃避检测补全（TODO 依旧） / 回退兜底的移除（观察期后另行决定）
