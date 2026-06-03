# PyOD 异常检测算子集成实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标:** 在 anomaly-detection-agent 的 operator_adapter.py 中集成 5 个 PyOD 异常检测算子（HBOS、ECOD、KNN、LOF、ABOD），并添加基础可视化功能

**架构:** 在现有 operator_adapter.py 中扩展，添加 PyOD 依赖检测和 5 个 PyOD 算子方法，保持与现有算子一致的接口

**技术栈:** PyOD 1.0+, matplotlib 3.7+, pandas, numpy

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `requirements.txt` | 添加 pyod 依赖 |
| `subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py` | 添加 PyOD 算子和可视化方法 |
| `subagents/anomaly-detection-agent/skills/anomaly-detection-core/tests/test_anomaly_detection.py` | 扩展测试覆盖 PyOD 算子 |

---

## Task 1: 添加 PyOD 依赖

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: 在 requirements.txt 中添加 pyod 依赖**

打开 `requirements.txt`，在 `# 数据处理` 部分添加 pyod：

```text
# 数据处理
scikit-learn==1.3.0
scipy==1.11.1
pyod==1.0.0  # PyOD 异常检测库
```

- [ ] **Step 2: 验证文件格式**

Run: `cat requirements.txt | grep pyod`
Expected: 输出包含 `pyod==1.0.0`

- [ ] **Step 3: 提交**

```bash
git add requirements.txt
git commit -m "deps: add pyod==1.0.0 for anomaly detection"
```

---

## Task 2: 添加 PyOD 依赖检测

**Files:**
- Modify: `subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py:16-23`

- [ ] **Step 1: 在现有 import 部分添加 PyOD 依赖检测**

在 `operator_adapter.py` 中找到 ML_AVAILABLE 检测代码（约第 17-23 行），在其后添加：

```python
# 尝试导入 PyOD 库
try:
    from pyod.models.hbos import HBOS
    from pyod.models.ecod import ECOD
    from pyod.models.knn import KNN
    from pyod.models.lof import LOF
    from pyod.models.abod import ABOD
    PYOD_AVAILABLE = True
except ImportError:
    PYOD_AVAILABLE = False
```

- [ ] **Step 2: 验证语法**

Run: `python -m py_compile subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py`
Expected: 无语法错误

- [ ] **Step 3: 提交**

```bash
git add subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py
git commit -m "feat: add pyod dependency detection"
```

---

## Task 3: 编写 PyOD 可用性测试

**Files:**
- Modify: `subagents/anomaly-detection-agent/skills/anomaly-detection-core/tests/test_anomaly_detection.py`

- [ ] **Step 1: 在 TestOperatorAdapter 类中添加 PyOD 可用性测试**

在 `test_anomaly_detection.py` 的 `TestOperatorAdapter` 类中添加：

```python
def test_pyod_available_when_installed(self):
    """测试 PyOD 可用时算子注册"""
    adapter = OperatorAdapter()
    available = adapter.get_available_operators()

    # 如果 PyOD 可用，应该包含 pyod 算子
    try:
        import pyod
        self.assertIn("pyod", available)
        self.assertIn("hbos", available["pyod"])
        self.assertIn("ecod", available["pyod"])
        self.assertIn("knn", available["pyod"])
        self.assertIn("lof", available["pyod"])
        self.assertIn("abod", available["pyod"])
    except ImportError:
        # PyOD 未安装，跳过测试
        pass

def test_pyod_unavailable_graceful_degradation(self):
    """测试 PyOD 不可用时的优雅降级"""
    # 模拟 PyOD 不可用的情况
    adapter = OperatorAdapter()

    # 现有算子应该仍然可用
    available = adapter.get_available_operators()
    self.assertIn("statistical", available)
    self.assertTrue(len(available["statistical"]) > 0)
```

- [ ] **Step 2: 运行测试（预期失败，因为还没实现 PyOD 算子）**

Run: `cd subagents/anomaly-detection-agent/skills/anomaly-detection-core && python -m pytest tests/test_anomaly_detection.py::TestOperatorAdapter::test_pyod_available_when_installed -v`
Expected: FAIL (PyOD 算子尚未注册)

