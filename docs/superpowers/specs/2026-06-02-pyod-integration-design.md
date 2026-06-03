# PyOD 异常检测算子集成设计文档

> **创建日期**: 2026-06-02
> **设计目标**: 在 anomaly-detection-agent 中集成 PyOD 库的异常检测算子
> **设计类型**: 功能扩展设计

---

## 1. 概述

本设计旨在为异常检测子智能体（anomaly-detection-agent）集成 PyOD（Python Outlier Detection）库的异常检测算子，在现有 `operator_adapter.py` 的基础上扩展支持 5 个 PyOD 算子，并提供基础的可视化功能。

**核心原则**：
- 最小化变更，保持现有架构稳定
- 接口一致性，与现有算子完全兼容
- 优雅降级，PyOD 不可用时不影响现有功能

---

## 2. 架构设计

### 2.1 架构概览

```
现有架构：
┌─────────────────────────────────────┐
│      operator_adapter.py            │
│  ┌──────────────────────────────┐  │
│  │ 现有算子                      │  │
│  │ - zscore, iqr, grubbs         │  │
│  │ - moving_average              │  │
│  │ - isolation_forest, svm       │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘

扩展后架构：
┌─────────────────────────────────────┐
│      operator_adapter.py            │
│  ┌──────────────────────────────┐  │
│  │ 现有算子（保持不变）          │  │
│  └──────────────────────────────┘  │
│  ┌──────────────────────────────┐  │
│  │ PyOD 算子（新增）             │  │
│  │ - HBOS, ECOD                 │  │
│  │ - KNN, LOF, ABOD             │  │
│  └──────────────────────────────┘  │
│  ┌──────────────────────────────┐  │
│  │ 可视化方法（新增）            │  │
│  │ - plot_anomalies()           │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

### 2.2 接口设计

所有 PyOD 算子保持与现有算子一致的接口：

```python
def _pyod_operator_anomaly(self, series: pd.Series,
                           contamination: float = 0.1,
                           **kwargs) -> tuple:
    """
    PyOD 算子通用接口

    Returns:
        (scores, anomaly_mask): 异常分数和异常掩码
        - scores: np.ndarray, 异常分数数组
        - anomaly_mask: np.ndarray[bool], True 表示异常
    """
```

---

## 3. PyOD 算子详细设计

### 3.1 算子列表

| 算子 | 全称 | 类型 | 核心参数 | 适用场景 |
|------|------|------|----------|----------|
| **HBOS** | Histogram-based Outlier Score | 统计类 | `n_bins=10`, `contamination=0.1` | 快速检测，适合大数据 |
| **ECOD** | Empirical Cumulative Distribution | 统计类 | `contamination=0.1` | 无参数敏感，稳定 |
| **KNN** | K-Nearest Neighbors | 距离类 | `n_neighbors=5`, `contamination=0.1` | 局部异常检测 |
| **LOF** | Local Outlier Factor | 密度类 | `n_neighbors=20`, `contamination=0.1` | 密度异常检测 |
| **ABOD** | Angle-Based Outlier Detection | 角度类 | `contamination=0.1` | 高维数据效果好 |

### 3.2 代码结构

在 `operator_adapter.py` 的 `OperatorAdapter` 类中新增：

```python
# 算子注册（在 __init__ 中扩展）
self.operators.update({
    "hbos": self._hbos_anomaly,
    "ecod": self._ecod_anomaly,
    "knn": self._knn_anomaly,
    "lof": self._lof_anomaly,
    "abod": self._abod_anomaly,
})

# PyOD 算子私有方法
def _hbos_anomaly(self, series, contamination=0.1) -> tuple
def _ecod_anomaly(self, series, contamination=0.1) -> tuple
def _knn_anomaly(self, series, n_neighbors=5, contamination=0.1) -> tuple
def _lof_anomaly(self, series, n_neighbors=20, contamination=0.1) -> tuple
def _abod_anomaly(self, series, contamination=0.1) -> tuple
```

---

## 4. 数据流设计

### 4.1 处理流程

```
输入数据 (DataFrame)
        ↓
选择指标 + 算子
        ↓
┌───────────────────────────────────┐
│  operator_adapter.apply_operators() │
├───────────────────────────────────┤
│ 算子循环：                         │
│  ├─ 现有算子 (zscore, iqr...)     │
│  └─ PyOD 算子 (hbos, ecod...)     │
├───────────────────────────────────┤
│ 每个算子返回：                     │
│  {                                │
│    "scores": [...],               │
│    "anomalies": [...],            │
│    "anomaly_count": 5,            │
│    "anomaly_rate": 0.05           │
│  }                                │
└───────────────────────────────────┘
        ↓
