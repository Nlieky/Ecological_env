import time
from types import SimpleNamespace

import pandas as pd
import pytest

from backend.services import influxdb_data_loader as module


def test_csv_cannot_silently_answer_for_arbitrary_plant(monkeypatch):
    from backend.services import monitoring_data_loader as factory
    from backend.core.config import settings
    from backend.exceptions import DataUnavailableException
    monkeypatch.setattr(settings, 'MONITORING_DATA_SOURCE', 'csv')
    with pytest.raises(DataUnavailableException, match='CSV'):
        factory.get_monitoring_data('plant-A')


def test_cached_data_refreshes_after_ttl(monkeypatch):
    clock = [0.]
    monkeypatch.setattr(time, 'monotonic', lambda: clock[0])
    monkeypatch.setattr(module, 'InfluxDBClient', lambda **_: SimpleNamespace(query_api=lambda: None))
    loader = module.InfluxDBMonitoringDataset('url', 'token', 'org', 'bucket')
    values = [10.]
    monkeypatch.setattr(loader, '_fetch', lambda *_: pd.DataFrame({'COD': values}, index=pd.to_datetime(['2026-07-14'])))
    assert loader.effluent().iloc[0]['COD'] == 10
    values[0] = 30
    clock[0] = 60
    loader.maybe_reload()
    assert loader.effluent().iloc[0]['COD'] == 30


def test_latest_time_works_for_effluent_only(monkeypatch):
    monkeypatch.setattr(module, 'InfluxDBClient', lambda **_: SimpleNamespace(query_api=lambda: None))
    loader = module.InfluxDBMonitoringDataset('url', 'token', 'org', 'bucket')
    monkeypatch.setattr(loader, '_fetch', lambda side, _: pd.DataFrame() if side == 'influent' else pd.DataFrame({'COD': [30]}, index=pd.to_datetime(['2026-07-14'])))
    assert loader.latest_timestamp == pd.Timestamp('2026-07-14')


def test_plant_filter_is_forwarded(monkeypatch):
    from shared.data import influxdb_query
    monkeypatch.setattr(module, 'InfluxDBClient', lambda **_: SimpleNamespace(query_api=lambda: None))
    loader = module.InfluxDBMonitoringDataset('url', 'token', 'org', 'bucket', plant_id='plant-A')
    captured = []
    monkeypatch.setattr(influxdb_query, 'fetch_wastewater_df', lambda *_, **kw: captured.append(kw) or pd.DataFrame({'COD': [30]}, index=pd.to_datetime(['2026-07-14'])))
    loader.effluent()
    assert all(item['plant_id'] == 'plant-A' for item in captured)