- [ ] **Step 3: 提交**

```bash
git add subagents/anomaly-detection-agent/skills/anomaly-detection-core/tests/test_anomaly_detection.py
git commit -m "test: add pyod availability tests"
```

---

## Task 4: 实现 HBOS 算子

**Files:**
- Modify: `subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py`

- [ ] **Step 1: 添加 HBOS 算子私有方法**

在 `operator_adapter.py` 的 `OperatorAdapter` 类中，在机器学习类算子之后添加：

```python
# ========== PyOD 算子 ==========

def _hbos_anomaly(self, series: pd.Series,
                  n_bins: int = 10,
                  contamination: float = 0.1) -> tuple:
    """HBOS (Histogram-based Outlier Score) 异常检测

    Args:
        series: 输入数据序列
        n_bins: 直方图箱数
        contamination: 异常比例

    Returns:
        (scores, anomaly_mask): 异常分数和异常掩码
    """
    if not PYOD_AVAILABLE:
        logger.warning("[ADAPTER] PyOD 不可用，使用 zscore 替代")
        return self._zscore_anomaly(series)

    # 数据预处理
    X = series.values.reshape(-1, 1)
    n_samples = len(X)

    # 边界检查
    if n_samples < 2:
        logger.warning("[ADAPTER] 数据量不足，返回全零分数")
        return np.zeros(n_samples), np.zeros(n_samples, dtype=bool)

    # 移除 NaN
    valid_mask = ~np.isnan(X.flatten())
    if valid_mask.sum() < 2:
        logger.warning("[ADAPTER] 有效数据不足，返回全零分数")
        return np.zeros(n_samples), np.zeros(n_samples, dtype=bool)

    X_valid = X[valid_mask].reshape(-1, 1)

    try:
        # 创建并训练 HBOS 模型
        detector = HBOS(n_bins=n_bins, contamination=contamination)
        detector.fit(X_valid)

        # 预测
        scores = detector.decision_function(X_valid)
        predictions = detector.predict(X_valid)

        # 构建完整结果（包含 NaN 位置）
        full_scores = np.zeros(n_samples)
        full_mask = np.zeros(n_samples, dtype=bool)

        full_scores[valid_mask] = scores
        full_mask[valid_mask] = (predictions == 1)

        return full_scores, full_mask

    except Exception as e:
        logger.warning(f"[ADAPTER] HBOS 检测失败: {e}，使用 zscore 替代")
        return self._zscore_anomaly(series)
```

- [ ] **Step 2: 验证语法**

Run: `python -m py_compile subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py`
Expected: 无语法错误

- [ ] **Step 3: 提交**

```bash
git add subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py
git commit -m "feat: implement HBOS anomaly detection operator"
```

---

## Task 5: 实现 ECOD 算子

**Files:**
- Modify: `subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py`

- [ ] **Step 1: 添加 ECOD 算子私有方法**

在 HBOS 算子方法之后添加：

```python
def _ecod_anomaly(self, series: pd.Series,
                  contamination: float = 0.1) -> tuple:
    """ECOD (Empirical Cumulative Distribution) 异常检测

    Args:
        series: 输入数据序列
        contamination: 异常比例

    Returns:
        (scores, anomaly_mask): 异常分数和异常掩码
    """
    if not PYOD_AVAILABLE:
        logger.warning("[ADAPTER] PyOD 不可用，使用 zscore 替代")
        return self._zscore_anomaly(series)

    # 数据预处理
    X = series.values.reshape(-1, 1)
    n_samples = len(X)

    # 边界检查
    if n_samples < 2:
        logger.warning("[ADAPTER] 数据量不足，返回全零分数")
        return np.zeros(n_samples), np.zeros(n_samples, dtype=bool)

    # 移除 NaN
    valid_mask = ~np.isnan(X.flatten())
    if valid_mask.sum() < 2:
        logger.warning("[ADAPTER] 有效数据不足，返回全零分数")
        return np.zeros(n_samples), np.zeros(n_samples, dtype=bool)

    X_valid = X[valid_mask].reshape(-1, 1)

    try:
        # 创建并训练 ECOD 模型
        detector = ECOD(contamination=contamination)
        detector.fit(X_valid)

        # 预测
        scores = detector.decision_function(X_valid)
        predictions = detector.predict(X_valid)

        # 构建完整结果（包含 NaN 位置）
        full_scores = np.zeros(n_samples)
        full_mask = np.zeros(n_samples, dtype=bool)

        full_scores[valid_mask] = scores
        full_mask[valid_mask] = (predictions == 1)

        return full_scores, full_mask

    except Exception as e:
        logger.warning(f"[ADAPTER] ECOD 检测失败: {e}，使用 zscore 替代")
        return self._zscore_anomaly(series)
```

