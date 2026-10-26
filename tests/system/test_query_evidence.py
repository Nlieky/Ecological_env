import json
import importlib
import importlib.util

def evidence_module():
    assert importlib.util.find_spec("shared.data.query_evidence"), "session evidence renderer is missing"
    return importlib.import_module("shared.data.query_evidence")


def test_empty_or_failed_artifact_does_not_change_response(tmp_path):
    query_evidence = evidence_module()
    assert query_evidence.append_evidence("你好", tmp_path) == "你好"
    (tmp_path / "data_result.json").write_text(json.dumps({"status": "failed"}))
    assert query_evidence.append_evidence("你好", tmp_path) == "你好"


def test_evidence_comes_from_actual_session_snapshot(tmp_path):
    query_evidence = evidence_module()
    artifact = {"status": "completed", "result": {"influent": [], "effluent": [{"timestamp": "2026-07-25 10:00:00"}],
        "metadata": {"plant": "A", "data_context": {"origin": "real", "bucket": "monitoring-real", "mode": "historical"}}}}
    (tmp_path / "data_result.json").write_text(json.dumps(artifact))
    text = query_evidence.append_evidence("研判", tmp_path)
    for expected in ["A", "monitoring-real", "real", "2026-07-25", "data_result.json", "历史", "人工复核", "不等于违规", "沿用"]:
        assert expected in text


def test_malformed_json_shapes_do_not_crash_response(tmp_path):
    query_evidence = evidence_module()
    (tmp_path / "data_result.json").write_text("[]")
    assert query_evidence.append_evidence("你好", tmp_path) == "你好"


def test_simulated_and_partial_multi_plant_evidence_is_labeled(tmp_path):
    query_evidence = evidence_module()
    artifact = {"status": "completed", "result": {"effluent": [{"timestamp": "2026-07-25 10:00:00"}],
        "metadata": {"plant": "A", "data_context": {"origin": "simulated", "bucket": "monitoring-simulation", "mode": "simulation"}}}}
    (tmp_path / "data_result.json").write_text(json.dumps(artifact))
    (tmp_path / "data_result_plants.json").write_text(json.dumps({"B": {"status": "completed", "metadata": {"sampling_range": {"start": "2026-01-01", "end": "2026-01-02"}}},
        "C": {"status": "completed", "metadata": {}}}))
    text = query_evidence.append_evidence("分析", tmp_path)
    assert "模拟演示" in text
    assert "监测点 B" in text and "unverified" in text
    assert "监测点 C" not in text


def test_nested_malformed_artifact_is_ignored(tmp_path):
    query_evidence = evidence_module()
    (tmp_path / "data_result.json").write_text(json.dumps({"status": "completed", "result": [1]}))
    assert query_evidence.append_evidence("你好", tmp_path) == "你好"


def test_successful_plant_survives_failed_last_primary_artifact(tmp_path):
    module = evidence_module()
    (tmp_path / "data_result.json").write_text(json.dumps({"status": "failed"}))
    (tmp_path / "data_result_plants.json").write_text(json.dumps({
        "A": {"status": "completed", "metadata": {"sampling_range": {"start": "2026-07-25 10:00", "end": "2026-07-25 11:00"},
            "data_context": {"origin": "real", "bucket": "monitoring-real", "mode": "historical"}}},
        "B": {"status": "failed", "metadata": {}}}))
    text = module.append_evidence("多厂分析", tmp_path)
    assert "监测点 A" in text and "monitoring-real" in text
    assert "data_result_plants.json" in text and "历史" in text
    assert "监测点 B" not in text


def test_malformed_plant_metadata_and_invalid_sampling_are_skipped(tmp_path):
    module = evidence_module()
    (tmp_path / "data_result_plants.json").write_text(json.dumps({
        "A": {"status": "completed", "metadata": [1]},
        "B": {"status": "completed", "metadata": {"sampling_range": {"start": "bad", "end": "bad"}}},
        "C": {"status": "completed", "metadata": {"sampling_range": {"start": "2026-07-25", "end": "2026-07-26"}, "data_context": [1]}}}))
    text = module.append_evidence("分析", tmp_path)
    assert "监测点 C" in text and "unverified" in text and "未知" in text and "来源未核实" in text
    assert "监测点 A" not in text and "监测点 B" not in text


def test_origin_without_bucket_is_incomplete_evidence(tmp_path):
    module = evidence_module()
    (tmp_path / "data_result_plants.json").write_text(json.dumps({
        "A": {"status": "completed", "metadata": {"sampling_range": {"start": "2026-07-25", "end": "2026-07-26"},
            "data_context": {"origin": "real", "mode": "historical"}}}}))
    text = module.append_evidence("分析", tmp_path)
    assert "来源 unverified" in text and "bucket `未知`" in text
    assert "历史真实数据" not in text
