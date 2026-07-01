from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class EvidenceSnapshot(BaseModel):
    pH: Optional[float] = None
    cod: Optional[float] = None
    ammoniaNitrogen: Optional[float] = None
    totalNitrogen: Optional[float] = None
    totalPhosphorus: Optional[float] = None
    flow: Optional[float] = None


class OperatorCall(BaseModel):
    name: str
    result: Any


class RuleMatch(BaseModel):
    name: str
    matched: bool


class EventEvidence(BaseModel):
    dataSnapshot: EvidenceSnapshot
    operators: List[OperatorCall]
    rules: List[RuleMatch]
    llmReasoning: str


class AlertEvent(BaseModel):
    id: str
    timestamp: str
    type: str
    plantId: str
    severity: str  # low, medium, high
    status: str  # pending, processing, resolved, ignored
    evidence: EventEvidence


class EventListResponse(BaseModel):
    data: List[AlertEvent]
    total: int


class EventStatusUpdate(BaseModel):
    status: str
