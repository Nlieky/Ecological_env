# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## Environment-Specific Information

- **Data file path**: `/home/NYJ2025/Ecological_env/data/`
- **Hydraulic retention time**: 2 hours
- **Data sampling interval**: 5 minutes
- **Timezone**: UTC+8 (Asia/Shanghai)

## Data Source Configuration

| 数据源 | 状态 | 路径/配置 |
|------|------|----------|
| CSV文件 | 已实现 | `data/pollution_water_influent.csv`<br>`data/pollution_water_effluent.csv` |
| API接口 | 预留 | 监管平台数据推送接口（待配置） |
| 数据库 | 预留 | 历史数据查询（待配置） |

## Script Locations

Your skills are in `skills/data-perception-core/scripts/`:

| 脚本 | 功能 | 路径 |
|------|------|------|
| 数据获取 | 从CSV/API/数据库获取数据 | `skills/data-perception-core/scripts/data_acquisition.py` |
| 数据分解 | 按8类数据分解复合数据 | `skills/data-perception-core/scripts/data_decomposition.py` |
| 时间对齐 | 处理2小时时滞，统一时间基准 | `skills/data-perception-core/scripts/time_alignment.py` |
| 数据清洗 | 异常值识别修正，缺失值补全 | `skills/data-perception-core/scripts/data_cleaning.py` |
| 标准化 | 统一字段命名、单位、时间格式 | `skills/data-perception-core/scripts/standardization.py` |

## Data Processing Tools

### Time Alignment Tools
- **Tool**: pandas.DataFrame.reindex + interpolate
- **Method**: Linear interpolation (max 3 consecutive missing points)
- **Time lag**: 2 hours (influent→effluent)
- **Timezone**: UTC+8统一时间基准

### Data Quality Control Tools
- **Anomaly detection**: Statistical threshold method
- **Missing value completion**: Linear interpolation / forward-fill
- **Consistency check**: Correlation analysis between related indicators

### Standardization Tools
- **Field mapping**: Chinese/English field name mapping table
- **Unit conversion**: Unified unit system (mg/L for concentration, m³/h for flow)
- **Time format**: ISO 8601 (YYYY-MM-DDTHH:MM:SS)

## Data Quality Thresholds

| 指标 | 阈值 | 处理策略 |
|------|------|---------|
| 缺失率 | >5% | 报错，不返回数据 |
| 异常值比例 | >1% | 修正后返回，附质量报告 |
| 连续缺失点 | >3个 | 不插值，标记为缺失 |
| pH值范围 | [0, 14] | 超出标记为异常 |
| COD范围 | [0, 1000]mg/L | 超出标记为可疑 |

## Field Naming Convention

| 中文 | English | Unit |
|------|---------|------|
| pH值 | pH | - |
| 化学需氧量 | COD | mg/L |
| 总氮 | TN | mg/L |
| 总磷 | TP | mg/L |
| 氨氮 | NH3_N | mg/L |
| 悬浮物 | SS | mg/L |
| 进水流量 | influent_flow | m³/h |
| 出水流量 | effluent_flow | m³/h |
| 溶解氧 | DO | mg/L |
| 污泥浓度 | MLSS | mg/L |

## Related

- [Agent workspace](/concepts/agent-workspace)
