"""OpenTelemetry exporter for the Reliability SDK.

Integrates with OpenTelemetry to export traces in OTLP format.
This teaches real observability engineering.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from reliability_shared.types.core import (
    Span,
    SpanType,
    Trace,
    SpanStatus,
)
from reliability_shared.utils import safe_json_dumps


class OpenTelemetryExporter:
    """Exporter that sends traces via OpenTelemetry OTLP.
    
    Uses opentelemetry-api and opentelemetry-exporter-otlp packages.
    """
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        service_name: str = "ai-agent",
        service_version: Optional[str] = None,
    ):
        self.endpoint = endpoint
        self.headers = headers or {}
        self.service_name = service_name
        self.service_version = service_version
        self._tracer_provider = None
        self._tracer = None
        self._initialized = False
    
    def _init_otel(self) -> None:
        """Lazy initialization of OpenTelemetry."""
        if self._initialized:
            return
        
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
            
            resource = Resource.create({
                SERVICE_NAME: self.service_name,
                SERVICE_VERSION: self.service_version or "0.0.1",
            })
            
            provider = TracerProvider(resource=resource)
            
            exporter = OTLPSpanExporter(
                endpoint=self.endpoint,
                headers=self.headers,
            )
            
            processor = BatchSpanProcessor(exporter)
            provider.add_span_processor(processor)
            
            trace.set_tracer_provider(provider)
            self._tracer = trace.get_tracer("reliability-sdk")
            self._initialized = True
            
        except ImportError:
            # OpenTelemetry not installed, fall back to console
            import logging
            logging.getLogger("reliability_sdk").warning(
                "OpenTelemetry not installed. Install with: pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp"
            )
    
    def export(self, trace: Trace) -> None:
        """Export a trace via OpenTelemetry."""
        self._init_otel()
        
        if not self._tracer:
            return
        
        with self._tracer.start_as_current_span(
            trace.name,
            kind=self._otel_span_kind(trace),
        ) as otel_span:
            # Set trace attributes
            otel_span.set_attribute("reliability.trace_id", trace.trace_id)
            otel_span.set_attribute("reliability.environment", trace.environment)
            otel_span.set_attribute("reliability.success", trace.success)
            
            if trace.agent_name:
                otel_span.set_attribute("reliability.agent_name", trace.agent_name)
            if trace.session_id:
                otel_span.set_attribute("reliability.session_id", trace.session_id)
            if trace.user_id:
                otel_span.set_attribute("reliability.user_id", trace.user_id)
            
            # Export root span and children
            if trace.root_span:
                self._export_span_recursive(trace.root_span, otel_span)
    
    def _export_span_recursive(self, span: Span, parent_otel_span: Any) -> None:
        """Recursively export spans to OpenTelemetry."""
        with self._tracer.start_as_current_span(
            span.name,
            context=parent_otel_span.get_span_context() if parent_otel_span else None,
        ) as otel_span:
            # Core attributes
            otel_span.set_attribute("reliability.span_id", span.span_id)
            otel_span.set_attribute("reliability.span_type", span.span_type.value)
            otel_span.set_attribute("reliability.latency_ms", span.latency_ms)
            
            if span.token_usage:
                otel_span.set_attribute("llm.token_usage.prompt", span.token_usage.prompt_tokens)
                otel_span.set_attribute("llm.token_usage.completion", span.token_usage.completion_tokens)
                otel_span.set_attribute("llm.token_usage.total", span.token_usage.total_tokens)
            
            if span.model_metadata:
                otel_span.set_attribute("llm.model.name", span.model_metadata.model_name)
                otel_span.set_attribute("llm.model.provider", span.model_metadata.provider)
                otel_span.set_attribute("llm.model.temperature", span.model_metadata.temperature)
            
            if span.retry_count > 0:
                otel_span.set_attribute("reliability.retry_count", span.retry_count)
            
            # Tool calls
            for i, tool_call in enumerate(span.tool_calls):
                prefix = f"reliability.tool_call.{i}"
                otel_span.set_attribute(f"{prefix}.name", tool_call.tool_name)
                otel_span.set_attribute(f"{prefix}.latency_ms", tool_call.latency_ms)
                otel_span.set_attribute(f"{prefix}.retry_count", tool_call.retry_count)
                if tool_call.error:
                    otel_span.set_attribute(f"{prefix}.error", tool_call.error)
            
            # Retrievals
            for i, retrieval in enumerate(span.retrievals):
                prefix = f"reliability.retrieval.{i}"
                otel_span.set_attribute(f"{prefix}.source", retrieval.source)
                otel_span.set_attribute(f"{prefix}.score", retrieval.score)
                otel_span.set_attribute(f"{prefix}.rank", retrieval.rank)
            
            # Memory operations
            for i, mem_op in enumerate(span.memory_ops):
                prefix = f"reliability.memory_op.{i}"
                otel_span.set_attribute(f"{prefix}.type", mem_op.op_type.value)
                otel_span.set_attribute(f"{prefix}.key", mem_op.key)
                otel_span.set_attribute(f"{prefix}.namespace", mem_op.namespace)
                otel_span.set_attribute(f"{prefix}.success", mem_op.success)
            
            # Reflections
            for i, reflection in enumerate(span.reflections):
                prefix = f"reliability.reflection.{i}"
                otel_span.set_attribute(f"{prefix}.iteration", reflection.iteration)
                otel_span.set_attribute(f"{prefix}.type", reflection.reflection_type)
                otel_span.set_attribute(f"{prefix}.confidence", reflection.confidence)
                otel_span.set_attribute(f"{prefix}.triggered_retry", reflection.triggered_retry)
            
            # Custom attributes
            for key, value in span.attributes.items():
                otel_span.set_attribute(f"reliability.attr.{key}", safe_json_dumps(value))
            
            # Status
            if span.status == SpanStatus.ERROR:
                otel_span.set_status(
                    trace.Status(trace.StatusCode.ERROR, description=str(span.attributes.get("error.message", "")))
                )
            
            # Recurse into children
            for child in span.children:
                self._export_span_recursive(child, otel_span)
    
    def _otel_span_kind(self, trace: Trace) -> Any:
        """Map trace to OpenTelemetry span kind."""
        from opentelemetry.trace import SpanKind
        return SpanKind.INTERNAL


class ConsoleExporter:
    """Simple console exporter for debugging."""
    
    def __init__(self, pretty: bool = True):
        self.pretty = pretty
    
    def export(self, trace: Trace) -> None:
        """Print trace to console."""
        if self.pretty:
            print(f"\n{'='*60}")
            print(f"TRACE: {trace.name} | ID: {trace.trace_id}")
            print(f"Agent: {trace.agent_name} | Env: {trace.environment} | Success: {trace.success}")
            if trace.root_span:
                self._print_span(trace.root_span, indent=0)
            print(f"{'='*60}\n")
        else:
            print(safe_json_dumps(trace.to_dict()))
    
    def _print_span(self, span: Span, indent: int = 0) -> None:
        prefix = "  " * indent
        status_icon = "✓" if span.status == SpanStatus.OK else "✗"
        print(f"{prefix}{status_icon} [{span.span_type.value}] {span.name} ({span.latency_ms:.0f}ms)")
        
        if span.token_usage:
            print(f"{prefix}   Tokens: {span.token_usage.total_tokens} ({span.token_usage.prompt_tokens} prompt)")
        
        if span.tool_calls:
            for tc in span.tool_calls:
                print(f"{prefix}   Tool: {tc.tool_name} | Latency: {tc.latency_ms:.0f}ms | Retries: {tc.retry_count}")
        
        if span.retrievals:
            for r in span.retrievals:
                print(f"{prefix}   Retrieval: {r.source} | Score: {r.score:.2f} | Rank: {r.rank}")
        
        if span.reflections:
            for ref in span.reflections:
                print(f"{prefix}   Reflection: iter={ref.iteration} | type={ref.reflection_type} | confidence={ref.confidence:.2f}")
        
        for child in span.children:
            self._print_span(child, indent + 1)


class HTTPExporter:
    """HTTP exporter that sends traces to the Reliability Lab API."""
    
    def __init__(
        self,
        endpoint: str = "http://localhost:8000/v1/traces",
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.endpoint = endpoint
        self.api_key = api_key
        self.timeout = timeout
    
    def export(self, trace: Trace) -> None:
        """Send trace to API endpoint."""
        import requests
        
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "trace": trace.to_dict(),
            "source": "sdk",
        }
        
        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except Exception as e:
            import logging
            logging.getLogger("reliability_sdk").warning(f"HTTP export failed: {e}")
