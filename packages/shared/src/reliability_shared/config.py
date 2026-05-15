"""Shared configuration and constants."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ReliabilityConfig:
    """Configuration for the reliability SDK."""
    
    # API endpoint for trace ingestion
    api_endpoint: str = "http://localhost:8000/v1/traces"
    
    # API key for authentication
    api_key: Optional[str] = None
    
    # Batch settings
    batch_size: int = 100
    flush_interval_ms: float = 5000.0
    max_queue_size: int = 10000
    
    # Sampling
    sample_rate: float = 1.0
    
    # Environment
    environment: str = "development"
    service_name: str = "ai-agent"
    service_version: Optional[str] = None
    
    # OpenTelemetry
    otel_endpoint: Optional[str] = None
    otel_headers: Optional[dict] = None
    
    # ClickHouse
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123
    clickhouse_database: str = "reliability_lab"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Processing
    enable_evaluations: bool = True
    enable_reliability_analysis: bool = True
    
    @classmethod
    def from_env(cls) -> "ReliabilityConfig":
        """Load configuration from environment variables."""
        return cls(
            api_endpoint=os.getenv("RELIABILITY_API_ENDPOINT", cls.api_endpoint),
            api_key=os.getenv("RELIABILITY_API_KEY"),
            batch_size=int(os.getenv("RELIABILITY_BATCH_SIZE", cls.batch_size)),
            flush_interval_ms=float(os.getenv("RELIABILITY_FLUSH_INTERVAL_MS", cls.flush_interval_ms)),
            max_queue_size=int(os.getenv("RELIABILITY_MAX_QUEUE_SIZE", cls.max_queue_size)),
            sample_rate=float(os.getenv("RELIABILITY_SAMPLE_RATE", cls.sample_rate)),
            environment=os.getenv("RELIABILITY_ENVIRONMENT", cls.environment),
            service_name=os.getenv("RELIABILITY_SERVICE_NAME", cls.service_name),
            service_version=os.getenv("RELIABILITY_SERVICE_VERSION"),
            otel_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
            otel_headers=_parse_headers(os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "")),
            clickhouse_host=os.getenv("CLICKHOUSE_HOST", cls.clickhouse_host),
            clickhouse_port=int(os.getenv("CLICKHOUSE_PORT", cls.clickhouse_port)),
            clickhouse_database=os.getenv("CLICKHOUSE_DATABASE", cls.clickhouse_database),
            redis_url=os.getenv("REDIS_URL", cls.redis_url),
            enable_evaluations=os.getenv("RELIABILITY_ENABLE_EVALS", "true").lower() == "true",
            enable_reliability_analysis=os.getenv("RELIABILITY_ENABLE_RELIABILITY", "true").lower() == "true",
        )


def _parse_headers(header_str: str) -> Optional[dict]:
    if not header_str:
        return None
    headers = {}
    for pair in header_str.split(","):
        if "=" in pair:
            key, value = pair.split("=", 1)
            headers[key.strip()] = value.strip()
    return headers if headers else None


# Default eval thresholds
DEFAULT_EVAL_THRESHOLDS = {
    "hallucination": 0.15,
    "rag_relevance": 0.70,
    "tool_accuracy": 0.90,
    "reflection_improvement": 0.05,
    "memory_retention": 0.80,
}
