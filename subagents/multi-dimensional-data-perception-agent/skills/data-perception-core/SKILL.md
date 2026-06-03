---
name: data-perception-core
description: 多维时序数据感知技能。当需要获取、分解、对齐、清洗和标准化多维监测数据时使用此技能。支持CSV多源数据获取、8类数据类型分解（水质、流量、设备状态、工艺参数、维护记录、生产记录、源信息、监测点信息）、进出水时间对齐（默认2小时滞后）、数据质控（缺失值/异常值检测）、字段标准化。为下游异常检测和规则推理提供高质量数据基础。在异常检测前务必使用此技能完成数据预处理。
version: 2.1.0
---

# 多维数据感知核心技能包

本技能包提供多维时序数据的获取、分解、对齐、清洗和标准化能力，为下游智能体提供高质量、标准化的数据基础。

## 为什么这个技能很重要

**数据质量是异常检测和规则推理的基础**——垃圾进，垃圾出（Garbage In, Garbage Out）。

本技能确保：
1. **数据完整性**：通过时间对齐消除进出水数据的2小时处理滞后
2. **数据一致性**：通过字段标准化统一不同数据源的命名差异
3. **数据有效性**：通过质控检测缺失值和超出合理范围的异常值
4. **数据结构化**：将复合数据按8类标准类型分解，便于下游处理

## 推荐使用方式

### 一键完成完整数据预处理（推荐）

```python
from scripts.data_acquisition import DataAcquisitionModule
from scripts.time_alignment import TimeAlignmentModule
from scripts.data_cleaning import DataCleaningModule
from scripts.standardization import StandardizationModule

# 1. 数据获取
acquisition = DataAcquisitionModule()
influent_data = acquisition.acquire_from_csv(
    "path/to/influent.csv",
    limit=1000
)
effluent_data = acquisition.acquire_from_csv(
    "path/to/effluent.csv",
    limit=1000
)

# 2. 时间对齐（默认2小时滞后）
alignment = TimeAlignmentModule()
aligned_data = alignment.align_with_lag(
    influent=influent_data["data"],
    effluent=effluent_data["data"]
)

# 3. 数据清洗
cleaning = DataCleaningModule()
cleaned = cleaning.clean_water_quality_data(
    aligned_data["effluent"]
)

# 4. 字段标准化
standardization = StandardizationModule()
standardized = standardization.standardize_water_quality({
    "influent": cleaned["cleaned_data"],
    "effluent": cleaned["cleaned_data"]
})
```

### 分步执行（特殊需求时）

```python
from scripts.data_acquisition import DataAcquisitionModule
from scripts.data_decomposition import DataDecompositionModule
from scripts.time_alignment import TimeAlignmentModule
from scripts.data_cleaning import DataCleaningModule
from scripts.standardization import StandardizationModule

# 1. 多维数据获取
acquisition = DataAcquisitionModule()
multi_data = acquisition.acquire_multi_dimensional({
    "influent_path": "path/to/influent.csv",
    "effluent_path": "path/to/effluent.csv",
    "equipment_path": "path/to/equipment.csv",
    "process_path": "path/to/process.csv"
})

# 2. 数据类型分解
decomposition = DataDecompositionModule()
decomposed = decomposition.decompose_multi_dimensional(multi_data)
# 返回8类数据：water_quality, flow, equipment_status,
#           process_parameters, maintenance_records,
#           production_records, source_info, monitoring_point_info

# 3. 时序对齐（自定义滞后时间）
alignment = TimeAlignmentModule(default_lag_hours=3)
aligned = alignment.align_with_lag(
    influent=decomposed["water_quality"]["influent"],
    effluent=decomposed["water_quality"]["effluent"],
    lag_hours=3  # 覆盖默认值
)

# 4. 数据质控
cleaning = DataCleaningModule()
cleaned_influent = cleaning.clean_water_quality_data(
    aligned["influent"]
)
cleaned_effluent = cleaning.clean_water_quality_data(
    aligned["effluent"]
)

# 5. 字段标准化
standardization = StandardizationModule()
final_data = standardization.standardize_water_quality({
    "influent": cleaned_influent["cleaned_data"],
    "effluent": cleaned_effluent["cleaned_data"]
})
```

## 核心脚本

### 1. data_acquisition.py (DataAcquisitionModule)
**功能**: 多源数据获取

- `acquire_from_csv(file_path, limit=None)`: 从CSV文件获取进出水数据
- `acquire_multi_dimensional(config)`: 获取多维数据（支持进水、出水、设备、工艺参数）
- `acquire_equipment_status(file_path, limit=None)`: 获取设备状态
- `acquire_process_parameters(file_path, limit=None)`: 获取工艺参数

**返回格式**:
```python
{
    "data": [...],        # 数据列表
    "count": 100,         # 记录数
    "columns": [...],      # 列名
    "source": "csv"       # 数据源
}
```

### 2. data_decomposition.py (DataDecompositionModule)
**功能**: 数据类型分解

- `decompose_multi_dimensional(input_data)`: 将复合数据按8类数据类型分解

**8类数据类型**:
1. `water_quality`: 水质数据（pH, COD, TN, NH3-N, TP, SS）
2. `flow`: 流量数据（流量、排放量）
3. `equipment_status`: 设备状态
4. `process_parameters`: 工艺参数
5. `maintenance_records`: 维护记录
6. `production_records`: 生产记录
7. `source_info`: 源信息
8. `monitoring_point_info`: 监测点信息

**字段映射**:
- pH/pH值 → water_quality
- 化学需氧量/化学需氧量浓度（毫克/升） → water_quality
- 总氮/总氮浓度（毫克/升） → water_quality
- 氨氮/氨氮浓度（毫克/升） → water_quality
- 总磷/总磷浓度（毫克/升） → water_quality
- 悬浮物/悬浮物浓度（毫克/升） → water_quality
- 流量/流量（升/秒） → flow
- 排放量/排放量（吨） → flow

