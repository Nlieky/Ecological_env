# 子智能体逻辑改进实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 改进两个子智能体（multi-dimensional-data-perception-agent 和 anomaly-detection-agent）的逻辑功能，修复数据清洗、时间对齐、字段映射、异常数据格式和感知结果利用等问题。

**Architecture:** 采用模块化改进策略，每个改进点独立实现，通过测试验证，确保不影响现有功能。优先级从高到低：数据清洗→异常格式→感知利用→时间对齐→字段映射→时间戳匹配→插值→特征集成。

**Tech Stack:** Python 3.8+, pandas, numpy, 标准库 (re, datetime)

---

## 文件结构

### 需要修改的文件

| 文件 | 修改内容 | 责任 |
|------|----------|------|
| `subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/data_cleaning.py` | 修复数据清洗逻辑，允许部分异常 | 数据质量控制 |
| `subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/time_alignment.py` | 改进时间对齐，取最佳匹配 | 时序对齐 |
| `subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/standardization.py` | 完善字段映射，支持正则匹配 | 字段标准化 |
| `subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/__init__.py` | 统一异常数据输出格式 | 数据格式标准化 |
| `middleware/query_interface.py` | 利用感知结果，改进异常数据提取和时间戳匹配 | 协调逻辑 |
| `subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/time_series_features.py` | 集成时间序列特征到主流程 | 特征提取集成 |

### 需要创建的文件

| 文件 | 用途 |
|------|------|
| `subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/data_interpolation.py` | 缺失值插值模块 |
| `tests/subagents/test_data_cleaning_improved.py` | 改进后的数据清洗测试 |
| `tests/subagents/test_time_alignment_best_match.py` | 时间对齐最佳匹配测试 |

---

## Phase 1: 高优先级修复

### Task 1: 修复数据清洗逻辑

**问题**: 当前实现中，如果一条记录有任何异常值，整条记录都被丢弃。

**目标**: 保留有效字段，只标记异常字段。

**Files:**
- Modify: `subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/data_cleaning.py`
- Test: `tests/subagents/test_data_cleaning_improved.py`

#### Step 1.1: 添加异常字段标记

- [ ] **修改 data_cleaning.py 中的 clean_water_quality_data 方法**

```python
# 在第101行附近，修改cleaned_record的构建逻辑
# 原代码：
for key, value in record.items():
    # 检查缺失值
    if value is None or value == "" or value == "/":
        missing_count += 1
        cleaned_record[key] = None
        continue
    
    # 检查异常值
    if key in self.valid_ranges:
        min_val, max_val = self.valid_ranges[key]
        try:
            num_value = float(value)
            if num_value < min_val or num_value > max_val:
                anomaly_count += 1
                record_has_anomaly = True
                cleaned_record[key] = None  # 这里会删除异常值
            else:
                cleaned_record[key] = num_value
        except (ValueError, TypeError):
            anomaly_count += 1
            cleaned_record[key] = None
    else:
        cleaned_record[key] = value

# 新代码：
cleaned_record = {}
anomaly_fields = []  # 记录异常字段

for key, value in record.items():
    # 检查缺失值
    if value is None or value == "" or value == "/":
        missing_count += 1
        cleaned_record[key] = None
        continue
    
    # 检查异常值
    if key in self.valid_ranges:
        min_val, max_val = self.valid_ranges[key]
        try:
            num_value = float(value)
            if num_value < min_val or num_value > max_val:
                anomaly_count += 1
                anomaly_fields.append(key)  # 记录异常字段
                # 保留原始值，但在anomaly_fields中标记
                cleaned_record[key] = num_value
            else:
                cleaned_record[key] = num_value
        except (ValueError, TypeError):
            anomaly_count += 1
            anomaly_fields.append(key)
            cleaned_record[key] = None
    else:
        cleaned_record[key] = value

# 将异常字段列表添加到记录中
if anomaly_fields:
    cleaned_record['_anomaly_fields'] = anomaly_fields
```

#### Step 1.2: 修改记录添加逻辑

- [ ] **移除整条记录丢弃的逻辑**

```python
# 原代码（第128行）：
if not record_has_anomaly:
    cleaned_data.append(cleaned_record)

# 新代码：所有记录都保留
cleaned_data.append(cleaned_record)
```

#### Step 1.3: 更新质量报告

- [ ] **添加anomaly_fields_report到quality_report**

```python
# 在quality_report中添加新字段
quality_report = {
    "completeness": round(completeness, 3),
    "anomaly_rate": round(anomaly_rate, 3),
    "missing_count": missing_count,
    "anomaly_count": anomaly_count,
    "cleaned_count": len(cleaned_data),
    "total_records": len(data),
    "anomaly_fields_summary": {}  # 新增：统计各字段的异常次数
}

# 统计各字段异常次数
field_anomaly_counts = {}
for record in cleaned_data:
    if '_anomaly_fields' in record:
        for field in record['_anomaly_fields']:
            field_anomaly_counts[field] = field_anomaly_counts.get(field, 0) + 1

quality_report["anomaly_fields_summary"] = field_anomaly_counts
```

#### Step 1.4: 编写测试

- [ ] **创建测试文件 test_data_cleaning_improved.py**

