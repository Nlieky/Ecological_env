import importlib.util
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "subagents" / "multi-dimensional-data-perception-agent" / "skills" / "data-perception-core" / "scripts" / "get_data.py"
SPEC = importlib.util.spec_from_file_location("get_data_freshness", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _rows(timestamp: str):
    return [{"timestamp": timestamp, "pH": 7.0}]


def test_relative_window_marks_old_data_stale():
    now = datetime(2026, 9, 30, 12, tzinfo=timezone.utc)
    result = MODULE.assess_data_freshness(
        _rows("2026-07-25 12:00:00"), [], requested_relative=True, now=now, stale_after_hours=6
    )
    assert result["is_stale"] is True
    assert result["lag_hours"] > 1000
    assert result["warning"]


def test_relative_window_marks_recent_data_fresh():
    now = datetime(2026, 9, 30, 12, tzinfo=timezone.utc)
    result = MODULE.assess_data_freshness(
        _rows("2026-09-30 10:00:00"), [], requested_relative=True, now=now, stale_after_hours=6
    )
    assert result["is_stale"] is False
    assert result["warning"] is None


def test_explicit_historical_range_is_not_mislabeled_stale():
    now = datetime(2026, 9, 30, 12, tzinfo=timezone.utc)
    result = MODULE.assess_data_freshness(
        _rows("2026-01-01 10:00:00"), [], requested_relative=False, now=now, stale_after_hours=6
    )
    assert result["is_stale"] is False
    assert result["mode"] == "historical"


def test_empty_dataset_has_no_actual_bounds():
    result = MODULE.assess_data_freshness([], [], requested_relative=True)
    assert result["actual_start"] is None
    assert result["actual_end"] is None
    assert result["is_stale"] is None