### 3. time_alignment.py (TimeAlignmentModule)
**功能**: 时序对齐

- `align_with_lag(influent, effluent, lag_hours=None)`: 使用时间滞后对齐进出水数据

**关键配置**:
- `default_lag_hours=2`: 默认2小时滞后（废水处理标准滞后期）
- `lag_records`: 自动计算滞后记录数（基于5分钟间隔）
- `time_tolerance=300秒`: 5分钟内的时间容差

### 4. data_cleaning.py (DataCleaningModule)
**功能**: 数据质量控制

- `clean_water_quality_data(data)`: 清洗水质数据，检测缺失值和异常值

**质控指标**:
- `completeness`: 完整度（有效记录占比）
- `anomaly_rate`: 异常率（超出范围记录占比）
- `missing_count`: 缺失值数量
- `anomaly_count`: 异常值数量
- `cleaned_count`: 清洗后记录数
- `total_records`: 总记录数

### 5. standardization.py (StandardizationModule)
**功能**: 数据格式统一

- `standardize_water_quality(input_data)`: 标准化水质数据格式

**字段标准化映射**:
| 原字段名 | 标准字段名 |
|---------|-----------|
| pH值 | pH |
| 化学需氧量浓度（毫克/升） | COD |
| 总氮浓度（毫克/升） | TN |
| 氨氮浓度（毫克/升） | NH3_N |
| 总磷浓度（毫克/升） | TP |
| 悬浮物浓度（毫克/升） | SS |
| 流量（升/秒） | flow_rate |
| 排放量（吨） | discharge_volume |

## 配置参数说明

### 时间对齐参数
- `default_lag_hours=2`: 进出水默认滞后时间（小时）
  - 废水处理工艺标准滞后期
  - 可根据实际工艺调整
- `DEFAULT_INTERVAL_MINUTES=5`: 数据采集间隔（分钟）
- `TIME_TOLERANCE_SECONDS=300`: 时间匹配容差（秒）

### 数据质控范围
以下指标超出范围将被标记为异常：

| 指标 | 有效范围 | 单位 |
|-----|---------|-----|
| pH值 | 0 - 14 | - |
| COD | 0 - 1000 | mg/L |
| 总氮(TN) | 0 - 100 | mg/L |
| 氨氮(NH3-N) | 0 - 50 | mg/L |
| 总磷(TP) | 0 - 20 | mg/L |
| 悬浮物(SS) | 0 - 500 | mg/L |

### 字段映射规则
- 中文字段名优先映射到英文标准名
- 带单位的字段名标准化为简洁英文
- 保持原始数据精度和单位

## LLM决策点

### 1. 数据源选择决策
**场景**: 需要获取监测数据时
**决策依据**:
- 数据文件存在且可读 → 使用 `acquire_from_csv`
- 需要多种数据类型 → 使用 `acquire_multi_dimensional`
- 需要设备或工艺参数 → 使用专用方法

**示例规则**:
```
IF 任务包含 "进出水" OR "水质" THEN
    使用 acquire_from_csv 获取 influent 和 effluent
ELSE IF 任务包含 "设备" THEN
    使用 acquire_equipment_status
ELSE IF 任务包含 "工艺参数" THEN
    使用 acquire_process_parameters
ELSE
    使用 acquire_multi_dimensional 获取全部数据
```

### 2. 对齐策略决策
**场景**: 进出水数据时间不匹配时
**决策依据**:
- 废水处理标准工艺 → 使用默认2小时滞后
- 特殊工艺或已知滞后期 → 传入自定义 `lag_hours`
- 数据已同步 → 跳过对齐步骤

**示例规则**:
```
IF 数据包含 "influent" AND "effluent" THEN
    检查时间戳差异
    IF 差异约2小时 THEN
        使用 align_with_lag(lag_hours=2)
    ELSE IF 已知特定滞后期 THEN
        使用 align_with_lag(lag_hours=<已知值>)
    ELSE
        跳过对齐并记录原因
```

### 3. 质控阈值决策
**场景**: 数据质量检查时
**决策依据**:
- 标准废水监测 → 使用内置 valid_ranges
- 特殊工况（如事故排放） → 可放宽阈值
- 异常数据较多 → 记录警告但保留原始数据

**示例规则**:
```
IF 超出范围数据占比 > 20% THEN
    记录警告："数据质量较差，建议检查传感器"
    保留原始数据供人工审查
ELSE IF 超出范围数据占比 > 50% THEN
    记录错误："数据异常率过高，可能传感器故障"
    返回清洗后数据但标记高风险
ELSE
    正常清洗并返回
```

### 4. 标准化决策
**场景**: 字段名不一致时
**决策依据**:
- 字段名在映射表中 → 使用标准映射
- 字段名不在映射表 → 保留原名并记录

**示例规则**:
```
IF 字段名 IN field_mapping THEN
    应用标准化映射
ELSE
    保留原始字段名
    记录到 metadata.unmapped_fields
```

## 输出格式

所有模块统一返回包含 `data` 和 `metadata` 的结构：

```python
{
    "data": {
        "water_quality": {
            "influent": [...],
            "effluent": [...]
        },
        "flow": {...},
        # ... 其他6类数据
    },
    "metadata": {
        "source": "csv",
        "records_processed": 1000,
        "quality_report": {...},
        "lag_hours": 2,
        "timestamp": "2026-06-01T12:00:00"
    }
}
```

## 参考文档

- 专利文档 - 多维数据感知子智能体规范
- `/shared/configs/anomaly_config.json` - 异常检测配置参考
- `/shared/configs/operator_config.json` - 算子配置参考
