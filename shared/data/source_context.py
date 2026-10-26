"""Shared wastewater provenance and sampling-time contract (file/API independent)."""
from __future__ import annotations
import os
from datetime import datetime, timezone
import pandas as pd


def data_timezone() -> str:
    return os.environ.get('DATA_TIMEZONE', 'Asia/Shanghai')


def sampling_timestamp(value) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize(data_timezone())
    return timestamp.tz_convert(data_timezone())


def simulation_bucket() -> str:
    bucket = os.environ.get('INFLUXDB_SIMULATION_BUCKET', 'monitoring-simulation')
    if not bucket or bucket in {os.environ.get('INFLUXDB_REAL_BUCKET', 'monitoring-real'), os.environ.get('INFLUXDB_BUCKET', 'monitoring-real')}:
        raise ValueError('模拟 bucket 必须与真实/业务查询 bucket 不同')
    return bucket


def describe_data_context(bucket: str, latest, *, now=None) -> dict:
    real = os.environ.get('INFLUXDB_REAL_BUCKET', 'monitoring-real')
    simulated = os.environ.get('INFLUXDB_SIMULATION_BUCKET', 'monitoring-simulation')
    origin = 'real' if bucket == real else 'simulated' if bucket == simulated else 'unverified'
    mode = 'simulation' if origin == 'simulated' else 'unverified'
    if origin == 'real':
        mode = os.environ.get('BUSINESS_DATA_MODE', 'historical')
        if mode not in {'historical', 'live'}:
            raise ValueError('BUSINESS_DATA_MODE must be historical or live')
    end = sampling_timestamp(latest) if latest is not None and not pd.isna(latest) else None
    current = sampling_timestamp(now if now is not None else datetime.now(timezone.utc))
    lag = (current - end).total_seconds() / 3600 if end is not None else None
    warning = None
    if end is None:
        freshness, warning = 'missing', '查询范围内没有采样记录'
    elif origin == 'unverified':
        freshness, warning = 'unverified', '来源未核实：可能包含历史真实与模拟记录，不得作为实时监管证据'
    elif mode == 'simulation':
        freshness, warning = 'simulation', '模拟演示数据；模拟采样时间不代表真实数据新鲜度'
    elif mode == 'historical':
        freshness, warning = 'historical', '历史真实数据，非实时接入；以原始采样时间为准'
    elif lag < -0.1:
        freshness, warning = 'future', '采样时间晚于系统时间，请检查时钟和来源时区'
    elif lag > float(os.environ.get('DATA_STALE_AFTER_HOURS', '6')):
        freshness, warning = 'stale', '实时接入数据更新滞后'
    else:
        freshness = 'fresh'
    return {'origin': origin, 'mode': mode, 'bucket': bucket, 'timezone': data_timezone(),
            'latest_sample_at': end.isoformat() if end is not None else None,
            'lag_hours': round(lag, 2) if lag is not None else None,
            'freshness': freshness, 'warning': warning}
