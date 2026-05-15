"""Core type definitions for the AI Reliability Lab."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID


class SpanType(str, enum.Enum):
    """Types of spans in a trace."""
    LLM = "llm"
    PROMPT = "prompt"
    COMPLETION = "completion"
    TOOL_CALL = "tool_call"
    RETRIEVAL = "retrieval"
    MEMORY_OP = "memory_op"
    REFLECTION = "reflection"
    REASONING = "reasoning"
    AGENT = "agent"
    WORKFLOW = "workflow"
    CUSTOM = "custom"


class SpanStatus(str, enum.Enum):
    """Status of a span."""
    OK = "ok"
    ERROR = "error"
    DEFERRED = "deferred"


class MemoryOpType(str, enum.Enum):
    """Types of memory operations."""
    READ = "read"
    WRITE = "write"
    UPDATE = "update"
    DELETE = "delete"
    SEARCH = "search"


@dataclass
class TokenUsage:
    """Token usage metrics."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    def __post_init__(self):
        if self.total_tokens == 0:
            self.total_tokens = self.prompt_tokens + self.completion_tokens


@dataclass
class ModelMetadata:
    """Model invocation metadata."""
    model_name: str
    provider: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    version: Optional[str] = None


@dataclass
class ToolCall:
    """A tool call within a span."""
    tool_name: str
    parameters: Dict[str, Any]
    result: Optional[Any] = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    retry_count: int = 0


@dataclass
class RetrievalResult:
    """A retrieval result within a span."""
    query: str
    source: str
    content: str
    score: float = 0.0
    rank: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryOperation:
    """A memory operation within a span."""
    op_type: MemoryOpType
    key: str
    value: Optional[Any] = None
    namespace: str = "default"
    success: bool = True


@dataclass
class ReflectionEvent:
    """A reflection/reasoning loop event."""
    iteration: int
    reflection_type: str  # self-correction, planning, verification
    input_context: str
    output_decision: str
    confidence: float = 0.0
    triggered_retry: bool = False


@dataclass
class Span:
    """A single operation within a trace."""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str] = None
    span_type: SpanType = SpanType.CUSTOM
    name: str = ""
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    status: SpanStatus = SpanStatus.OK
    
    # Content
    input: Optional[Any] = None
    output: Optional[Any] = None
    
    # AI-specific fields
    token_usage: Optional[TokenUsage] = None
    model_metadata: Optional[ModelMetadata] = None
    tool_calls: List[ToolCall] = field(default_factory=list)
    retrievals: List[RetrievalResult] = field(default_factory=list)
    memory_ops: List[MemoryOperation] = field(default_factory=list)
    reflections: List[ReflectionEvent] = field(default_factory=list)
    
    # Metrics
    latency_ms: float = 0.0
    retry_count: int = 0
    
    # Metadata
    attributes: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    # Relationships
    children: List[Span] = field(default_factory=list)

    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return self.latency_ms


@dataclass
class Trace:
    """Top-level trace representing an agent run or workflow execution."""
    trace_id: str
    name: str = ""
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    status: SpanStatus = SpanStatus.OK
    
    # Root span
    root_span: Optional[Span] = None
    
    # Metadata
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    agent_name: Optional[str] = None
    environment: str = "development"
    version: Optional[str] = None
    
    # Reliability
    success: bool = True
    error_message: Optional[str] = None
    
    # Computed metrics (populated by processing layer)
    metrics: Dict[str, float] = field(default_factory=dict)
    
    # Raw attributes
    attributes: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize trace to dictionary."""
        return {
            "trace_id": self.trace_id,
            "name": self.name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status.value,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "agent_name": self.agent_name,
            "environment": self.environment,
            "version": self.version,
            "success": self.success,
            "error_message": self.error_message,
            "metrics": self.metrics,
            "attributes": self.attributes,
            "tags": self.tags,
        }


@dataclass
class TelemetryBatch:
    """Batch of traces for ingestion."""
    traces: List[Trace] = field(default_factory=list)
    source: str = "sdk"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def size(self) -> int:
        return len(self.traces)


# Type aliases
TraceId = str
SpanId = str
JSONDict = Dict[str, Any]
