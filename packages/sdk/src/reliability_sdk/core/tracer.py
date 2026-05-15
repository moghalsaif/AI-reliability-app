"""Core trace builder and context manager for the Reliability SDK."""

from __future__ import annotations

import contextlib
import threading
import traceback
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from reliability_shared.types.core import (
    ModelMetadata,
    ReflectionEvent,
    RetrievalResult,
    Span,
    SpanStatus,
    SpanType,
    ToolCall,
    Trace,
    TokenUsage,
    MemoryOperation,
    TelemetryBatch,
)
from reliability_shared.utils import (
    current_timestamp_ms,
    generate_span_id,
    generate_trace_id,
)


class TraceContext:
    """Thread-local trace context for automatic span nesting."""
    
    _local = threading.local()
    
    @classmethod
    def current_trace(cls) -> Optional[Trace]:
        return getattr(cls._local, "current_trace", None)
    
    @classmethod
    def current_span(cls) -> Optional[Span]:
        return getattr(cls._local, "current_span", None)
    
    @classmethod
    def set_trace(cls, trace: Optional[Trace]) -> None:
        cls._local.current_trace = trace
    
    @classmethod
    def set_span(cls, span: Optional[Span]) -> None:
        cls._local.current_span = span
    
    @classmethod
    def clear(cls) -> None:
        cls._local.current_trace = None
        cls._local.current_span = None


class TraceBuilder:
    """Builder for constructing traces with spans."""
    
    def __init__(self, name: str, trace_id: Optional[str] = None):
        self.trace = Trace(
            trace_id=trace_id or generate_trace_id(),
            name=name,
        )
        self._spans: List[Span] = []
        self._span_stack: List[Span] = []
    
    def start_span(
        self,
        name: str,
        span_type: SpanType = SpanType.CUSTOM,
        parent: Optional[Span] = None,
        **kwargs: Any,
    ) -> Span:
        """Start a new span within the trace."""
        parent_span = parent or self._span_stack[-1] if self._span_stack else None
        
        span = Span(
            span_id=generate_span_id(),
            trace_id=self.trace.trace_id,
            parent_span_id=parent_span.span_id if parent_span else None,
            span_type=span_type,
            name=name,
            start_time=datetime.utcnow(),
            **kwargs,
        )
        
        self._spans.append(span)
        self._span_stack.append(span)
        
        if not self.trace.root_span:
            self.trace.root_span = span
        elif parent_span:
            parent_span.children.append(span)
        
        TraceContext.set_span(span)
        return span
    
    def end_span(
        self,
        span: Optional[Span] = None,
        status: SpanStatus = SpanStatus.OK,
        output: Any = None,
        error: Optional[Exception] = None,
    ) -> Span:
        """End a span and pop it from the stack."""
        if span is None:
            span = self._span_stack.pop() if self._span_stack else None
        
        if span is None:
            raise RuntimeError("No active span to end")
        
        span.end_time = datetime.utcnow()
        span.status = status
        span.latency_ms = (span.end_time - span.start_time).total_seconds() * 1000
        
        if output is not None:
            span.output = output
        
        if error is not None:
            span.status = SpanStatus.ERROR
            span.attributes["error.type"] = type(error).__name__
            span.attributes["error.message"] = str(error)
            span.attributes["error.stack"] = traceback.format_exc()
        
        # Update context
        if self._span_stack and self._span_stack[-1] == span:
            self._span_stack.pop()
        
        new_current = self._span_stack[-1] if self._span_stack else None
        TraceContext.set_span(new_current)
        
        return span
    
    def finish(self, success: bool = True, error_message: Optional[str] = None) -> Trace:
        """Finish the trace and return it."""
        self.trace.end_time = datetime.utcnow()
        self.trace.success = success
        if error_message:
            self.trace.error_message = error_message
        
        # Auto-end any open spans
        while self._span_stack:
            self.end_span()
        
        TraceContext.clear()
        return self.trace
    
    @contextlib.contextmanager
    def span(
        self,
        name: str,
        span_type: SpanType = SpanType.CUSTOM,
        **kwargs: Any,
    ):
        """Context manager for a span."""
        span = self.start_span(name, span_type, **kwargs)
        try:
            yield span
            self.end_span(span, status=SpanStatus.OK)
        except Exception as e:
            self.end_span(span, status=SpanStatus.ERROR, error=e)
            raise