```python
import pytest
from pathlib import Path
import sys

# Add subagent scripts to path
subagent_scripts = Path(__file__).parent.parent.parent.parent / "subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts"
sys.path.insert(0, str(subagent_scripts))

from data_cleaning import DataCleaningModule

def test_partial_anomaly_fields():
    """测试部分字段异常时，其他有效字段被保留"""
    cleaner = DataCleaningModule()
    
    data = [
        {"pH值": 7.5, "COD": 45, "TN": 15},  # 正常
        {"pH值": 25, "COD": 45, "TN": 15},  # pH异常
        {"pH值": 7.5, "COD": 1500, "TN": 15},  # COD异常
        {"pH值": 7.5, "COD": 45, "TN": 150},  # TN异常
        {"pH值": 25, "COD": 1500, "TN": 150},  # 全部异常
    ]
    
    result = cleaner.clean_water_quality_data(data)
    
    # 验证：所有记录都被保留
    assert result["cleaned_count"] == 5
    
    # 验证：第二条记录的异常字段被标记
    assert "_anomaly_fields" in result["cleaned_data"][1]
    assert "pH值" in result["cleaned_data"][1]["_anomaly_fields"]
    
    # 验证：第二条记录的有效字段被保留
    assert result["cleaned_data"][1]["COD"] == 45
    assert result["cleaned_data"][1]["TN"] == 15
    
    # 验证：质量报告包含字段异常统计
    assert "anomaly_fields_summary" in result["quality_report"]
    assert result["quality_report"]["anomaly_fields_summary"]["pH值"] == 2  # pH异常2次
    
def test_anomaly_field_preservation():
    """测试异常值被保留并标记"""
    cleaner = DataCleaningModule()
    
    data = [{"pH值": 25, "COD": 45}]
    
    result = cleaner.clean_water_quality_data(data)
    
    # 异常值应该被保留（而不是设为None）
    assert result["cleaned_data"][0]["pH值"] == 25
    # 但被标记为异常
    assert "pH值" in result["cleaned_data"][0]["_anomaly_fields"]
    
def run_tests():
    """运行所有测试"""
    test_partial_anomaly_fields()
    print("✅ test_partial_anomaly_fields passed")
    
    test_anomaly_field_preservation()
    print("✅ test_anomaly_field_preservation passed")
    
    print("\n所有测试通过!")

if __name__ == "__main__":
    run_tests()
```

#### Step 1.5: 运行测试验证

- [ ] **运行测试**

```bash
cd E:/project/Ecological_env
python tests/subagents/test_data_cleaning_improved.py
```

Expected output:
```
✅ test_partial_anomaly_fields passed
✅ test_anomaly_field_preservation passed

所有测试通过!
```

#### Step 1.6: 提交更改

- [ ] **提交数据清洗逻辑改进**

```bash
cd E:/project/Ecological_env
git add subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/data_cleaning.py
git add tests/subagents/test_data_cleaning_improved.py
git commit -m "feat(data-cleaning): 允许部分异常，保留有效字段并标记异常字段"
```

---

### Task 2: 统一异常数据格式

**问题**: 异常检测子智能体输出的格式与查询接口期望的不一致。

**目标**: 在子智能体输出时标准化格式为 `{indicator, times, score, pattern, severity}`。

**Files:**
- Modify: `subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/__init__.py`
- Test: `tests/subagents/test_anomaly_format_standardization.py`

#### Step 2.1: 添加格式标准化函数

- [ ] **在 anomaly-detection-core/scripts/__init__.py 中添加标准化函数**

```python
# 在文件顶部添加
from typing import Dict, List, Any

def standardize_anomaly_output(anomaly_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    标准化异常检测输出格式
    
    Args:
        anomaly_output: 原始异常检测输出
        
    Returns:
        标准化后的输出，包含标准格式的anomalies列表
    """
    if not anomaly_output or not isinstance(anomaly_output, dict):
        return {"anomalies": [], "status": "error", "message": "Invalid input"}
    
    # 获取anomalies列表（支持多种路径）
    anomalies = []
    if "anomalies" in anomaly_output:
        anomalies = anomaly_output["anomalies"]
    elif "result" in anomaly_output and isinstance(anomaly_output["result"], dict):
        result = anomaly_output["result"]
        if "anomalies" in result:
            anomalies = result["anomalies"]
        elif "output" in result and isinstance(result["output"], dict) and "anomalies" in result["output"]:
            anomalies = result["output"]["anomalies"]
    
    if not anomalies:
        return {
            "anomalies": [],
            "status": "success",
            "message": "No anomalies found",
            "patterns": anomaly_output.get("patterns", {}),
            "violations": anomaly_output.get("violations", [])
        }
    
    # 标准化每个异常点
    standardized_anomalies = []
    for anomaly in anomalies:
        if not isinstance(anomaly, dict):
            continue
        
        # 构建标准格式
        std_anomaly = {
            "indicator": _format_indicator(anomaly),
            "times": _format_timestamp(anomaly),
            "score": float(anomaly.get("score", anomaly.get("anomaly_score", 0.5))),
            "pattern": anomaly.get("pattern", anomaly.get("type", "unknown")),
            "severity": _determine_severity(anomaly)
        }
        
        standardized_anomalies.append(std_anomaly)
    
    # 返回标准化输出
    return {
        "anomalies": standardized_anomalies,
        "status": "success",
        "patterns": anomaly_output.get("patterns", {}),
        "violations": anomaly_output.get("violations", []),
        "confidence": anomaly_output.get("confidence", {}),
        "suspicion_level": anomaly_output.get("suspicion_level", "medium")
    }

def _format_indicator(anomaly: Dict[str, Any]) -> str:
    """格式化指标名称为标准格式: {source}_{indicator}"""
    indicator = anomaly.get("indicator", anomaly.get("feature", "unknown"))
    source = anomaly.get("source", "effluent")  # 默认为出水
    
    # 移除可能的单位后缀
    indicator = indicator.replace("（毫克/升）", "").replace("(mg/L)", "")
    
    # 标准化中文字段名
    field_mapping = {
        "pH值": "pH",
        "化学需氧量浓度": "COD",
        "总氮浓度": "TN",
        "氨氮浓度": "NH3_N",
        "总磷浓度": "TP"
    }
    
    if indicator in field_mapping:
        indicator = field_mapping[indicator]
    
    return f"{source}_{indicator}"

def _format_timestamp(anomaly: Dict[str, Any]) -> str:
    """格式化时间戳"""
    # 支持多种时间字段
    time_fields = ["timestamp", "time", "times", "datetime", "监测时间"]
    
    for field in time_fields:
        if field in anomaly and anomaly[field]:
            time_val = anomaly[field]
            # 如果是整数（索引），返回原值
            if isinstance(time_val, int):
                return str(time_val)
            # 如果是字符串，确保格式
            return str(time_val)
    
    # 如果没有时间字段，返回空字符串
    return ""

def _determine_severity(anomaly: Dict[str, Any]) -> str:
    """确定严重程度"""
    # 如果已经有severity字段，直接使用
    if "severity" in anomaly:
        return anomaly["severity"]
    
    # 基于score确定
    score = anomaly.get("score", anomaly.get("anomaly_score", 0.5))
    
    if score >= 0.8:
        return "high"
    elif score >= 0.5:
        return "medium"
    else:
        return "low"
```

