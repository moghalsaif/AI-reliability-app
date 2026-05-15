# AI Reliability Lab — User Guide

## Quick Start (5 minutes)

### 1. Install the SDK

```bash
cd /Users/moghalsaif/Documents/AI\ Reliability\ Lab
source venv/bin/activate
pip install -e packages/sdk
```

### 2. Instrument Your Agent (Python)

The SDK wraps around your existing agent code with a single context manager:

```python
from reliability_sdk import Tracer

tracer = Tracer(service_name="my-agent")

# Wrap your agent run with a trace
with tracer.trace("contract_review", agent_name="legal_v1"):
    response = agent.run(user_query)
```

That's it. The SDK automatically captures:
- Prompts and completions
- Tool calls and parameters
- Retrieval results
- Memory operations
- Reflection/retry loops
- Latency and token usage

### 3. Run It

```bash
python your_agent.py
```

You'll see traces printed to console. Next, send them to the platform.

---

## Full Walkthrough

### Step 1: Install Everything

```bash
# Clone the repo
cd ai-reliability-lab

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install all packages
make install

# Or manually:
pip install -e packages/shared
pip install -e packages/sdk
pip install -e packages/evals
pip install -e packages/reliability
```

### Step 2: Start Infrastructure (Docker)

```bash
cd infra/docker

# Start ClickHouse (traces), Redis (queue), and supporting services
docker compose up -d clickhouse redis postgres

# Verify they're running
docker compose ps
```

Services started:
- **ClickHouse** on port 8123 (trace storage)
- **Redis** on port 6379 (job queue)
- **PostgreSQL** on port 5432 (metadata)

### Step 3: Instrument Your Agent

#### Basic Example

```python
from reliability_sdk import Tracer, HTTPExporter

# Create tracer with HTTP export to the API
tracer = Tracer(service_name="customer-support")
tracer.add_exporter(HTTPExporter(
    endpoint="http://localhost:8000/v1/traces",
))

# Wrap agent execution
with tracer.trace("ticket_resolution", agent_name="support_bot"):
    result = agent.process_ticket(ticket_text)
```

#### Advanced: Record Everything Explicitly

```python
from reliability_sdk import Tracer
from reliability_shared.types.core import (
    ModelMetadata, TokenUsage, RetrievalResult
)

tracer = Tracer(service_name="rag-agent")

with tracer.trace("knowledge_query", agent_name="kb_bot"):
    
    # 1. Record memory read
    tracer.record_memory_op(
        op_type="read",
        key="user_preferences",
        value={"language": "en", "tier": "premium"},
        namespace="profile",
    )
    
    # 2. Record retrieval
    tracer.record_retrieval(
        query="refund policy",
        results=[
            RetrievalResult(
                query="refund policy",
                source="kb://policies",
                content="Full refund within 30 days",
                score=0.95,
                rank=0,
            ),
        ],
        latency_ms=120,
    )
    
    # 3. Record LLM call
    tracer.record_llm_call(
        prompt="Customer wants refund. Context: premium tier. Policy: 30 days.",
        completion="As a premium customer, you're eligible for a full refund.",
        model_metadata=ModelMetadata(
            model_name="gpt-4",
            provider="openai",
            temperature=0.3,
        ),
        token_usage=TokenUsage(prompt_tokens=50, completion_tokens=20),
        latency_ms=1500,
    )
    
    # 4. Record tool call
    tracer.record_tool_call(
        tool_name="process_refund",
        parameters={"amount": 99.99, "order_id": "ORD-123"},
        result={"status": "success"},
        latency_ms=300,
    )
    
    # 5. Record reflection (self-correction loop)
    tracer.record_reflection(
        iteration=1,
        reflection_type="verification",
        input_context="Verify refund amount",
        output_decision="Amount confirmed",
        confidence=0.92,
        triggered_retry=False,
    )
```

### Step 4: Start the API Server

```bash
cd apps/api
uvicorn src.main:app --reload --port 8000
```

API endpoints now available:
- `POST /v1/traces` — Ingest traces
- `GET /v1/traces` — List traces
- `GET /v1/traces/{id}` — Get specific trace
- `GET /v1/traces/{id}/evaluations` — Get evaluations
- `GET /v1/metrics/reliability` — Get reliability metrics
- `GET /health` — Health check

### Step 5: View the Dashboard