返回完整结果字典
```

### 4.2 可视化设计

**新增可视化方法**：

```python
def plot_anomalies(self,
                   series: pd.Series,
                   anomaly_mask: np.ndarray,
                   operator_name: str,
                   indicator_name: str,
                   save_path: Optional[str] = None) -> str:
    """
    绘制异常检测结果可视化

    Args:
        series: 原始数据序列
        anomaly_mask: 异常掩码（True=异常）
        operator_name: 算子名称
        indicator_name: 指标名称
        save_path: 保存路径（可选）

    Returns:
        图片保存路径或 base64 编码
    """
```

**可视化输出**：
- 时序图：原始数据曲线
- 异常标记：红点标出异常时刻
- 图例说明：算子名称、指标名称
- 返回：图片保存路径或 base64 编码

---

## 5. 错误处理

### 5.1 依赖检测

```python
# 模块级依赖检测
try:
    from pyod.models.hbos import HBOS
    from pyod.models.ecod import ECOD
    from pyod.models.knn import KNN
    from pyod.models.lof import LOF
    from pyod.models.abod import ABOD
    PYOD_AVAILABLE = True
except ImportError:
    PYOD_AVAILABLE = False
    logger.warning("[ADAPTER] PyOD 库不可用，PyOD 算子将被跳过")
```

### 5.2 降级策略

| 情况 | 处理方式 |
|------|----------|
| PyOD 不可用 | PyOD 算子注册为空，不影响现有算子 |
| 调用 PyOD 算子但库不可用 | 记录警告，返回空结果 |
| 查询可用算子 | PyOD 算子返回空列表 |

### 5.3 数据边界情况

| 情况 | 处理方式 |
|------|----------|
| 数据量 < 最小样本数 | 返回全零分数，记录警告 |
| 数据全为 NaN | 返回空结果，错误提示 |
| 单一值数据 | 返回全零分数，记录警告 |
| PyOD 算法失败 | 降级到 zscore，记录警告 |

### 5.4 可视化边界

| 情况 | 处理方式 |
|------|----------|
| 无异常点 | 正常绘图，无红点标记 |
| matplotlib 不可用 | 返回错误信息 |
| 保存路径无效 | 返回 base64 编码 |

---

## 6. 测试策略

### 6.1 单元测试

| 测试用例 | 描述 | 预期结果 |
|----------|------|----------|
| `test_pyod_available` | PyOD 可用时正常注册 | `get_available_operators()` 包含 PyOD 算子 |
| `test_pyod_unavailable` | PyOD 不可用时优雅降级 | 不影响现有算子，返回空列表 |
| `test_hbos_anomaly` | HBOS 算子检测异常 | 返回正确分数和异常掩码 |
| `test_ecod_anomaly` | ECOD 算子检测异常 | 返回正确分数和异常掩码 |
| `test_knn_anomaly` | KNN 算子检测异常 | 返回正确分数和异常掩码 |
| `test_lof_anomaly` | LOF 算子检测异常 | 返回正确分数和异常掩码 |
| `test_abod_anomaly` | ABOD 算子检测异常 | 返回正确分数和异常掩码 |
| `test_plot_anomalies` | 可视化功能正常 | 返回有效图片路径或 base64 |
| `test_small_data` | 小样本数据边界情况 | 正常处理或返回默认值 |
| `test_nan_data` | NaN 数据边界情况 | 正确处理或返回错误 |

### 6.2 集成测试

- 使用真实废水监测数据测试 PyOD 算子
- 验证与现有算子的接口一致性
- 验证可视化输出

---

## 7. 文件变更清单

| 文件路径 | 变更类型 | 说明 |
|----------|----------|------|
| `subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py` | 修改 | 添加 PyOD 算子和可视化方法 |
| `requirements.txt` | 修改 | 添加 pyod 依赖 |
| `subagents/anomaly-detection-agent/skills/anomaly-detection-core/tests/test_operator_adapter.py` | 新增/修改 | 扩展测试覆盖 PyOD 算子 |

---

## 8. 实施计划概要

1. 安装 PyOD 库
2. 修改 `operator_adapter.py`：
   - 添加 PyOD 依赖检测
   - 实现 5 个 PyOD 算子方法
   - 添加可视化方法
   - 更新算子注册逻辑
3. 编写单元测试
4. 使用真实数据验证
5. 更新文档

---

## 9. 验收标准

完成后应满足：
- ✅ PyOD 算子可正常调用并返回正确结果
- ✅ PyOD 不可用时不影响现有功能
- ✅ 可视化功能正常输出
- ✅ 所有测试通过
- ✅ 代码通过自检和代码审查
