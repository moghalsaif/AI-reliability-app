# AI Reliability Lab SDK Guide

## Installation

```bash
pip install reliability-sdk
```

## Quick Start

### Basic Tracing

```python
from reliability_sdk import Tracer

tracer = Tracer(service_name="my-agent")

with tracer.trace("contract_review"):
    result = agent.run(contract_text)
```

### Framework Integrations

#### LangGraph

```python
from reliability_sdk import Tracer, LangGraphIntegration

tracer = Tracer()
integration = LangGraphIntegration(tracer)
instrumented_graph = integration.instrument_graph(my_graph)
```

#### OpenAI

```python
from reliability_sdk import Tracer, OpenAIIntegration
import openai

tracer = Tracer()
client = openai.OpenAI()
integration = OpenAIIntegration(tracer)
instrumented_client = integration.instrument_client(client)
```

#### LiteLLM

```python
from reliability_sdk import Tracer, LiteLLMIntegration

tracer = Tracer()
LiteLLMIntegration(tracer).instrument()
```

### Manual Span Recording

```python
from reliability_sdk import Tracer
from reliability_shared.types.core import ModelMetadata, TokenUsage

tracer = Tracer()

# Record LLM call
tracer.record_llm_call(
    prompt="What is the capital of France?",
    completion="Paris",
    model_metadata=ModelMetadata(
        model_name="gpt-4",
        provider="openai",
        temperature=0.7,
    ),
    token_usage=TokenUsage(
        prompt_tokens=10,
        completion_tokens=5,
    ),
    latency_ms=1200,
)

# Record tool call
tracer.record_tool_call(
    tool_name="weather_api",
    parameters={"location": "Tokyo"},
    result={"temp": 25, "condition": "sunny"},
    latency_ms=300,
)

# Record retrieval
tracer.record_retrieval(
    query="quantum computing",
    results=[
        {"source": "arxiv", "content": "...", "score": 0.95},
    ],
    latency_ms=150,
)

# Record reflection
tracer.record_reflection(
    iteration=1,
    reflection_type="self-correction",
    input_context="Incorrect calculation",
    output_decision="Recalculate with correct formula",
    confidence=0.85,
    triggered_retry=True,
)

# Record memory operation
tracer.record_memory_op(
    op_type="write",
    key="user_name",
    value="Alice",
    namespace="session",
)
```

### Exporters

```python
from reliability_sdk import (
    Tracer,
    OpenTelemetryExporter,
    HTTPExporter,
    ConsoleExporter,
)

tracer = Tracer()

# OpenTelemetry (recommended)
otel = OpenTelemetryExporter(
    endpoint="http://localhost:4317",
    service_name="my-agent",
)
tracer.add_exporter(otel)

# HTTP to Reliability Lab API
http = HTTPExporter(
    endpoint="http://localhost:8000/v1/traces",
    api_key="your-api-key",
)
tracer.add_exporter(http)

# Console (for debugging)
console = ConsoleExporter(pretty=True)
tracer.add_exporter(console)
```

## Configuration

```python
from reliability_sdk import ReliabilityConfig

# Load from environment variables
config = ReliabilityConfig.from_env()

# Or set manually
config = ReliabilityConfig(
    api_endpoint="https://api.reliability-lab.io/v1/traces",
    api_key="sk-...",
    environment="production",
    batch_size=100,
    flush_interval_ms=5000,
)
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `RELIABILITY_API_ENDPOINT` | Trace ingestion endpoint |
| `RELIABILITY_API_KEY` | API key |
| `RELIABILITY_ENVIRONMENT` | Environment tag |
| `RELIABILITY_SERVICE_NAME` | Service name |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OpenTelemetry endpoint |
| `CLICKHOUSE_HOST` | ClickHouse server |
| `REDIS_URL` | Redis connection |