```bash
cd apps/dashboard
npm install  # if not already done
npm run dev
```

Open http://localhost:3000

Pages:
- **/** — Trace Explorer (list traces, latency trends)
- **/reflections** — Reflection Loop Visualizer (React Flow graph)
- **/reliability** — Reliability Analytics (radar charts, failure hotspots)
- **/benchmarks** — Benchmark Lab (run suites, compare results)

---

## Framework Integrations

### OpenAI SDK

```python
from reliability_sdk import Tracer, OpenAIIntegration
import openai

tracer = Tracer()
client = openai.OpenAI()

# Instrument the client
integration = OpenAIIntegration(tracer)
instrumented_client = integration.instrument_client(client)

# All calls are now traced automatically
with tracer.trace("openai_chat"):
    response = instrumented_client.chat.completions.create(
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
# ... add nodes ...
graph = builder.compile()

# Instrument
integration = LangGraphIntegration(tracer)
instrumented_graph = integration.instrument_graph(graph)

with tracer.trace("langgraph_workflow"):
    result = instrumented_graph.invoke({"input": "hello"})
```

### LiteLLM

```python
from reliability_sdk import Tracer, LiteLLMIntegration

tracer = Tracer()
LiteLLMIntegration(tracer).instrument()

# Now litellm.completion calls are traced
import litellm
response = litellm.completion(model="gpt-4", messages=[...])
```

---

## Running Evaluations

### Via Python API

```python
from reliability_evals import HallucinationEvaluator, RAGEvaluator

# Load a trace
trace_data = {"spans": [...]}  # Your trace

# Run evaluators
hallucination_eval = HallucinationEvaluator()
result = hallucination_eval.evaluate(trace_data)

print(f"Score: {result.score}")
print(f"Passed: {result.passed}")
print(f"Details: {result.details}")
```

### Via CLI

```bash
# Run all evaluators on a trace JSON file
python cli.py eval --trace-file trace.json

# Output:
#   [FAIL] Hallucination    | Score: 0.624 | Threshold: 0.850
#   [PASS] Tool Use        | Score: 0.960 | Threshold: 0.900
#   [PASS] Reflection       | Score: 0.997 | Threshold: 0.700
```

---

## Running Benchmarks

### Via Python

```python
from benchmarks.runner import BenchmarkRegistry

registry = BenchmarkRegistry()

# List suites
for name in registry.list_suites():
    tests = registry.get_suite(name)
    print(f"{name}: {len(tests)} tests")

# Export to JSON
registry.export_all(output_dir="datasets")
```

### Via CLI

```bash
# List available suites
python cli.py benchmark --list

# Run a specific suite
python cli.py benchmark --suite rag
```

---

## Regression Testing / CI-CD

### In Your CI Pipeline

```python
from reliability_engine.regression import (
    RegressionTestRunner, CICDPipeline, TestCase
)

# Define test cases
test_cases = [
    TestCase(id="t1", name="Basic QA", input="What is 2+2?", expected_output="4"),
    TestCase(id="t2", name="Tool Use", input="Weather in Tokyo?", expected_tools=["weather_api"]),
]

# Define your agent factory
def my_agent_factory():
    return MyAgent()

# Run regression
runner = RegressionTestRunner(agent_factory=my_agent_factory)
pipeline = CICDPipeline(runner)

result = pipeline.run_pipeline(test_cases, commit_hash="abc123")
```

### CLI Mode

```bash
python cli.py regress
```

Output:
```
AI RELIABILITY CI/CD PIPELINE
========================================

Run ID: regression_171577...
Commit: abc123
Tests: 2/3 passed
Success Rate: 66.7%

--- Eval Scores ---
Hallucination: 0.920
RAG: 0.850
Tool Accuracy: 0.960

--- Regression Diffs ---
Success Rate: -10.0% (degraded)
Latency: +15.0% (degraded)

--- Decision ---
Deploy: NO
Recommendation: Deployment BLOCKED. Issues: Success rate 66.7% below 85% threshold
```

---

## Reliability Analysis

### Compare Multiple Runs

