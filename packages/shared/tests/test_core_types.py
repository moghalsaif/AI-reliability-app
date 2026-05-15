"""Tests for core trace types."""

import pytest
from datetime import datetime

from reliability_shared.types.core import (
    Trace,
    Span,
    SpanType,
    SpanStatus,
    TokenUsage,
    ModelMetadata,
    ToolCall,
    ReflectionEvent,
    MemoryOperation,
    MemoryOpType,
)
from reliability_shared.utils import generate_trace_id, generate_span_id


def test_trace_creation():
    trace = Trace(trace_id="test-123", name="test_trace")
    assert trace.trace_id == "test-123"
    assert trace.name == "test_trace"
    assert trace.success is True
    assert trace.start_time is not None


def test_span_creation():
    span = Span(
        span_id="span-1",
        trace_id="trace-1",
        span_type=SpanType.LLM,
        name="llm.call",
    )
    assert span.span_type == SpanType.LLM
    assert span.status == SpanStatus.OK


def test_token_usage():
    usage = TokenUsage(prompt_tokens=10, completion_tokens=20)
    assert usage.total_tokens == 30
    
    # Test auto-calculation
    usage2 = TokenUsage(prompt_tokens=5, completion_tokens=5, total_tokens=0)
    assert usage2.total_tokens == 10


def test_tool_call():
    tc = ToolCall(
        tool_name="weather_api",
        parameters={"location": "Tokyo"},
        result={"temp": 25},
    )
    assert tc.tool_name == "weather_api"
    assert tc.retry_count == 0


def test_reflection_event():
    refl = ReflectionEvent(
        iteration=1,
        reflection_type="self-correction",
        input_context="error detected",
        output_decision="retry",
        confidence=0.85,
        triggered_retry=True,
    )
    assert refl.iteration == 1
    assert refl.triggered_retry is True


def test_memory_operation():
    mem = MemoryOperation(
        op_type=MemoryOpType.READ,
        key="user_name",
        value="Alice",
    )
    assert mem.op_type == MemoryOpType.READ
    assert mem.namespace == "default"


def test_trace_serialization():
    trace = Trace(
        trace_id="test-123",
        name="test",
        environment="test",
    )
    data = trace.to_dict()
    assert data["trace_id"] == "test-123"
    assert data["environment"] == "test"
