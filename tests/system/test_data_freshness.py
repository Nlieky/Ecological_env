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
        _rows("2026-09-30T10:00:00+00:00"), [], requested_relative=True, now=now, stale_after_hours=6
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


def test_naive_sampling_time_always_means_shanghai_not_now_timezone():
    result = MODULE.assess_data_freshness(_rows("2026-09-30 10:00:00"), [],
        requested_relative=True, now=datetime(2026, 9, 30, 12, tzinfo=timezone.utc))
    assert result["lag_hours"] == 10
    assert result["actual_end"].endswith("+08:00")


def test_hours_are_elapsed_and_both_sides_share_latest(monkeypatch):
    import pandas as pd
    frames = {"influent": pd.DataFrame({"COD": [1, 2]}, index=pd.to_datetime(["2026-07-01", "2026-07-10"])),
              "effluent": pd.DataFrame({"COD": [3]}, index=pd.to_datetime(["2026-07-11"]))}
    monkeypatch.setattr(MODULE, "_fetch_df", lambda client, bucket, side, plant: frames[side])
    rows_in, rows_out, bounds = MODULE.get_data_window(None, "monitoring-real", "A", hours_back=24)
    assert [r["COD"] for r in rows_in] == [2]
    assert [r["COD"] for r in rows_out] == [3]
    assert str(bounds[0]) == "2026-07-10 00:00:00"


def test_unscoped_fetch_is_rejected_before_query():
    import pytest
    with pytest.raises(ValueError, match="plant"):
        MODULE._fetch_df(None, "monitoring-real", "influent")


def test_explicit_utc_range_aligns_to_local_sampling(monkeypatch):
    import pandas as pd
    frame = pd.DataFrame({"COD": [1, 2]}, index=pd.to_datetime(["2026-07-10 08:00", "2026-07-10 09:00"]))
    monkeypatch.setattr(MODULE, "_fetch_df", lambda *args: frame)
    rows = MODULE.get_data_by_range(None, "monitoring-real", "effluent", "2026-07-10T00:00Z", "2026-07-10T00:00Z", "A")
    assert len(rows) == 1


def test_missing_points_use_actual_common_window_even_empty_side():
    missing = MODULE._compute_missing_points([], True, "2026-07-10 00:00", "2026-07-10 02:00", 2)
    assert missing == ["2026-07-10 00:00:00", "2026-07-10 01:00:00", "2026-07-10 02:00:00"]

