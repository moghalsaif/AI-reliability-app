# AI Reliability Lab — Complete Textbook

> A zero-to-hero guide to understanding every concept, tool, and component in the AI Reliability Lab project.

---

## Table of Contents

1. [What Is This Project?](#1-what-is-this-project)
2. [Core Concepts You Must Know](#2-core-concepts-you-must-know)
3. [System Architecture](#3-system-architecture)
4. [Layer 1: The SDK (Python)](#4-layer-1-the-sdk-python)
5. [Layer 2: The API (FastAPI)](#5-layer-2-the-api-fastapi)
6. [Layer 3: The Database (ClickHouse)](#6-layer-3-the-database-clickhouse)
7. [Layer 4: The Queue (Redis)](#7-layer-4-the-queue-redis)
8. [Layer 5: The Evaluators](#8-layer-5-the-evaluators)
9. [Layer 6: The Reliability Engine](#9-layer-6-the-reliability-engine)
10. [Layer 7: The Dashboard (Next.js)](#10-layer-7-the-dashboard-nextjs)
11. [Layer 8: Docker & Infrastructure](#11-layer-8-docker--infrastructure)
12. [End-to-End Data Flow](#12-end-to-end-data-flow)
13. [Concept Deep Dives](#13-concept-deep-dives)
14. [Production Deployment Concepts](#14-production-deployment-concepts)
15. [Testing & Quality Assurance](#15-testing--quality-assurance)
16. [File-by-File Guide](#16-file-by-file-guide)

---

## 1. What Is This Project?

### The Big Picture

The **AI Reliability Lab** is an **infrastructure platform** for measuring and monitoring the reliability of AI agents. Think of it as "Datadog meets Langfuse" — a purpose-built observability system that tracks how well AI systems perform, where they fail, and how they reason.

### Why Does This Exist?

Modern AI applications (chatbots, coding assistants, research agents) make mistakes:
- **Hallucinations** — making up facts
- **Tool misuse** — calling APIs with wrong parameters
- **Reflection loops** — getting stuck in endless self-correction
- **Memory failures** — forgetting context

Most monitoring tools track servers and databases. Almost none track *AI reasoning quality*. This platform does exactly that.

### What It Measures

| Metric | What It Means |
|--------|---------------|
| Success Rate | % of agent runs that complete correctly |
| Hallucination Rate | % of outputs containing false information |
| Tool Accuracy | % of tool calls that succeed |
| Variance Score | Consistency across multiple runs |
| Reflection Density | How often agents retry/correct themselves |
| Latency P95 | 95th percentile response time |

---

## 2. Core Concepts You Must Know

### 2.1 Traces

A **trace** is the complete record of one AI agent execution.

**Analogy:** If you order food delivery, the trace is the entire journey — from placing the order, to the restaurant cooking, to the driver delivering. Every step is recorded.

```
Trace: "Customer Support Bot Response"
├── Started at: 2026-05-15 12:00:00
├── Agent: support_bot
├── Success: true
├── Total Time: 2.4 seconds
├── Total Tokens: 1,250
└── Contains 5 spans (steps)
```

**In the system:** Traces are stored in the `traces` table in ClickHouse.

### 2.2 Spans

A **span** is a single operation *inside* a trace.

**Analogy:** In the food delivery trace, spans are individual actions:
- Span 1: "Receive order" (0.1s)
- Span 2: "Query database for menu" (0.3s)
- Span 3: "Call restaurant API" (1.2s)
- Span 4: "Calculate delivery time" (0.2s)
- Span 5: "Send confirmation to customer" (0.6s)

**Span Types in our system:**
| Type | Description |
|------|-------------|
| `llm` | A language model call |
| `tool_call` | An external API/function call |
| `retrieval` | Fetching data from a knowledge base (RAG) |
| `memory_op` | Reading/writing to memory/context |
| `reflection` | Self-correction or verification step |
| `reasoning` | Chain-of-thought processing |

### 2.3 OpenTelemetry (OTel)

**OpenTelemetry** is an industry standard for collecting telemetry data (traces, metrics, logs).

**Analogy:** Think of it as a universal power adapter — instead of every company inventing their own monitoring format, everyone uses OTel and tools understand each other.

**What it does:**
- Defines a standard way to represent traces and spans
- Provides SDKs for many languages (Python, JS, Go, etc.)
- Can export data to many backends (our ClickHouse, Datadog, Jaeger, etc.)

**In our project:** The SDK wraps OTel to send traces to our backend. This makes the system compatible with any OTel-compatible tool.

### 2.4 RAG (Retrieval-Augmented Generation)

**RAG** is when an AI doesn't just rely on its training data — it looks up information from a database first.

**Analogy:** Instead of memorizing an entire textbook, you keep the textbook on your desk and look up answers when asked. More accurate, but introduces a new failure mode: "what if you look up the wrong page?"

**Why it matters for reliability:**
- The retrieval might find irrelevant documents
- The AI might ignore the retrieved information
- The source documents might be outdated

Our `RAGEvaluator` measures how well the retrieval is working.

### 2.5 Reflection Loops

A **reflection loop** is when an AI agent checks its own work and decides to retry.

**Analogy:** You're writing an essay. You finish a paragraph, read it back, realize it doesn't make sense, and rewrite it. That's a reflection loop.

**Why it matters:**
- Good: Self-correction improves accuracy
- Bad: Endless loops waste time and money
- Our system visualizes these loops as graphs (React Flow)

### 2.6 Evaluators (Judges)

**Evaluators** are automated tests that score AI outputs.

**Analogy:** A teacher grading a student's essay, but the teacher is also an AI.

**Our 5 evaluators:**
| Evaluator | What It Checks |
|-----------|----------------|
| Hallucination | Is the output factually supported? |
| RAG | Is the retrieved information relevant? |
| Tool Use | Were API calls correct and successful? |
| Reflection | Did self-correction actually help? |
| Memory | Was context properly retained? |

**Important:** Evaluators use a "judge" LLM (like Qwen3 32B) to evaluate traces. They run with low temperature (deterministic) to ensure consistent scoring.

### 2.7 Reliability Metrics

These are statistical measures of system health over time:

- **Success Rate:** `successful_traces / total_traces`
- **Hallucination Rate:** `hallucinated_outputs / total_outputs`
- **Variance Score:** How much do results vary across identical prompts?
- **Drift Detection:** Is performance getting worse over time?

### 2.8 Benchmarks & Regression Testing

**Benchmarks** are standardized test suites that run on every code change.

**Analogy:** Like SAT tests for AI — same questions, scored consistently, so you can compare performance across versions.

**Regression testing** ensures that new changes don't break existing capabilities. If version 1.0 scored 90% and version 1.1 scores 85%, we block the deployment.

---

## 3. System Architecture

### High-Level Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   AI Agent      │────▶│   SDK (Python)  │────▶│  FastAPI        │
│   (Your App)    │     │  (Instrumentation)│    │  (Ingestion)    │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                              ┌─────────────────────────┼─────────────────────────┐
                              │                         │                         │
                              ▼                         ▼                         ▼
                        ┌─────────┐             ┌─────────┐               ┌─────────┐
                        │ClickHouse│             │  Redis  │               │Evaluators│
                        │(Storage) │             │ (Queue) │               │ (Judges) │
                        └────┬────┘             └────┬────┘               └────┬────┘
                             │                       │                       │
                             │                       │                       │
                             ▼                       ▼                       ▼
                        ┌─────────┐             ┌─────────┐               ┌─────────┐
                        │ Grafana │             │  Worker │               │Reliability│
                        │(Metrics)│             │ (Celery)│               │  Engine   │
                        └─────────┘             └─────────┘               └─────────┘
                                                                                 │
                                                                                 ▼
                                                                           ┌─────────┐
                                                                           │Dashboard│
                                                                           │(Next.js)│
                                                                           └─────────┘
```

### Data Flow Summary

1. **Your AI agent** runs and generates a trace
2. **SDK** captures the trace and sends it to the API
3. **API** stores the trace in **ClickHouse**
4. **API** queues the trace in **Redis** for evaluation
5. **Worker** (Celery) picks up the trace and runs **Evaluators**
6. **Evaluator results** are stored back in ClickHouse
7. **Reliability Engine** computes aggregate metrics
8. **Dashboard** queries the API and displays everything

---

## 4. Layer 1: The SDK (Python)

### What It Is

The **SDK** (Software Development Kit) is a Python library that you install in your AI application. It automatically captures traces and sends them to the platform.

### Key Design Principle

> **The SDK must never crash user code.**

If the platform is down, the SDK logs an error but doesn't raise an exception. Your AI agent keeps working.

### How It Works

```python
# Your AI agent code
from reliability_sdk import ReliabilityTracer

tracer = ReliabilityTracer()

with tracer.start_trace("customer_support") as trace:
    # This block is automatically traced
    response = llm.generate(user_query)
    trace.add_span("llm_call", latency=1.2, tokens=500)
    
    # Tool call is also traced
    result = tool_api.search(response)
    trace.add_span("tool_call", latency=0.8)
```

### What's Inside

| Component | Purpose |
|-----------|---------|
| `Tracer` | Creates and manages traces/spans |
| `OTel Exporter` | Sends traces via OpenTelemetry protocol |
| `Console Exporter` | Prints traces to console (default, for debugging) |
| `HTTP Exporter` | Sends traces to our FastAPI endpoint |
| `Batch Processor` | Buffers traces and sends them efficiently |

### OpenTelemetry Integration

The SDK uses OpenTelemetry under the hood:

```
Your Code → SDK Tracer → OTel Span → OTel Exporter → Our API → ClickHouse
```

This means:
- If you already use OTel, we can ingest your existing traces
- If you switch to Datadog/Jaeger later, the instrumentation still works

---

## 5. Layer 2: The API (FastAPI)

### What It Is

The **API** is a Python web service built with **FastAPI** that receives traces, serves data to the dashboard, and coordinates background processing.

### Why FastAPI?

- **Async-native:** Handles many concurrent requests efficiently
- **Auto-docs:** Generates OpenAPI/Swagger docs automatically
- **Type-safe:** Uses Python type hints for validation
- **Fast:** One of the fastest Python web frameworks

### API Endpoints

| Endpoint | Method | What It Does |
|----------|--------|--------------|
| `/health` | GET | Check if the API is running |
| `/v1/traces` | POST | Receive a new trace from the SDK |
| `/v1/traces` | GET | List traces (for the dashboard) |
| `/v1/traces/{id}` | GET | Get a specific trace |
| `/v1/traces/{id}/spans` | GET | Get spans for a trace |
| `/v1/traces/{id}/evaluations` | GET | Get evaluation results |
| `/v1/metrics/reliability` | GET | Get aggregated reliability metrics |
| `/v1/alerts` | GET | List active alerts |
| `/v1/alerts/{id}/acknowledge` | POST | Acknowledge an alert |
| `/v1/seed` | POST | Insert demo data |
| `/v1/benchmarks` | GET | List benchmark suites |
| `/v1/reflections/{id}` | GET | Get reflection data for a trace |
| `/v1/ws/traces` | WebSocket | Real-time trace updates |

### Background Tasks

The API runs 3 background loops:

1. **Eval Queue Processor** — Every 1 second, checks Redis for traces to evaluate
2. **Reliability Analysis** — Every 60 seconds, computes aggregate metrics
3. **Alert Engine** — Every 30 seconds, checks thresholds and sends Slack alerts

### CORS (Cross-Origin Resource Sharing)

The API allows requests from any origin (`*`). In production, you'd restrict this to your Vercel domain:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-dashboard.vercel.app"],
)
```

---

## 6. Layer 3: The Database (ClickHouse)

### What Is ClickHouse?

**ClickHouse** is a **column-oriented database** designed for high-speed analytics on large datasets.

### Why ClickHouse and Not PostgreSQL?

| PostgreSQL | ClickHouse |
|------------|------------|
| Row-oriented (good for transactions) | Column-oriented (good for analytics) |
| UPDATE/DELETE are fast | Optimized for INSERT and SELECT |
| Best for < 1M rows/second | Handles > 1M rows/second |
| Great for user data | Great for time-series telemetry |

**Analogy:** PostgreSQL is like a filing cabinet ( organized, good for retrieving one file). ClickHouse is like a spreadsheet ( great for computing averages across millions of rows).

### Our ClickHouse Schema

We have 5 tables:

#### `traces` — The main event log
```sql
CREATE TABLE traces (
    trace_id String,
    name String,
    start_time DateTime64(3),
    end_time DateTime64(3),
    duration_ms Float64,
    status String,
    agent_name Nullable(String),
    environment String,
    success Bool,
    span_count UInt32,
    total_tokens UInt32,
    total_latency_ms Float64,
    tags Array(String),
    attributes String  -- JSON
) ENGINE = MergeTree()
ORDER BY (start_time, trace_id)
TTL start_time + INTERVAL 90 DAY  -- Auto-delete after 90 days
```

#### `spans` — Individual operations
```sql
CREATE TABLE spans (
    span_id String,
    trace_id String,
    span_type String,
    name String,
    start_time DateTime64(3),
    duration_ms Float64,
    status String,
    input Nullable(String),
    output Nullable(String),
    prompt_tokens UInt32,
    tool_calls String,    -- JSON
    retrievals String,    -- JSON
    memory_ops String,    -- JSON
    reflections String     -- JSON
) ENGINE = MergeTree()
ORDER BY (trace_id, start_time)
```

#### `evaluations` — Evaluator scores
```sql
CREATE TABLE evaluations (
    eval_id String,
    trace_id String,
    eval_type String,    -- hallucination, rag, tool_use, etc.
    score Float64,       -- 0.0 to 1.0
    passed Bool,
    threshold Float64,
    details String       -- JSON
) ENGINE = MergeTree()
```

#### `reliability_metrics` — Computed statistics
```sql
CREATE TABLE reliability_metrics (
    metric_id String,
    trace_id String,
    run_id String,
    success_rate Float64,
    hallucination_rate Float64,
    variance_score Float64,
    latency_p95 Float64,
    tool_accuracy Float64
) ENGINE = MergeTree()
```

#### `alerts` — Generated alerts
```sql
CREATE TABLE alerts (
    alert_id String,
    trace_id String,
    alert_type String,
    severity String,     -- P0, P1, P2, P3
    message String,
    metric_name Nullable(String),
    metric_value Nullable(Float64),
    acknowledged Bool DEFAULT false
) ENGINE = MergeTree()
```

### Key Features

- **Bloom Filters** — Speed up queries on `agent_name`, `environment`, `trace_id`
- **TTL (Time To Live)** — Auto-delete old data after 90 days
- **MergeTree Engine** — Optimized for time-series data

---

## 7. Layer 4: The Queue (Redis)

### What Is Redis?

**Redis** is an in-memory data store used as a:
- **Message queue** — Pass tasks between services
- **Cache** — Store frequently accessed data
- **Pub/Sub broker** — Real-time messaging

### Why Redis?

| Feature | Why It Matters |
|---------|----------------|
| In-memory | Extremely fast (microsecond latency) |
| Persistent | Can survive restarts (we use `appendonly yes`) |
| Simple | Easy to operate and monitor |
| Lists | Perfect for job queues |

### How We Use Redis

```
┌─────────┐      ┌─────────┐      ┌─────────┐
│   API   │─────▶│  Redis  │─────▶│ Worker  │
│         │ PUSH │  Queue  │  POP │         │
└─────────┘      └─────────┘      └─────────┘
```

1. API receives a trace
2. API pushes `{"trace_id": "abc", "trace_data": {...}}` to Redis list `eval_queue`
3. Worker (Celery) pops from the queue
4. Worker runs evaluators and stores results

### Redis in Docker

```yaml
redis:
  image: redis:7-alpine
  command: redis-server --appendonly yes  # Persist to disk
  volumes:
    - redis_data:/data
```

---

## 8. Layer 5: The Evaluators

### What Are Evaluators?

**Evaluators** are automated tests that analyze traces and assign scores. They are the "judges" of the system.

### The Base Interface

Every evaluator inherits from `BaseEvaluator`:

```python
class BaseEvaluator:
    def default_threshold(self) -> float:
        """Return the passing threshold (0.0 to 1.0)"""
        return 0.5
    
    def evaluate(self, trace_data: dict) -> EvalResult:
        """Analyze the trace and return a score"""
        score = self._calculate_score(trace_data)
        return EvalResult(
            score=score,
            passed=score >= self.default_threshold(),
            threshold=self.default_threshold(),
            details={"reason": "..."}
        )
```

### Our 5 Evaluators

#### 1. HallucinationEvaluator

**What it checks:** Does the AI output contain claims that aren't supported by the input?

**How it works:**
1. Extract the AI's output from the trace
2. Compare it against the input context
3. Use an LLM judge (Qwen3 32B) to determine if claims are supported
4. Return score: 1.0 = no hallucination, 0.0 = complete hallucination

**Example:**
- Input: "What is the capital of France?"
- Output: "The capital of France is Berlin."
- Score: 0.0 (failed — it's Paris, not Berlin)

#### 2. RAGEvaluator

**What it checks:** When the AI retrieves documents, are they relevant to the query?

**How it works:**
1. Look at the `retrievals` field in spans
2. Check if retrieved documents contain relevant keywords
3. Measure semantic similarity between query and retrieved content

**Example:**
- Query: "How do I reset my password?"
- Retrieved: "Our company was founded in 2010..."
- Score: 0.1 (poor retrieval — completely irrelevant)

#### 3. ToolUseEvaluator

**What it checks:** Are tool/API calls correct and successful?

**How it works:**
1. Look at `tool_calls` in spans
2. Check if parameters match the expected schema
3. Check if the tool returned an error
4. Verify the tool result was used in the final output

**Example:**
- Tool call: `weather_api(city="New York", units="celsius")`
- Result: `{"error": "Invalid units: celsius, expected: metric"}`
- Score: 0.0 (wrong parameter value)

#### 4. ReflectionEvaluator

**What it checks:** Did the self-correction loop actually improve the output?

**How it works:**
1. Look at `reflections` in spans
2. Compare the output before and after reflection
3. Check if confidence increased
4. Verify the retry didn't just oscillate (flip back and forth)

**Example:**
- Iteration 1: Output = "Answer A", Confidence = 60%
- Iteration 2: Output = "Answer B", Confidence = 85%
- Iteration 3: Output = "Answer A", Confidence = 70%
- Score: 0.3 (oscillation — the system is flip-flopping)

#### 5. MemoryEvaluator

**What it checks:** Is the AI properly using and retaining context?

**How it works:**
1. Look at `memory_ops` in spans
2. Check if context was retrieved before being needed
3. Verify the AI didn't forget important information from earlier in the conversation

**Example:**
- User says: "My name is Alice. What's the weather?"
- Later user says: "Do I need an umbrella?"
- AI forgets name and responds to "Do I need an umbrella?" without context
- Memory score: 0.5 (failed to retain user identity)

### Judge Model Configuration

```python
class JudgeConfig:
    model_name: str = "qwen3:32b"    # Default judge (high quality)
    fast_model: str = "mistral"        # Quick evals (lower quality, faster)
    temperature: float = 0.1          # Low = deterministic scoring
```

**Why low temperature?** We want evaluators to be consistent. High temperature makes LLMs creative (random), which is bad for scoring.

---

## 9. Layer 6: The Reliability Engine

### What It Does

The **Reliability Engine** computes statistical metrics from raw trace data.

### Key Computations

#### Success Rate
```
success_rate = successful_traces / total_traces
```

#### Hallucination Rate
```
hallucination_rate = hallucinated_evaluations / total_evaluations
```

#### Variance Score
```python
import numpy as np

scores = [eval.score for eval in evaluations]
variance = np.var(scores)  # How much do scores vary?
```

**Why variance matters:** If you run the same prompt 10 times and get wildly different quality scores, your system is unreliable.

#### Drift Detection

Compare current metrics against a baseline:

```python
current_success_rate = 0.85
baseline_success_rate = 0.92

if current_success_rate < baseline_success_rate - 0.05:
    alert("Performance drift detected!")
```

### Regression Testing

Before deploying new code:
1. Run the full benchmark suite
2. Compare scores against the previous version's baseline
3. If any critical metric drops, **block the deployment**

---

## 10. Layer 7: The Dashboard (Next.js)

### What It Is

The **Dashboard** is a web application built with **Next.js 14** that visualizes all the data.

### Technology Stack

| Technology | What It Is | Why We Use It |
|------------|------------|---------------|
| Next.js | React framework | Server-side rendering, API routes, fast builds |
| React | UI library | Component-based, declarative, huge ecosystem |
| TypeScript | Typed JavaScript | Catches bugs before runtime |
| Tailwind CSS | Utility CSS | Rapid styling without leaving HTML |
| Radix UI | Primitive components | Accessible, unstyled building blocks |
| Recharts | Charting library | Beautiful, responsive charts |
| React Flow | Graph visualization | Interactive node/edge diagrams |

### Pages

#### `/` — Trace Explorer
- **Metrics cards:** Total traces, success rate, average latency, active alerts
- **Latency Trend chart:** Line chart showing response times over time
- **Span Count Distribution:** Bar chart showing complexity of traces
- **Trace table:** Live list with color-coded status badges

#### `/reflections` — Reflection Loop Visualizer
- **React Flow graph:** Interactive diagram showing reasoning loops
  - Purple = Decision nodes
  - Blue = Reflection nodes (with iteration count and confidence)
  - Yellow = Retry nodes
  - Green = Success
  - Red = Failure
- **Drill-down panel:** Click any node to see its details
- **Trace selector:** Load real trace reflection data from the API

#### `/reliability` — Reliability Analytics
- **Summary cards:** 5 key metrics (success rate, hallucination, variance, latency, tool accuracy)
- **Radar chart:** Current performance vs baseline across 6 dimensions
- **Scatter chart:** Model comparison (success rate vs latency, bubble size = cost)
- **Trend charts:** 30-day stability and failure hotspots
- **Alerts table:** Live list of threshold breaches

#### `/benchmarks` — Benchmark Lab
- **Category performance:** Bar chart comparing current vs baseline scores
- **Benchmark suites table:** RAG, Agents, Memory, Tool Use, Security tests
- **Test type cards:** Adversarial tests, prompt injection, stress tests
- **Drill-down panel:** Click any benchmark to see test breakdowns

### Data Fetching

The dashboard uses a centralized API client (`lib/api.ts`):

```typescript
// All API calls go through this client
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = {
  getTraces: () => fetch(`${API_BASE}/v1/traces`).then(r => r.json()),
  getReliabilityMetrics: () => fetch(`${API_BASE}/v1/metrics/reliability`).then(r => r.json()),
  // ... etc
};
```

### WebSocket Real-Time Updates

```typescript
const ws = new WebSocket("ws://localhost:8000/v1/ws/traces");

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  if (message.type === "trace_update") {
    // Add the new trace to the top of the list
    setTraces(prev => [message.data, ...prev]);
  }
};
```

### Dark Mode

The dashboard uses Tailwind's dark mode class strategy:

```html
<html class="dark">
  <body class="bg-background text-foreground">
```

Colors are defined in CSS variables for automatic dark mode.

---

## 11. Layer 8: Docker & Infrastructure

### What Is Docker?

**Docker** packages applications into **containers** — lightweight, isolated environments that run the same everywhere.

**Analogy:** Instead of shipping a factory, you ship a shipping container with everything inside. It works the same whether it's on a truck, train, or ship.

### Our Docker Compose Stack

```yaml
services:
  clickhouse:     # Database (port 8123)
  redis:          # Queue (port 6379)
  api:            # FastAPI backend (port 8000)
  worker:         # Celery task workers
  evaluator:      # Evaluation workers
  dashboard:      # Next.js frontend (port 3000)
  ollama:         # Local LLM inference (port 11434)
  jaeger:         # Distributed tracing UI (port 16686)
  prometheus:     # Metrics collection (port 9090)
  grafana:        # Metrics dashboards (port 3001)
```

### Why Each Service?

| Service | Purpose |
|---------|---------|
| ClickHouse | Store traces, spans, evaluations, metrics, alerts |
| Redis | Queue traces for evaluation, cache recent data |
| API | Receive traces, serve data, run background loops |
| Worker | Process evaluation jobs from Redis queue |
| Evaluator | Run LLM-based evaluators (needs GPU) |
| Dashboard | Visualize data for humans |
| Ollama | Run local LLMs (Qwen3, Mistral) for judging |
| Jaeger | View distributed traces (OpenTelemetry compatible) |
| Prometheus | Collect system metrics (CPU, memory, request rates) |
| Grafana | Build monitoring dashboards |

---

## 12. End-to-End Data Flow

Let's trace a single AI agent request through the entire system.

### Scenario: Customer asks a chatbot a question

**Step 1: AI Agent Runs**
```
User: "What's the weather in Tokyo?"
```

The chatbot:
1. Receives the message
2. Decides to call a weather API
3. Calls the API (this is a span)
4. Formats the response (another span)
5. Sends reply to user

**Step 2: SDK Captures the Trace**
```python
# Inside the chatbot code
with tracer.start_trace("weather_query") as trace:
    trace.add_span("llm_planning", latency=0.5, tokens=200)
    trace.add_span("tool_call_weather_api", latency=1.2)
    trace.add_span("llm_formatting", latency=0.8, tokens=150)
```

**Step 3: Trace Sent to API**
```
HTTP POST http://localhost:8000/v1/traces
Body: {
  "trace": {
    "trace_id": "trace-abc123",
    "agent_name": "weather_bot",
    "success": true,
    "total_latency_ms": 2500,
    "spans": [...]
  }
}
```

**Step 4: API Stores in ClickHouse**
```sql
INSERT INTO traces (trace_id, agent_name, success, total_latency_ms, ...)
VALUES ('trace-abc123', 'weather_bot', true, 2500, ...)
```

**Step 5: API Queues for Evaluation**
```
Redis LPUSH eval_queue '{"trace_id": "trace-abc123", "trace_data": {...}}'
```

**Step 6: Worker Picks Up Job**
```python
# Celery worker pops from Redis queue
trace_data = redis.rpop("eval_queue")
```

**Step 7: Evaluators Run**
```python
# HallucinationEvaluator
score = judge_llm.ask("Is 'The weather in Tokyo is sunny' supported by the API response?")
# Returns: score=1.0, passed=true

# ToolUseEvaluator  
score = check_tool_call(trace["spans"][1])
# Returns: score=1.0, passed=true
```

**Step 8: Results Stored in ClickHouse**
```sql
INSERT INTO evaluations (trace_id, eval_type, score, passed)
VALUES ('trace-abc123', 'hallucination', 1.0, true),
       ('trace-abc123', 'tool_use', 1.0, true)
```

**Step 9: WebSocket Broadcast**
```json
{
  "type": "trace_update",
  "data": {
    "trace_id": "trace-abc123",
    "agent_name": "weather_bot",
    "success": true
  }
}
```

**Step 10: Dashboard Updates**
- Trace table adds new row
- Success rate recalculates
- Latency chart adds new data point

**Step 11: Alert Engine Checks**
```python
# Every 30 seconds
if avg_success_rate < 0.90:
    send_slack_alert("Success rate dropped to 85%!")
    INSERT INTO alerts (severity='P0', message='...')
```

**Step 12: Dashboard Shows Alert**
- New alert appears in the alerts table
- Reliability card turns red

---

## 13. Concept Deep Dives

### 13.1 Why Column-Oriented Databases?

**Row-oriented (PostgreSQL):**
```
| id | name  | age | city     |
| 1  | Alice | 30  | New York |
| 2  | Bob   | 25  | London   |
```

To compute `AVG(age)`, the database reads the entire table row by row. Slow for analytics.

**Column-oriented (ClickHouse):**
```
ids:    [1, 2]
names:  [Alice, Bob]
ages:   [30, 25]
cities: [New York, London]
```

To compute `AVG(age)`, ClickHouse reads ONLY the `ages` column. It's compressed and vectorized. **100x faster** for analytics.

### 13.2 Why MergeTree Engine?

ClickHouse's `MergeTree` engine:
- Stores data in sorted parts
- Automatically merges small parts in the background
- Supports **TTL** (auto-delete old data)
- Supports **indexing** (bloom filters, min-max)

### 13.3 Bloom Filters

A **Bloom filter** is a space-efficient way to check "is this value possibly in the set?"

- **False positives:** Possible ("might be there")
- **False negatives:** Impossible ("definitely not there")

**Why we use them:** To skip reading entire data parts when querying by `trace_id`. "Is trace-123 in this 1-million-row part?" Bloom filter says "probably not" → skip entirely.

### 13.4 Async/Await in Python

The API uses `async def` because:
- While waiting for ClickHouse to respond, the server can handle other requests
- Without async, 100 concurrent requests = 100 threads (expensive)
- With async, 100 concurrent requests = 1 thread + event loop (cheap)

```python
# BAD: Blocks the server
@app.get("/slow")
def slow_endpoint():
    time.sleep(10)  # Server can't handle other requests
    return "done"

# GOOD: Server stays responsive
@app.get("/slow")
async def slow_endpoint():
    await asyncio.sleep(10)  # Other requests run during the wait
    return "done"
```

### 13.5 WebSockets vs HTTP Polling

**HTTP Polling (bad):**
```
Dashboard: "Any new traces?" → API: "No" (every 5 seconds)
Dashboard: "Any new traces?" → API: "No" (every 5 seconds)
Dashboard: "Any new traces?" → API: "Yes!" (5 second delay)
```

**WebSocket (good):**
```
Dashboard: [opens persistent connection]
API: [pushes immediately when trace arrives] → "New trace!"
```

WebSockets are 10x more efficient for real-time updates.

### 13.6 Celery Workers

**Celery** is a distributed task queue for Python.

**Why we need it:**
- Evaluators can take 5-30 seconds per trace (LLM inference is slow)
- We don't want the API waiting for evaluators
- Workers run in separate processes/containers
- Can scale workers horizontally (add more containers)

```
API ──fast──▶ Redis ──async──▶ Worker ──slow──▶ LLM Judge
```

---

## 14. Production Deployment Concepts

### 14.1 Horizontal Scaling

Instead of making one server bigger (vertical), add more servers (horizontal):

```
Before: 1 API server handling 1000 req/s
After:  3 API servers behind a load balancer, each handling 333 req/s
```

### 14.2 Load Balancing

A **load balancer** distributes traffic across multiple API instances:

```
Users → Load Balancer → API Server 1
                        → API Server 2
                        → API Server 3
```

### 14.3 SSL/TLS Termination

**SSL/TLS** encrypts traffic between users and servers.

**Termination** means the load balancer handles encryption/decryption, so API servers can focus on business logic:

```
User (HTTPS) → Load Balancer (decrypts) → API (HTTP, internal)
```

### 14.4 Environment Variables

Never hardcode secrets in code. Use environment variables:

```bash
# .env file (never commit this!)
CLICKHOUSE_PASSWORD=super-secret-password
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx
```

### 14.5 Health Checks

Production systems have automated health checks:
- Every 10 seconds: `GET /health` → expect `{"status": "healthy"}`
- If unhealthy for 30 seconds: restart the container

---

## 15. Testing & Quality Assurance

### 15.1 Unit Tests

Test individual functions in isolation:

```python
def test_hallucination_evaluator():
    trace = {"output": "Paris is the capital of France"}
    result = HallucinationEvaluator().evaluate(trace)
    assert result.passed == True
```

### 15.2 Integration Tests

Test how components work together:

```python
def test_api_to_clickhouse():
    response = client.post("/v1/traces", json=trace_data)
    assert response.status_code == 200
    
    traces = clickhouse.query("SELECT * FROM traces")
    assert len(traces) > 0
```

### 15.3 End-to-End Tests

Test the entire pipeline:

```python
def test_full_pipeline():
    # 1. Send trace
    # 2. Wait for processing
    # 3. Query from API
    # 4. Verify in ClickHouse
    # 5. Check dashboard endpoints
```

### 15.4 Regression Tests

Ensure new changes don't break existing functionality:

```python
# Baseline score from version 1.0
baseline_score = 0.87

# Run same tests on version 1.1
current_score = run_benchmark_suite()

assert current_score >= baseline_score - 0.02, "Regression detected!"
```

### 15.5 CI/CD Pipeline

**Continuous Integration:** Run tests on every code change.
**Continuous Deployment:** Deploy automatically if tests pass.

Our GitHub Actions workflow:
1. Push code → trigger CI
2. Run Python unit tests (pytest)
3. Run TypeScript build check
4. Run regression benchmarks
5. Build Docker images
6. If all pass: deploy to production

---

## 16. File-by-File Guide

### Python Packages

#### `packages/shared/src/reliability_shared/types/core.py`
**What:** Data models (Trace, Span, TokenUsage, ReflectionEvent, etc.)
**Key classes:**
- `Trace` — top-level container
- `Span` — individual operation
- `TokenUsage` — prompt/completion tokens
- `ReflectionEvent` — self-correction metadata

#### `packages/shared/src/reliability_shared/config.py`
**What:** Configuration management
**Key class:** `ReliabilityConfig.from_env()` — loads settings from environment variables

#### `packages/sdk/src/reliability_sdk/core/tracer.py`
**What:** The main tracing interface
**Key class:** `ReliabilityTracer` — starts traces, adds spans, exports data

#### `packages/evals/src/reliability_evals/evaluators/hallucination.py`
**What:** Detects unsupported claims in AI outputs
**Key method:** `evaluate(trace_data) -> EvalResult`

#### `packages/evals/src/reliability_evals/evaluators/rag.py`
**What:** Measures retrieval quality
**Key method:** `evaluate(trace_data) -> EvalResult`

#### `packages/evals/src/reliability_evals/evaluators/tool_use.py`
**What:** Validates API/tool calls
**Key method:** `evaluate(trace_data) -> EvalResult`

#### `packages/evals/src/reliability_evals/evaluators/reflection.py`
**What:** Scores self-correction loops
**Key method:** `evaluate(trace_data) -> EvalResult`

#### `packages/evals/src/reliability_evals/evaluators/memory.py`
**What:** Checks context retention
**Key method:** `evaluate(trace_data) -> EvalResult`

#### `packages/reliability/src/reliability_engine/engine.py`
**What:** Computes aggregate reliability metrics
**Key methods:** `compute_success_rate()`, `detect_drift()`

#### `packages/reliability/src/reliability_engine/regression.py`
**What:** Regression testing framework
**Key class:** `RegressionRunner` — compares current vs baseline scores

### API

#### `apps/api/src/reliability_api/main.py`
**What:** The FastAPI application
**Key endpoints:**
- `/v1/traces` — ingest and query traces
- `/v1/metrics/reliability` — aggregated metrics
- `/v1/seed` — insert demo data
- `/v1/ws/traces` — WebSocket for real-time updates

#### `apps/api/src/reliability_api/db/clickhouse.py`
**What:** ClickHouse client and schema
**Key class:** `ClickHouseClient` — async connection, query execution, INSERT

### Dashboard

#### `apps/dashboard/app/page.tsx`
**What:** Trace Explorer page
**Features:** Metrics cards, latency chart, trace table

#### `apps/dashboard/app/reflections/page.tsx`
**What:** Reflection Loop Visualizer
**Features:** React Flow graph, node drill-down, trace selector

#### `apps/dashboard/app/reliability/page.tsx`
**What:** Reliability Analytics
**Features:** Radar chart, scatter plot, trend charts, alerts table

#### `apps/dashboard/app/benchmarks/page.tsx`
**What:** Benchmark Lab
**Features:** Category scores, benchmark suites, test breakdowns

#### `apps/dashboard/lib/api.ts`
**What:** Centralized API client
**Exports:** `api` object with typed methods for all endpoints

### Infrastructure

#### `infra/docker/docker-compose.yml`
**What:** Defines all services for Docker deployment
**Services:** ClickHouse, Redis, API, Worker, Dashboard, Ollama, Jaeger, Prometheus, Grafana

#### `infra/docker/Dockerfile.api`
**What:** Builds the API Docker image
**Steps:** Install Python, copy packages, install dependencies, expose port 8000

#### `infra/docker/Dockerfile.dashboard`
**What:** Builds the dashboard Docker image
**Steps:** Install Node.js, build Next.js, serve static files

### Configuration

#### `.github/workflows/ci.yml`
**What:** GitHub Actions CI pipeline
**Jobs:** Python tests, TypeScript build, regression tests, Docker builds

#### `setup.py`
**What:** Python package installation config
**Packages:** shared, sdk, evals, reliability, api, worker

### Tests

#### `tests/e2e/test_pipeline.py`
**What:** End-to-end test of the full system
**Steps:** Health check → trace ingestion → query → ClickHouse verify → metrics → alerts

---

## Glossary

| Term | Definition |
|------|------------|
| **Agent** | An autonomous AI system that performs tasks |
| **Alert** | A notification when a metric crosses a threshold |
| **Analytics** | Computing statistics from raw data |
| **Async** | Non-blocking code execution |
| **Baseline** | A reference point for comparison |
| **Benchmark** | A standardized test suite |
| **Bloom Filter** | A probabilistic data structure for fast lookups |
| **Celery** | A distributed task queue for Python |
| **CI/CD** | Continuous Integration / Continuous Deployment |
| **ClickHouse** | A column-oriented analytical database |
| **Column-oriented** | Stores data by columns, not rows |
| **Container** | An isolated runtime environment |
| **CORS** | Cross-Origin Resource Sharing (browser security) |
| **Docker** | A platform for containerizing applications |
| **Drift** | Performance degradation over time |
| **Evaluator** | An automated test that scores AI outputs |
| **FastAPI** | A modern, fast Python web framework |
| **Grafana** | A dashboard tool for metrics visualization |
| **Hallucination** | An AI output containing false information |
| **Ingestion** | Receiving and storing data |
| **Jaeger** | A distributed tracing system |
| **Judge** | An LLM used to evaluate other LLMs |
| **Latency** | Time delay between request and response |
| **LLM** | Large Language Model (AI text generator) |
| **MergeTree** | ClickHouse's default table engine |
| **Metrics** | Quantitative measurements of system behavior |
| **Next.js** | A React framework for web applications |
| **Node** | A server-side JavaScript runtime |
| **Ollama** | A tool for running LLMs locally |
| **OpenTelemetry** | An observability framework standard |
| **OTel** | Short for OpenTelemetry |
| **P0/P1/P2/P3** | Severity levels (P0 = critical, P3 = low) |
| **Prometheus** | A metrics collection and alerting system |
| **RAG** | Retrieval-Augmented Generation |
| **Redis** | An in-memory data store |
| **Reflection** | An AI checking and correcting its own output |
| **Regression** | A decline in performance after a change |
| **SDK** | Software Development Kit |
| **Span** | A single operation within a trace |
| **Tailwind** | A utility-first CSS framework |
| **Telemetry** | Data about system behavior |
| **Threshold** | A boundary value that triggers an alert |
| **TLS** | Transport Layer Security (encryption) |
| **Trace** | A complete record of an AI execution |
| **TTL** | Time To Live (auto-deletion period) |
| **TypeScript** | JavaScript with static types |
| **Variance** | How much values differ from the average |
| **WebSocket** | A persistent bidirectional connection |

---

## Quick Start Commands

```bash
# 1. Start infrastructure
cd infra/docker
docker-compose up -d

# 2. Verify services
curl http://localhost:8123/ping          # ClickHouse
curl http://localhost:8000/health      # API
redis-cli ping                           # Redis

# 3. Seed demo data
curl -X POST http://localhost:8000/v1/seed

# 4. View dashboard
cd apps/dashboard && npm run dev
# Open http://localhost:3000

# 5. Run tests
cd /Users/moghalsaif/Documents/AI\ Reliability\ Lab
pytest packages/
python tests/e2e/test_pipeline.py
```

---

## Summary

The AI Reliability Lab is a **7-layer observability platform** for AI agents:

1. **SDK** — Captures traces from your AI application
2. **API** — Receives and serves trace data
3. **ClickHouse** — Stores high-volume telemetry efficiently
4. **Redis** — Queues traces for background processing
5. **Evaluators** — Automatically score AI output quality
6. **Reliability Engine** — Computes statistics and detects drift
7. **Dashboard** — Visualizes everything in real-time

It uses **OpenTelemetry** for compatibility, **ClickHouse** for speed, **Redis** for queuing, **FastAPI** for the backend, and **Next.js** for the frontend.

Every component is designed to be **observable, scalable, and production-ready**.
