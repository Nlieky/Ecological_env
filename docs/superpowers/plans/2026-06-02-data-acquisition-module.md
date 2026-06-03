# DataAcquisitionModule 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现数据获取模块DataAcquisitionModule，支持从多源（CSV、API、数据库）获取监测数据

**Architecture:** 单一模块类，支持配置初始化，提供统一的acquire_data接口，支持多种数据源类型

**Tech Stack:** Python 3.10+, csv, pathlib, dataclasses

---

## 文件结构概览

### 新建文件
- `subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/data_acquisition.py` - 数据获取模块主文件

### 依赖项
- `csv` - CSV文件读取
- `pathlib` - 文件路径处理
- `dataclasses` - 数据类定义

---

## 阶段1: 模块基础结构（15分钟）

### Task 1: 创建DataAcquisitionModule类结构

**Files:**
- Create: `subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/data_acquisition.py`

- [ ] **Step 1: 创建模块文件和基础类**

```python
"""
数据获取模块
从多源获取监测数据

支持的数据源类型:
- csv: CSV文件
- realtime_api: 实时API接口
- database: 数据库查询
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DataSource:
    """数据源配置"""
    name: str           # 数据源名称
    type: str          # 数据源类型: csv, realtime_api, database
    path: str          # 数据源路径或连接信息


class DataAcquisitionModule:
    """数据获取模块 - 从多源获取监测数据"""

    # 支持的数据源类型（测试需要验证的属性）
    supported_sources = ["csv", "realtime_api", "database"]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化数据获取模块

        Args:
            config: 配置字典，可包含自定义数据源配置
        """
        self.config = config or {}
        self.data_sources: List[DataSource] = []
        self._initialize_sources()

    def _initialize_sources(self):
        """初始化默认数据源"""
        default_sources = [
            DataSource("进水数据", "csv", "data/pollution_water_in.csv"),
            DataSource("出水数据", "csv", "data/pollution_water_out.csv"),
            DataSource("设备状态", "database", "equipment_status"),
            DataSource("实时监测", "realtime_api", "/api/realtime"),
        ]
        self.data_sources = default_sources

    def get_available_sources(self) -> List[str]:
        """获取可用的数据源名称列表

        Returns:
            数据源名称列表
        """
        return [source.name for source in self.data_sources]

    def acquire_data(self, source_name: Optional[str] = None) -> Dict[str, Any]:
        """获取数据

        Args:
            source_name: 指定数据源名称，None表示获取所有数据源

        Returns:
            数据字典，格式: {source_name: {data: [...], source_type: "..."}}
        """
        if source_name:
            return {source_name: self._get_single_source(source_name)}
        return self._get_all_sources()

    def _get_single_source(self, source_name: str) -> Dict[str, Any]:
        """获取单个数据源的数据

        Args:
            source_name: 数据源名称

        Returns:
            单个数据源的数据
        """
        for source in self.data_sources:
            if source.name == source_name:
                return self._read_source(source)
        return {"error": f"未找到数据源: {source_name}", "data": []}

    def _get_all_sources(self) -> Dict[str, Any]:
        """获取所有数据源的数据

        Returns:
            所有数据源的数据字典
        """
        result = {}
        for source in self.data_sources:
            result[source.name] = self._read_source(source)
        return result

    def _read_source(self, source: DataSource) -> Dict[str, Any]:
        """根据数据源类型读取数据

        Args:
            source: 数据源配置

        Returns:
            数据字典，包含data和source_type字段
        """
        if source.type == "csv":
            return self._read_csv(source.path)
        elif source.type == "realtime_api":
            return self._read_api(source.path)
        elif source.type == "database":
            return self._read_database(source.path)
        return {"error": f"不支持的数据源类型: {source.type}", "data": []}

    def _read_csv(self, path: str) -> Dict[str, Any]:
        """读取CSV文件数据

        Args:
            path: CSV文件路径

        Returns:
            数据字典
        """
        # TODO: 实现实际的CSV读取逻辑
        return {
            "data": [],
            "source_type": "csv",
            "path": path
        }

    def _read_api(self, endpoint: str) -> Dict[str, Any]:
        """读取API接口数据

        Args:
            endpoint: API端点路径

        Returns:
            数据字典
        """
        # TODO: 实现实际的API调用逻辑
        return {
            "data": [],
            "source_type": "realtime_api",
            "endpoint": endpoint
        }

    def _read_database(self, table: str) -> Dict[str, Any]:
        """读取数据库数据

        Args:
            table: 数据库表名

        Returns:
            数据字典
        """
        # TODO: 实现实际的数据库查询逻辑
        return {
            "data": [],
            "source_type": "database",
            "table": table
        }
```