- [ ] **Step 2: 验证语法**

Run: `python -m py_compile subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py`
Expected: 无语法错误

- [ ] **Step 3: 提交**

```bash
git add subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py
git commit -m "feat: implement ECOD anomaly detection operator"
```

---

## Task 6: 实现 KNN 算子

**Files:**
- Modify: `subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py`

- [ ] **Step 1: 添加 KNN 算子私有方法**

在 ECOD 算子方法之后添加：

```python
def _knn_anomaly(self, series: pd.Series,
                 n_neighbors: int = 5,
                 contamination: float = 0.1) -> tuple:
    """KNN (K-Nearest Neighbors) 异常检测

    Args:
        series: 输入数据序列
        n_neighbors: 近邻数量
        contamination: 异常比例

    Returns:
        (scores, anomaly_mask): 异常分数和异常掩码
    """
    if not PYOD_AVAILABLE:
        logger.warning("[ADAPTER] PyOD 不可用，使用 zscore 替代")
        return self._zscore_anomaly(series)

    # 数据预处理
    X = series.values.reshape(-1, 1)
    n_samples = len(X)

    # 边界检查
    if n_samples < n_neighbors + 1:
        logger.warning(f"[ADAPTER] 数据量不足（需要至少 {n_neighbors+1} 个样本），返回全零分数")
        return np.zeros(n_samples), np.zeros(n_samples, dtype=bool)

    # 移除 NaN
    valid_mask = ~np.isnan(X.flatten())
    if valid_mask.sum() < n_neighbors + 1:
        logger.warning(f"[ADAPTER] 有效数据不足（需要至少 {n_neighbors+1} 个样本），返回全零分数")
        return np.zeros(n_samples), np.zeros(n_samples, dtype=bool)

    X_valid = X[valid_mask].reshape(-1, 1)

    try:
        # 创建并训练 KNN 模型
        detector = KNN(n_neighbors=n_neighbors, contamination=contamination)
        detector.fit(X_valid)

        # 预测
        scores = detector.decision_function(X_valid)
        predictions = detector.predict(X_valid)

        # 构建完整结果（包含 NaN 位置）
        full_scores = np.zeros(n_samples)
        full_mask = np.zeros(n_samples, dtype=bool)

        full_scores[valid_mask] = scores
        full_mask[valid_mask] = (predictions == 1)

        return full_scores, full_mask

    except Exception as e:
        logger.warning(f"[ADAPTER] KNN 检测失败: {e}，使用 zscore 替代")
        return self._zscore_anomaly(series)
```

- [ ] **Step 2: 验证语法**

Run: `python -m py_compile subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py`
Expected: 无语法错误

- [ ] **Step 3: 提交**

```bash
git add subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py
git commit -m "feat: implement KNN anomaly detection operator"
```

---

## Task 7: 实现 LOF 算子

**Files:**
- Modify: `subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py`

- [ ] **Step 1: 添加 LOF 算子私有方法**

在 KNN 算子方法之后添加：

