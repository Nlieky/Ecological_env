"""Scoped plugin isolation; never discover real user plugins or use credentials."""
from contextlib import nullcontext
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading
import pytest


@pytest.fixture
def plugins(monkeypatch, tmp_path):
    monkeypatch.setenv('HERMES_HOME', str(tmp_path))
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / 'shared/framework/hermes-agent'))
    from hermes_cli import plugins
    manager = plugins.PluginManager()
    manager._hooks['on_session_start'] = [lambda **kw: 'hook-ran']
    manager._middleware['pre_llm'] = [lambda **kw: 'middleware-ran']
    monkeypatch.setattr(plugins, '_plugin_manager', manager)
    return plugins


def test_suppressed_callbacks_do_not_disable_overlapping_professional_thread(plugins):
    entered, release = threading.Event(), threading.Event()
    def sidebar():
        with getattr(plugins, 'suppress_hooks', nullcontext)():
            entered.set()
            assert release.wait(3)
            return (plugins.has_hook('on_session_start'), plugins.invoke_hook('on_session_start'),
                    plugins.has_middleware('pre_llm'), plugins.invoke_middleware('pre_llm'))
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(sidebar)
        try:
            assert entered.wait(3)
            assert plugins.invoke_hook('on_session_start') == ['hook-ran']
            assert plugins.invoke_middleware('pre_llm') == ['middleware-ran']
        finally:
            release.set()
        assert pending.result() == (False, [], False, [])
    assert plugins.has_hook('on_session_start')


def test_suppression_nested_exception_restores_outer_and_default_context(plugins):
    scope = getattr(plugins, 'suppress_hooks', nullcontext)
    with scope():
        with pytest.raises(RuntimeError):
            with scope():
                raise RuntimeError('fixture')
        assert plugins.invoke_hook('on_session_start') == []
    assert plugins.invoke_hook('on_session_start') == ['hook-ran']


def test_suppression_blocks_custom_context_engine_discovery(plugins, monkeypatch, tmp_path):
    from plugins import context_engine
    sentinel = object()
    (tmp_path / 'fixture').mkdir()
    monkeypatch.setattr(context_engine, '_CONTEXT_ENGINE_PLUGINS_DIR', tmp_path)
    monkeypatch.setattr(context_engine, '_load_engine_from_dir', lambda path: sentinel)
    class Manager:
        _context_engine = sentinel
    monkeypatch.setattr(plugins, '_ensure_plugins_discovered', lambda: Manager())
    with getattr(plugins, 'suppress_hooks', nullcontext)():
        assert context_engine.load_context_engine('fixture') is None
        assert plugins.get_plugin_context_engine() is None
    assert context_engine.load_context_engine('fixture') is sentinel
    assert plugins.get_plugin_context_engine() is sentinel


def test_restricted_session_never_overwrites_professional_environment(plugins, monkeypatch):
    from gateway import session_context
    import os
    monkeypatch.setenv('HERMES_SESSION_ID', 'professional')
    with plugins.suppress_hooks():
        session_context.set_current_session_id('sidebar')
        assert session_context.get_session_env('HERMES_SESSION_ID') == 'sidebar'
        assert os.environ['HERMES_SESSION_ID'] == 'professional'


def test_restricted_aux_routing_does_not_change_professional_defaults(plugins, monkeypatch):
    from agent import auxiliary_client
    monkeypatch.setattr(auxiliary_client, '_RUNTIME_MAIN_MODEL', 'professional')
    with plugins.suppress_hooks():
        auxiliary_client.set_runtime_main('fixture', 'sidebar')
    assert auxiliary_client._RUNTIME_MAIN_MODEL == 'professional'


def test_restricted_tool_selection_does_not_overwrite_professional_catalog(plugins, monkeypatch):
    import model_tools
    monkeypatch.setattr(model_tools, '_last_resolved_tool_names', ['professional-tool'])
    with plugins.suppress_hooks():
        assert model_tools.get_tool_definitions(enabled_toolsets=[], quiet_mode=True) == []
    assert model_tools._last_resolved_tool_names == ['professional-tool']


def test_restricted_log_previews_do_not_include_page_or_query_text(plugins):
    from agent.codex_responses_adapter import _summarize_user_message_for_log
    private = '{"query":"private-question","context":{"plant":"private-plant"}}'
    with plugins.suppress_hooks():
        result = _summarize_user_message_for_log(private)
        assert 'private-question' not in result
        assert 'private-plant' not in result
    assert _summarize_user_message_for_log('ordinary preview') == 'ordinary preview'
