"""InfluxDB 监测数据加载器。

从 InfluxDB ``monitoring-data`` bucket 读取废水监测数据,鸭子兼容
:class:`backend.services.monitoring_data_loader.MonitoringDataset` 的接口
(``maybe_reload`` / ``latest_timestamp`` / ``influent`` / ``effluent`` / ``window``),
使 :mod:`backend.services.data_service` 与 :mod:`backend.metrics.updater` 零改动即可切换数据源。

数据来源:``shared/data/import_to_influxdb.py`` 把 real-time/*.xls 真实报表写入
measurement=wastewater,tags=data_type(influent/effluent)+plant_id,
fields=pH/COD/TN/AN/TP/flow/discharge/suspended_solids(+各 *_mass)。

时区:导入时按 UTC 写入(naive 视作 UTC);此处读出后转回 naive Timestamp,
与 CSV loader 的 ``latest_timestamp`` 语义一致(供 data_service ``_iso_z`` 拼 ``Z``)。
"""
from __future__ import annotations

import threading
from typing import List, Optional

import pandas as pd
from influxdb_client import InfluxDBClient

from backend.exceptions import DataUnavailableException

# 契约字段(与 monitoring_data_loader.REQUIRED_KEYS/RESPONSE_INDICATORS 对齐)
INFLUENT_FIELDS: List[str] = ["pH", "COD", "TN", "AN", "TP", "flow", "discharge"]
EFFLUENT_FIELDS: List[str] = ["pH", "COD", "TN", "AN", "TP", "flow", "discharge", "suspended_solids"]

_MEASUREMENT = "wastewater"


class InfluxDBMonitoringDataset:
    """从 InfluxDB 读监测数据,鸭子兼容 :class:`MonitoringDataset`。

    数据为静态导入;首次访问时全量查询并缓存(无 mtime 概念,``maybe_reload`` 不重载)。
    """

    def __init__(self, url: str, token: str, org: str, bucket: str):
        self._bucket = bucket
        self._client = InfluxDBClient(url=url, token=token, org=org, timeout=30_000)
        self._query_api = self._client.query_api()
        self._in: Optional[pd.DataFrame] = None
        self._out: Optional[pd.DataFrame] = None
        self._lock = threading.Lock()

    # ---------- 内部 ----------

    def _fetch(self, data_type: str, fields: List[str]) -> pd.DataFrame:
        """查一侧数据(委托 shared.data.influxdb_query,避免查询逻辑重复)。"""
        from shared.data.influxdb_query import fetch_wastewater_df
        return fetch_wastewater_df(self._client, self._bucket, data_type, fields)

    def _load(self) -> None:
        if self._in is not None and self._out is not None:
            return
        with self._lock:
            if self._in is not None and self._out is not None:
                return
            in_df = self._fetch("influent", INFLUENT_FIELDS)
            out_df = self._fetch("effluent", EFFLUENT_FIELDS)
            if in_df.empty and out_df.empty:
                raise DataUnavailableException(
                    "InfluxDB monitoring-data bucket 无 wastewater 数据",
                    details={"bucket": self._bucket, "org_hint": "确认已运行 import_to_influxdb.py"},
                )
            self._in = in_df
            self._out = out_df

    # ---------- 契约接口(与 MonitoringDataset 一致)----------

    def maybe_reload(self) -> None:
        """数据静态导入;首次访问触发加载,之后不重载(与 CSV 版按 mtime 重载不同)。"""
        self._load()

    @property
    def latest_timestamp(self) -> pd.Timestamp:
        self._load()
        return max(self._in.index.max(), self._out.index.max())

    def influent(self) -> pd.DataFrame:
        self._load()
        return self._in

    def effluent(self) -> pd.DataFrame:
        self._load()
        return self._out

    def window(self, side: str, time_range: Optional[str]) -> pd.DataFrame:
        """返回指定系列在 ``time_range`` 窗口内的切片(含端点)。

        复用 CSV loader 的窗口解析逻辑(避免实现漂移)。
        """
        # 延迟导入,避免与 monitoring_data_loader 形成循环导入
        from backend.services.monitoring_data_loader import parse_window_endpoints

        df = self.influent() if side == "influent" else self.effluent()
        start, end = parse_window_endpoints(self.latest_timestamp, time_range)
        return df.loc[start:end]