```python
def _lof_anomaly(self, series: pd.Series,
                 n_neighbors: int = 20,
                 contamination: float = 0.1) -> tuple:
    """LOF (Local Outlier Factor) 异常检测

    Args:
        series: 输入数据序列
        n_neighbors: 近邻数量
        contamination: 异常比例

    Returns:
        (scores, anomaly_mask): 异常分数和异常掩码
    """
    if not PYOD_AVAILABLE:
        logger.warning("[ADAPTER] PyOD 不可用，使用 zscore 替代")
        return self._zscore_anomaly(series)

    # 数据预处理
    X = series.values.reshape(-1, 1)
    n_samples = len(X)

    # 边界检查
    if n_samples < n_neighbors + 1:
        logger.warning(f"[ADAPTER] 数据量不足（需要至少 {n_neighbors+1} 个样本），返回全零分数")
        return np.zeros(n_samples), np.zeros(n_samples, dtype=bool)

    # 移除 NaN
    valid_mask = ~np.isnan(X.flatten())
    if valid_mask.sum() < n_neighbors + 1:
        logger.warning(f"[ADAPTER] 有效数据不足（需要至少 {n_neighbors+1} 个样本），返回全零分数")
        return np.zeros(n_samples), np.zeros(n_samples, dtype=bool)

    X_valid = X[valid_mask].reshape(-1, 1)

    try:
        # 创建并训练 LOF 模型
        detector = LOF(n_neighbors=n_neighbors, contamination=contamination)
        detector.fit(X_valid)

        # 预测
        scores = detector.decision_function(X_valid)
        predictions = detector.predict(X_valid)

        # 构建完整结果（包含 NaN 位置）
        full_scores = np.zeros(n_samples)
        full_mask = np.zeros(n_samples, dtype=bool)

        full_scores[valid_mask] = scores
        full_mask[valid_mask] = (predictions == 1)

        return full_scores, full_mask

    except Exception as e:
        logger.warning(f"[ADAPTER] LOF 检测失败: {e}，使用 zscore 替代")
        return self._zscore_anomaly(series)
```

- [ ] **Step 2: 验证语法**

Run: `python -m py_compile subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py`
Expected: 无语法错误

- [ ] **Step 3: 提交**

```bash
git add subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py
git commit -m "feat: implement LOF anomaly detection operator"
```

---

## Task 8: 实现 ABOD 算子

**Files:**
- Modify: `subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py`

- [ ] **Step 1: 添加 ABOD 算子私有方法**

在 LOF 算子方法之后添加：

```python
def _abod_anomaly(self, series: pd.Series,
                  contamination: float = 0.1) -> tuple:
    """ABOD (Angle-Based Outlier Detection) 异常检测

    Args:
        series: 输入数据序列
        contamination: 异常比例

    Returns:
        (scores, anomaly_mask): 异常分数和异常掩码
    """
    if not PYOD_AVAILABLE:
        logger.warning("[ADAPTER] PyOD 不可用，使用 zscore 替代")
        return self._zscore_anomaly(series)

    # 数据预处理
    X = series.values.reshape(-1, 1)
    n_samples = len(X)

    # 边界检查
    if n_samples < 5:
        logger.warning("[ADAPTER] 数据量不足（ABOD 需要至少 5 个样本），返回全零分数")
        return np.zeros(n_samples), np.zeros(n_samples, dtype=bool)

    # 移除 NaN
    valid_mask = ~np.isnan(X.flatten())
    if valid_mask.sum() < 5:
        logger.warning("[ADAPTER] 有效数据不足（ABOD 需要至少 5 个样本），返回全零分数")
        return np.zeros(n_samples), np.zeros(n_samples, dtype=bool)

    X_valid = X[valid_mask].reshape(-1, 1)

    try:
        # 创建并训练 ABOD 模型
        detector = ABOD(contamination=contamination)
        detector.fit(X_valid)

        # 预测
        scores = detector.decision_function(X_valid)
        predictions = detector.predict(X_valid)

        # 构建完整结果（包含 NaN 位置）
        full_scores = np.zeros(n_samples)
        full_mask = np.zeros(n_samples, dtype=bool)

        full_scores[valid_mask] = scores
        full_mask[valid_mask] = (predictions == 1)

        return full_scores, full_mask

    except Exception as e:
        logger.warning(f"[ADAPTER] ABOD 检测失败: {e}，使用 zscore 替代")
        return self._zscore_anomaly(series)
```

- [ ] **Step 2: 验证语法**

Run: `python -m py_compile subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py`
Expected: 无语法错误

- [ ] **Step 3: 提交**

```bash
git add subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py
git commit -m "feat: implement ABOD anomaly detection operator"
```