```python
from reliability_engine import ReliabilityAnalyzer, ReliabilityRun

# Create multiple runs
runs = [
    ReliabilityRun(
        run_id="run-1",
        trace_id="trace-1",
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

# Compare with baseline
baseline = analyzer.analyze(runs[:5], experiment_id="baseline")
diff = analyzer.compare_experiments(baseline, report)
for metric, data in diff["metrics"].items():
    print(f"{metric}: {data['change_pct']:+.1f}%")
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RELIABILITY_API_ENDPOINT` | `http://localhost:8000/v1/traces` | Where to send traces |
| `RELIABILITY_API_KEY` | None | API key for authentication |
| `RELIABILITY_ENVIRONMENT` | `development` | Environment tag |
| `RELIABILITY_SERVICE_NAME` | `ai-agent` | Service identifier |
| `RELIABILITY_BATCH_SIZE` | `100` | Traces per batch |
| `CLICKHOUSE_HOST` | `localhost` | ClickHouse server |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | None | OpenTelemetry endpoint |

### Config File

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
)
```

---

## Common Use Cases

### 1. Monitor Agent in Production

```python
from reliability_sdk import Tracer, HTTPExporter

tracer = Tracer(service_name="production-agent")
tracer.add_exporter(HTTPExporter(
    endpoint="https://api.reliability-lab.io/v1/traces",
    api_key="your-api-key",
))

# Every agent run is traced and sent
with tracer.trace("user_request"):
    response = agent.run(query)
```

### 2. Debug Reflection Loops

```python
with tracer.trace("complex_task"):
    for attempt in range(max_retries):
        tracer.record_reflection(
            iteration=attempt,
            reflection_type="self-correction",
            input_context=f"Attempt {attempt}",
            output_decision="retry" if attempt < max_retries - 1 else "proceed",
            confidence=0.8,
            triggered_retry=attempt < max_retries - 1,
        )
```

View in Dashboard → Reflections page to see the loop graph.

### 3. Evaluate RAG Quality

```python
from reliability_evals import RAGEvaluator

evaluator = RAGEvaluator()
result = evaluator.evaluate(trace_data)

if not result.passed:
    print("RAG quality degraded:")
    print(f"  Relevance: {result.details['avg_relevance']}")
    print(f"  Precision: {result.details['avg_precision']}")
```

### 4. Block Bad Deployments

```python
from reliability_engine.regression import CICDPipeline

result = pipeline.run_pipeline(test_cases, commit_hash=git_sha)

if not result["should_deploy"]:
    print("DEPLOYMENT BLOCKED")
    for issue in result["blocking_issues"]:
        print(f"  - {issue}")
    sys.exit(1)
```

---

## Troubleshooting

### "Module not found" errors

```bash
# Make sure venv is activated
source venv/bin/activate

# Reinstall packages
make install
```

### Dashboard won't build

```bash
cd apps/dashboard
rm -rf node_modules .next
npm install
npm run build
```

### ClickHouse connection errors

```bash
# Check if ClickHouse is running
docker compose -f infra/docker/docker-compose.yml ps

# Start it
docker compose -f infra/docker/docker-compose.yml up -d clickhouse
```

### Evaluator judge fails (Ollama not running)

The evaluators work without Ollama — they fall back to heuristic scoring. To get LLM judge evaluation:

```bash
# Start Ollama
docker compose -f infra/docker/docker-compose.yml up -d ollama

# Pull models
docker exec -it ollama ollama pull qwen3:32b
docker exec -it ollama ollama pull mistral
```

---

## Architecture Overview

```
Your Agent → SDK → API → ClickHouse → Dashboard
                ↓
              Redis → Worker → Evaluations
                ↓
              Benchmarks → Regression Tests
```

1. **Your Agent** calls the SDK
2. **SDK** creates traces and exports them
3. **API** receives traces, stores in ClickHouse
4. **Redis** queues traces for processing
5. **Worker** picks up traces, runs evaluators
6. **Evaluators** compute scores (hallucination, RAG, etc.)
7. **Dashboard** visualizes everything
8. **Benchmarks** test against adversarial datasets
9. **Regression** compares versions, blocks bad deployments

---

## Next Steps

1. **Instrument your agent** with the SDK
2. **Start the API** and send traces
3. **Open the dashboard** to view results
4. **Run benchmarks** to establish baselines
5. **Set up CI/CD** to block regressions

For more details, see:
- `docs/sdk-guide.md` — SDK reference
- `docs/CONTRIBUTING.md` — Contributing guide
- `examples/` — Working code examples
