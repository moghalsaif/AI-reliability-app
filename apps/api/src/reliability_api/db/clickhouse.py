"""ClickHouse schema and client for trace storage."""

from typing import Any, Dict, List, Optional
from datetime import datetime

from reliability_shared.types.core import Trace, Span


TRACE_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS traces (
    trace_id String,
    name String,
    start_time DateTime64(3),
    end_time DateTime64(3),
    duration_ms Float64,
    status String,
    session_id Nullable(String),
    user_id Nullable(String),
    agent_name Nullable(String),
    environment String,
    version Nullable(String),
    success Bool,
    error_message Nullable(String),
    span_count UInt32,
    total_tokens UInt32,
    total_latency_ms Float64,
    tags Array(String),
    attributes String,  -- JSON
    
    INDEX idx_agent agent_name TYPE bloom_filter GRANULARITY 3,
    INDEX idx_env environment TYPE bloom_filter GRANULARITY 3,
    INDEX idx_session session_id TYPE bloom_filter GRANULARITY 3
) ENGINE = MergeTree()
ORDER BY (start_time, trace_id)
TTL start_time + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;
"""

SPANS_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS spans (
    span_id String,
    trace_id String,
    parent_span_id Nullable(String),
    span_type String,
    name String,
    start_time DateTime64(3),
    end_time DateTime64(3),
    duration_ms Float64,
    status String,
    
    input Nullable(String),
    output Nullable(String),
    
    prompt_tokens UInt32,
    completion_tokens UInt32,
    total_tokens UInt32,
    model_name Nullable(String),
    model_provider Nullable(String),
    temperature Nullable(Float64),
    
    latency_ms Float64,
    retry_count UInt32,
    
    tool_calls String,  -- JSON array
    retrievals String,  -- JSON array
    memory_ops String,  -- JSON array
    reflections String, -- JSON array
    
    attributes String,  -- JSON
    tags Array(String),
    
    INDEX idx_trace trace_id TYPE bloom_filter GRANULARITY 3,
    INDEX idx_type span_type TYPE bloom_filter GRANULARITY 3
) ENGINE = MergeTree()
ORDER BY (trace_id, start_time)
TTL start_time + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;
"""

EVALUATIONS_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS evaluations (
    eval_id String,
    trace_id String,
    span_id Nullable(String),
    eval_type String,
    score Float64,
    passed Bool,
    threshold Float64,
    details String,  -- JSON
    model_judge Nullable(String),
    timestamp DateTime64(3),
    
    INDEX idx_trace trace_id TYPE bloom_filter GRANULARITY 3,
    INDEX idx_type eval_type TYPE bloom_filter GRANULARITY 3
) ENGINE = MergeTree()
ORDER BY (timestamp, trace_id)
TTL timestamp + INTERVAL 90 DAY;
"""

RELIABILITY_METRICS_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS reliability_metrics (
    metric_id String,
    trace_id String,
    run_id String,
    agent_name Nullable(String),
    
    success_rate Float64,
    hallucination_rate Float64,
    variance_score Float64,
    retry_density Float64,
    cost_per_success Float64,
    latency_p95 Float64,
    context_retention Float64,
    tool_accuracy Float64,
    
    model_name Nullable(String),
    temperature Nullable(Float64),
    prompt_version Nullable(String),
    
    timestamp DateTime64(3),
    
    INDEX idx_trace trace_id TYPE bloom_filter GRANULARITY 3
) ENGINE = MergeTree()
ORDER BY (timestamp, trace_id)
TTL timestamp + INTERVAL 90 DAY;
"""