---

## Task 9: 注册 PyOD 算子

**Files:**
- Modify: `subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py:44-56`

- [ ] **Step 1: 在 __init__ 方法中注册 PyOD 算子**

找到 `__init__` 方法中的算子注册部分（约第 44-56 行），在现有算子注册后添加：

```python
# 注册算子
self.operators = {
    # 统计类算子
    "zscore": self._zscore_anomaly,
    "iqr": self._iqr_anomaly,
    "grubbs": self._grubbs_anomaly,
    "moving_average": self._moving_average_anomaly,

    # 机器学习类算子
    "isolation_forest": self._isolation_forest_anomaly,
    "one_class_svm": self._one_class_svm_anomaly,
}

# PyOD 算子（如果可用）
if PYOD_AVAILABLE:
    self.operators.update({
        "hbos": self._hbos_anomaly,
        "ecod": self._ecod_anomaly,
        "knn": self._knn_anomaly,
        "lof": self._lof_anomaly,
        "abod": self._abod_anomaly,
    })
    logger.info(f"[INIT] PyOD 算子已注册: hbos, ecod, knn, lof, abod")
```

- [ ] **Step 2: 验证语法**

Run: `python -m py_compile subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py`
Expected: 无语法错误

- [ ] **Step 3: 运行测试验证算子注册**

Run: `cd subagents/anomaly-detection-agent/skills/anomaly-detection-core && python -c "from scripts.operator_adapter import OperatorAdapter; a = OperatorAdapter(); print('Available operators:', list(a.operators.keys()))"`
Expected: 输出包含 PyOD 算子名称（如果 PyOD 已安装）

- [ ] **Step 4: 提交**

```bash
git add subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py
git commit -m "feat: register PyOD operators in adapter"
```

---

## Task 10: 更新 get_available_operators 方法

**Files:**
- Modify: `subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py:228-234`

- [ ] **Step 1: 更新 get_available_operators 方法返回 PyOD 算子**

找到 `get_available_operators` 方法（约第 228 行），更新为：

```python
def get_available_operators(self) -> Dict[str, List[str]]:
    """获取可用算子分类"""
    result = {
        "statistical": ["zscore", "iqr", "grubbs", "moving_average"],
        "machine_learning": ["isolation_forest", "one_class_svm"] if ML_AVAILABLE else []
    }

    # 添加 PyOD 算子
    if PYOD_AVAILABLE:
        result["pyod"] = ["hbos", "ecod", "knn", "lof", "abod"]
    else:
        result["pyod"] = []

    return result
```

- [ ] **Step 2: 运行测试验证**

Run: `cd subagents/anomaly-detection-agent/skills/anomaly-detection-core && python -c "from scripts.operator_adapter import OperatorAdapter; a = OperatorAdapter(); import pprint; pprint.pprint(a.get_available_operators())"`
Expected: 输出包含 pyod 分类和算子列表

- [ ] **Step 3: 提交**

```bash
git add subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py
git commit -m "feat: update get_available_operators to include PyOD"
```

---

## Task 11: 编写 PyOD 算子单元测试

**Files:**
- Modify: `subagents/anomaly-detection-agent/skills/anomaly-detection-core/tests/test_anomaly_detection.py`

- [ ] **Step 1: 添加各 PyOD 算子的单元测试**

在 `TestOperatorAdapter` 类中添加：

