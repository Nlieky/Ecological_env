import asyncio
from types import SimpleNamespace

import pandas as pd
import pytest

from backend.api.v1.plants import routes
from shared.data import influxdb_query


@pytest.fixture
def frames(monkeypatch):
    monkeypatch.setenv('INFLUXDB_REAL_BUCKET', 'real-test')
    monkeypatch.setenv('BUSINESS_DATA_MODE', 'historical')
    data = {'influent': pd.DataFrame(), 'effluent': pd.DataFrame()}
    closed = []
    queries = []
    def query(flux):
        queries.append(flux)
        side = 'influent' if 'influent' in flux else 'effluent'
        return data[side].copy()
    client = SimpleNamespace(query_api=lambda: SimpleNamespace(query_data_frame=query), close=lambda: closed.append(True))
    monkeypatch.setattr(influxdb_query, 'get_client_and_bucket', lambda: (client, 'real-test'))
    monkeypatch.setattr(routes, '_plant_overrides', lambda _: {})
    return data, closed, queries


def test_missing_plant_returns_empty_not_500(frames):
    result = asyncio.run(routes.get_plant_dashboard('missing'))['data']
    assert result['effluent_points'] == 0
    assert result['data_context']['freshness'] == 'missing'


def test_all_history_ui_window_is_supported(frames):
    assert asyncio.run(routes.get_plant_dashboard('plant-A', hours=10000))['success']


def test_sorted_latest_values_and_source_context(frames):
    data, closed, queries = frames
    data['effluent'] = pd.DataFrame({'_time': ['2026-07-14T02:00:00Z', '2026-07-14T00:00:00Z'], 'COD': [30., 10.]})
    result = asyncio.run(routes.get_plant_dashboard('plant-A'))['data']
    assert result['indicators']['COD']['effluent'] == 30
    assert result['indicators']['COD']['series']['effluent'][0]['time'] == '2026-07-14 08:00:00'
    assert result['data_context']['origin'] == 'real'
    assert result['data_context']['mode'] == 'historical'
    assert result['influent_points'] == 0
    assert closed
    assert all('plant-A' in q for q in queries)


def test_custom_range_longer_than_seven_days_and_inclusive_end(frames):
    data, _, _ = frames
    data['effluent'] = pd.DataFrame({'_time': ['2026-07-01T00:00:00Z', '2026-07-14T15:00:00Z', '2026-07-14T16:00:00Z'], 'COD': [10., 30., 40.]})
    result = asyncio.run(routes.get_plant_dashboard('plant-A', anchor='2026-07-01', end_date='2026-07-14'))['data']
    assert result['effluent_points'] == 2
    assert result['indicators']['COD']['effluent'] == 30


def test_invalid_range_returns_422_without_client_leak(frames):
    with pytest.raises(Exception) as error:
        asyncio.run(routes.get_plant_dashboard('plant-A', anchor='2026-07-15', end_date='2026-07-01'))
    assert error.value.status_code == 422


def test_list_ph_threshold_is_supported(frames, monkeypatch):
    frames[0]['effluent'] = pd.DataFrame({'_time': ['2026-07-14T00:00:00Z'], 'pH': [10.]})
    monkeypatch.setattr(routes, '_plant_overrides', lambda _: {'limits': {'pH': [6, 9]}})
    assert asyncio.run(routes.get_plant_dashboard('plant-A'))['data']['indicators']['pH']['status'] == 'warning'


def test_unknown_numeric_indicator_is_preserved(frames):
    frames[0]['effluent'] = pd.DataFrame({'_time': ['2026-07-14T00:00:00Z'], 'temperature': [22.], '_source_file': ['report.xls']})
    result = asyncio.run(routes.get_plant_dashboard('plant-A'))['data']['indicators']
    assert result['temperature']['effluent'] == 22
    assert '_source_file' not in result