ALERTS_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS alerts (
    alert_id String,
    trace_id String,
    alert_type String,
    severity String,  -- P0, P1, P2, P3
    message String,
    metric_name Nullable(String),
    metric_value Nullable(Float64),
    threshold Nullable(Float64),
    acknowledged Bool DEFAULT false,
    timestamp DateTime64(3),
    
    INDEX idx_trace trace_id TYPE bloom_filter GRANULARITY 3
) ENGINE = MergeTree()
ORDER BY (timestamp, trace_id);
"""


class ClickHouseClient:
    """Async ClickHouse client for trace storage."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8123,
        database: str = "reliability_lab",
        username: str = "default",
        password: str = "",
    ):
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self._client = None
    
    async def connect(self) -> None:
        """Initialize ClickHouse connection."""
        try:
            import aiochclient
            url = f"http://{self.host}:{self.port}"
            self._client = aiochclient.ChClient(
                url=url,
                database=self.database,
                user=self.username,
                password=self.password,
            )
        except ImportError:
            # Fallback to sync client
            import clickhouse_connect
            self._client = clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                database=self.database,
                username=self.username,
                password=self.password,
            )
    
    async def init_schema(self) -> None:
        """Initialize database schema."""
        schemas = [
            TRACE_TABLE_SCHEMA,
            SPANS_TABLE_SCHEMA,
            EVALUATIONS_TABLE_SCHEMA,
            RELIABILITY_METRICS_TABLE_SCHEMA,
            ALERTS_TABLE_SCHEMA,
        ]
        for schema in schemas:
            await self.execute(schema)
    
    async def execute(self, query: str, *args) -> Any:
        """Execute a query."""
        if self._client is None:
            await self.connect()
        
        import inspect
        is_async = inspect.iscoroutinefunction(self._client.execute)
        
        if is_async:
            # aiochclient
            query_stripped = query.strip().upper()
            if query_stripped.startswith("SELECT") or query_stripped.startswith("SHOW"):
                result = await self._client.fetch(query, *args)
                # Convert Record objects to dicts
                return [dict(row) for row in result] if result else []
            if args:
                return await self._client.execute(query, *args)
            return await self._client.execute(query)
        else:
            # clickhouse-connect sync client
            if args:
                return self._client.execute(query, *args)
            return self._client.execute(query)
    
    async def insert_trace(self, trace: Trace) -> None:
        """Insert a trace into ClickHouse."""
        import json
        
        # Compute aggregated metrics
        total_tokens = 0
        total_latency = 0.0
        span_count = self._count_spans(trace.root_span)
        
        if trace.root_span:
            self._aggregate_span_metrics(trace.root_span, total_tokens, total_latency)
        
        query = """
        INSERT INTO traces (
            trace_id, name, start_time, end_time, duration_ms,
            status, session_id, user_id, agent_name, environment,
            version, success, error_message, span_count, total_tokens,
            total_latency_ms, tags, attributes
        ) VALUES
        """
        
        values = [(
            trace.trace_id,
            trace.name,
            trace.start_time,
            trace.end_time,
            (trace.end_time - trace.start_time).total_seconds() * 1000 if trace.end_time else 0,
            trace.status.value,
            trace.session_id,
            trace.user_id,
            trace.agent_name,
            trace.environment,
            trace.version,
            trace.success,
            trace.error_message,
            span_count,
            total_tokens,
            total_latency,
            trace.tags,
            json.dumps(trace.attributes),
        )]
        
        await self.execute(query, *values)
        
        # Insert spans
        if trace.root_span:
            await self._insert_spans_recursive(trace.trace_id, trace.root_span)
    
    async def _insert_spans_recursive(self, trace_id: str, span: Span) -> None:
        """Recursively insert spans."""
        import json
        
        query = """
        INSERT INTO spans (
            span_id, trace_id, parent_span_id, span_type, name,
            start_time, end_time, duration_ms, status,
            input, output,
            prompt_tokens, completion_tokens, total_tokens,
            model_name, model_provider, temperature,
            latency_ms, retry_count,
            tool_calls, retrievals, memory_ops, reflections,
            attributes, tags
        ) VALUES
        """
        
        values = [(
            span.span_id,
            trace_id,
            span.parent_span_id,
            span.span_type.value,
            span.name,
            span.start_time,
            span.end_time,
            span.duration_ms,
            span.status.value,
            json.dumps(span.input) if span.input else None,
            json.dumps(span.output) if span.output else None,
            span.token_usage.prompt_tokens if span.token_usage else 0,
            span.token_usage.completion_tokens if span.token_usage else 0,
            span.token_usage.total_tokens if span.token_usage else 0,
            span.model_metadata.model_name if span.model_metadata else None,
            span.model_metadata.provider if span.model_metadata else None,
            span.model_metadata.temperature if span.model_metadata else None,
            span.latency_ms,
            span.retry_count,
            json.dumps([{"name": tc.tool_name, "params": tc.parameters, "error": tc.error, "latency_ms": tc.latency_ms, "retry_count": tc.retry_count} for tc in span.tool_calls]),
            json.dumps([{"source": r.source, "score": r.score, "rank": r.rank} for r in span.retrievals]),
            json.dumps([{"type": m.op_type.value, "key": m.key, "namespace": m.namespace, "success": m.success} for m in span.memory_ops]),
            json.dumps([{"iteration": r.iteration, "type": r.reflection_type, "confidence": r.confidence, "triggered_retry": r.triggered_retry} for r in span.reflections]),
            json.dumps(span.attributes),
            span.tags,
        )]
        
        await self.execute(query, *values)
        
        for child in span.children:
            await self._insert_spans_recursive(trace_id, child)
    
    def _count_spans(self, span: Optional[Span]) -> int:
        if not span:
            return 0
        count = 1
        for child in span.children:
            count += self._count_spans(child)
        return count
    
    def _aggregate_span_metrics(self, span: Span, total_tokens: int, total_latency: float) -> None:
        if span.token_usage:
            total_tokens += span.token_usage.total_tokens
        total_latency += span.latency_ms
        for child in span.children:
            self._aggregate_span_metrics(child, total_tokens, total_latency)
    
    async def query_traces(
        self,
        agent_name: Optional[str] = None,
        environment: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        success_only: bool = False,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query traces with filters."""
        conditions = ["1=1"]
        if agent_name:
            conditions.append(f"agent_name = '{agent_name}'")
        if environment:
            conditions.append(f"environment = '{environment}'")
        if start_time:
            conditions.append(f"start_time >= '{start_time.isoformat()}'")
        if end_time:
            conditions.append(f"start_time <= '{end_time.isoformat()}'")
        if success_only:
            conditions.append("success = true")
        
        query = f"""
        SELECT *
        FROM traces
        WHERE {' AND '.join(conditions)}
        ORDER BY start_time DESC
        LIMIT {limit}
        """
        
        return await self.execute(query) or []