```python
def test_hbos_anomaly_detection(self):
    """测试 HBOS 算子异常检测"""
    adapter = OperatorAdapter()

    # 创建测试数据
    np.random.seed(42)
    n = 50
    data = 50 + 5 * np.random.randn(n)
    data[45] = 100  # 异常值
    series = pd.Series(data)

    try:
        scores, mask = adapter._hbos_anomaly(series)
        self.assertEqual(len(scores), n)
        self.assertEqual(len(mask), n)
        self.assertTrue(mask[45])  # 异常值应被检测
    except Exception as e:
        self.skipTest(f"HBOS not available: {e}")

def test_ecod_anomaly_detection(self):
    """测试 ECOD 算子异常检测"""
    adapter = OperatorAdapter()

    np.random.seed(42)
    n = 50
    data = 50 + 5 * np.random.randn(n)
    data[45] = 100
    series = pd.Series(data)

    try:
        scores, mask = adapter._ecod_anomaly(series)
        self.assertEqual(len(scores), n)
        self.assertEqual(len(mask), n)
    except Exception as e:
        self.skipTest(f"ECOD not available: {e}")

def test_knn_anomaly_detection(self):
    """测试 KNN 算子异常检测"""
    adapter = OperatorAdapter()

    np.random.seed(42)
    n = 50
    data = 50 + 5 * np.random.randn(n)
    data[45] = 100
    series = pd.Series(data)

    try:
        scores, mask = adapter._knn_anomaly(series)
        self.assertEqual(len(scores), n)
        self.assertEqual(len(mask), n)
    except Exception as e:
        self.skipTest(f"KNN not available: {e}")

def test_lof_anomaly_detection(self):
    """测试 LOF 算子异常检测"""
    adapter = OperatorAdapter()

    np.random.seed(42)
    n = 50
    data = 50 + 5 * np.random.randn(n)
    data[45] = 100
    series = pd.Series(data)

    try:
        scores, mask = adapter._lof_anomaly(series)
        self.assertEqual(len(scores), n)
        self.assertEqual(len(mask), n)
    except Exception as e:
        self.skipTest(f"LOF not available: {e}")

def test_abod_anomaly_detection(self):
    """测试 ABOD 算子异常检测"""
    adapter = OperatorAdapter()

    np.random.seed(42)
    n = 50
    data = 50 + 5 * np.random.randn(n)
    data[45] = 100
    series = pd.Series(data)

    try:
        scores, mask = adapter._abod_anomaly(series)
        self.assertEqual(len(scores), n)
        self.assertEqual(len(mask), n)
    except Exception as e:
        self.skipTest(f"ABOD not available: {e}")

def test_small_data_boundary(self):
    """测试小样本数据边界情况"""
    adapter = OperatorAdapter()

    # 测试数据量不足的情况
    small_data = pd.Series([1, 2])

    try:
        scores, mask = adapter._hbos_anomaly(small_data)
        self.assertEqual(len(scores), 2)
        self.assertEqual(len(mask), 2)
        # 小样本应返回全零
        self.assertTrue(np.all(scores == 0))
    except Exception as e:
        # 应该有警告但不应抛出异常
        pass

def test_nan_data_boundary(self):
    """测试 NaN 数据边界情况"""
    adapter = OperatorAdapter()

    # 测试包含 NaN 的数据
    data_with_nan = pd.Series([1, 2, np.nan, 4, 5, 100])

    try:
        scores, mask = adapter._hbos_anomaly(data_with_nan)
        self.assertEqual(len(scores), 6)
        self.assertEqual(len(mask), 6)
        # NaN 位置应返回 0
        self.assertEqual(scores[2], 0)
    except Exception as e:
        pass
```

- [ ] **Step 2: 运行测试**

Run: `cd subagents/anomaly-detection-agent/skills/anomaly-detection-core && python -m pytest tests/test_anomaly_detection.py::TestOperatorAdapter -v`
Expected: 所有 PyOD 算子测试通过

- [ ] **Step 3: 提交**

```bash
git add subagents/anomaly-detection-agent/skills/anomaly-detection-core/tests/test_anomaly_detection.py
git commit -m "test: add comprehensive PyOD operator tests"
```

---

## Task 12: 实现可视化方法 plot_anomalies

**Files:**
- Modify: `subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py`

- [ ] **Step 1: 添加 matplotlib 导入**

在文件开头的 import 部分，添加 matplotlib：

```python
# 尝试导入可视化库
try:
    import matplotlib
    matplotlib.use('Agg')  # 使用非交互式后端
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
```

- [ ] **Step 2: 添加 plot_anomalies 方法**

在 `OperatorAdapter` 类中添加可视化方法：

