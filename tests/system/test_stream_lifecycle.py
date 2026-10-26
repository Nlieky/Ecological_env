"""Exercise the real stream entrypoint with a fake Agent, without model startup."""
import ast
import importlib.util
import queue
import asyncio
import json
import logging
import threading
import time
import uuid
from pathlib import Path
from types import SimpleNamespace

from fastapi.responses import StreamingResponse
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[2]


def stream_entrypoint(service, clock=time, classifier=None, inject_context=True):
    tree = ast.parse((ROOT / 'scripts/start_agent.py').read_text(encoding='utf-8'))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'query_stream')
    fn.decorator_list = []
    context_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_query_view_context')
    reserved_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_reject_reserved_session')
    namespace = dict(agent_service=service, QueryRequest=object, time=clock, uuid=uuid,
                     threading=threading, StreamingResponse=StreamingResponse,
                     _try_shortcircuit=classifier or (lambda *a, **k: None), _apply_style_strategy=lambda a: None,
                     _gp=lambda *a, **k: 10, append_evidence=lambda c, p: c,
                     logger=logging.getLogger(__name__), _gst=lambda *a: inject_context, json=json,
                     HTTPException=HTTPException)
    exec(compile(ast.Module(body=[reserved_fn, context_fn, fn], type_ignores=[]), 'start_agent.py', 'exec'), namespace)
    return namespace['query_stream']


def collect(response):
    async def read():
        return [json.loads(frame[6:]) async for frame in response.body_iterator if frame.startswith('data:')]
    return asyncio.run(read())


def service_with(lock, begin=True):
    marker = object()
    tool = SimpleNamespace(_current_progress_queue=marker,
                           _run_detector_handler=SimpleNamespace(_view_context={'active': True}))
    service = SimpleNamespace(_tool_reg=tool, _agent_lock=lock, _agent_lock_timeout=1,
        _begin_agent_turn=lambda: begin, _fresh_session_dir=lambda sid: None,
        _cur_session_dir=lambda sid: None, _session_dirs={}, session_histories={},
        _turn_guard=SimpleNamespace(finish=lambda: None),
        master_agent=SimpleNamespace(run_conversation=lambda **k: {'final_response': 'answer'}))
    return service, marker


def request():
    return SimpleNamespace(query='q', session_id='s', view_context='{"waiting":true}', mode=None)


def test_waiting_request_cannot_change_active_progress_routing():
    acquired = threading.Event()
    class BusyLock:
        def acquire(self, **kwargs):
            acquired.set()
            return False
    service, marker = service_with(BusyLock())
    events = collect(stream_entrypoint(service)(request()))
    assert acquired.is_set()
    assert service._tool_reg._current_progress_queue is marker
    assert service._tool_reg._run_detector_handler._view_context == {'active': True}
    assert events[-1]['type'] == 'error'
    assert events[-1]['queue_elapsed_ms'] >= 0


def test_rejected_turn_leaves_active_routing_untouched():
    service, marker = service_with(threading.Lock(), begin=False)
    events = collect(stream_entrypoint(service)(request()))
    assert service._tool_reg._current_progress_queue is marker
    assert events[-1]['type'] == 'error'


def test_completed_turn_exposes_measured_queue_and_turn_duration():
    service, _ = service_with(threading.Lock())
    events = collect(stream_entrypoint(service)(request()))
    assert events[-1]['type'] == 'done'
    assert events[-1]['queue_elapsed_ms'] >= 0
    assert events[-1]['turn_elapsed_ms'] >= 0
    assert service._tool_reg._current_progress_queue is None


def test_disabled_context_reaches_neither_stream_tool_nor_agent():
    service, _ = service_with(threading.Lock())
    observed = []
    service.master_agent.run_conversation = lambda **k: observed.append(k) or {'final_response': 'answer'}
    req = request()
    req.view_context = '{"anchor":"2026-10-01","segmentStart":"a"}'
    events = collect(stream_entrypoint(service, inject_context=False)(req))
    assert events[-1]['type'] == 'done'
    assert observed[0]['user_message'] == 'q'
    assert service._tool_reg._run_detector_handler._view_context == {}


def test_subagent_done_duration_is_measured(monkeypatch):
    path = ROOT / 'skills/orchestrator-core/scripts/tool_registration.py'
    spec = importlib.util.spec_from_file_location('timed_tool_registration', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module._current_progress_queue = queue.Queue()
    monkeypatch.setattr(module, 'call_subagent', lambda **k: {'status': 'completed'})
    module._call_subagent_handler({'subagent_name': 'anomaly-detection', 'task': 'fake'})
    start = module._current_progress_queue.get_nowait()
    done = module._current_progress_queue.get_nowait()
    assert start['stage'] == 'start'
    assert done['stage'] == 'done'
    assert done['elapsed_ms'] >= 0


def test_agent_failure_is_a_terminal_error_not_an_empty_success():
    service, _ = service_with(threading.Lock())
    service.master_agent.run_conversation = lambda **k: {'success': False, 'error': 'model failed'}
    events = collect(stream_entrypoint(service)(request()))
    assert events[-1]['type'] == 'error'
    assert events[-1]['message'] == 'model failed'


def test_busy_queue_duration_excludes_classifier_runtime():
    clock = SimpleNamespace(value=10.0)
    clock.monotonic = lambda: clock.value
    def classifier(*a, **k):
        clock.value += 5.0
    class BusyLock:
        def acquire(self, **kwargs):
            clock.value += 0.25
            return False
    service, _ = service_with(BusyLock())
    events = collect(stream_entrypoint(service, clock, classifier)(request()))
    assert events[-1]['queue_elapsed_ms'] == 250.0