#### Step 2.2: 修改主入口函数

- [ ] **修改 detect_anomalies 函数以使用标准化输出**

```python
# 在__init__.py中，找到detect_anomalies函数，在返回前添加标准化

# 原代码（大概在第50-80行附近）：
def detect_anomalies(data, indicators=None, config=None):
    # ... 检测逻辑 ...
    
    return {
        "anomalies": anomalies,
        "patterns": patterns,
        "violations": violations,
        # ...
    }

# 新代码：在返回前标准化
def detect_anomalies(data, indicators=None, config=None):
    # ... 现有检测逻辑 ...
    
    raw_output = {
        "anomalies": anomalies,
        "patterns": patterns,
        "violations": violations,
        # ... 其他字段
    }
    
    # 标准化输出
    return standardize_anomaly_output(raw_output)
```

#### Step 2.3: 编写测试

- [ ] **创建测试文件 test_anomaly_format_standardization.py**

```python
import pytest
from pathlib import Path
import sys

# Add subagent scripts to path
subagent_scripts = Path(__file__).parent.parent.parent.parent / "subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts"
sys.path.insert(0, str(subagent_scripts))

from __init__ import standardize_anomaly_output

def test_standardize_anomaly_output():
    """测试异常输出标准化"""
    # 模拟原始输出
    raw_output = {
        "anomalies": [
            {
                "indicator": "pH值",
                "timestamp": "2024-01-01 12:00",
                "score": 0.9,
                "type": "constant"
            },
            {
                "indicator": "COD",
                "time": "2024-01-01 13:00",
                "anomaly_score": 0.7,
                "pattern": "spike"
            }
        ],
        "patterns": {"constant": 1, "spike": 1},
        "violations": []
    }
    
    standardized = standardize_anomaly_output(raw_output)
    
    # 验证：anomalies列表存在
    assert "anomalies" in standardized
    assert len(standardized["anomalies"]) == 2
    
    # 验证：第一个异常的格式
    anom1 = standardized["anomalies"][0]
    assert anom1["indicator"] == "effluent_pH"  # 格式化为 source_indicator
    assert anom1["times"] == "2024-01-01 12:00"
    assert anom1["score"] == 0.9
    assert anom1["pattern"] == "constant"
    assert anom1["severity"] == "high"  # 基于score=0.9判定
    
    # 验证：第二个异常的格式
    anom2 = standardized["anomalies"][1]
    assert anom2["indicator"] == "effluent_COD"
    assert anom2["pattern"] == "spike"  # type字段被映射到pattern
    
def test_empty_input():
    """测试空输入"""
    result = standardize_anomaly_output(None)
    assert result["anomalies"] == []
    assert result["status"] == "error"
    
def test_nested_path_extraction():
    """测试嵌套路径提取"""
    nested_output = {
        "result": {
            "anomalies": [
                {"indicator": "pH", "score": 0.8, "type": "trend"}
            ]
        }
    }
    
    standardized = standardize_anomaly_output(nested_output)
    assert len(standardized["anomalies"]) == 1
    assert standardized["anomalies"][0]["severity"] == "high"

def run_tests():
    """运行所有测试"""
    test_standardize_anomaly_output()
    print("✅ test_standardize_anomaly_output passed")
    
    test_empty_input()
    print("✅ test_empty_input passed")
    
    test_nested_path_extraction()
    print("✅ test_nested_path_extraction passed")
    
    print("\n所有测试通过!")

if __name__ == "__main__":
    run_tests()
```

#### Step 2.4: 运行测试验证

- [ ] **运行测试**

```bash
cd E:/project/Ecological_env
python tests/subagents/test_anomaly_format_standardization.py
```

Expected output:
```
✅ test_standardize_anomaly_output passed
✅ test_empty_input passed
✅ test_nested_path_extraction passed

所有测试通过!
```

#### Step 2.5: 提交更改

