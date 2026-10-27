"""Strict transport schema for the independent assistant."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class AssistantContext(StrictModel):
    pageId: str = Field(default='', max_length=50)
    route: str = Field(default='', max_length=200)
    objectId: str | None = Field(default=None, max_length=100)
    plant: str | None = Field(default=None, max_length=100)
    indicator: str | None = Field(default=None, max_length=50)
    range: str | dict[str, str] | None = None
    source: str = Field(default='未核验', max_length=200)
    freshness: str | None = Field(default=None, max_length=100)
    filters: dict[str, str | int | bool | None] = Field(default_factory=dict)
    status: Literal['loading', 'ready', 'empty', 'error', 'stale'] = 'ready'
    actions: list[str] = Field(default_factory=list, max_length=30)
    revision: int = Field(default=0, ge=0)

    @field_validator('filters')
    @classmethod
    def safe_filters(cls, value):
        if set(value) - {'status', 'severity', 'page', 'module', 'tab', 'entity', 'side', 'search', 'dirty'}:
            raise ValueError('Unsupported filter')
        if any(isinstance(v, str) and len(v) > 200 for v in value.values()):
            raise ValueError('Filter too long')
        return value

    @field_validator('range')
    @classmethod
    def safe_range(cls, value):
        if isinstance(value, dict) and (set(value) - {'start', 'end'} or any(len(v) > 50 for v in value.values())):
            raise ValueError('Unsupported time range')
        if isinstance(value, str) and len(value) > 100:
            raise ValueError('Time range too long')
        return value


class HistoryMessage(StrictModel):
    role: Literal['user', 'assistant']
    content: str = Field(max_length=4000)


class RespondRequest(StrictModel):
    query: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(min_length=1, max_length=100)
    context: AssistantContext | None = Field(default_factory=AssistantContext)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=20)
    pending: dict | None = None

    @field_validator('pending')
    @classmethod
    def safe_pending(cls, value):
        if value is not None:
            from shared.assistant.preparation import validate_pending
            return validate_pending(value)
        return None


class ProposalRequest(StrictModel):
    session_id: str = Field(min_length=1, max_length=100)
    event_id: str = Field(min_length=1, max_length=50)
    new_status: Literal['pending', 'processing', 'resolved', 'ignored']
    reason: str = Field(min_length=1, max_length=1000)
    expected_status: Literal['pending', 'processing', 'resolved', 'ignored'] | None = None
    expected_updated_at: datetime | None = None


class ConfirmRequest(StrictModel):
    session_id: str = Field(min_length=1, max_length=100)
    idempotency_key: str = Field(min_length=1, max_length=100)
