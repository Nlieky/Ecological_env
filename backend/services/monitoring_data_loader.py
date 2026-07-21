"""监测数据加载器

从 ``data/pollution_water_in.csv``（进水）和 ``data/pollution_water_out.csv``（出水）
加载真实监测数据，提供清洗、内存缓存和查询辅助函数，供 :class:`DataService` 使用。

数据特征（实测）：
- UTF-8 编码，每小时一条，覆盖 2024 全年（约 8761 行/文件）。
- 缺失值是字面字符串 ``"/"``（**非** NaN）——读取时用 ``na_values=["/"]`` 处理，
  否则 ``isna()`` 会误报 0 缺失、且数值列会被推断为 object 类型。
- 列名为中文，通过子串匹配映射为稳定英文键。
- 出水比进水多一列 ``悬浮物浓度``，不在响应契约内，丢弃。

时间语义：数据为静态历史数据集，最新时间戳为 ``2024-12-31 00:00``。
``time_range`` 窗口以**数据集最新时间**为基准计算（非墙钟当前时间）。
"""

import os
import re
import threading
from datetime import timedelta
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

from backend.exceptions import DataUnavailableException

# 响应中暴露的指标(进水/出水通用)。AN=氨氮,两份 CSV 都有,可对称暴露。
# flow 已作为顶层 flow_rate 字段单独返回(不纳入,避免影响质量评分);
# discharge 仅进水侧有,不对称,不纳入。
RESPONSE_INDICATORS: List[str] = ["pH", "COD", "TN", "AN", "TP"]
# 必须存在的列（缺失则视为数据不可用）
REQUIRED_KEYS: List[str] = ["time", "pH", "COD", "TN", "AN", "TP"]

# 指标别名（用户传入 indicators 参数时兼容多种写法）
INDICATOR_ALIASES = {
    "ph": "pH", "ph值": "pH",
    "cod": "COD", "化学需氧量": "COD",
    "tn": "TN", "总氮": "TN",
    "an": "AN", "氨氮": "AN", "ammonia": "AN",
    "tp": "TP", "总磷": "TP",
}

# 列名子串映射规则（顺序敏感：``排放`` 必须在 ``流量`` 之前判断，避免歧义）
_COLUMN_RULES = [
    ("监测时间", "time"),
    ("pH", "pH"),
    ("化学需氧量", "COD"),
    ("总氮", "TN"),
    ("氨氮", "AN"),
    ("总磷", "TP"),
    ("悬浮物", "suspended_solids"),  # 出水独有，保留供 Prometheus gauge
    ("排放", "discharge"),
    ("流量", "flow"),
]

# time_range 形如 "<整数><h|d>"
_TIME_RE = re.compile(r"^\s*(\d+)\s*(h|d)\s*$", re.IGNORECASE)


def _build_rename_map(columns: List[str]) -> dict:
    """根据子串规则把中文列名映射为英文键；未匹配的列在后续被丢弃。"""
    rename = {}
    for col in columns:
        for needle, key in _COLUMN_RULES:
            if needle in col:
                if key is not None:
                    rename[col] = key
                break  # 一个列只命中第一条规则
    return rename


def _load_one(path: Path, side: str) -> pd.DataFrame:
    """加载并清洗单个 CSV，返回以 ``time`` 为索引的 DataFrame。"""
    if not path.exists():
        raise DataUnavailableException(
            f"{side} data file not found",
            details={"path": str(path)},
        )
    # na_values=["/"]：把缺失标记 "/" 当作 NaN，并让 pandas 推断 float64
    df = pd.read_csv(path, encoding="utf-8", na_values=["/"])
    rename = _build_rename_map(list(df.columns))
    df = df.rename(columns=rename)
    # 仅保留成功映射的列
    keep = [c for c in df.columns if c in rename.values()]
    df = df[keep]

    missing = [k for k in REQUIRED_KEYS if k not in df.columns]
    if missing:
        raise DataUnavailableException(
            f"{side} data missing required columns",
            details={"missing": missing, "path": str(path)},
        )

    df["time"] = pd.to_datetime(df["time"], format="%Y-%m-%d %H", errors="coerce")
    df = df.dropna(subset=["time"]).set_index("time").sort_index()
    return df


