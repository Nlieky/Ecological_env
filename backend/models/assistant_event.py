"""Assistant proposal and atomic operation audit; never an identity system."""
from sqlalchemy import Column, String, DateTime, JSON, UniqueConstraint
from backend.database.base import Base


class AssistantEventProposal(Base):
    __tablename__ = 'assistant_event_proposals'
    id = Column(String(64), primary_key=True)
    session_id = Column(String(100), nullable=False)
    event_id = Column(String(50), nullable=False)
    old_status = Column(String(20), nullable=False)
    new_status = Column(String(20), nullable=False)
    expected_updated_at = Column(DateTime, nullable=False)
    reason = Column(String(1000), nullable=False)
    plant_id = Column(String(100), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    consumed_at = Column(DateTime)


class AssistantEventOperation(Base):
    __tablename__ = 'assistant_event_operations'
    __table_args__ = (UniqueConstraint('session_id', 'idempotency_key'), UniqueConstraint('proposal_id'))
    id = Column(String(64), primary_key=True)
    proposal_id = Column(String(64), nullable=False)
    session_id = Column(String(100), nullable=False)
    idempotency_key = Column(String(100), nullable=False)
    result = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False)
