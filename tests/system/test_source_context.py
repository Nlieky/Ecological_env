from datetime import datetime, timezone

import pytest

from shared.data.source_context import describe_data_context, simulation_bucket, sampling_timestamp


def test_unknown_legacy_bucket_is_not_claimed_real(monkeypatch):
    monkeypatch.setenv('INFLUXDB_REAL_BUCKET', 'real-test')
    result = describe_data_context('monitoring-data', '2026-07-14T00:00:00Z')
    assert result['origin'] == 'unverified'
    assert result['mode'] == 'unverified'
    assert result['warning']


def test_file_history_is_not_a_service_failure(monkeypatch):
    monkeypatch.setenv('INFLUXDB_REAL_BUCKET', 'real-test')
    monkeypatch.setenv('BUSINESS_DATA_MODE', 'historical')
    result = describe_data_context('real-test', '2026-07-14T00:00:00Z', now=datetime(2026, 10, 8, tzinfo=timezone.utc))
    assert result['origin'] == 'real'
    assert result['freshness'] == 'historical'
    assert result['lag_hours'] > 1000
    assert result['latest_sample_at'].endswith('+08:00')


def test_simulation_has_separate_time_semantics(monkeypatch):
    monkeypatch.setenv('INFLUXDB_SIMULATION_BUCKET', 'sim-test')
    result = describe_data_context('sim-test', '2030-01-01T00:00:00Z')
    assert result['origin'] == 'simulated'
    assert result['mode'] == 'simulation'
    assert result['freshness'] == 'simulation'


def test_simulator_rejects_business_bucket(monkeypatch):
    monkeypatch.setenv('INFLUXDB_BUCKET', 'real-test')
    monkeypatch.setenv('INFLUXDB_REAL_BUCKET', 'real-test')
    monkeypatch.setenv('INFLUXDB_SIMULATION_BUCKET', 'real-test')
    with pytest.raises(ValueError):
        simulation_bucket()


def test_explicit_timezone_is_not_shifted_twice(monkeypatch):
    monkeypatch.setenv('DATA_TIMEZONE', 'Asia/Shanghai')
    assert sampling_timestamp('2026-07-14T08:00:00+08:00').isoformat() == '2026-07-14T08:00:00+08:00'


def test_future_live_timestamp_is_flagged(monkeypatch):
    monkeypatch.setenv('INFLUXDB_REAL_BUCKET', 'real-test')
    monkeypatch.setenv('BUSINESS_DATA_MODE', 'live')
    result = describe_data_context('real-test', '2030-01-01T00:00:00Z', now=datetime(2026, 10, 8, tzinfo=timezone.utc))
    assert result['freshness'] == 'future'


def test_no_sample_is_missing_not_online(monkeypatch):
    monkeypatch.setenv('INFLUXDB_REAL_BUCKET', 'real-test')
    assert describe_data_context('real-test', None)['freshness'] == 'missing'
