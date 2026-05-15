<p align="center">
  <img src="https://img.shields.io/badge/AI-Reliability%20Engineering-blue?style=for-the-badge" alt="AI Reliability Lab" />
</p>

<h1 align="center">AI Reliability Lab</h1>

<p align="center">
  <strong>Infrastructure for measuring, evaluating, and ensuring the reliability of AI agents</strong>
</p>

<p align="center">
  <a href="#architecture"><img src="https://img.shields.io/badge/Architecture-7%20Layers-orange" alt="Architecture" /></a>
  <a href="#evaluators"><img src="https://img.shields.io/badge/Evaluators-5-green" alt="Evaluators" /></a>
  <a href="#benchmarks"><img src="https://img.shields.io/badge/Benchmarks-28-purple" alt="Benchmarks" /></a>
  <a href="#tests"><img src="https://img.shields.io/badge/Tests-21%20Passing-brightgreen" alt="Tests" /></a>
  <a href="#dashboard"><img src="https://img.shields.io/badge/Dashboard-Next.js%2014-blue" alt="Dashboard" /></a>
</p>

---

## Table of Contents

- [What is This?](#what-is-this)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Core Features](#core-features)
  - [Phase 1: AI Telemetry SDK](#phase-1-ai-telemetry-sdk)
  - [Phase 2: Trace Ingestion Pipeline](#phase-2-trace-ingestion-pipeline)
  - [Phase 3: Evaluation Engine](#phase-3-evaluation-engine)
  - [Phase 4: Reliability Engine](#phase-4-reliability-engine)
  - [Phase 5: Regression Testing / CI-CD](#phase-5-regression-testing--ci-cd)
  - [Phase 6: Dashboard](#phase-6-dashboard)
  - [Phase 7: Benchmark Lab](#phase-7-benchmark-lab)
- [Installation](#installation)
- [Usage Guide](#usage-guide)
  - [Instrument Your Agent](#instrument-your-agent)
  - [Record Rich Telemetry](#record-rich-telemetry)
  - [Run Evaluations](#run-evaluations)
  - [Run Benchmarks](#run-benchmarks)
  - [Regression Testing](#regression-testing)
  - [Reliability Analysis](#reliability-analysis)
- [Framework Integrations](#framework-integrations)
  - [OpenAI SDK](#openai-sdk)
  - [LangGraph](#langgraph)
  - [LiteLLM](#litellm)
- [CLI Tool](#cli-tool)
- [Dashboard](#dashboard)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Project Structure](#project-structure)
- [Model Recommendations](#model-recommendations)
- [Contributing](#contributing)
- [License](#license)

---

## What is This?

**AI Reliability Lab** is an open-source infrastructure platform for **agent reliability engineering**.

Think of it as:
- **Datadog** — but for AI agent traces, not system metrics
- **Langfuse** — but with statistical reliability analysis and reflection loop evaluation
- **Phoenix** — but with built-in regression testing and CI-CD integration

### The Problem

AI agents fail in ways traditional software doesn't:
- They **hallucinate** and make up facts
- They **loop endlessly** trying to self-correct
- They **select wrong tools** or pass invalid parameters
- They **forget context** mid-conversation
- They **retrieve irrelevant documents** for RAG

Most teams build AI apps but have **zero visibility** into these failure modes. This platform solves that.

### The Solution

A 7-layer infrastructure stack that:
1. **Instruments** your agent to capture every operation
2. **Evaluates** agent outputs for quality and correctness
3. **Measures** statistical reliability across runs
4. **Blocks bad deployments** before they reach production
5. **Visualizes** everything in a production-grade dashboard

---

## Architecture

The system follows a layered architecture inspired by production observability platforms:

```
┌─────────────────────────────────────────────────────────────┐
│                      DASHBOARD LAYER                        │
│              Next.js 14 + React Flow + Recharts             │
│         Trace Explorer | Reflection Visualizer | Analytics  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        API LAYER                            │
│              FastAPI + Pydantic + OpenTelemetry             │
│     /v1/traces | /v1/metrics | /v1/alerts | /health         │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
     ┌────────────┐  ┌────────────┐  ┌────────────┐
     │ ClickHouse │  │   Redis    │  │ PostgreSQL │
     │  (Traces)  │  │  (Queue)   │  │(Metadata)  │
     └────────────┘  └────────────┘  └────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
     ┌────────────┐  ┌────────────┐  ┌────────────┐
     │  Worker    │  │ Evaluator  │  │Reliability │
     │  (Celery)  │  │  (Evals)   │  │  (Stats)  │
     └────────────┘  └────────────┘  └────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      SDK LAYER                              │
│            Python SDK with OpenTelemetry                    │
│      Tracer | Exporters | Framework Integrations            │
└─────────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

| Layer | Tech Stack | What It Does |
|-------|-----------|--------------|
| **SDK Layer** | Python 3.11, OpenTelemetry API | Instruments agents, captures traces |
| **Ingestion Layer** | FastAPI, Pydantic v2 | Receives telemetry via REST API |
| **Processing Layer** | Celery + Redis | Async job queue for evaluations |
| **Storage Layer** | ClickHouse, PostgreSQL, Qdrant | High-throughput trace analytics |
| **Evaluation Engine** | Custom evaluators + LLM judges | Scores agent behavior |
| **Dashboard** | Next.js 14, React Flow, Recharts | Visualizes traces and metrics |
| **Benchmark Runner** | Python test suites | Adversarial regression testing |

---

## Quick Start

### Prerequisites

- **Python 3.10+** (tested on 3.11)
- **Node.js 20+** (for dashboard)
- **Docker & Docker Compose** (for infrastructure)
- **Git**

### 1. Clone and Setup

```bash
git clone https://github.com/moghalsaif/AI-reliability-app.git
cd AI-reliability-app
```

### 2. Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Python Packages

```bash
# Install all packages in development mode
pip install -e packages/shared
pip install -e packages/sdk
pip install -e packages/evals
pip install -e packages/reliability
pip install -e packages/tracing
pip install -e packages/prompts
pip install -e apps/api
pip install -e apps/worker
pip install -e apps/evaluator

# Install dev dependencies
pip install pytest pytest-asyncio black mypy
```

### 4. Run Tests

```bash
pytest packages/shared/tests/ packages/evals/tests/ packages/reliability/tests/ -v
```

Expected output: **21 tests passing**.

### 5. Run the Demo

```bash
python examples/quickstart.py
```

You'll see a fully instrumented RAG agent trace printed to the console.

---

## Core Features

### Phase 1: AI Telemetry SDK

**Location:** `packages/sdk/`

The SDK is the entry point. It wraps around your agent code and automatically captures:

- **Prompts** and **completions**
- **Tool calls** with parameters and results
- **Retrieval** results with relevance scores
- **Memory operations** (reads/writes)
- **Reflection loops** (self-correction iterations)
- **Latency** and **token usage**
- **Model metadata** (name, provider, temperature)
- **Errors** and stack traces

#### OpenTelemetry Integration

This is not optional. Every trace flows through OpenTelemetry OTLP, teaching real observability engineering. The SDK exports to:
- **Console** (for debugging)
- **HTTP** (to the FastAPI backend)
- **OTLP** (to Jaeger or any OTLP-compatible collector)

#### Framework Support

- **LangGraph** — automatic node wrapping
- **OpenAI SDK** — `chat.completions.create` instrumentation
- **LiteLLM** — global completion interception
- **CrewAI** — compatible via manual tracing
- **AutoGen** — compatible via manual tracing

### Phase 2: Trace Ingestion Pipeline

**Location:** `apps/api/`

The FastAPI backend accepts telemetry and routes it through the system:

```python
POST /v1/traces       # Ingest a single trace
POST /v1/traces/batch # Ingest a batch of traces
GET  /v1/traces       # List traces with filters
GET  /v1/traces/{id}  # Get specific trace
GET  /v1/traces/{id}/spans        # Get all spans
GET  /v1/traces/{id}/evaluations  # Get evaluations
GET  /v1/metrics/reliability      # Aggregated metrics
GET  /v1/alerts                   # List alerts
POST /v1/alerts/{id}/acknowledge  # Acknowledge alert
GET  /health                      # Health check
```

**Storage:** ClickHouse handles high-ingest analytics workloads with TTL-based data expiration.

**Async Processing:** Redis queues traces for evaluation by Celery workers.

### Phase 3: Evaluation Engine

**Location:** `packages/evals/`

This is the core of the platform. Five evaluators score different aspects of agent behavior:

#### 1. Hallucination Evaluator

Detects **unsupported claims**, **contradictions**, and **fabricated citations**.

Methods:
- **Semantic grounding** — compares output against retrieved context
- **LLM judge** — Qwen3 32B evaluates claim validity
- **Citation validation** — verifies that cited sources exist

```python
from reliability_evals import HallucinationEvaluator

evaluator = HallucinationEvaluator()
result = evaluator.evaluate(trace_data)

print(result.score)      # 0.0 to 1.0 (higher = less hallucination)
print(result.passed)     # True if score >= threshold
print(result.details)    # { "unsupported_claims": [...], ... }
```

#### 2. RAG Evaluator

Measures **retrieval relevance**, **context precision**, and **answer grounding**.

Inspired by RAGAS and DeepEval.

```python
from reliability_evals import RAGEvaluator

evaluator = RAGEvaluator()
result = evaluator.evaluate(trace_data)

# result.details:
#   avg_relevance: 0.87
#   avg_precision: 0.72
#   avg_answer_relevance: 0.91
```

#### 3. Tool Use Evaluator

Checks **correct tool selection**, **parameter validity**, and **redundant retries**.

Critical for agent reliability — bad tool calls break workflows.

```python
from reliability_evals import ToolUseEvaluator

evaluator = ToolUseEvaluator()
result = evaluator.evaluate(trace_data)

# result.details:
#   error_rate: 0.05
#   avg_retries: 0.2
#   avg_latency_ms: 250.0
```

#### 4. Reflection Loop Evaluator

**This is the key differentiator.** Most tools don't measure reasoning retries.

Detects:
- **Oscillation** — flip-flopping between decisions
- **Indecision** — high iterations with low confidence
- **Loop collapse** — infinite loops with no progress
- **Retry density** — too many retries per unit of work

```python
from reliability_evals import ReflectionEvaluator

evaluator = ReflectionEvaluator()
result = evaluator.evaluate(trace_data)

# result.details:
#   reflection_count: 3
#   oscillation_score: 0.2 (low = detected oscillation)
#   improvement_score: 0.8 (high = getting better)
#   collapse_score: 0.1 (low = loop detected)
```

#### 5. Memory Evaluator

Checks **memory retrieval quality**, **stale data**, **poisoning**, and **forgotten context**.

```python
from reliability_evals import MemoryEvaluator

evaluator = MemoryEvaluator()
result = evaluator.evaluate(trace_data)

# result.details:
#   read_success: 0.95
#   retrieval_quality: 0.88
#   utilization: 0.72
```

All evaluators implement the `BaseEvaluator` interface:

```python
class BaseEvaluator(ABC):
    @abstractmethod
    def default_threshold(self) -> float: pass

    @abstractmethod
    def evaluate(self, trace_data: Dict) -> EvalResult: pass
```

Adding a new evaluator is 3 steps: create the file, implement the methods, register it.

### Phase 4: Reliability Engine

**Location:** `packages/reliability/`

Runs **statistical reliability analysis** across multiple agent executions.

Metrics computed:
- `success_rate` — percentage of successful runs
- `hallucination_rate` — percentage with hallucination
- `variance_score` — consistency across runs (lower CV = higher score)
- `retry_density` — retries per unit of work
- `cost_per_success` — token cost normalized by success
- `latency_p95` — 95th percentile latency
- `context_retention` — memory quality score
- `tool_accuracy` — tool call success rate

```python
from reliability_engine import ReliabilityAnalyzer, ReliabilityRun

# Run the same task 10 times
runs = [ReliabilityRun(...), ...]

analyzer = ReliabilityAnalyzer()
report = analyzer.analyze(runs, experiment_id="exp-001")

print(report.success_rate)      # 0.85
print(report.variance_score)   # 0.92
print(report.drift_detected)   # True
```

**Drift Detection:** Automatically detects when performance degrades over time (e.g., success rate dropping, latency increasing).

**Experiment Comparison:** Compare two versions and show diffs:

```python
baseline = analyzer.analyze(runs_v1, experiment_id="baseline")
current = analyzer.analyze(runs_v2, experiment_id="current")
diff = analyzer.compare_experiments(baseline, current)

# diff:
#   success_rate: +5%
#   latency_p95: -12%
#   hallucination_rate: +2%
```

### Phase 5: Regression Testing / CI-CD

**Location:** `packages/reliability/src/regression.py`

This is **AI-native CI-CD**. When you change:
- A prompt
- A model
- Retrieval logic
- Tool definitions

The system automatically:
1. Runs the benchmark suite
2. Runs the eval suite
3. Computes reliability metrics
4. Compares against baseline
5. **Blocks deployment** if critical regressions are detected

Output looks like:
```
Truthfulness: +7%
Latency: -12%
Hallucination: +19%

Deploy: NO
Blocking Issues:
  - Hallucination increased by 19%
```

```python
from reliability_engine.regression import RegressionTestRunner, TestCase

test_cases = [
    TestCase(id="t1", name="Basic QA", input="What is 2+2?", expected_output="4"),
    TestCase(id="t2", name="Tool Use", input="Get weather", expected_tools=["weather_api"]),
]

runner = RegressionTestRunner(agent_factory=my_agent_factory)
report = runner.run_test_suite(test_cases, commit_hash="abc123")

if not report.should_deploy:
    sys.exit(1)  # Block the CI pipeline
```

### Phase 6: Dashboard

**Location:** `apps/dashboard/`

A production-grade Next.js 14 application with four pages:

#### Trace Explorer (`/`)
- Datadog-style span listing
- Real-time latency trends
- Success/failure rates
- Trace detail view with all spans

#### Reflection Loop Visualizer (`/reflections`)
- **This is the killer feature.**
- React Flow graph showing reasoning retries
- Color-coded nodes: reflection, decision, retry, success, failure
- Statistics: iteration count, oscillation rate, loop collapses

#### Reliability Analytics (`/reliability`)
- Radar chart comparing current vs baseline
- Scatter plot: model comparison (success rate vs latency vs cost)
- Stability trends over time
- Failure hotspot analysis

#### Benchmark Lab (`/benchmarks`)
- Run benchmark suites
- Track progress per suite
- Compare category performance
- Test breakdown with pass/fail ratios

### Phase 7: Benchmark Lab

**Location:** `benchmarks/`

28 adversarial test cases across 4 categories:

| Suite | Tests | What They Test |
|-------|-------|---------------|
| **RAG** | 8 | Contradiction, entailment, paraphrase, negation, multi-hop reasoning |
| **Agents** | 6 | Planning, tool selection, error recovery, logical reasoning |
| **Memory** | 5 | Long-context retention, poisoning, stale data, forgotten context |
| **Tool Use** | 9 | Tool selection, parameter validation, timeout recovery, rate limit fallback |

```python
from benchmarks.runner import BenchmarkRegistry

registry = BenchmarkRegistry()
registry.export_all(output_dir="datasets")
# Creates 4 JSON files with test cases
```

---

## Installation

### Development Setup

```bash
# Clone
git clone https://github.com/moghalsaif/AI-reliability-app.git
cd AI-reliability-app

# Python environment
python3.11 -m venv venv
source venv/bin/activate

# Install all packages
make install

# Or manually:
for pkg in shared sdk evals reliability tracing prompts; do
    pip install -e packages/$pkg
done

for app in api worker evaluator; do
    pip install -e apps/$app
done

# Dashboard dependencies
cd apps/dashboard
npm install
```

### Production Setup

```bash
# Start all infrastructure
cd infra/docker
docker compose up -d

# Verify services
docker compose ps
```

Services started:
- **ClickHouse** (8123) — Trace storage
- **Redis** (6379) — Job queue
- **PostgreSQL** (5432) — Metadata
- **Qdrant** (6333) — Vector DB
- **API** (8000) — FastAPI backend
- **Dashboard** (3000) — Next.js frontend
- **Ollama** (11434) — Local LLM inference
- **Jaeger** (16686) — Distributed tracing
- **Prometheus** (9090) — Metrics
- **Grafana** (3001) — Dashboards

---

## Usage Guide

### Instrument Your Agent

**Minimum viable integration (2 lines):**

```python
from reliability_sdk import Tracer

tracer = Tracer(service_name="my-agent")

with tracer.trace("workflow_name", agent_name="bot_v1"):
    response = agent.run(user_query)
```

**Rich telemetry (recommended):**

```python
from reliability_sdk import Tracer
from reliability_shared.types.core import (
    ModelMetadata, TokenUsage, RetrievalResult
)

tracer = Tracer(service_name="rag-agent")

with tracer.trace("knowledge_query", agent_name="kb_bot"):
    
    # Memory read
    tracer.record_memory_op(
        op_type="read",
        key="user_preferences",
        value={"tier": "premium"},
        namespace="profile",
    )
    
    # Retrieval
    tracer.record_retrieval(
        query="refund policy",
        results=[
            RetrievalResult(
                query="refund policy",
                source="kb://policies",
                content="Full refund within 30 days",
                score=0.96,
                rank=0,
            ),
        ],
        latency_ms=145,
    )
    
    # LLM call
    tracer.record_llm_call(
        prompt="Customer wants refund",
        completion="You are eligible",
        model_metadata=ModelMetadata(
            model_name="gpt-4",
            provider="openai",
            temperature=0.3,
        ),
        token_usage=TokenUsage(prompt_tokens=50, completion_tokens=20),
        latency_ms=1500,
    )
    
    # Tool call
    tracer.record_tool_call(
        tool_name="process_refund",
        parameters={"amount": 99.99},
        result={"status": "success"},
        latency_ms=300,
    )
    
    # Reflection
    tracer.record_reflection(
        iteration=1,
        reflection_type="verification",
        input_context="Check answer",
        output_decision="Confirmed",
        confidence=0.92,
        triggered_retry=False,
    )
```

### Run Evaluations

**Via Python API:**

```python
from reliability_evals import HallucinationEvaluator, RAGEvaluator

hallucination = HallucinationEvaluator()
rag = RAGEvaluator()

# Evaluate a trace
trace_data = {"spans": [...]}  # Your trace

h_result = hallucination.evaluate(trace_data)
r_result = rag.evaluate(trace_data)

print(f"Hallucination: {h_result.score:.3f} ({'PASS' if h_result.passed else 'FAIL'})")
print(f"RAG: {r_result.score:.3f} ({'PASS' if r_result.passed else 'FAIL'})")
```

**Via CLI:**

```bash
python cli.py eval --trace-file my_trace.json --output results.json
```

### Run Benchmarks

```bash
# List suites
python cli.py benchmark --list

# Run specific suite
python cli.py benchmark --suite rag

# Export all to JSON
python -c "from benchmarks.runner import BenchmarkRegistry; BenchmarkRegistry().export_all()"
```

### Regression Testing

```python
from reliability_engine.regression import (
    RegressionTestRunner, TestCase, CICDPipeline
)

def my_agent_factory():
    return MyAgent()

test_cases = [
    TestCase(id="t1", name="Basic QA", input="2+2=", expected_output="4"),
    TestCase(id="t2", name="Tool Use", input="Weather?", expected_tools=["weather_api"]),
]

runner = RegressionTestRunner(agent_factory=my_agent_factory)
pipeline = CICDPipeline(runner)

# This blocks deployment on regression
result = pipeline.run_pipeline(test_cases, commit_hash="abc123")
```

### Reliability Analysis

```python
from reliability_engine import ReliabilityAnalyzer, ReliabilityRun

# Create runs from your traces
runs = [
    ReliabilityRun(
        run_id="r1",
        trace_id="t1",
        agent_name="qa_bot",
        model_name="qwen3-32b",
        temperature=0.7,
        prompt_version="v1.0",
        success=True,
        latency_ms=1200,
        token_count=500,
        hallucination_score=0.92,
        tool_accuracy=0.95,
        reflection_score=0.88,
        timestamp="2024-01-01",
    ),
    # ... more runs
]

analyzer = ReliabilityAnalyzer()
report = analyzer.analyze(runs, experiment_id="exp-001")

print(f"Success Rate: {report.success_rate:.1%}")
print(f"Variance: {report.variance_score:.3f}")
print(f"Drift: {report.drift_detected}")
```

---

## Framework Integrations

### OpenAI SDK

```python
from reliability_sdk import Tracer, OpenAIIntegration
import openai

tracer = Tracer()
client = openai.OpenAI()

integration = OpenAIIntegration(tracer)
instrumented = integration.instrument_client(client)

with tracer.trace("openai_chat"):
    response = instrumented.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Hello"}],
    )
```

### LangGraph

```python
from reliability_sdk import Tracer, LangGraphIntegration
from langgraph.graph import StateGraph

tracer = Tracer()
builder = StateGraph(dict)
# ... build graph ...
graph = builder.compile()

integration = LangGraphIntegration(tracer)
instrumented = integration.instrument_graph(graph)

with tracer.trace("workflow"):
    result = instrumented.invoke({"input": "hello"})
```

### LiteLLM

```python
from reliability_sdk import Tracer, LiteLLMIntegration

tracer = Tracer()
LiteLLMIntegration(tracer).instrument()

import litellm
response = litellm.completion(model="gpt-4", messages=[...])
# Automatically traced
```

### Decorators

```python
from reliability_sdk import instrument_llm, instrument_tool

@instrument_llm(model_name="gpt-4", provider="openai")
def generate_response(prompt):
    return openai_client.chat.completions.create(...)

@instrument_tool(tool_name="calculator")
def calculate(x, y):
    return x + y
```

---

## CLI Tool

The CLI provides quick access to all platform features:

```bash
# Trace a single operation
python cli.py trace --name "test" --input "hello" --service "my-agent"

# Evaluate a trace file
python cli.py eval --trace-file trace.json --output results.json

# List benchmark suites
python cli.py benchmark --list

# Run regression tests
python cli.py regress
```

---

## Dashboard

The dashboard is a Next.js 14 application.

### Development

```bash
cd apps/dashboard
npm install
npm run dev
```

Open http://localhost:3000

### Pages

| Route | What You See |
|-------|-------------|
| `/` | Trace Explorer — list traces, latency trends, span counts |
| `/reflections` | Reflection Visualizer — React Flow graph of reasoning loops |
| `/reliability` | Analytics — radar charts, scatter plots, failure hotspots |
| `/benchmarks` | Benchmark Lab — run suites, track progress, view results |

### Build for Production

```bash
cd apps/dashboard
npm run build
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RELIABILITY_API_ENDPOINT` | `http://localhost:8000/v1/traces` | Trace ingestion endpoint |
| `RELIABILITY_API_KEY` | None | API key for authentication |
| `RELIABILITY_ENVIRONMENT` | `development` | Environment tag |
| `RELIABILITY_SERVICE_NAME` | `ai-agent` | Service identifier |
| `RELIABILITY_BATCH_SIZE` | `100` | Traces per batch |
| `RELIABILITY_FLUSH_INTERVAL_MS` | `5000` | Auto-flush interval |
| `CLICKHOUSE_HOST` | `localhost` | ClickHouse server |
| `CLICKHOUSE_PORT` | `8123` | ClickHouse port |
| `CLICKHOUSE_DATABASE` | `reliability_lab` | Database name |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | None | OpenTelemetry endpoint |
| `OTEL_EXPORTER_OTLP_HEADERS` | None | OTLP headers |

### Config Object

```python
from reliability_sdk import ReliabilityConfig

# Load from environment
config = ReliabilityConfig.from_env()

# Or create manually
config = ReliabilityConfig(
    api_endpoint="https://api.reliability-lab.io/v1/traces",
    api_key="sk-...",
    environment="production",
    batch_size=100,
    flush_interval_ms=5000,
)
```

---

## API Reference

### Trace Ingestion

```http
POST /v1/traces
Content-Type: application/json

{
  "trace": {
    "trace_id": "uuid",
    "name": "workflow_name",
    "start_time": "2024-01-01T00:00:00",
    "end_time": "2024-01-01T00:00:05",
    "status": "ok",
    "success": true,
    "agent_name": "bot_v1",
    "environment": "production",
    "spans": [...]
  },
  "source": "sdk"
}
```

### Trace Query

```http
GET /v1/traces?agent_name=bot_v1&environment=production&limit=100
```

### Reliability Metrics

```http
GET /v1/metrics/reliability?agent_name=bot_v1
```

Response:
```json
{
  "metrics": {
    "avg_success_rate": 0.94,
    "avg_hallucination_rate": 0.05,
    "avg_variance_score": 0.89,
    "avg_latency_p95": 2100,
    "avg_tool_accuracy": 0.96
  }
}
```

---

## Docker Deployment

### Full Stack

```bash
cd infra/docker
docker compose up -d
```

This starts:
- ClickHouse (trace storage)
- Redis (queue)
- PostgreSQL (metadata)
- Qdrant (vector DB)
- FastAPI (backend)
- Next.js (dashboard)
- Ollama (local LLMs)
- Jaeger (distributed tracing)
- Prometheus (metrics)
- Grafana (dashboards)

### Individual Services

```bash
# Just databases
docker compose up -d clickhouse redis postgres

# Add API and workers
docker compose up -d api worker evaluator

# Full stack with monitoring
docker compose up -d
```

---

## Kubernetes Deployment

```bash
kubectl apply -f infra/kubernetes/deployments.yaml
```

This creates:
- 3 API replicas
- 5 worker replicas
- 2 dashboard replicas
- Ingress for routing

---

## Project Structure

```
ai-reliability-lab/
│
├── apps/                          # Runnable applications
│   ├── api/                       # FastAPI backend
│   │   └── src/
│   │       └── main.py            # API routes, trace ingestion
│   ├── dashboard/                 # Next.js 14 frontend
│   │   ├── app/                   # Pages (trace explorer, reflections, etc.)
│   │   │   ├── page.tsx           # Trace Explorer
│   │   │   ├── reflections/     # Reflection Loop Visualizer
│   │   │   ├── reliability/       # Reliability Analytics
│   │   │   └── benchmarks/        # Benchmark Lab
│   │   └── lib/api.ts             # API client
│   ├── worker/                    # Celery async workers
│   └── evaluator/                 # Standalone evaluation worker
│
├── packages/                      # Reusable Python packages
│   ├── sdk/                       # AI Telemetry SDK
│   │   └── src/reliability_sdk/
│   │       ├── core/tracer.py     # Trace builder & context manager
│   │       ├── exporters/         # Console, HTTP, OpenTelemetry
│   │       └── integrations/      # OpenAI, LangGraph, LiteLLM
│   ├── evals/                     # Evaluation Engine
│   │   └── src/reliability_evals/
│   │       ├── base.py            # BaseEvaluator interface
│   │       └── evaluators/
│   │           ├── hallucination.py
│   │           ├── rag.py
│   │           ├── tool_use.py
│   │           ├── reflection.py   # KEY DIFFERENTIATOR
│   │           └── memory.py
│   ├── reliability/               # Reliability Engine
│   │   └── src/reliability_engine/
│   │       ├── engine.py          # Statistical analysis
│   │       └── regression.py     # CI/CD pipeline
│   ├── shared/                    # Shared types & utilities
│   │   └── src/reliability_shared/
│   │       ├── types/core.py      # Trace, Span, TokenUsage, etc.
│   │       ├── config.py          # ReliabilityConfig
│   │       └── utils.py           # Helper functions
│   ├── tracing/                   # OpenTelemetry wrappers
│   └── prompts/                   # Prompt templates
│
├── benchmarks/                    # Adversarial test datasets
│   ├── rag/adversarial.py         # 8 RAG tests
│   ├── agents/suite.py            # 6 agent tests
│   ├── memory/stress.py           # 5 memory tests
│   ├── tool_use/suite.py          # 9 tool tests
│   └── runner.py                  # Benchmark registry & exporter
│
├── infra/                         # Deployment configs
│   ├── docker/
│   │   ├── docker-compose.yml     # 11 services
│   │   ├── Dockerfile.api
│   │   ├── Dockerfile.dashboard
│   │   ├── Dockerfile.worker
│   │   └── Dockerfile.evaluator
│   ├── kubernetes/
│   │   └── deployments.yaml       # K8s manifests
│   └── terraform/
│       └── main.tf                # Terraform starter
│
├── examples/                      # Working code examples
│   ├── quickstart.py              # 5-minute quick start
│   ├── basic_usage.py             # SDK features demo
│   └── framework_integrations.py  # OpenAI, LangGraph, LiteLLM
│
├── docs/                          # Documentation
│   ├── user-guide.md              # Comprehensive usage guide
│   ├── sdk-guide.md               # SDK reference
│   └── CONTRIBUTING.md            # Contributing guide
│
├── datasets/                      # Exported benchmark JSON files
│   ├── rag_benchmark.json
│   ├── agents_benchmark.json
│   ├── memory_benchmark.json
│   └── tool_use_benchmark.json
│
├── cli.py                         # Command-line interface
├── demo.py                        # Full system demonstration
├── test_all.py                    # Comprehensive test suite
├── setup.py                       # Unified setup script
├── Makefile                       # Development commands
├── .github/workflows/ci.yml       # GitHub Actions CI
└── README.md                      # This file
```

---

## Model Recommendations

This platform is designed to work with multiple model classes:

| Purpose | Recommended Model | Why |
|---------|-------------------|-----|
| **Primary Reasoning** | Qwen3 32B | Best balance of reasoning, tool calling, structured outputs, and cost |
| **Fast Evaluation** | Ministral 8B | Lightweight scoring, semantic checks, fast eval loops |
| **Embeddings** | bge-m3 | Semantic similarity, RAG evals, retrieval scoring, clustering |
| **Reranking** | bge-reranker-v2 | Retrieval quality scoring, citation validation |
| **Classification** | ModernBERT | Hallucination classification, trace tagging, anomaly detection |

All models can be run locally via **Ollama** or remotely via APIs (OpenAI, LiteLLM, etc.).

---

## Tests

Run the test suite:

```bash
# All tests
pytest packages/ apps/ -v

# Specific packages
pytest packages/shared/tests/ -v
pytest packages/evals/tests/ -v
pytest packages/reliability/tests/ -v

# With coverage
pytest packages/ --cov=packages --cov-report=html
```

Current test coverage:
- **Shared types**: 7 tests (trace creation, span types, token usage, etc.)
- **Evaluators**: 6 tests (hallucination, reflection)
- **Reliability**: 8 tests (regression, report generation, baseline comparison)

---

## Contributing

We welcome contributions! See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

Quick start for contributors:

```bash
# Fork and clone
git clone https://github.com/your-username/AI-reliability-app.git
cd AI-reliability-app

# Install in dev mode
make install

# Run tests
make test

# Format code
make format
```

---

## Why This Exists

AI agents are the future of software. But they fail in unpredictable ways:

- **Hallucination** costs businesses money (wrong advice, bad decisions)
- **Tool errors** break workflows (invalid parameters, timeouts)
- **Reflection loops** waste compute (infinite retries, oscillation)
- **Memory failures** destroy user trust (forgetting preferences, stale context)

Existing tools (Langfuse, Phoenix) provide basic observability. But they don't:
- Measure **reflection loop quality**
- Run **statistical reliability analysis**
- Provide **CI-native regression testing**
- Offer **adversarial benchmark suites**

This platform fills those gaps.

---

## Roadmap

- [x] Core SDK with OpenTelemetry
- [x] 5 production evaluators
- [x] Reliability engine with drift detection
- [x] Regression testing / CI-CD pipeline
- [x] Next.js dashboard with React Flow
- [x] 28 adversarial benchmarks
- [x] Docker Compose infrastructure
- [x] Kubernetes manifests
- [ ] Real-time alerting engine
- [ ] Cost optimization analysis
- [ ] Multi-agent workflow evaluation
- [ ] A/B testing framework
- [ ] Custom evaluator marketplace

---

## License

MIT License — see LICENSE file for details.

---

## Acknowledgments

- Inspired by Datadog, Langfuse, Phoenix, and Weights & Biases
- Built with FastAPI, Next.js, ClickHouse, Redis, Celery, and OpenTelemetry
- Evaluation methodologies inspired by RAGAS and DeepEval

---

## Contact

- **Issues**: [GitHub Issues](https://github.com/moghalsaif/AI-reliability-app/issues)
- **Discussions**: [GitHub Discussions](https://github.com/moghalsaif/AI-reliability-app/discussions)

---

<p align="center">
  <strong>Built for systems engineers who care about AI reliability.</strong>
</p>
