import asyncio
import json
from types import SimpleNamespace
import pytest
from fastapi import HTTPException


def test_detection_rejects_different_source_before_subprocess(monkeypatch):
    from backend.api.v1.detection import routes
    from backend.core.config import settings
    monkeypatch.setattr(settings, 'INFLUXDB_BUCKET', 'expected-real')
    calls = []
    monkeypatch.setattr(routes.subprocess, 'run', lambda *a, **k: calls.append(a) or SimpleNamespace(stdout=json.dumps({'status': 'completed'})))
    with pytest.raises(HTTPException) as error:
        asyncio.run(routes.run_detection(routes.DetectRequest(algorithm='iforest', indicator='TN', plant='A', start='2026-07-01', end='2026-07-02', side='influent', source='different-simulation')))
    assert error.value.status_code == 400
    assert calls == []


def test_detection_reports_actual_execution_binding(monkeypatch):
    from backend.api.v1.detection import routes
    from backend.core.config import settings
    monkeypatch.setattr(settings, 'INFLUXDB_BUCKET', 'expected-real')
    monkeypatch.setattr(routes.subprocess, 'run', lambda *a, **k: SimpleNamespace(stdout=json.dumps({'status': 'completed', 'actionData': {'annotations': []}})))
    result = asyncio.run(routes.run_detection(routes.DetectRequest(algorithm='constant', indicator='TN', plant='B', start='2026-07-01 00:00:00', end='2026-07-02 00:00:00', side='effluent', source='expected-real')))
    assert result['data']['execution_context'] == {'algorithm': 'constant', 'indicator': 'TN', 'plant': 'B', 'start': '2026-07-01 00:00:00', 'end': '2026-07-02 00:00:00', 'side': 'effluent', 'source': 'expected-real'}


def test_detector_subprocess_does_not_block_api_event_loop(monkeypatch):
    import threading
    from backend.api.v1.detection import routes
    main = threading.get_ident()
    calls = []
    def run(*args, **kwargs):
        calls.append(threading.get_ident())
        return SimpleNamespace(stdout=json.dumps({'status': 'completed', 'actionData': {'annotations': []}}))
    monkeypatch.setattr(routes.subprocess, 'run', run)
    asyncio.run(routes.run_detection(routes.DetectRequest()))
    assert calls and calls[0] != main


def test_detector_plant_catalog_drops_mixed_value_before_grouping():
    import importlib.util
    from pathlib import Path
    path = Path('skills/action-command-core/scripts/run_detector.py')
    spec = importlib.util.spec_from_file_location('operation_detector_catalog', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    captured = []
    def query(flux):
        captured.append(flux)
        return [SimpleNamespace(records=[SimpleNamespace(values={'plant_id': '厂甲'})])]
    client = SimpleNamespace(query_api=lambda: SimpleNamespace(query=query))
    assert module.resolve_plant(client, 'real', '厂甲') == '厂甲'
    assert captured[0].index('keep(columns: ["plant_id"])') < captured[0].index('group(')


@pytest.mark.parametrize('end,expected', [('2026-07-02 00:00:00', 2), ('2026-07-02', 3)])
def test_explicit_midnight_window_is_not_extended(monkeypatch, end, expected):
    import importlib.util
    from pathlib import Path
    import pandas as pd
    import influxdb_client
    from shared.data import influxdb_query
    path = Path('skills/action-command-core/scripts/run_detector.py')
    spec = importlib.util.spec_from_file_location('operation_detector_window', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'resolve_plant', lambda client, bucket, name: name)
    monkeypatch.setattr(influxdb_client, 'InfluxDBClient', lambda **kwargs: SimpleNamespace(close=lambda: None))
    frame = pd.DataFrame({'TN': [1., 2., 3.]}, index=pd.to_datetime(['2026-07-01 12:00:00', '2026-07-02 00:00:00', '2026-07-02 12:00:00']))
    monkeypatch.setattr(influxdb_query, 'fetch_wastewater_df', lambda *args, **kwargs: frame)
    result = module.load_series('TN', '2026-07-01 00:00:00', end, 'influent', '厂A')
    assert len(result) == expected
