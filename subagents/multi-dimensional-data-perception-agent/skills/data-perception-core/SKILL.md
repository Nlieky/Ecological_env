---
name: data-perception-core
description: Multi-dimensional time-series data preprocessing for wastewater monitoring. Use when data needs to be acquired, aligned, cleaned, or standardized before anomaly detection. Supports CSV multi-source acquisition, 8-type data decomposition (water quality, flow, equipment status, process parameters, maintenance records, production records, source info, monitoring point info), influent/effluent time alignment (default 2-hour lag), data quality control (missing/anomaly detection), and field standardization. Required before anomaly detection to ensure high-quality data input.
---

# Multi-Dimensional Data Perception

## Overview

Provides data acquisition, decomposition, time alignment, cleaning, and standardization for wastewater monitoring time-series data. Ensures data quality through completeness checks, consistency validation, and structured decomposition.

## Quick Start

```python
from scripts.data_acquisition import DataAcquisitionModule
from scripts.time_alignment import TimeAlignmentModule
from scripts.data_cleaning import DataCleaningModule
from scripts.standardization import StandardizationModule

# Complete pipeline
acquisition = DataAcquisitionModule()
influent = acquisition.acquire_from_csv("path/to/influent.csv", limit=1000)
effluent = acquisition.acquire_from_csv("path/to/effluent.csv", limit=1000)

alignment = TimeAlignmentModule()
aligned = alignment.align_with_lag(influent=influent["data"], effluent=effluent["data"])

cleaning = DataCleaningModule()
cleaned = cleaning.clean_water_quality_data(aligned["effluent"])

standardization = StandardizationModule()
standardized = standardization.standardize_water_quality({
    "influent": cleaned["cleaned_data"],
    "effluent": cleaned["cleaned_data"]
})
```

## Core Modules

### data_acquisition.py
- `acquire_from_csv(file_path, limit=None)`: Get influent/effluent data from CSV
- `acquire_multi_dimensional(config)`: Multi-source data acquisition
- Returns: `{"data": [...], "count": N, "columns": [...], "source": "csv"}`

### data_decomposition.py
- `decompose_multi_dimensional(input_data)`: Decompose into 8 data types
  1. water_quality: pH, COD, TN, NH3-N, TP, SS
  2. flow: flow_rate, discharge_volume
  3. equipment_status, 4. process_parameters
  5. maintenance_records, 6. production_records
  7. source_info, 8. monitoring_point_info

### time_alignment.py
- `align_with_lag(influent, effluent, lag_hours=None)`: Time alignment with lag
  - `default_lag_hours=2`: Standard wastewater treatment lag
  - `TIME_TOLERANCE_SECONDS=300`: 5-minute matching window

### data_cleaning.py
- `clean_water_quality_data(data)`: Quality control for missing/anomaly values
  - Returns: completeness, anomaly_rate, missing_count, anomaly_count

### standardization.py
- `standardize_water_quality(input_data)`: Field name standardization
  - pH值 → pH, 化学需氧量浓度（毫克/升） → COD
  - 总氮浓度（毫克/升） → TN, 氨氮浓度（毫克/升） → NH3_N

## Configuration

### Time Alignment
- `default_lag_hours=2`: Influent-to-effluent processing lag
- `DEFAULT_INTERVAL_MINUTES=5`: Data collection interval
- `TIME_TOLERANCE_SECONDS=300`: Time matching tolerance

### Quality Control Ranges
| Indicator | Valid Range | Unit |
|-----------|-------------|------|
| pH | 0-14 | - |
| COD | 0-1000 | mg/L |
| TN | 0-100 | mg/L |
| NH3-N | 0-50 | mg/L |
| TP | 0-20 | mg/L |
| SS | 0-500 | mg/L |

## LLM Decision Points

### Data Source Selection
- Contains "influent/effluent" or "water quality" → `acquire_from_csv`
- Contains "equipment" → `acquire_equipment_status`
- Multiple data types needed → `acquire_multi_dimensional`

### Alignment Strategy
- Standard wastewater process → default 2-hour lag
- Known specific lag → pass `lag_hours` parameter
- Data already synchronized → skip alignment

### Quality Thresholds
- Anomaly rate > 20% → Warning: "Check sensors"
- Anomaly rate > 50% → Error: "Possible sensor failure"
- Preserve original data for manual review

## Output Format

```python
{
    "data": {
        "water_quality": {"influent": [...], "effluent": [...]},
        "flow": {...}
    },
    "metadata": {
        "source": "csv",
        "records_processed": 1000,
        "quality_report": {...},
        "lag_hours": 2
    }
}
```

## References

For detailed configuration: patent documentation, `/shared/configs/anomaly_config.json`
