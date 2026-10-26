from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.models.conversation import Conversation, ConversationStatus
from backend.services.conversation_service import ConversationService
from backend.api.v1.conversations import conversations as routes


@pytest.fixture
def service():
    engine = create_engine('sqlite://', poolclass=StaticPool, connect_args={'check_same_thread': False})
    Conversation.__table__.create(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        for id, title, status in [('a', 'literal %_\\', ConversationStatus.ACTIVE), ('b', 'ordinary', ConversationStatus.ACTIVE), ('session_%_\\', 'third', ConversationStatus.ACTIVE), ('z', 'literal %_\\', ConversationStatus.COMPLETED)]:
            db.add(Conversation(id=id, title=title, status=status, started_at=datetime(2026, 1, 1)))
        db.commit()
    instance = ConversationService()
    instance.db = factory
    yield instance
    engine.dispose()


def test_literal_search_status_count_and_stable_pages(service):
    first = service.list_conversations(page=1, page_size=1, status='active', search='%_\\')
    second = service.list_conversations(page=2, page_size=1, status='active', search='%_\\')
    assert first['total_count'] == second['total_count'] == 2
    assert [first['conversations'][0]['id'], second['conversations'][0]['id']] == ['session_%_\\', 'a']
    assert service.list_conversations(search='ordinary')['total_count'] == 1


def test_api_search_and_existing_validation(service, monkeypatch):
    monkeypatch.setattr(routes, 'conversation_service', service)
    app = FastAPI()
    app.include_router(routes.router)
    with TestClient(app) as client:
        response = client.get('/conversations', params={'search': '%_\\', 'status': 'active', 'page_size': 1})
        assert response.json()['data']['total_count'] == 2
        for params in [{'search': 'x' * 201}, {'page': 0}, {'page_size': 101}, {'page_size': 0}]:
            assert client.get('/conversations', params=params).status_code == 422

def test_search_trims_and_matches_all_partial_terms(service):
    with service.get_db_session() as db:
        db.add(Conversation(id='cn', title='当阳市 金桥 污水处理厂历史违规研判', status=ConversationStatus.ACTIVE, started_at=datetime(2026, 1, 2)))
        db.commit()
    assert service.list_conversations(search='  金桥   历史  ')['total_count'] == 1
    assert service.list_conversations(search='金桥 不存在')['total_count'] == 0
