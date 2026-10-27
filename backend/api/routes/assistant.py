from fastapi import APIRouter, Query
from backend.models.assistant import RespondRequest, ProposalRequest, ConfirmRequest
from backend.services import assistant_service, assistant_events

router = APIRouter(prefix='/assistant', tags=['系统助手'])


@router.post('/respond')
async def respond(req: RespondRequest):
    return await assistant_service.respond(req)


@router.get('/capabilities')
def capabilities():
    from shared.assistant.contract import contract_document
    return {**contract_document(), 'event_writes_enabled': assistant_events.enabled()}


@router.post('/event-proposals')
def propose(req: ProposalRequest):
    return assistant_events.propose(req)


@router.post('/event-proposals/{proposal_id}/confirm')
def confirm(proposal_id: str, req: ConfirmRequest):
    return assistant_events.confirm(proposal_id, req)


@router.get('/operations/by-key/{idempotency_key}')
def operation_by_key(idempotency_key: str, session_id: str = Query(min_length=1, max_length=100)):
    return assistant_events.operation_by_key(idempotency_key, session_id)


@router.get('/operations/{operation_id}')
def operation(operation_id: str, session_id: str = Query(min_length=1, max_length=100)):
    return assistant_events.operation(operation_id, session_id)