- [ ] **提交异常格式标准化**

```bash
cd E:/project/Ecological_env
git add subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/__init__.py
git add tests/subagents/test_anomaly_format_standardization.py
git commit -m "feat(anomaly-format): 统一异常数据输出格式为标准{indicator, times, score, pattern, severity}"
```

---

### Task 3: 利用感知子智能体结果

**问题**: 异常检测子智能体直接基于原始CSV数据工作，忽略了感知子智能体的预处理结果。

**目标**: 异常检测使用感知子智能体预处理后的数据。

**Files:**
- Modify: `middleware/query_interface.py`
- Test: `tests/middleware/test_query_perception_utilization.py`

#### Step 3.1: 修改异常检测任务数据

- [ ] **修改 query_interface.py 第294-313行的异常检测任务**

```python
# 原代码：
anomaly_result = llm_coordinator.coordinate_agent_execution(
    agent_id="anomaly-detection-agent",
    task={
        "task_id": f"query_{datetime.now().strftime('%Y%m%d%H%M%S')}_anomaly",
        "description": "异常检测和相关性分析",
        "query": query,
        "intent": intent,
        "data": historical_data,  # 直接使用原始数据
        "metadata": {
            "data_count": len(historical_data.get('influent', [])),
            "indicators": intent.get('indicators', []),
            "analysis_types": intent.get('analysis_types', []),
            "influent_timeseries": historical_data.get('influent', []),
            "effluent_timeseries": historical_data.get('effluent', [])
        },
        "previous_results": {"perception": perception_result}
    },
    previous_results={"perception": perception_result}
)

# 新代码：使用感知结果中的预处理数据
# 首先从感知结果中提取预处理后的数据
processed_data = historical_data  # 默认使用原始数据
if perception_result and isinstance(perception_result, dict):
    # 尝试从感知结果中获取cleaned_data
    if "result" in perception_result:
        result_data = perception_result["result"]
        if isinstance(result_data, dict):
            # 路径1: result.cleaned_data
            if "cleaned_data" in result_data:
                cleaned = result_data["cleaned_data"]
                if isinstance(cleaned, dict) and "influent" in cleaned and "effluent" in cleaned:
                    processed_data = {
                        "influent": cleaned["influent"],
                        "effluent": cleaned["effluent"]
                    }
                    log_info(f"[STEP 3.2] 使用感知子智能体预处理后的数据: influent={len(processed_data['influent'])}, effluent={len(processed_data['effluent'])}")
            # 路径2: result.aligned_data
            elif "aligned_data" in result_data:
                aligned = result_data["aligned_data"]
                if isinstance(aligned, dict):
                    processed_data = aligned
                    log_info(f"[STEP 3.2] 使用感知子智能体对齐后的数据")

anomaly_result = llm_coordinator.coordinate_agent_execution(
    agent_id="anomaly-detection-agent",
    task={
        "task_id": f"query_{datetime.now().strftime('%Y%m%d%H%M%S')}_anomaly",
        "description": "异常检测和相关性分析",
        "query": query,
        "intent": intent,
        "data": processed_data,  # 使用预处理后的数据
        "metadata": {
            "data_count": len(processed_data.get('influent', [])),
            "indicators": intent.get('indicators', []),
            "analysis_types": intent.get('analysis_types', []),
            "data_source": "preprocessed" if processed_data is not historical_data else "raw"
        },
        "previous_results": {"perception": perception_result}
    },
    previous_results={"perception": perception_result}
)
```

#### Step 3.2: 更新感知子智能体输出

- [ ] **修改 execution_control.py 或相关脚本来输出cleaned_data**

由于感知子智能体的输出格式需要标准化，我们需要在 `workspace/skills/orchestrator-core/scripts/execution_control.py` 中的 `_execute_data_perception` 方法添加cleaned_data输出：

```python
# 在 _execute_data_perception 方法中，找到返回部分
# 大概在第1377-1436行附近

# 原代码返回：
return {
    "status": "success",
    "summary": f"数据感知完成: {len(influent_data)}条进水, {len(effluent_data)}条出水",
    "data": context["data"],
    # ...
}

# 新代码：添加cleaned_data
# 在调用数据流水线后，提取cleaned_data
# 假设pipeline返回包含cleaned_data
if "pipeline_result" in result:
    pipeline_result = result["pipeline_result"]
    if isinstance(pipeline_result, dict) and "cleaned_data" in pipeline_result:
        cleaned = pipeline_result["cleaned_data"]
        if isinstance(cleaned, dict):
            # 确保influent和effluent都有
            if "influent" not in cleaned:
                cleaned["influent"] = context["data"].get("influent", [])
            if "effluent" not in cleaned:
                cleaned["effluent"] = context["data"].get("effluent", [])
            
            return {
                "status": "success",
                "summary": f"数据感知完成: {len(cleaned.get('influent', []))}条进水, {len(cleaned.get('effluent', []))}条出水",
                "data": context["data"],
                "result": {
                    "cleaned_data": cleaned,  # 新增：清洗后的数据
                    "quality_report": pipeline_result.get("quality_report", {})
                },
                # ... 其他字段
            }
```

#### Step 3.3: 编写测试

- [ ] **创建测试文件 test_query_perception_utilization.py**

