"""
Logging data models for evidence chain system.

This module defines the data models for logging various system events:
- API calls
- Master agent decisions
- Sub agent executions
- Operator calls
- LLM calls
- System errors
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class LogLevel(str, Enum):
    """Log severity levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class APICallLog(BaseModel):
    """Log entry for API calls made to external services."""

    log_id: str = Field(default_factory=lambda: f"api_{datetime.utcnow().timestamp()}")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Request details
    endpoint: str = Field(..., description="API endpoint called")
    method: str = Field(..., description="HTTP method (GET, POST, etc.)")
    request_headers: Optional[Dict[str, str]] = Field(None, description="Request headers")
    request_body: Optional[Dict[str, Any]] = Field(None, description="Request payload")

    # Response details
    status_code: Optional[int] = Field(None, description="HTTP status code")
    response_headers: Optional[Dict[str, str]] = Field(None, description="Response headers")
    response_body: Optional[Dict[str, Any]] = Field(None, description="Response data")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")

    # Error tracking
    error_message: Optional[str] = Field(None, description="Error message if call failed")
    retry_count: int = Field(default=0, description="Number of retry attempts")

    # Metadata
    service_name: str = Field(..., description="Name of the external service")
    trace_id: Optional[str] = Field(None, description="Trace ID for distributed tracing")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MasterAgentDecisionLog(BaseModel):
    """Log entry for master agent decision-making process."""

    log_id: str = Field(default_factory=lambda: f"master_{datetime.utcnow().timestamp()}")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Decision context
    task_id: str = Field(..., description="ID of the task being processed")
    task_description: str = Field(..., description="Description of the task")
    context_summary: str = Field(..., description="Summary of the context at decision time")

    # Decision details
    decision_type: str = Field(..., description="Type of decision (e.g., 'route_to_agent', 'parallel_dispatch')")
    decision_reasoning: str = Field(..., description="Explanation of why this decision was made")
    selected_agents: list[str] = Field(..., description="List of agents selected for execution")

    # Confidence and alternatives
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in the decision")
    alternative_decisions: Optional[list[Dict[str, Any]]] = Field(
        None,
        description="Alternative decisions considered"
    )

    # Outcomes
    execution_successful: Optional[bool] = Field(None, description="Whether execution succeeded")
    outcome_summary: Optional[str] = Field(None, description="Summary of the execution outcome")

    # Evidence chain reference
    evidence_chain_id: Optional[str] = Field(None, description="ID of the evidence chain")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SubAgentExecutionLog(BaseModel):
    """Log entry for sub-agent execution details."""

    log_id: str = Field(default_factory=lambda: f"subagent_{datetime.utcnow().timestamp()}")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Execution identification
    execution_id: str = Field(..., description="Unique ID for this execution")
    agent_name: str = Field(..., description="Name of the agent executed")
    agent_type: str = Field(..., description="Type/category of the agent")

    # Task details
    task_id: str = Field(..., description="ID of the parent task")
    task_assignment: str = Field(..., description="Specific task assigned to this agent")
    input_data: Dict[str, Any] = Field(..., description="Input data provided to the agent")

    # Execution metrics
    start_time: datetime = Field(..., description="Execution start time")
    end_time: Optional[datetime] = Field(None, description="Execution end time")
    duration_seconds: Optional[float] = Field(None, description="Execution duration in seconds")

    # Results
    status: str = Field(..., description="Execution status (e.g., 'started', 'completed', 'failed')")
    output_data: Optional[Dict[str, Any]] = Field(None, description="Output data from the agent")
    error_details: Optional[str] = Field(None, description="Error details if execution failed")

    # Resource usage
    tokens_used: Optional[int] = Field(None, description="Number of tokens used")
    api_calls_made: Optional[int] = Field(None, description="Number of API calls made")

    # References
    master_decision_log_id: Optional[str] = Field(None, description="Reference to master agent decision log")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class OperatorCallLog(BaseModel):
    """Log entry for operator/function tool calls."""

    log_id: str = Field(default_factory=lambda: f"operator_{datetime.utcnow().timestamp()}")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Call details
    operator_name: str = Field(..., description="Name of the operator/function called")
    operator_type: str = Field(..., description="Type of operator (e.g., 'bash', 'file_io', 'database')")
    caller_agent: str = Field(..., description="Name of the agent making the call")

    # Input/Output
    input_parameters: Dict[str, Any] = Field(..., description="Parameters passed to the operator")
    output_result: Optional[Dict[str, Any]] = Field(None, description="Result returned by the operator")

    # Execution info
    execution_time_ms: Optional[float] = Field(None, description="Execution time in milliseconds")
    success: bool = Field(..., description="Whether the call succeeded")
    error_message: Optional[str] = Field(None, description="Error message if call failed")

    # Safety and validation
    safety_validation_passed: bool = Field(default=True, description="Whether safety checks passed")
    validation_notes: Optional[str] = Field(None, description="Notes from safety validation")

    # References
    sub_agent_execution_id: Optional[str] = Field(None, description="Reference to sub-agent execution")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class LLMCallLog(BaseModel):
    """Log entry for LLM API calls."""

    log_id: str = Field(default_factory=lambda: f"llm_{datetime.utcnow().timestamp()}")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Model details
    model_name: str = Field(..., description="Name of the LLM model used")
    model_version: Optional[str] = Field(None, description="Version of the model")
    provider: str = Field(..., description="LLM provider (e.g., 'anthropic', 'openai')")

    # Call details
    call_type: str = Field(..., description="Type of call (e.g., 'completion', 'embedding')")
    caller_agent: str = Field(..., description="Name of the agent making the call")

    # Input/Output
    prompt_template: Optional[str] = Field(None, description="Template used for the prompt")
    prompt_variables: Optional[Dict[str, Any]] = Field(None, description="Variables filled in the template")
    system_prompt: Optional[str] = Field(None, description="System prompt used")
    messages: Optional[list[Dict[str, Any]]] = Field(None, description="Full message history sent")

    # Response details
    response_text: Optional[str] = Field(None, description="Text response from the LLM")
    finish_reason: Optional[str] = Field(None, description="Reason for completion (e.g., 'stop', 'length')")

    # Token usage
    prompt_tokens: int = Field(..., description="Number of tokens in the prompt")
    completion_tokens: int = Field(..., description="Number of tokens in the completion")
    total_tokens: int = Field(..., description="Total number of tokens used")

    # Performance
    latency_ms: Optional[float] = Field(None, description="Call latency in milliseconds")

    # Cost tracking
    estimated_cost_usd: Optional[float] = Field(None, description="Estimated cost in USD")

    # Error tracking
    error_message: Optional[str] = Field(None, description="Error message if call failed")
    retry_count: int = Field(default=0, description="Number of retry attempts")

    # References
    sub_agent_execution_id: Optional[str] = Field(None, description="Reference to sub-agent execution")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SystemErrorLog(BaseModel):
    """Log entry for system errors and exceptions."""

    log_id: str = Field(default_factory=lambda: f"error_{datetime.utcnow().timestamp()}")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Error details
    error_type: str = Field(..., description="Type/class of the error")
    error_message: str = Field(..., description="Error message")
    error_severity: LogLevel = Field(..., description="Severity level of the error")

    # Stack trace
    stack_trace: Optional[str] = Field(None, description="Full stack trace")
    file_name: Optional[str] = Field(None, description="File where error occurred")
    line_number: Optional[int] = Field(None, description="Line number where error occurred")
    function_name: Optional[str] = Field(None, description="Function where error occurred")

    # Context
    context_data: Optional[Dict[str, Any]] = Field(None, description="Additional context data")
    affected_component: str = Field(..., description="Component/system affected by the error")

    # Recovery
    recovery_attempted: bool = Field(default=False, description="Whether recovery was attempted")
    recovery_successful: Optional[bool] = Field(None, description="Whether recovery succeeded")
    recovery_action: Optional[str] = Field(None, description="Description of recovery action taken")

    # References
    related_execution_id: Optional[str] = Field(None, description="Reference to related execution")
    related_llm_call_id: Optional[str] = Field(None, description="Reference to related LLM call")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
