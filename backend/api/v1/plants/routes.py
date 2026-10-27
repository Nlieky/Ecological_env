"""Plant-scoped dashboard and metric query share sampling/source/time semantics."""
import asyncio
from datetime import timedelta
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException

from shared.data.source_context import describe_data_context, sampling_timestamp

router = APIRouter(tags=["多厂区仪表盘"])
_INDICATOR_META = {
    'pH': ('pH', (6., 9.), ''), 'COD': ('COD', 100., 'mg/L'),
    'TN': ('总氮', 20., 'mg/L'), 'AN': ('氨氮', 15., 'mg/L'),
    'TP': ('总磷', 1., 'mg/L'), 'suspended_solids': ('悬浮物', None, 'mg/L'),
    'flow': ('流量', None, 'm³/h'), 'discharge': ('累计排放量', None, 'm³'),
}
_INDICATOR_ORDER = list(_INDICATOR_META)


def _plant_overrides(plant_id: str) -> dict:
    import yaml
    path = Path(__file__).resolve().parents[4] / 'shared/data/plant-hierarchy.yaml'
    if not path.exists():
        return {}
    with path.open(encoding='utf-8') as handle:
        return ((yaml.safe_load(handle) or {}).get('plant_configs') or {}).get(plant_id) or {}


@router.get('/plants/tree')
async def get_plant_tree():
    try:
        from shared.data.discover_plants import build_tree
        return {'success': True, 'data': await asyncio.to_thread(build_tree)}
    except Exception as error:
        raise HTTPException(status_code=500, detail=f'构建厂目录树失败: {error}') from error


def _query_dashboard(plant_id, hours, anchor, end_date):
    from shared.data.influxdb_query import get_client_and_bucket, fetch_wastewater_df
    from backend.services.monitoring_data_loader import parse_window_endpoints
    # Validate before opening a client, including end-only and reversed dates.
    if not plant_id or not 1 <= hours <= 10000:
        raise HTTPException(status_code=422, detail='厂区不能为空；小时窗口须为 1..10000')
    if end_date and not anchor:
        raise HTTPException(status_code=422, detail='结束日期必须同时指定开始日期')
    try:
        start_dt = sampling_timestamp(anchor).normalize() if anchor else None
        stop_dt = sampling_timestamp(end_date).normalize() + timedelta(days=1) if end_date else None
        if start_dt is not None and stop_dt is not None and not 0 < (stop_dt - start_dt).total_seconds() <= 366 * 86400:
            raise ValueError('日期范围须为 1..366 天')
    except (ValueError, TypeError) as error:
        raise HTTPException(status_code=422, detail=f'无效日期范围: {error}') from error
    client, bucket = get_client_and_bucket()
    try:
        # Include additional numeric business indicators, not provenance bookkeeping.
        dfs = {side: fetch_wastewater_df(client, bucket, side, plant_id=plant_id, include_all_fields=True) for side in ('influent', 'effluent')}
    finally:
        client.close()
    last = max((df.index.max() for df in dfs.values() if not df.empty), default=None)
    if anchor:
        start = start_dt.tz_localize(None)
        stop = (stop_dt or start_dt + timedelta(days=7)).tz_localize(None)
        dfs = {side: df.loc[(df.index >= start) & (df.index < stop)] if not df.empty else df for side, df in dfs.items()}
    elif last is not None:
        start, stop = parse_window_endpoints(last, f'{hours}h')
        dfs = {side: df.loc[start:stop] if not df.empty else df for side, df in dfs.items()}
    else:
        start = stop = None
    selected_last = max((df.index.max() for df in dfs.values() if not df.empty), default=None)
    limits = _plant_overrides(plant_id).get('limits') or {}
    fields = [f for f in _INDICATOR_ORDER if any(f in df.columns for df in dfs.values())]
    fields += sorted({f for df in dfs.values() for f in df.columns} - set(fields))
    if not fields:
        fields = _INDICATOR_ORDER[:6]
    indicators = {}
    for field in fields:
        label, limit, unit = _INDICATOR_META.get(field, (field, None, ''))
        limit = limits.get(field, limit)
        item = {'label': label, 'unit': unit, 'limit': limit, 'influent': None, 'effluent': None,
                'status': 'nodata', 'series': {'influent': [], 'effluent': []}}
        for side, df in dfs.items():
            if field not in df.columns:
                continue
            series = pd.to_numeric(df[field], errors='coerce').replace([float('inf'), -float('inf')], float('nan')).dropna()
            item['series'][side] = [{'time': ts.strftime('%Y-%m-%d %H:%M:%S'), 'value': round(float(v), 2)} for ts, v in series.items()]
            if not series.empty:
                item[side] = round(float(series.iloc[-1]), 2)
        effluent = item['effluent']
        if effluent is not None:
            lo, hi = limit if isinstance(limit, (tuple, list)) else (None, limit)
            bad = (lo is not None and effluent < lo) or (hi is not None and effluent > hi)
            item['status'] = 'warning' if bad else 'normal'
        indicators[field] = item
    return {'success': True, 'data': {
        'plant_id': plant_id, 'window_hours': hours, 'latest_time': last.strftime('%Y-%m-%d %H:%M') if last is not None else '',
        'anchor': anchor or '', 'segment_start': start.strftime('%Y-%m-%d %H:%M') if start is not None else '',
        'segment_end': stop.strftime('%Y-%m-%d %H:%M') if stop is not None else '',
        'indicators': indicators, 'influent_points': len(dfs['influent']), 'effluent_points': len(dfs['effluent']),
        'data_context': describe_data_context(bucket, selected_last),
    }}


@router.get('/plants/{plant_id}/dashboard')
async def get_plant_dashboard(plant_id: str, hours: int = 24, anchor: str | None = None, end_date: str | None = None):
    """Latest-sample-relative hours, or inclusive local dates; replay defaults to seven days."""
    try:
        return await asyncio.to_thread(_query_dashboard, plant_id, hours, anchor, end_date)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f'厂看板数据获取失败: {error}') from error