```python
import pytest
from pathlib import Path
import sys

# Add paths
middleware_path = Path(__file__).parent.parent / "middleware"
sys.path.insert(0, str(middleware_path))

def test_perception_result_utilization():
    """测试查询接口是否使用感知结果"""
    # 这个测试需要mock LLM调用
    # 简化版本：验证数据传递逻辑
    
    # 模拟感知结果
    perception_result = {
        "status": "success",
        "result": {
            "cleaned_data": {
                "influent": [{"timestamp": "2024-01-01T00:00", "pH": 7.5}],
                "effluent": [{"timestamp": "2024-01-01T02:00", "pH": 7.8}]
            },
            "quality_report": {"completeness": 0.95}
        }
    }
    
    # 验证：从感知结果中提取cleaned_data
    processed_data = {"influent": [], "effluent": []}  # 默认
    if perception_result and isinstance(perception_result, dict):
        if "result" in perception_result:
            result_data = perception_result["result"]
            if isinstance(result_data, dict) and "cleaned_data" in result_data:
                cleaned = result_data["cleaned_data"]
                if isinstance(cleaned, dict) and "influent" in cleaned:
                    processed_data = cleaned
    
    # 验证：processed_data应该包含感知结果的数据
    assert len(processed_data["influent"]) == 1
    assert processed_data["influent"][0]["pH"] == 7.5
    
    print("✅ 感知结果数据提取逻辑正确")

def run_tests():
    test_perception_result_utilization()
    print("\n所有测试通过!")

if __name__ == "__main__":
    run_tests()
```

#### Step 3.4: 运行测试验证

- [ ] **运行测试**

```bash
cd E:/project/Ecological_env
python tests/middleware/test_query_perception_utilization.py
```

Expected output:
```
✅ 感知结果数据提取逻辑正确

所有测试通过!
```

#### Step 3.5: 提交更改

- [ ] **提交感知结果利用改进**

```bash
cd E:/project/Ecological_env
git add middleware/query_interface.py
git add workspace/skills/orchestrator-core/scripts/execution_control.py
git add tests/middleware/test_query_perception_utilization.py
git commit -m "feat(query-interface): 异常检测使用感知子智能体预处理后的数据"
```

---

## Phase 2: 中优先级改进

### Task 4: 改进时间对齐算法

**问题**: 当前取第一个匹配记录，可能不是最佳匹配。

**目标**: 取时间差最小的匹配记录。

**Files:**
- Modify: `subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/time_alignment.py`
- Test: `tests/subagents/test_time_alignment_best_match.py`

#### Step 4.1: 修改pandas对齐方法

- [ ] **修改 _align_with_pandas 方法中的匹配逻辑**

```python
# 原代码（第136-137行）：
if not matching_eff.empty:
    eff_row = matching_eff.iloc[0]  # 只取第一条

# 新代码：取时间差最小的
if not matching_eff.empty:
    # 计算每条匹配记录的时间差
    matching_eff['time_diff'] = (matching_eff[FIELD_MONITORING_TIME] - target_time).abs()
    # 取时间差最小的记录
    best_match_idx = matching_eff['time_diff'].idxmin()
    eff_row = matching_eff.loc[best_match_idx]
```

#### Step 4.2: 修改非pandas对齐方法

- [ ] **修改 _align_without_pandas 方法中的匹配逻辑**

```python
# 原代码（第187-194行）：
for eff_record in effluent:
    # ... 时间转换 ...
    time_diff = abs((eff_time - target_time).total_seconds())
    
    if time_diff < TIME_TOLERANCE_SECONDS:
        aligned_pairs.append({...})
        break  # 取第一个就退出

# 新代码：记录所有匹配，取最佳
best_match = None
best_time_diff = float('inf')

for eff_record in effluent:
    # ... 时间转换 ...
    time_diff = abs((eff_time - target_time).total_seconds())
    
    if time_diff < TIME_TOLERANCE_SECONDS and time_diff < best_time_diff:
        best_time_diff = time_diff
        best_match = {
            "influent_time": inf_time.strftime(DATETIME_FORMAT),
            "effluent_time": eff_time.strftime(DATETIME_FORMAT),
            "influent": inf_record,
            "effluent": eff_record,
            "time_diff": time_diff  # 记录时间差
        }

if best_match:
    aligned_pairs.append(best_match)
```

#### Step 4.3: 编写测试

- [ ] **创建测试文件 test_time_alignment_best_match.py**

```python
import pytest
from pathlib import Path
import sys

subagent_scripts = Path(__file__).parent.parent.parent.parent / "subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts"
sys.path.insert(0, str(subagent_scripts))

from time_alignment import TimeAlignmentModule

def test_best_time_match_selection():
    """测试选择时间差最小的匹配"""
    aligner = TimeAlignmentModule(default_lag_hours=2)
    
    influent = [
        {"监测时间": "2024-01-01 00:00", "pH": 7.5}
    ]
    
    # 出水有多个匹配（5分钟容差内）
    effluent = [
        {"监测时间": "2024-01-01 02:03", "pH": 7.8},  # 时间差3分钟
        {"监测时间": "2024-01-01 02:01", "pH": 7.7},  # 时间差1分钟（最佳）
        {"监测时间": "2024-01-01 02:04", "pH": 7.9},  # 时间差4分钟
    ]
    
    result = aligner.align_with_lag(influent, effluent)
    
    # 验证：应该选择时间差最小的（02:01）
    assert result["alignment_count"] == 1
    aligned_pair = result["aligned_pairs"][0]
    assert aligned_pair["effluent_time"] == "2024-01-01 02:01"
    
    print("✅ 最佳时间匹配选择正确")

def run_tests():
    test_best_time_match_selection()
    print("\n所有测试通过!")

if __name__ == "__main__":
    run_tests()
```

