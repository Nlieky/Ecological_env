"""废水指标 Prometheus 后台更新器。

守护线程按固定间隔从 :class:`MonitoringDataset` 推进游标，把当前行的进水/出水
指标写入 prometheus gauge（供 Prometheus 抓取、Grafana 可视化）。

数据本身是历史 CSV，但 gauge 值随游标推进而变化，Grafana 因此能画出"实时"曲线。
这是新版本的模拟实时方案——完全在 FastAPI 进程内，无需旧的 :5000 Flask 中间件。
"""
import logging
import threading
from typing import Optional, Dict

import pandas as pd

from backend.metrics.definitions import (
    wastewater_influent,
    wastewater_effluent,
    wastewater_data_processed_total,
    wastewater_anomaly_detected_total,
)

logger = logging.getLogger(__name__)

# CSV 列名(英文键) → prometheus gauge 后缀
_COL_TO_KEY: Dict[str, str] = {
    "pH": "ph",
    "COD": "cod",
    "TN": "tn",
    "AN": "an",
    "TP": "tp",
    "flow": "flow_rate",
    "discharge": "discharge_volume",
}

# 出水简单超标阈值（用于 anomaly 计数器；标准限值近似）
_EFFLUENT_LIMITS = {"COD": 50.0, "TN": 15.0, "AN": 5.0, "TP": 0.5}


class WastewaterGaugeUpdater:
    """单例式后台更新器；start 幂等。"""

    def __init__(self, interval: float = 5.0):
        self.interval = interval
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._cursor = 0

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="ww-metrics-updater", daemon=True
        )
        self._thread.start()
        logger.info("wastewater gauge updater started (interval=%ss)", self.interval)

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        # 延迟导入，避免模块加载期访问单例/配置
        from backend.services.monitoring_data_loader import get_monitoring_data

        while not self._stop.is_set():
            try:
                ds = get_monitoring_data()
                in_df, out_df = ds.influent(), ds.effluent()
                n = min(len(in_df), len(out_df))
                if n > 0:
                    i = self._cursor % n
                    self._update_once(in_df.iloc[i], out_df.iloc[i])
                    self._cursor += 1
            except Exception as e:  # 数据未就绪等，不要让线程死掉
                logger.warning("gauge update skipped: %s", e)
            self._stop.wait(self.interval)

    def _update_once(self, in_row: pd.Series, out_row: pd.Series) -> None:
        self._set_side(wastewater_influent, in_row)
        self._set_side(wastewater_effluent, out_row)
        # 计数器：每 tick 处理 1 行；出水任意超标字段则计 1 次异常
        wastewater_data_processed_total.inc()
        exceeded = any(
            (not pd.isna(out_row.get(col))) and float(out_row[col]) > lim
            for col, lim in _EFFLUENT_LIMITS.items()
            if col in out_row.index
        )
        if exceeded:
            wastewater_anomaly_detected_total.inc()

    @staticmethod
    def _set_side(gauges: Dict[str, object], row: pd.Series) -> None:
        for col, key in _COL_TO_KEY.items():
            g = gauges.get(key)
            if g is None or col not in row.index:
                continue
            v = row[col]
            g.set(0.0 if pd.isna(v) else float(v))


_updater: Optional[WastewaterGaugeUpdater] = None


def get_updater(interval: float = 5.0) -> WastewaterGaugeUpdater:
    global _updater
    if _updater is None:
        _updater = WastewaterGaugeUpdater(interval=interval)
    return _updater
