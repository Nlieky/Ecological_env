from pathlib import Path
import asyncio
import pytest


@pytest.mark.parametrize('status,word', [(409, '繁忙'), (504, '超时')])
def test_proxy_configured_url_and_private_status(monkeypatch, status, word):
    from backend.services import assistant_service
    from backend.core.config import settings
    from backend.models.assistant import RespondRequest
    from fastapi import HTTPException
    calls = []
    monkeypatch.setattr(settings, 'AGENT_SERVICE_URL', 'http://configured.invalid:9000/')
    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, **kwargs):
            calls.append(url)
            return assistant_service.httpx.Response(status, json={'detail':'secret'})
    monkeypatch.setattr(assistant_service.httpx, 'AsyncClient', Client)
    with pytest.raises(HTTPException) as error:
        asyncio.run(assistant_service.respond(RespondRequest(query='x', session_id='s')))
    assert calls == ['http://configured.invalid:9000/system-assistant/respond']
    assert error.value.status_code == status
    assert word in error.value.detail and 'secret' not in error.value.detail


def test_backend_must_proxy_existing_agent_service():
    source = Path('backend/services/assistant_service.py').read_text(encoding='utf-8')
    assert '/system-assistant/respond' in source
    assert '/chat/completions' not in source


def test_runtime_is_separate_from_professional_lock():
    source = Path('scripts/start_agent.py').read_text(encoding='utf-8')
    assert 'SystemInteractionRuntime' in source
    assert 'def _create_main_agent(' in source