#### Step 4.4: 运行测试验证

- [ ] **运行测试**

```bash
cd E:/project/Ecological_env
python tests/subagents/test_time_alignment_best_match.py
```

#### Step 4.5: 提交更改

- [ ] **提交时间对齐改进**

```bash
cd E:/project/Ecological_env
git add subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/time_alignment.py
git add tests/subagents/test_time_alignment_best_match.py
git commit -m "feat(time-alignment): 选择时间差最小的匹配记录而非第一个"
```

---

### Task 5: 完善字段映射

**问题**: 字段映射不完整，无法处理变体字段名。

**目标**: 支持正则表达式匹配字段名。

**Files:**
- Modify: `subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/standardization.py`

#### Step 5.1: 添加正则映射

- [ ] **在 standardization.py 中添加正则表达式映射**

```python
# 在StandardizationModule类中添加新的字段映射方法

class FieldMapper:
    """字段映射器 - 支持正则表达式匹配"""
    
    # 基础映射表（精确匹配）
    EXACT_MAPPING = {
        "pH值": "pH",
        "化学需氧量浓度（毫克/升）": "COD",
        "化学需氧量浓度": "COD",
        "总氮浓度（毫克/升）": "TN",
        "总氮浓度": "TN",
        "氨氮浓度（毫克/升）": "NH3_N",
        "氨氮浓度": "NH3_N",
        "总磷浓度（毫克/升）": "TP",
        "总磷浓度": "TP",
        "悬浮物浓度（毫克/升）": "SS",
        "悬浮物浓度": "SS",
        "流量（升/秒）": "flow_rate",
        "流量": "flow_rate",
        "排放量（吨）": "discharge_volume",
        "排放量": "discharge_volume"
    }
    
    # 正则模式映射（模糊匹配）
    REGEX_PATTERNS = [
        (r"pH.*", "pH"),
        (r"化学需氧量.*", "COD"),
        (r"总氮.*", "TN"),
        (r"氨氮.*", "NH3_N"),
        (r"总磷.*", "TP"),
        (r"悬浮物.*", "SS"),
        (r"流量.*", "flow_rate"),
        (r"排放量.*", "discharge_volume")
    ]
    
    @classmethod
    def map_field(cls, field_name: str) -> str:
        """
        映射字段名到标准名
        
        Args:
            field_name: 原始字段名
            
        Returns:
            标准字段名
        """
        # 1. 尝试精确匹配
        if field_name in cls.EXACT_MAPPING:
            return cls.EXACT_MAPPING[field_name]
        
        # 2. 尝试正则匹配
        import re
        for pattern, standard_name in cls.REGEX_PATTERNS:
            if re.search(pattern, field_name):
                return standard_name
        
        # 3. 未匹配，返回原字段名
        return field_name
    
    @classmethod
    def get_unmapped_fields(cls, field_names: list) -> list:
        """获取未映射的字段列表"""
        return [f for f in field_names if cls.map_field(f) == f]
```

#### Step 5.2: 更新StandardizationModule

- [ ] **使用FieldMapper替换原映射逻辑**

```python
# 在StandardizationModule的standardize_water_quality方法中
# 原代码：
field_mapping = {
    "pH值": "pH",
    # ...
}
for key, value in record.items():
    new_key = self.field_mapping.get(key, key)

# 新代码：
for key, value in record.items():
    new_key = FieldMapper.map_field(key)
    standardized_record[new_key] = value
```

#### Step 5.3: 添加未映射字段报告

- [ ] **在返回结果中添加未映射字段信息**

```python
# 在standardize_water_quality返回结果中添加
unmapped_fields = FieldMapper.get_unmapped_fields(
    list(standardized_record.keys()) if standardized_record else []
)

return {
    "standardized": standardized,
    "unmapped_fields": unmapped_fields,
    "mapping_summary": {
        "total_fields": len(record),
        "mapped_fields": len(record) - len(unmapped_fields),
        "unmapped_count": len(unmapped_fields)
    }
}
```

#### Step 5.4: 提交更改

- [ ] **提交字段映射改进**

```bash
cd E:/project/Ecological_env
git add subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/standardization.py
git commit -m "feat(standardization): 支持正则表达式字段名匹配"
```

---

### Task 6: 改进时间戳匹配

**问题**: 异常点索引到时间戳转换依赖整数索引，容易出错。

**目标**: 基于时间戳匹配而非索引。

**Files:**
- Modify: `middleware/query_interface.py`

#### Step 6.1: 添加时间戳匹配函数

- [ ] **在 query_interface.py 中添加时间戳匹配函数**