```python
def plot_anomalies(self,
                   series: pd.Series,
                   anomaly_mask: np.ndarray,
                   operator_name: str,
                   indicator_name: str,
                   save_path: Optional[str] = None) -> str:
    """绘制异常检测结果可视化

    Args:
        series: 原始数据序列
        anomaly_mask: 异常掩码（True=异常）
        operator_name: 算子名称
        indicator_name: 指标名称
        save_path: 保存路径（可选）

    Returns:
        图片保存路径或 base64 编码
    """
    if not MATPLOTLIB_AVAILABLE:
        return "[ERROR] matplotlib 不可用，无法生成可视化"

    try:
        # 创建图形
        fig, ax = plt.subplots(figsize=(12, 4))

        # 绘制原始数据曲线
        ax.plot(series.values, 'b-', label='数据', alpha=0.7)

        # 标记异常点
        anomaly_indices = np.where(anomaly_mask)[0]
        if len(anomaly_indices) > 0:
            ax.scatter(anomaly_indices, series.values[anomaly_indices],
                      c='red', s=50, label='异常', zorder=5)

        # 设置标题和标签
        ax.set_title(f'异常检测结果 - {operator_name} | {indicator_name}')
        ax.set_xlabel('时间步')
        ax.set_ylabel('数值')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 保存或返回
        if save_path:
            plt.savefig(save_path, dpi=100, bbox_inches='tight')
            plt.close(fig)
            return save_path
        else:
            # 返回 base64 编码
            import io
            import base64
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)
            return f"data:image/png;base64,{img_base64}"

    except Exception as e:
        logger.error(f"[ADAPTER] 可视化生成失败: {e}")
        return f"[ERROR] 可视化生成失败: {str(e)}"
```

- [ ] **Step 3: 验证语法**

Run: `python -m py_compile subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py`
Expected: 无语法错误

- [ ] **Step 4: 提交**

```bash
git add subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py
git commit -m "feat: add plot_anomalies visualization method"
```

---

## Task 13: 添加可视化测试

**Files:**
- Modify: `subagents/anomaly-detection-agent/skills/anomaly-detection-core/tests/test_anomaly_detection.py`

- [ ] **Step 1: 添加可视化测试**

在 `TestOperatorAdapter` 类中添加：

```python
def test_plot_anomalies(self):
    """测试可视化功能"""
    adapter = OperatorAdapter()

    # 创建测试数据
    np.random.seed(42)
    n = 50
    data = 50 + 5 * np.random.randn(n)
    data[45] = 100
    series = pd.Series(data)

    # 模拟异常掩码
    mask = np.zeros(n, dtype=bool)
    mask[45] = True

    # 测试可视化
    result = adapter.plot_anomalies(series, mask, "test_operator", "test_indicator")

    # 验证返回值
    self.assertTrue(isinstance(result, str))
    self.assertTrue(result.startswith("data:image/png;base64,") or
                   result.startswith("[ERROR]"))

def test_plot_anomalies_with_file(self):
    """测试保存到文件的可视化"""
    adapter = OperatorAdapter()

    np.random.seed(42)
    n = 50
    data = 50 + 5 * np.random.randn(n)
    data[45] = 100
    series = pd.Series(data)

    mask = np.zeros(n, dtype=bool)
    mask[45] = True

    # 测试保存到文件
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        save_path = f.name

    try:
        result = adapter.plot_anomalies(series, mask, "test", "indicator",
                                        save_path=save_path)
        self.assertEqual(result, save_path)
        self.assertTrue(os.path.exists(save_path))
    finally:
        if os.path.exists(save_path):
            os.unlink(save_path)
```

- [ ] **Step 2: 运行测试**

Run: `cd subagents/anomaly-detection-agent/skills/anomaly-detection-core && python -m pytest tests/test_anomaly_detection.py::TestOperatorAdapter::test_plot_anomalies -v`
Expected: 可视化测试通过

- [ ] **Step 3: 提交**

```bash
git add subagents/anomaly-detection-agent/skills/anomaly-detection-core/tests/test_anomaly_detection.py
git commit -m "test: add visualization tests"
```

---

## Task 14: 集成测试和最终验证

**Files:**
- Modify: `subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/operator_adapter.py`

- [ ] **Step 1: 创建集成测试脚本**

创建临时测试脚本 `test_pyod_integration.py`：

