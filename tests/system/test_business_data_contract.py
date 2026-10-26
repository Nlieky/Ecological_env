from datetime import datetime, timezone
import random
from types import SimpleNamespace

import pandas as pd

from shared.data import import_to_influxdb as importer
from shared.data import data_simulator as simulator
from shared.data.influxdb_query import fetch_wastewater_df


def test_report_sampling_time_is_beijing_not_utc(monkeypatch):
    monkeypatch.setenv('DATA_TIMEZONE', 'Asia/Shanghai')
    assert importer._to_utc('2026-07-14T08:00:00') == datetime(2026, 7, 14, tzinfo=timezone.utc)


def test_import_records_traceable_origin_without_changing_series_per_file(monkeypatch, tmp_path):
    path = tmp_path / 'report.xls'
    path.write_bytes(b'original report')
    monkeypatch.setattr(importer, 'parse_xls_report', lambda _: ('plant-A', 'effluent', [{'time': '2026-07-14T08:00:00', 'COD': 30}]))
    _, _, points = importer.build_points(str(path))
    line = points[0].to_line_protocol()
    assert 'data_origin=real' in line.split(' ')[0]
    assert '_source_file="report.xls"' in line
    assert '_source_sha256=' in line
    assert '_ingestion_method="file"' in line
    assert 'source_file=' not in line.split(' ')[0]


def test_simulation_points_are_explicitly_simulated():
    line = simulator.build_points_at(datetime(2026, 7, 14, tzinfo=timezone.utc), random.Random(1))[0].to_line_protocol()
    assert 'data_origin=simulated' in line.split(' ')[0]


def test_query_returns_local_sampling_time_and_preserves_missing_sides(monkeypatch):
    monkeypatch.setenv('DATA_TIMEZONE', 'Asia/Shanghai')
    frame = pd.DataFrame({'_time': ['2026-07-14T00:00:00Z'], 'COD': [30.]})
    client = SimpleNamespace(query_api=lambda: SimpleNamespace(query_data_frame=lambda _: frame))
    result = fetch_wastewater_df(client, 'real-test', 'effluent', ['COD'], plant_id='plant-A')
    assert result.index[0] == pd.Timestamp('2026-07-14 08:00:00')
    assert result.iloc[0]['COD'] == 30


def test_system_status_does_not_claim_historical_plant_online(monkeypatch):
    from backend.api.v1.system import routes
    monkeypatch.setenv('INFLUXDB_BUCKET', 'real-test')
    monkeypatch.setenv('INFLUXDB_REAL_BUCKET', 'real-test')
    monkeypatch.setenv('BUSINESS_DATA_MODE', 'historical')
    monkeypatch.setattr('shared.data.discover_plants.discover_plants', lambda: [{'plant_id': 'A', 'latest_time': '2026-07-14T00:00:00Z', 'data_types': ['effluent']}])
    monkeypatch.setattr(routes, '_probe_services', lambda: [])
    plant = routes._build_status_data()['data']['plants'][0]
    assert plant['status'] == 'historical'
    assert plant['data_context']['origin'] == 'real'
    assert plant['latest_time'] == '2026-07-14 08:00'


def test_system_daily_history_uses_sampling_timezone_and_source(monkeypatch):
    import asyncio
    from backend.api.v1.system import routes
    queries = []
    def query(flux):
        queries.append(flux)
        return pd.DataFrame({'_time': ['2026-07-14T16:00:00Z'], 'data_type': ['effluent'], 'COD': [30.]})
    client = SimpleNamespace(query_api=lambda: SimpleNamespace(query_data_frame=query), close=lambda: None)
    monkeypatch.setenv('INFLUXDB_REAL_BUCKET', 'real-test')
    monkeypatch.setattr('shared.data.influxdb_query.get_client_and_bucket', lambda: (client, 'real-test'))
    result = asyncio.run(routes.get_system_history())['data']
    assert result[0]['day'] == '2026-07-15'
    assert 'r.data_origin == "real"' in queries[0]


def test_plant_discovery_uses_source_filter(monkeypatch):
    from shared.data.discover_plants import discover_plants
    queries = []
    def query(flux):
        queries.append(flux)
        return []
    client = SimpleNamespace(query_api=lambda: SimpleNamespace(query=query), close=lambda: None)
    monkeypatch.setenv('INFLUXDB_REAL_BUCKET', 'real-test')
    monkeypatch.setattr('shared.data.influxdb_query.get_client_and_bucket', lambda: (client, 'real-test'))
    assert discover_plants() == []
    assert 'r.data_origin == "real"' in queries[0]
    # Provenance strings and numeric pollutants cannot share an Influx _value group.
    assert queries[0].index('keep(columns:') < queries[0].index('group(columns:')


def test_simulator_discovery_and_latest_do_not_group_mixed_value_types():
    queries = []
    def query(flux):
        queries.append(flux)
        return []
    client = SimpleNamespace(query_api=lambda: SimpleNamespace(query=query))
    assert simulator.discover_plants_sides(client, 'monitoring-real') == {}
    assert simulator.query_latest(client, 'monitoring-simulation', 'A') is None
    for query in queries:
        assert query.index('keep(columns:') < query.index('group(')