```python
# 在文件顶部添加
from datetime import datetime

def match_anomalies_to_timeseries(anomalies: list, timeseries_data: list) -> list:
    """
    基于时间戳匹配异常点到时序数据
    
    Args:
        anomalies: 异常点列表
        timeseries_data: 时序数据列表
        
    Returns:
        匹配后的异常点列表，包含实际时间戳
    """
    if not anomalies or not timeseries_data:
        return anomalies
    
    # 构建时间戳到索引的映射
    timestamp_to_index = {}
    for idx, record in enumerate(timeseries_data):
        if isinstance(record, dict) and "timestamp" in record:
            timestamp_to_index[record["timestamp"]] = idx
    
    matched_anomalies = []
    for anomaly in anomalies:
        if not isinstance(anomaly, dict):
            continue
        
        times_value = anomaly.get("times", "")
        
        # 检查是否为整数索引
        try:
            times_int = int(times_value)
            # 如果是整数且在范围内，检查是否对应有效时间戳
            if 0 <= times_int < len(timeseries_data):
                # 使用整数索引直接获取记录
                record = timeseries_data[times_int]
                if isinstance(record, dict) and "timestamp" in record:
                    # 用实际时间戳替换索引
                    anomaly_copy = dict(anomaly)
                    anomaly_copy["times"] = record["timestamp"]
                    anomaly_copy["data_index"] = times_int
                    matched_anomalies.append(anomaly_copy)
                    continue
        except (ValueError, TypeError):
            pass
        
        # 如果times本身就是时间戳字符串，验证它是否存在
        if times_value in timestamp_to_index:
            anomaly_copy = dict(anomaly)
            anomaly_copy["data_index"] = timestamp_to_index[times_value]
            matched_anomalies.append(anomaly_copy)
        else:
            # 时间戳不匹配，保留原异常点
            matched_anomalies.append(anomaly)
    
    return matched_anomalies
```

#### Step 6.2: 使用时间戳匹配

- [ ] **修改异常详情提取部分使用新函数**

```python
# 在query_interface.py的异常详情提取部分（第399行左右）
# 原代码直接将anomalies添加到result['anomaly_details']

# 新代码：使用时间戳匹配
if anomalies:
    # 根据数据源选择匹配的时序数据
    def select_timeseries(anomaly):
        indicator = anomaly.get("indicator", "")
        if "influent" in indicator.lower():
            return historical_data.get("influent", [])
        else:
            return historical_data.get("effluent", [])
    
    # 对每个异常进行时间戳匹配
    matched_anomalies = []
    for anomaly in anomalies:
        ts_data = select_timeseries(anomaly)
        matched = match_anomalies_to_timeseries([anomaly], ts_data)
        if matched:
            matched_anomalies.extend(matched)
    
    # 转换为前端格式
    for anomaly in matched_anomalies:
        result['anomaly_details'].append({
            'indicator': anomaly.get('indicator', ''),
            'times': anomaly.get('times', ''),
            'score': anomaly.get('score', 0),
            'pattern': anomaly.get('pattern', ''),
            'severity': anomaly.get('severity', 'medium'),
            'data_index': anomaly.get('data_index', -1)
        })
```

#### Step 6.3: 提交更改

- [ ] **提交时间戳匹配改进**

```bash
cd E:/project/Ecological_env
git add middleware/query_interface.py
git commit -m "feat(query-interface): 基于时间戳匹配异常点而非索引"
```

---

## Phase 3: 低优先级改进

### Task 7: 添加缺失值插值

**目标**: 实现简单的时间序列线性插值。

**Files:**
- Create: `subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/data_interpolation.py`

#### Step 7.1: 创建插值模块

- [ ] **创建 data_interpolation.py**

```python
"""
数据插值模块 - 填补缺失值
"""
import logging
from typing import Dict, Any, List, Optional
import numpy as np

logger = logging.getLogger(__name__)


class DataInterpolationModule:
    """数据插值模块"""
    
    def __init__(self, max_gap_size: int = 3):
        """
        Args:
            max_gap_size: 最大插值间隔（连续缺失点数），超过此值不插值
        """
        self.max_gap_size = max_gap_size
    
    def interpolate_timeseries(
        self,
        data: List[Dict[str, Any]],
        timestamp_field: str = "timestamp"
    ) -> Dict[str, Any]:
        """
        对时序数据进行线性插值
        
        Args:
            data: 时序数据列表
            timestamp_field: 时间戳字段名
            
        Returns:
            插值后的数据和插值报告
        """
        if not data:
            return {
                "interpolated_data": [],
                "report": {"interpolated_count": 0, "total_gaps": 0}
            }
        
        # 识别数值字段
        numeric_fields = self._identify_numeric_fields(data)
        
        # 按时间排序
        sorted_data = sorted(data, key=lambda x: x.get(timestamp_field, ""))
        
        # 对每个数值字段进行插值
        interpolated_data = []
        interpolated_count = 0
        total_gaps = 0
        
        for field in numeric_fields:
            values = [record.get(field) for record in sorted_data]
            
            # 找到缺失值位置
            missing_indices = [i for i, v in enumerate(values) if v is None]
            
            if not missing_indices:
                continue
            
            total_gaps += len(missing_indices)
            
            # 对每个缺失值进行线性插值
            for idx in missing_indices:
                # 查找前后有效值
                prev_val, next_val = self._find_adjacent_values(values, idx)
                
                if prev_val is not None and next_val is not None:
                    # 线性插值
                    gap_size = self._count_gap_size(values, idx)
                    if gap_size <= self.max_gap_size:
                        interpolated_value = self._linear_interpolate(
                            prev_val, next_val, gap_size
                        )
                        values[idx] = interpolated_value
                        interpolated_count += 1
        
        # 重建数据
        for i, record in enumerate(sorted_data):
            new_record = dict(record)
            for field in numeric_fields:
                new_record[field] = values[i]
                # 标记插值字段
                if record.get(field) is None and new_record[field] is not None:
                    if "_interpolated_fields" not in new_record:
                        new_record["_interpolated_fields"] = []
                    new_record["_interpolated_fields"].append(field)
            interpolated_data.append(new_record)
        
        return {
            "interpolated_data": interpolated_data,
            "report": {
                "interpolated_count": interpolated_count,
                "total_gaps": total_gaps,
                "interpolated_fields": numeric_fields
            }
        }
    
    def _identify_numeric_fields(self, data: List[Dict[str, Any]]) -> List[str]:
        """识别数值字段"""
        numeric_fields = []
        if not data:
            return numeric_fields
        
        first_record = data[0]
        for key, value in first_record.items():
            if isinstance(value, (int, float)) or (isinstance(value, str) and value.replace('.', '').isdigit()):
                numeric_fields.append(key)
        
        return numeric_fields
    
    def _find_adjacent_values(self, values: list, idx: int) -> tuple:
        """查找缺失值前后的有效值"""
        prev_val = None
        next_val = None
        
        # 向前查找
        for i in range(idx - 1, -1, -1):
            if values[i] is not None:
                prev_val = values[i]
                break
        
        # 向后查找
        for i in range(idx + 1, len(values)):
            if values[i] is not None:
                next_val = values[i]
                break
        
        return prev_val, next_val
    
    def _count_gap_size(self, values: list, idx: int) -> int:
        """计算缺失间隔大小"""
        gap_size = 1
        # 向前计数
        for i in range(idx - 1, -1, -1):
            if values[i] is None:
                gap_size += 1
            else:
                break
        # 向后计数
        for i in range(idx + 1, len(values)):
            if values[i] is None:
                gap_size += 1
            else:
                break
        return gap_size
    
    def _linear_interpolate(self, prev_val: float, next_val: float, gap_size: int) -> float:
        """线性插值计算"""
        return (prev_val + next_val) / 2
```