class Tracer:
    """Main tracer interface for instrumenting AI systems."""
    
    def __init__(self, service_name: str = "ai-agent", environment: str = "development"):
        self.service_name = service_name
        self.environment = environment
        self._exporters: List[Any] = []
        self._batch: List[Trace] = []
    
    def add_exporter(self, exporter: Any) -> None:
        """Add a trace exporter (e.g., OTLP, HTTP, Console)."""
        self._exporters.append(exporter)
    
    @contextlib.contextmanager
    def trace(
        self,
        name: str,
        trace_id: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        **attributes: Any,
    ):
        """Start a new trace context.
        
        Usage:
            with tracer.trace("contract_agent", agent_name="legal_v1"):
                response = agent.run(query)
        """
        builder = TraceBuilder(name, trace_id=trace_id)
        builder.trace.session_id = session_id
        builder.trace.user_id = user_id
        builder.trace.agent_name = agent_name or name
        builder.trace.environment = self.environment
        builder.trace.attributes.update(attributes)
        
        TraceContext.set_trace(builder.trace)
        
        try:
            yield builder
            trace = builder.finish(success=True)
        except Exception as e:
            trace = builder.finish(success=False, error_message=str(e))
            self._export(trace)
            raise
        else:
            self._export(trace)
    
    def _export(self, trace: Trace) -> None:
        """Export trace to all configured exporters."""
        for exporter in self._exporters:
            try:
                exporter.export(trace)
            except Exception as e:
                # Don't let exporter errors break user code
                import logging
                logging.getLogger("reliability_sdk").warning(f"Export failed: {e}")
    
    def current_span(self) -> Optional[Span]:
        """Get the currently active span."""
        return TraceContext.current_span()
    
    def current_trace(self) -> Optional[Trace]:
        """Get the currently active trace."""
        return TraceContext.current_trace()
    
    def record_llm_call(
        self,
        prompt: Any,
        completion: Any,
        model_metadata: ModelMetadata,
        token_usage: Optional[TokenUsage] = None,
        latency_ms: float = 0.0,
    ) -> Span:
        """Record an LLM call as a span."""
        builder = TraceBuilder("")
        trace = TraceContext.current_trace()
        if trace:
            builder.trace = trace
        
        span = builder.start_span(
            name=f"llm.{model_metadata.model_name}",
            span_type=SpanType.LLM,
            input=prompt,
            output=completion,
            model_metadata=model_metadata,
            token_usage=token_usage,
            latency_ms=latency_ms,
        )
        return span
    
    def record_tool_call(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        result: Any = None,
        error: Optional[str] = None,
        latency_ms: float = 0.0,
        retry_count: int = 0,
    ) -> Span:
        """Record a tool call as a span."""
        builder = TraceBuilder("")
        trace = TraceContext.current_trace()
        if trace:
            builder.trace = trace
        
        tool_call = ToolCall(
            tool_name=tool_name,
            parameters=parameters,
            result=result,
            error=error,
            latency_ms=latency_ms,
            retry_count=retry_count,
        )
        
        span = builder.start_span(
            name=f"tool.{tool_name}",
            span_type=SpanType.TOOL_CALL,
            tool_calls=[tool_call],
            latency_ms=latency_ms,
        )
        return span
    
    def record_retrieval(
        self,
        query: str,
        results: List[RetrievalResult],
        latency_ms: float = 0.0,
    ) -> Span:
        """Record a retrieval operation as a span."""
        builder = TraceBuilder("")
        trace = TraceContext.current_trace()
        if trace:
            builder.trace = trace
        
        span = builder.start_span(
            name="retrieval",
            span_type=SpanType.RETRIEVAL,
            input=query,
            retrievals=results,
            latency_ms=latency_ms,
        )
        return span
    
    def record_reflection(
        self,
        iteration: int,
        reflection_type: str,
        input_context: str,
        output_decision: str,
        confidence: float = 0.0,
        triggered_retry: bool = False,
    ) -> Span:
        """Record a reflection/reasoning loop event."""
        builder = TraceBuilder("")
        trace = TraceContext.current_trace()
        if trace:
            builder.trace = trace
        
        reflection = ReflectionEvent(
            iteration=iteration,
            reflection_type=reflection_type,
            input_context=input_context,
            output_decision=output_decision,
            confidence=confidence,
            triggered_retry=triggered_retry,
        )
        
        span = builder.start_span(
            name=f"reflection.{reflection_type}",
            span_type=SpanType.REFLECTION,
            reflections=[reflection],
        )
        return span
    
    def record_memory_op(
        self,
        op_type: str,
        key: str,
        value: Any = None,
        namespace: str = "default",
        success: bool = True,
    ) -> Span:
        """Record a memory operation as a span."""
        from reliability_shared.types.core import MemoryOpType
        
        builder = TraceBuilder("")
        trace = TraceContext.current_trace()
        if trace:
            builder.trace = trace
        
        mem_op = MemoryOperation(
            op_type=MemoryOpType(op_type),
            key=key,
            value=value,
            namespace=namespace,
            success=success,
        )
        
        span = builder.start_span(
            name=f"memory.{op_type}",
            span_type=SpanType.MEMORY_OP,
            memory_ops=[mem_op],
        )
        return span
