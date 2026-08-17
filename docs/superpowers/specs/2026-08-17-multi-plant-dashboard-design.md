# 多厂区仪表盘目录系统设计

> 日期：2026-08-17
> 状态：已确认（用户批准）
> 目标：建立"市→厂区→厂"三级仪表盘目录，从 InfluxDB 自动发现厂，每厂有专属看板页

## 背景

参考项目（AIOps 平台）的"仪表盘"按目录组织多套看板，支持层级导航。本项目现有前端是平铺导航，无层级概念；数据层 InfluxDB 已天然支持多厂（每点带 plant_id tag），但后端 `/realtime/plants` 是纯 mock（16 个假厂），从未接真实数据。

## 核心决策

1. **厂列表从数据自动发现**（InfluxDB group by plant_id）——导新厂报表自动出现，零维护
2. **层级映射（市→厂区→厂）用配置文件**——业务知识手写维护，未配置的厂自动落"未分组"
3. **不动现有 MetricsView**——新页面是"单厂专注"视角，与"全市汇总"视角并存

## 一、数据层

### 1. 自动发现（新建 `shared/data/discover_plants.py`）

```python
def discover_plants() -> list[dict]:
    """InfluxDB group by plant_id，返回所有有数据的厂。
    [{plant_id, data_types: ["influent","effluent"], latest_time, point_count}]"""
```

### 2. 层级配置（新建 `shared/data/plant-hierarchy.yaml`）

```yaml
当阳市:
  城东厂区:
    - 当阳市金桥污水处理厂一期
```

### 3. 合并逻辑

- 发现 ∩ 配置 → 目录树对应节点
- 配置里有但无数据 → 显示灰色/离线（预登记）
- 有数据但未配置 → "未分组"节点

## 二、后端 API（2 个新接口）

```
GET /api/v1/plants/tree
→ {"cities":[{"name","districts":[{"name","plants":[{id,status,latest,points}]}]}],
   "ungrouped":[...]}

GET /api/v1/plants/{plant_id}/dashboard
→ 单厂数据包：当前值(进出水各指标) + 24h趋势 + 缺失点 + 超限状态
```

现有 mock `/realtime/plants` 保留兼容，新接口走真实数据。

## 三、前端

### 1. 目录树（新组件 `PlantTree.vue`）

- 左侧栏三级可折叠：市→厂区→厂
- 厂节点：状态点（绿=有数据/灰=无数据）+ 最新时间
- 点击厂 → 路由 `/plants/:plantId`

### 2. 厂看板页（新视图 `PlantDashboardView.vue`，路由 `/plants/:plantId`）

- 顶部：厂名 + 状态 + 数据时间范围
- 指标卡片区：pH/COD/TN/氨氮/TP/SS 当前值（进出水对比，超限红）
- 趋势区：ECharts 双轴趋势图（按 plant_id 过滤取数）
- 接 AI 动作指令（actionStore 指标切换/标注在本页生效）

### 3. 入口

"监测大屏"菜单默认进目录树视图。

## 四、不做（YAGNI）

- 厂的增删改管理界面（导数据即新增）
- 地图（后续可加）
- 不动 MetricsView

## 技术栈

全部现有：Vue3 + Pinia + Vue Router / FastAPI / InfluxDB（InfluxDB Client）/ YAML 配置。
