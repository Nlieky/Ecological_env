import importlib.util
from pathlib import Path
import pandas as pd
import pytest

PATH = Path(__file__).resolve().parents[2] / "subagents/anomaly-detection-agent/skills/anomaly-detection-core/scripts/run_anomaly_detection_simple.py"
SPEC = importlib.util.spec_from_file_location("anomaly_sampling_window", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_unscoped_detector_fetch_is_rejected():
    with pytest.raises(ValueError, match="plant"):
        MODULE._fetch_influx_cn(None, "monitoring-real", "influent")


def test_direct_fallback_closes_client_after_query_failure(monkeypatch):
    import influxdb_client
    closed = []
    class Client:
        def __init__(self, **kwargs): pass
        def close(self): closed.append(True)
    monkeypatch.setattr(influxdb_client, 'InfluxDBClient', Client)
    monkeypatch.setattr(MODULE, '_load_influx_env', lambda: None)
    monkeypatch.setenv('INFLUXDB_TOKEN', 'test')
    monkeypatch.setenv('DETECTOR_PLANT', 'A')
    monkeypatch.delenv('SESSION_DIR', raising=False)
    monkeypatch.setattr(MODULE, '_fetch_influx_cn', lambda *args: (_ for _ in ()).throw(RuntimeError('offline')))
    assert MODULE.load_recent_data(24)['effluent_df'].empty
    assert closed == [True]


def test_direct_fallback_uses_elapsed_combined_sampling_window(monkeypatch):
    import influxdb_client
    class Client:
        def __init__(self, **kwargs): pass
        def close(self): pass
    monkeypatch.setattr(influxdb_client, "InfluxDBClient", Client)
    monkeypatch.setattr(MODULE, "_load_influx_env", lambda: None)
    monkeypatch.setenv("INFLUXDB_TOKEN", "test")
    monkeypatch.setenv("DETECTOR_PLANT", "A")
    monkeypatch.delenv("SESSION_DIR", raising=False)
    frames = {"influent": pd.DataFrame({"监测时间": pd.to_datetime(["2026-07-01", "2026-07-10"]), "pH值": [6, 7]}),
              "effluent": pd.DataFrame({"监测时间": pd.to_datetime(["2026-07-11"]), "pH值": [8]})}
    monkeypatch.setattr(MODULE, "_fetch_influx_cn", lambda client, bucket, side, plant: frames[side])
    result = MODULE.load_recent_data(24)
    assert list(result["influent_df"]["pH值"]) == [7]


def test_main_direct_fallback_honors_requested_hours(monkeypatch, tmp_path):
    monkeypatch.setenv("SESSION_DIR", str(tmp_path))
    monkeypatch.setattr(MODULE.sys, "argv", ["run_anomaly_detection_simple.py", "--hours", "72"])
    monkeypatch.setattr(MODULE, "load_data_from_result", lambda: None)
    received = []
    def fallback(hours):
        received.append(hours)
        raise ValueError("stop before detection")
    monkeypatch.setattr(MODULE, "load_recent_data", fallback)
    with pytest.raises(SystemExit):
        MODULE.main()
    assert received == [72]
