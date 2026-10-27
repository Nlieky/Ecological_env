import ast
import asyncio
import json
import logging
import time
from pathlib import Path
from types import SimpleNamespace

import httpx
from fastapi.responses import StreamingResponse


def proxy_entrypoint(chunks, records, logs, fail=False, executions=None):
    path = Path(__file__).resolve().parents[2] / 'backend/api/routes/query.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    fn = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'query_stream')
    fn.decorator_list = []
    class Response:
        status_code = 200
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def aiter_text(self):
            for chunk in chunks: yield chunk
            if fail: raise httpx.ReadError('lost')
    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        def stream(self, *args, **kwargs): return Response()
    namespace = dict(QueryRequest=object, time=time, json=json, httpx=SimpleNamespace(AsyncClient=Client, Timeout=httpx.Timeout),
        StreamingResponse=StreamingResponse, generate_session_id=lambda: 'generated', _agent_timeout=lambda: 30,
        AGENT_SERVICE_URL='http://fake', conversation_service=SimpleNamespace(record_exchange=lambda **k: records.append(k)),
        event_service=SimpleNamespace(collect_from_session=lambda *a, **k: None), _ran_disposition=lambda a: False,
        log_master_decision=lambda **k: logs.append(k), log_subagent_execution=lambda **k: executions.append(k) if executions is not None else None,
        logger=logging.getLogger(__name__))
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace['query_stream']


def req(): return SimpleNamespace(query='q', session_id='s', view_context=None, mode=None)


def test_proxy_persists_before_delivering_done_even_with_mixed_chunk():
    records, logs = [], []
    fn = proxy_entrypoint(['data:{"type":"delta","text":"partial"}\r\n\r\ndata:{"type":"done","content":"answer","session_id":"s"}\r', '\n\r\n'], records, logs)
    async def run():
        response = await fn(req())
        frames = []
        async for frame in response.body_iterator:
            frames.append(frame)
            if '"done"' in frame:
                assert len(records) == 1
                assert len(logs) == 1
                break
        await response.body_iterator.aclose()
        assert any('"delta"' in frame for frame in frames)
        assert records[0]['assistant_response'] == 'answer'
    asyncio.run(run())


def test_proxy_eof_without_done_is_error_without_success_persistence():
    records, logs = [], []
    fn = proxy_entrypoint(['data:{"type":"delta","text":"partial"}\n\n'], records, logs)
    async def run():
        response = await fn(req())
        frames = [f async for f in response.body_iterator]
        assert '"error"' in frames[-1]
    asyncio.run(run())
    assert records == logs == []


def test_proxy_network_failure_is_terminal_error():
    records, logs = [], []
    fn = proxy_entrypoint([], records, logs, fail=True)
    async def run():
        response = await fn(req())
        frames = [f async for f in response.body_iterator]
        assert '"error"' in frames[-1]
    asyncio.run(run())
    assert records == logs == []


def test_proxy_preserves_unknown_subagent_duration_in_audit():
    executions = []
    fn = proxy_entrypoint(['data:{"type":"progress","subagent":"anomaly-detection","stage":"done"}\n\ndata:{"type":"done","content":"answer"}\n\n'], [], [], executions=executions)
    async def run():
        response = await fn(req())
        return [f async for f in response.body_iterator]
    asyncio.run(run())
    assert executions[0]['execution_time_ms'] is None