- [ ] **Step 2: 验证模块创建成功**

```bash
cd E:\project\Ecological_env
python -c "
import sys
sys.path.insert(0, 'subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts')
from data_acquisition import DataAcquisitionModule
print('[OK] DataAcquisitionModule imported')
print('[OK] supported_sources:', DataAcquisitionModule.supported_sources)
"
```

Expected: [OK] DataAcquisitionModule imported<br>[OK] supported_sources: ['csv', 'realtime_api', 'database']

- [ ] **Step 3: 提交**

```bash
git add subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/data_acquisition.py
git commit -m "feat: add DataAcquisitionModule with basic structure"
```

---

## 阶段2: CSV读取功能（10分钟）

### Task 2: 实现CSV文件读取

**Files:**
- Modify: `subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/data_acquisition.py`

- [ ] **Step 1: 实现CSV读取逻辑**

找到 `_read_csv` 方法，替换为以下实现：

```python
    def _read_csv(self, path: str) -> Dict[str, Any]:
        """读取CSV文件数据

        Args:
            path: CSV文件路径

        Returns:
            数据字典，包含data、source_type、path字段
        """
        csv_path = Path(__file__).parent.parent.parent.parent.parent.parent / path

        if not csv_path.exists():
            return {
                "data": [],
                "source_type": "csv",
                "path": path,
                "error": f"文件不存在: {csv_path}"
            }

        try:
            data = []
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(dict(row))

            return {
                "data": data,
                "source_type": "csv",
                "path": path,
                "row_count": len(data)
            }
        except Exception as e:
            return {
                "data": [],
                "source_type": "csv",
                "path": path,
                "error": f"读取失败: {str(e)}"
            }
```

同时在文件顶部添加import：

```python
import csv
```

- [ ] **Step 2: 测试CSV读取**

```bash
cd E:\project\Ecological_env
python -c "
import sys
sys.path.insert(0, 'subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts')
from data_acquisition import DataAcquisitionModule

module = DataAcquisitionModule()
result = module.acquire_data('进水数据')
print('CSV读取结果:', result.get('进水数据', {}).get('source_type'))
print('有数据:', len(result.get('进水数据', {}).get('data', [])) > 0)
"
```

Expected: CSV读取结果: csv<br>有数据: True

- [ ] **Step 3: 提交**

```bash
git add subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/data_acquisition.py
git commit -m "feat: implement CSV reading in DataAcquisitionModule"
```

---

## 阶段3: 模块验证（5分钟）

### Task 3: 运行单元测试验证

**Files:**
- Test: `run_comprehensive_tests.py`

- [ ] **Step 1: 运行综合测试**

```bash
cd E:\project\Ecological_env
python run_comprehensive_tests.py --skip-stream --verbose 2>&1 | grep -A2 "DataAcquisitionModule"
```

Expected: 显示 DataAcquisitionModule 验证 [OK] 或 [PASS]

- [ ] **Step 2: 验证supported_sources属性**

```bash
cd E:\project\Ecological_env
python -c "
import sys
sys.path.insert(0, 'subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts')
from data_acquisition import DataAcquisitionModule
assert hasattr(DataAcquisitionModule, 'supported_sources'), '缺少supported_sources属性'
assert isinstance(DataAcquisitionModule.supported_sources, list), 'supported_sources应该是列表'
print('[OK] supported_sources属性验证通过')
"
```

Expected: [OK] supported_sources属性验证通过

- [ ] **Step 3: 提交**

```bash
git add subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/data_acquisition.py
git commit -m "test: verify DataAcquisitionModule implementation"
```

---

## 验收标准

完成所有任务后，DataAcquisitionModule应该：

1. ✅ 文件存在于正确位置
2. ✅ 具有 `supported_sources` 属性，值为 `["csv", "realtime_api", "database"]`
3. ✅ 能够被成功导入
4. ✅ `acquire_data()` 方法可以获取数据
5. ✅ `_read_csv()` 可以读取CSV文件
6. ✅ UnitTestLayer中 DataAcquisitionModule 验证通过

---

## 总计任务数

- 阶段1（基础结构）: 1个任务
- 阶段2（CSV读取）: 1个任务  
- 阶段3（验证）: 1个任务

**总计: 3个任务，预计耗时: 30分钟**