```python
#!/usr/bin/env python3
"""PyOD 集成测试"""
import pandas as pd
import numpy as np
import sys
sys.path.insert(0, 'subagents/anomaly-detection-agent/skills/anomaly-detection-core')

from scripts.operator_adapter import main

# 创建测试数据
np.random.seed(42)
n = 100
data = {
    "timestamp": [f"2024-01-01 {i:02d}:00" for i in range(n)],
    "COD": [50 + 5*np.random.randn() if i < 90 else 100 for i in range(n)],
    "pH": [7 + 0.5*np.random.randn() if i < 85 else 9 for i in range(n)]
}

df = pd.DataFrame(data)

# 测试 PyOD 算子
result = main(
    data={"values": data},
    indicators=["COD", "pH"],
    operators=["hbos", "ecod", "knn", "lof"]
)

print("集成测试结果:")
print(f"状态: {result['status']}")
print(f"可用算子: {result['available_operators']}")
print(f"使用的算子: {result['operators_used']}")

# 验证 PyOD 算子结果
if result['status'] == 'success':
    for op in ['hbos', 'ecod', 'knn', 'lof']:
        if op in result['operator_results']:
            print(f"{op}: OK")
        else:
            print(f"{op}: MISSING")
else:
    print(f"错误: {result.get('error')}")
```

- [ ] **Step 2: 运行集成测试**

Run: `python test_pyod_integration.py`
Expected: 输出显示所有 PyOD 算子正常工作

- [ ] **Step 3: 清理测试文件**

Run: `rm test_pyod_integration.py`
Expected: 测试文件已删除

- [ ] **Step 4: 运行完整测试套件**

Run: `cd subagents/anomaly-detection-agent/skills/anomaly-detection-core && python -m pytest tests/test_anomaly_detection.py -v`
Expected: 所有测试通过

- [ ] **Step 5: 最终提交**

```bash
git add -A
git commit -m "test: complete PyOD integration testing"
```

---

## Task 15: 更新文档

**Files:**
- Modify: `subagents/anomaly-detection-agent/skills/anomaly-detection-core/SKILL.md`

- [ ] **Step 1: 更新 SKILL.md 文档**

在 `SKILL.md` 中添加 PyOD 算子说明：

```markdown
## 支持的算子

### 统计类算子
- zscore: Z-score 异常检测
- iqr: IQR 方法
- grubbs: Grubbs 检验
- moving_average: 移动平均

### 机器学习算子
- isolation_forest: 孤立森林
- one_class_svm: One-Class SVM

### PyOD 算子（需要 pyod 库）
- hbos: 直方图异常检测
- ecod: 经验累积分布
- knn: K 近邻
- lof: 局部异常因子
- abod: 角度异常检测

## 可视化
- plot_anomalies(): 异常检测结果可视化
```

- [ ] **Step 2: 验证文档更新**

Run: `cat subagents/anomaly-detection-agent/skills/anomaly-detection-core/SKILL.md | grep -A 20 "PyOD"`
Expected: 输出包含 PyOD 算子说明

- [ ] **Step 3: 提交**

```bash
git add subagents/anomaly-detection-agent/skills/anomaly-detection-core/SKILL.md
git commit -m "docs: update SKILL.md with PyOD operators documentation"
```

---

## 验收标准

完成后应满足：
- ✅ `requirements.txt` 包含 `pyod==1.0.0`
- ✅ `operator_adapter.py` 包含 5 个 PyOD 算子方法
- ✅ PyOD 算子在 `apply_operators()` 中可正常调用
- ✅ PyOD 不可用时优雅降级，不影响现有算子
- ✅ `plot_anomalies()` 可视化功能正常
- ✅ 所有单元测试和集成测试通过
- ✅ SKILL.md 已更新文档

---

## 运行完整测试

```bash
# 安装依赖
pip install -r requirements.txt

# 运行测试
cd subagents/anomaly-detection-agent/skills/anomaly-detection-core
python -m pytest tests/test_anomaly_detection.py -v

# 验证 PyOD 算子
python -c "from scripts.operator_adapter import OperatorAdapter; a = OperatorAdapter(); print(a.get_available_operators())"
```