class MonitoringDataset:
    """加载并缓存进水/出水监测数据，按文件 mtime 失效重载。"""

    def __init__(self, data_dir: Path):
        self._in_path = data_dir / "pollution_water_in.csv"
        self._out_path = data_dir / "pollution_water_out.csv"
        self._in: Optional[pd.DataFrame] = None
        self._out: Optional[pd.DataFrame] = None
        self._in_mtime: Optional[float] = None
        self._out_mtime: Optional[float] = None
        self._lock = threading.Lock()

    def _mtimes(self) -> Tuple[float, float]:
        try:
            return os.stat(self._in_path).st_mtime, os.stat(self._out_path).st_mtime
        except FileNotFoundError as e:
            raise DataUnavailableException(
                "monitoring CSV file missing", details={"error": str(e)}
            )

    def maybe_reload(self) -> None:
        """若文件 mtime 变化或尚未加载，则重新加载（线程安全，双重检查）。"""
        in_mt, out_mt = self._mtimes()
        if (self._in is None or self._out is None
                or in_mt != self._in_mtime or out_mt != self._out_mtime):
            with self._lock:
                if (self._in is None or self._out is None
                        or in_mt != self._in_mtime or out_mt != self._out_mtime):
                    self._in = _load_one(self._in_path, "influent")
                    self._out = _load_one(self._out_path, "effluent")
                    self._in_mtime = in_mt
                    self._out_mtime = out_mt

    @property
    def latest_timestamp(self) -> pd.Timestamp:
        """两个系列的最新时间戳。"""
        self.maybe_reload()
        return max(self._in.index.max(), self._out.index.max())

    def influent(self) -> pd.DataFrame:
        self.maybe_reload()
        return self._in

    def effluent(self) -> pd.DataFrame:
        self.maybe_reload()
        return self._out

    def window(self, side: str, time_range: Optional[str]) -> pd.DataFrame:
        """返回指定系列在 ``time_range`` 窗口内的切片（含端点）。"""
        df = self.influent() if side == "influent" else self.effluent()
        start, end = parse_window_endpoints(self.latest_timestamp, time_range)
        return df.loc[start:end]


# ---------- 查询辅助函数 ----------

def parse_window_endpoints(latest: pd.Timestamp,
                           time_range: Optional[str]) -> Tuple[pd.Timestamp, pd.Timestamp]:
    """把 ``time_range`` 解析为 ``[start, end]``，相对于数据集最新时间。

    接受 ``<int>h`` / ``<int>d``（如 ``24h``、``7d``）；无效值回退到 ``24h``（不报错）。
    """
    tr = (time_range or "24h").strip()
    end = latest
    m = _TIME_RE.match(tr)
    if m:
        n = int(m.group(1))
        delta = timedelta(hours=n) if m.group(2).lower() == "h" else timedelta(days=n)
    else:
        delta = timedelta(hours=24)  # 无效回退
    return end - delta, end


def parse_indicators(indicators: Optional[str]) -> List[str]:
    """解析指标字符串，返回 :data:`RESPONSE_INDICATORS` 的子集；空或全无效则返回默认。"""
    if not indicators:
        return list(RESPONSE_INDICATORS)
    result: List[str] = []
    for token in (t.strip() for t in indicators.split(",")):
        if not token:
            continue
        key = INDICATOR_ALIASES.get(token.lower())
        if key in RESPONSE_INDICATORS and key not in result:
            result.append(key)
    return result or list(RESPONSE_INDICATORS)


def count_anomalies(df: pd.DataFrame, cols: List[str]) -> int:
    """对指定列做 3σ 异常计数（各列求和）。样本不足或方差为 0 的列跳过。"""
    total = 0
    sub = df[[c for c in cols if c in df.columns]]
    for c in sub.columns:
        s = sub[c].dropna()
        if len(s) < 2:
            continue
        sd = s.std()
        if pd.isna(sd) or sd == 0:
            continue
        mu = s.mean()
        total += int(((s < mu - 3 * sd) | (s > mu + 3 * sd)).sum())
    return total


def compute_quality_score(influent_win: pd.DataFrame,
                          effluent_win: pd.DataFrame) -> float:
    """综合质量评分 ∈ [0,1]。

    ``score = 0.7 * 完整率 + 0.3 * (1 - 异常率)``，基于 pH/COD/TN/TP。
    权重可调；完整率占主导。
    """
    cols = [c for c in RESPONSE_INDICATORS]
    in_sub = influent_win[[c for c in cols if c in influent_win.columns]]
    out_sub = effluent_win[[c for c in cols if c in effluent_win.columns]]
    total_cells = in_sub.size + out_sub.size
    if total_cells == 0:
        return 0.0
    missing = int(in_sub.isna().sum().sum() + out_sub.isna().sum().sum())
    completeness = 1 - missing / total_cells
    anomalies = count_anomalies(influent_win, cols) + count_anomalies(effluent_win, cols)
    anomaly_ratio = min(1.0, anomalies / total_cells)
    score = 0.7 * completeness + 0.3 * (1 - anomaly_ratio)
    return round(max(0.0, min(1.0, score)), 4)


# ---------- 模块级单例 ----------

_SINGLETON: Optional[MonitoringDataset] = None
_SINGLETON_LOCK = threading.Lock()


def get_monitoring_data() -> MonitoringDataset:
    """返回进程级单例 :class:`MonitoringDataset`。"""
    global _SINGLETON
    if _SINGLETON is None:
        with _SINGLETON_LOCK:
            if _SINGLETON is None:
                from backend.core.config import settings
                project_root = Path(__file__).resolve().parents[2]
                data_dir = Path(settings.DATA_SOURCE_PATH)
                if not data_dir.is_absolute():
                    data_dir = project_root / data_dir
                if not data_dir.exists():
                    data_dir = project_root / "data"
                _SINGLETON = MonitoringDataset(data_dir)
    return _SINGLETON
