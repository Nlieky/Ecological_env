"""数据服务层

负责监测数据的查询和处理。从真实监测数据集（进水/出水 CSV）读取并加工数据，
返回结构化结果供 v1 API 路由使用。方法签名与返回字典形状保持稳定，
真实数据加载逻辑封装在 :mod:`backend.services.monitoring_data_loader`。
"""

from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from backend.services.monitoring_data_loader import (
    RESPONSE_INDICATORS,
    compute_quality_score,
    count_anomalies,
    get_monitoring_data,
    parse_indicators,
)


class DataService:
    """数据服务类

    所有查询方法从进程级单例 :class:`MonitoringDataset` 取数；返回字典的形状
    与历史 mock 版本保持一致，仅数据来源改为真实监测数据。
    """

    def __init__(self, plant_id=None):
        # 保留 data_dir 以向后兼容；真实数据目录由 loader 单例管理
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self._loader = get_monitoring_data(plant_id) if plant_id else get_monitoring_data()

    # ---------- 内部辅助 ----------

    @staticmethod
    def _round_or_none(v: Any) -> Optional[float]:
        """转 python float 并保留 4 位小数；NaN/None/不可解析时返回 None（JSON 安全）。"""
        if v is None:
            return None
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        if pd.isna(f) or f in (float('inf'), -float('inf')):
            return None
        return round(f, 4)

    @staticmethod
    def _iso_z(ts: pd.Timestamp) -> str:
        """ISO 8601 时间戳并以 ``Z`` 标注 UTC（满足 RealtimeDataResponse 时区校验）。"""
        from shared.data.source_context import sampling_timestamp
        return sampling_timestamp(ts).tz_convert('UTC').isoformat().replace('+00:00', 'Z')

    def _metrics(self, row: pd.Series) -> Dict[str, Optional[float]]:
        """从一行数据提取响应指标 {pH, COD, TN, TP}。"""
        return {c: self._round_or_none(row[c]) for c in RESPONSE_INDICATORS if c in row.index}

    def _context(self):
        from shared.data.source_context import describe_data_context
        context = describe_data_context(getattr(self._loader, '_bucket', 'csv-unverified'), self._loader.latest_timestamp)
        context['plant_id'] = getattr(self._loader, '_plant_id', None)
        return context

    # ---------- 查询方法 ----------

    def get_realtime_data(self) -> Dict[str, Any]:
        """获取实时监测数据（数据集最新一条记录）。"""
        loader = self._loader
        loader.maybe_reload()
        influent = loader.influent()
        effluent = loader.effluent()
        latest = loader.latest_timestamp

        in_row = influent.ffill().iloc[-1] if not influent.empty else pd.Series(dtype=float)
        out_row = effluent.ffill().iloc[-1] if not effluent.empty else pd.Series(dtype=float)

        # 流量取进水最新非缺失值
        flow_series = influent.get('flow', pd.Series(dtype=float)).dropna()
        flow_rate = self._round_or_none(flow_series.iloc[-1]) if len(flow_series) else None

        # 质量评分基于最近 24h
        quality_score = compute_quality_score(
            loader.window("influent", "24h"),
            loader.window("effluent", "24h"),
        )

        return {
            "timestamp": self._iso_z(latest),
            "influent": self._metrics(in_row),
            "effluent": self._metrics(out_row),
            "flow_rate": flow_rate,
            "quality_score": quality_score,
            'data_context': self._context(),
        }

    def get_data_quality(self, time_range: str = "24h") -> Dict[str, Any]:
        """获取数据质量指标（完整率、缺失数、异常数）。

        完整率/缺失数基于 pH/COD/TN/TP 在进水+出水窗口内统计；
        异常数按各列 3σ 规则计数。
        """
        loader = self._loader
        win_inf = loader.window("influent", time_range)
        win_eff = loader.window("effluent", time_range)

        cols = RESPONSE_INDICATORS
        in_sub = win_inf[[c for c in cols if c in win_inf.columns]]
        out_sub = win_eff[[c for c in cols if c in win_eff.columns]]
        total_cells = in_sub.size + out_sub.size

        if total_cells == 0:
            completeness_rate, missing = 0.0, 0
        else:
            missing = int(in_sub.isna().sum().sum() + out_sub.isna().sum().sum())
            completeness_rate = round(1 - missing / total_cells, 4)

        anomaly_count = count_anomalies(win_inf, cols) + count_anomalies(win_eff, cols)

        return {
            "completeness_rate": completeness_rate,
            "missing_data_count": missing,
            "anomaly_count": anomaly_count,
            "last_update": self._iso_z(loader.latest_timestamp),
            'data_context': self._context(),
        }

    def query_history_data(self, time_range: str = "24h",
                           indicators: Optional[str] = None,
                           aggregation: str = "raw",
                           page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """查询历史监测数据，支持指标筛选、聚合与分页。

        每条记录形如 ``{timestamp, influent:{...}, effluent:{...}}``；
        ``summary`` 为窗口内进水各指标的 avg/max/min。
        """
        loader = self._loader
        win_inf = loader.window("influent", time_range)
        win_eff = loader.window("effluent", time_range)

        ind = parse_indicators(indicators)
        ind_inf = [c for c in ind if c in win_inf.columns]
        ind_eff = [c for c in ind if c in win_eff.columns]

        # 聚合：hourly/daily 取均值，raw 不聚合
        rule = {"hourly": "1H", "daily": "1D"}.get(aggregation)
        if rule:
            agg_inf = win_inf[ind_inf].resample(rule).mean() if not win_inf.empty else win_inf[ind_inf]
            agg_eff = win_eff[ind_eff].resample(rule).mean() if not win_eff.empty else win_eff[ind_eff]
        else:
            agg_inf = win_inf[ind_inf]
            agg_eff = win_eff[ind_eff]

        # 按时间戳合并进水/出水
        records = []
        for ts in agg_inf.index.union(agg_eff.index).sort_values():
            rec: Dict[str, Any] = {
                "timestamp": self._iso_z(ts),
                "influent": {c: self._round_or_none(agg_inf.loc[ts, c]) for c in ind_inf} if ts in agg_inf.index else {},
                "effluent": {},
            }
            if ts in agg_eff.index:
                rec["effluent"] = {
                    c: self._round_or_none(agg_eff.loc[ts, c]) for c in ind_eff
                }
            records.append(rec)

        # 分页（夹紧到合法区间）
        page = max(1, page)
        page_size = max(1, min(500, page_size))
        total_count = len(records)
        lo, hi = (page - 1) * page_size, (page - 1) * page_size + page_size

        # summary：窗口内进水各指标统计
        summary: Dict[str, float] = {}
        for c in ind_inf:
            s = win_inf[c].dropna()
            if len(s):
                summary[f"{c}_avg"] = round(float(s.mean()), 4)
                summary[f"{c}_max"] = round(float(s.max()), 4)
                summary[f"{c}_min"] = round(float(s.min()), 4)

        return {
            "records": records[lo:hi],
            "summary": summary,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "timestamp": self._iso_z(loader.latest_timestamp),
            'data_context': self._context(),
        }

    def get_aggregated_data(self, period: str = "daily",
                            metrics: str = "avg,max,min") -> Dict[str, Any]:
        """获取聚合统计数据（按周期对 pH/COD/TN/TP 做 avg/max/min 等）。"""
        loader = self._loader

        rule = {"hourly": "1H", "daily": "1D", "weekly": "1W", "monthly": "1MS"}.get(period, "1D")
        metric_map = {
            "avg": "mean", "average": "mean",
            "max": "max", "min": "min", "std": "std", "sum": "sum",
        }
        # 去重保留 (展示标签, pandas 函数名)
        funcs = []
        seen = set()
        for t in (metrics or "").split(","):
            t = t.strip()
            fn = metric_map.get(t.lower())
            if fn and fn not in seen:
                seen.add(fn)
                funcs.append((t.lower(), fn))

        label_fmt = "%Y-%m-%d %H:00" if rule == "1H" else "%Y-%m-%d"
        ind = RESPONSE_INDICATORS
        func_list = [fn for _, fn in funcs]

        def _aggregate(df: pd.DataFrame) -> Dict[str, Dict[str, Optional[float]]]:
            if df.empty:
                return {}
            sub = df[[c for c in ind if c in df.columns]]
            res = sub.resample(rule).agg(func_list) if func_list else sub.resample(rule).mean()
            if 'sum' in func_list:
                # pandas sum defaults to zero for empty/all-missing buckets.
                counts = sub.resample(rule).count()
                for column in sub.columns:
                    res[(column, 'sum')] = res[(column, 'sum')].where(counts[column] > 0)
            out: Dict[str, Dict[str, Optional[float]]] = {}
            for ts in res.index:
                bucket: Dict[str, Optional[float]] = {}
                if func_list:
                    row = res.loc[ts]
                    for c in ind:
                        if c not in sub.columns:
                            continue
                        for label, fn in funcs:
                            try:
                                bucket[f"{c}_{label}"] = self._round_or_none(row[(c, fn)])
                            except KeyError:
                                bucket[f"{c}_{label}"] = None
                out[ts.strftime(label_fmt)] = bucket
            return out

        return {
            "period": period,
            'data_context': self._context(),
            "metrics": [label for label, _ in funcs],
            "data": {
                "influent": _aggregate(loader.influent()),
                "effluent": _aggregate(loader.effluent()),
            },
        }
