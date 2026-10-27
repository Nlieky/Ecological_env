import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "orchestrator-core" / "scripts"
sys.path.insert(0, str(SCRIPTS))


def test_all_aliases_resolve_to_one_canonical_contract():
    from subagent_registry import resolve_subagent

    cases = {
        "multi-dimensional-data-perception": ("multi-dimensional-data-perception", "data_result.json"),
        "data-perception": ("multi-dimensional-data-perception", "data_result.json"),
        "anomaly": ("anomaly-detection", "anomaly_result.json"),
        "rule": ("rule-reasoning", "rule_reasoning_result.json"),
        "disposition": ("disposition-execution", "disposition_result.json"),
    }
    for supplied, expected in cases.items():
        spec = resolve_subagent(supplied)
        assert (spec.name, spec.result_file) == expected


def test_prepare_result_target_removes_only_current_stage_output(tmp_path):
    from subagent_registry import prepare_result_target

    stale_target = tmp_path / "anomaly_result.json"
    upstream = tmp_path / "data_result.json"
    stale_target.write_text('{"status":"completed","task_id":"old"}', encoding="utf-8")
    upstream.write_text('{"status":"completed","task_id":"context"}', encoding="utf-8")

    prepare_result_target(tmp_path, "anomaly_result.json")

    assert not stale_target.exists()
    assert upstream.exists()


def test_failed_preflight_cannot_leave_carried_target_as_current(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location(
        "call_subagent_for_test", SCRIPTS / "call_subagent.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    target = tmp_path / "data_result.json"
    target.write_text('{"status":"completed","task_id":"old"}', encoding="utf-8")
    monkeypatch.setattr(module, "get_session_dir", lambda: str(tmp_path))
    monkeypatch.setattr(module, "_project_root", lambda: ROOT)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    result = module.call_subagent(
        subagent_name="data-perception", task="获取最近24小时数据"
    )

    assert result["status"] == "failed"
    assert not target.exists()


def test_subagent_tool_filter_is_read_execute_only():
    from subagent_registry import filter_subagent_tools

    tools = [
        {"function": {"name": "skill_view"}},
        {"function": {"name": "skills_list"}},
        {"function": {"name": "skill_manage"}},
        {"function": {"name": "terminal"}},
        {"function": {"name": "browser_navigate"}},
    ]
    filtered = filter_subagent_tools(tools)
    names = {item["function"]["name"] for item in filtered}
    assert names == {"skill_view", "skills_list", "terminal"}


def test_compact_result_exposes_stale_warning_to_master():
    spec = importlib.util.spec_from_file_location(
        "tool_registration_for_test", SCRIPTS / "tool_registration.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = {
        "status": "completed",
        "result": {
            "influent": [{"timestamp": "2026-07-25 00:00:00", "pH": 7.0}],
            "effluent": [],
            "metadata": {
                "time_range": "最近24小时",
                "data_context": {"origin": "real", "mode": "historical"},
                "sampling_range": {"start": "2026-07-24T00:00:00+08:00", "end": "2026-07-25T00:00:00+08:00"},
                "freshness": {
                    "is_stale": True,
                    "warning": "最新数据已停更",
                },
            },
        },
    }

    compact = module._compact_result_for_master(result)

    assert compact["freshness"]["is_stale"] is True
    assert compact["summary"].startswith("⚠️ 数据已停更")
    assert compact['data_context']['mode'] == 'historical'
    assert compact['sampling_range']['end'] == '2026-07-25T00:00:00+08:00'


def test_compact_empty_sides_do_not_report_successful_chart():
    spec = importlib.util.spec_from_file_location('tool_registration_empty_test', SCRIPTS / 'tool_registration.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module._compact_result_for_master({'status': 'completed', 'result': {'influent': [], 'effluent': []}})
    assert 'chart_generated' not in result
    assert 'data_stats' not in result