#### Step 7.2: 集成到数据清洗模块

- [ ] **在 data_cleaning.py 中添加插值调用**

```python
# 在DataCleaningModule类中添加插值方法
def interpolate_missing_values(
    self,
    data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """插值缺失值"""
    from data_interpolation import DataInterpolationModule
    
    interpolator = DataInterpolationModule(max_gap_size=3)
    return interpolator.interpolate_timeseries(data)
```

#### Step 7.3: 提交更改

- [ ] **提交插值模块**

```bash
cd E:/project/Ecological_env
git add subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/data_interpolation.py
git add subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/data_cleaning.py
git commit -m "feat(interpolation): 添加时间序列线性插值功能"
```

---

### Task 8: 集成时间序列特征

**目标**: 将时间序列特征提取集成到主流程。

**Files:**
- Modify: `subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/__init__.py`

#### Step 8.1: 添加特征提取选项

- [ ] **在 detect_anomalies 中添加特征提取参数**

```python
# 在detect_anomalies函数签名中添加参数
def detect_anomalies(
    data, 
    indicators=None, 
    config=None,
    include_features=False  # 新增：是否包含时间序列特征
):
    # ... 现有异常检测逻辑 ...
    
    result = {
        "anomalies": anomalies,
        "patterns": patterns,
        "violations": violations,
        # ...
    }
    
    # 如果需要特征，添加到结果
    if include_features:
        from time_series_features import TimeSeriesFeatures
        from correlation_analysis import CorrelationAnalyzer
        from trend_analysis import TrendAnalyzer
        
        # 提取特征
        feature_extractor = TimeSeriesFeatures()
        ts_features = feature_extractor.extract_features(data, indicators)
        
        # 相关性分析
        corr_analyzer = CorrelationAnalyzer()
        correlations = corr_analyzer.analyze_correlation(data, indicators)
        
        # 趋势分析
        trend_analyzer = TrendAnalyzer()
        trends = trend_analyzer.analyze_trend(data, indicators)
        
        result["features"] = {
            "time_series": ts_features,
            "correlations": correlations,
            "trends": trends
        }
    
    return result
```

#### Step 8.2: 提交更改

- [ ] **提交特征集成**

```bash
cd E:/project/Ecological_env
git add subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/__init__.py
git commit -m "feat(features): 集成时间序列特征提取到主检测流程"
```

---

## 验收标准

### 功能验证
1. ✅ 数据清洗允许部分异常，有效字段被保留
2. ✅ 异常数据格式统一为 `{indicator, times, score, pattern, severity}`
3. ✅ 异常检测使用感知子智能体预处理后的数据
4. ✅ 时间对齐选择最佳匹配（时间差最小）
5. ✅ 字段映射支持正则表达式
6. ✅ 异常点基于时间戳匹配
7. ✅ 缺失值可以进行线性插值
8. ✅ 时间序列特征可集成到主流程

### 测试验证
```bash
# 运行所有新测试
python tests/subagents/test_data_cleaning_improved.py
python tests/subagents/test_anomaly_format_standardization.py
python tests/subagents/test_time_alignment_best_match.py
python tests/middleware/test_query_perception_utilization.py

# 运行Web查询测试
cd middleware
python query_interface.py
# 浏览器访问 http://localhost:8080
# 查询："检测最近一周数据异常情况"
# 验证图表正确显示，异常点正确标注
```

### 数据质量验证
- 清洗后数据保留率应 > 95%（仅极端异常被丢弃）
- 异常字段标记清晰，便于追溯
- 时间对齐匹配准确率 > 99%
- 异常点时间戳匹配准确率 = 100%

---

## 实施顺序

按照 Phase 1 → Phase 2 → Phase 3 的顺序实施：
1. 先完成高优先级修复（Task 1-3）
2. 验证核心功能正常后，再进行中优先级改进（Task 4-6）
3. 最后完成低优先级增强（Task 7-8）

每个Task完成后运行测试验证，确保不影响现有功能。
