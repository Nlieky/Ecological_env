# 事件中心真实化（子项目 2/4）设计文档

- 日期：2026-09-09
- 状态：待用户审阅
- 上位规划：知识图谱体系 4 子项目之 2（依赖：无；为子项目 4 根因分析供料）

## 背景与目标

事件中心（/events）与告警中心（/alerts）当前读 `backend/api/routes/events.py` 里的 3 条内存 mock（重启即失、plantId 全是假的 plant_a）。处置子智能体每轮研判真实产出 `sessions/<id>/disposition_result.json`（嫌疑等级/违规类型/证据点/工单），但只沉在会话目录里无人消费。

本子项目打通：**处置结果 → events 表 → /api/events 真数据 → 前端事件中心/告警中心**。完成后的直接收益：修好一个 mock 页面；为子项目 4（根因分析）提供真实事件数据源。

## 已确认的设计决策

| 决策点 | 结论 |
|---|---|
| 采集时机 | backend 落库 conversations 的同一位置顺扫 session 目录（B 方案）——与 record_exchange 持久化模式一致，agent 服务零改动 |
| 入事件门槛 | 非 none 全入（high/medium/low）；none（无违规，占多数）只留审计链路 |
| 证据结构 | evidence 列存处置输出 evidence_points 原文（JSON），前端详情抽屉改造渲染真结构 |
| 存量数据 | 不回灌历史（sessions/ 唯一一份历史 disposition_result 为 none 级，无回灌价值） |
| 顺手修复 | /export 路由顺序 404、stores/events.ts 参数 snake_case、run_disposition 打印 KeyError 三 bug |
| 明确不做 | ActionExecutor 工单归档接线（工单内容已在事件 evidence 可见；飞书/监管平台推送留配置化后续） |

## 数据模型

新表 `alert_events`（现有 SQLite ecological_logs.db，init_db.py 导入模型后 create_all 即建）。SQLAlchemy 模型放 `backend/models/alert_event.py`，遵循 conversation.py 惯例（Base 继承、字符串主键应用侧生成、枚举 SQLEnum、JSON 列）：

```
id               String(50) PK     "evt_<uuid12>"
timestamp        TIMESTAMP         研判完成时刻（disposition metadata.timestamp）
session_id       String(64) UNIQUE 来源会话（防重复采集；溯源 sessions/ 目录）
conversation_id  String(50) NULL   关联对话（可空，非流式路径可能无对话）
plant_id         String(100)       厂（真实 plant_id 全称，如"当阳市金桥污水处理厂一期"）
violation_types  JSON              ["插瓶干扰", ...]（中文类型名）
severity         SQLEnum           high|medium|low（= suspicion_level 一比一，对齐前端枚举）
action           String(100)       立即调查取证|现场核查|持续监控
confidence       Float             研判置信度
evidence         JSON              evidence_points 原文（指标异常点 + 专家模式命中）
work_order       JSON NULL         工单原文（none 不会有；low 以上通常有）
status           SQLEnum           pending|processing|resolved|ignored，默认 pending
created_at       TIMESTAMP default now
updated_at       TIMESTAMP onupdate now
```

**severity 映射**：suspicion_level 与前端 severity 枚举一比一（high/medium/low），无转换层。type 字段（mock 的 cod_high 等）废弃——违规类型信息由 violation_types JSON 承载，前端 type 列改渲染 violation_types 中文串。

**plant_id 提取**：从 session 目录的 task.json（task 文本含厂全称）+ plant_aliases 解析；解析不出时记 "unknown"（事件不丢）。

## 采集器

`backend/services/event_service.py`（类模式，仿 conversation_service：短会话、try/finally close、返回 dict）：

```python
class EventService:
    def collect_from_session(self, session_id, conversation_id=None) -> dict | None:
        """读 sessions/<session_id>/disposition_result.json；
        status=completed 且 suspicion_level != none 时入库。
        session_id 唯一索引兜底幂等（重复调用不重复入库）。
        文件不存在/损坏/none → 静默返回 None（打印 debug 日志）。
        plant_id 从同目录 task.json 解析（正则匹配层级 yaml 的厂全称 + 别名表）。"""
```

**接入点**：`backend/api/routes/query.py` 落库 conversations 的位置（流式透传解析 done 后、非流式 record_exchange 附近）调用 `collect_from_session(session_id, conversation_id)`。失败不阻断对话主链路（try/except 包裹，仅记 SystemErrorLog）。

## API 改造（路由签名不变，前端列表零感知）

`backend/api/routes/events.py` 重写数据源（mock 删除）：

- `GET /api/events`：SQLite 分页 + 全筛选（start_time/end_time **真正实现**（mock 声明未用）、type→violation_types LIKE、plantId、severity、status）；空表返回 `{data: [], total: 0}`（前端显示空态）
- `GET /api/events/export`：**挪到 /{event_id} 路由之前**（修 404 根因），json 全量导出真数据
- `GET /api/events/{event_id}`：详情含完整 evidence/work_order；404 语义保留
- `PUT /api/events/{event_id}/status`：**加状态机校验**——合法流转：任意状态→自身（幂等重放）、pending→processing、pending→resolved、pending→ignored、processing→resolved、processing→ignored；其余（如 resolved→pending 回退、目标值不在四枚举内）400 带原因文案（mock 是任意值直写）
- Pydantic 模型 `backend/models/event.py` 同步改：EventEvidence 换成真结构（indicators: List[IndicatorAnomaly] + patterns: List[PatternHit]），alert 字段对齐表列

## 前端改造（两处）

**EventCenterView.vue**：
- type 列改渲染 violation_types（中文串，逗号分隔）
- 详情抽屉 evidence 区重写：「指标异常点」表（指标/时间/实测值/期望区间/得分）+「专家模式命中」列表（模式/匹配分/置信度/等级）+ 研判行动 + 工单摘要（id/时间/建议行动数）
- 其余（筛选/状态流转/列表）不动

**AlertCenterView.vue**：零改动（消费的 timestamp/severity/status/plantId 字段全部保留）。

**stores/events.ts**：默认参数 `page_size`→`pageSize`（bug 修复；视图虽未用它，修掉防将来踩坑）。

## 顺手修的三 bug

1. `/events/export` 路由顺序（上面 API 改造内完成）
2. `run_disposition.py` 末尾打印引用不存在的 `output["result"]["alert"]` 键——成功路径存盘后 KeyError；改为打印实际存在的 result 字段
3. `stores/events.ts` snake_case 参数

## 测试

pytest `tests/events/`：
- 采集器单测：临时目录伪造 session（含 high/medium/low/none 四份 disposition_result + 空/损坏文件）→ 断言入库 3 条、none 不入、幂等（二次采集 0 新增）、plant_id 解析正确
- 路由测试（TestClient + 临时库）：list 分页筛选、详情、状态机合法流转/非法 400、export 在 /{event_id} 前可访问、空表空态
- run_disposition 修复：直接跑真实 session 复制件不抛 KeyError

前端 Vitest：evidence 真结构 → 渲染数据的转换函数（指标异常点/模式命中分组）。

## 明确出界（本期不做）

工单归档 ActionExecutor 接线与飞书/监管平台推送配置化、事件写回知识图谱（子项目 3 案例沉淀）、根因分析（子项目 4）、历史会话回灌。
