# AI Reliability Lab — Agent Instructions

## Project Overview

This is an **AI infrastructure platform** for agent reliability engineering — not an AI app itself. Think Datadog meets Langfuse, purpose-built for measuring agent reliability, reflection loops, tool use accuracy, and hallucination detection.

## Architecture

The system follows a layered architecture:

| Layer | Responsibility | Key Files |
|-------|---------------|-----------|
| SDK Layer | Instrument AI systems | `packages/sdk/src/` |
| Ingestion | Receive traces/events | `apps/api/src/main.py` |
| Processing | Compute evals/reliability | `apps/worker/`, `apps/evaluator/` |
| Storage | Store telemetry | ClickHouse (`apps/api/src/db/clickhouse.py`) |
| Evaluation | Run eval metrics | `packages/evals/src/evaluators/` |
| Dashboard | Visualize failures | `apps/dashboard/` |
| Benchmarks | Regression testing | `benchmarks/` |

## Coding Conventions

### Python
- Python 3.10+ with type hints everywhere
- Use `from __future__ import annotations` for forward references
- Dataclasses for data models
- Async patterns with `asyncio` for I/O
- Pydantic v2 for API models
- `ReliabilityConfig.from_env()` for configuration

### TypeScript / Next.js
- Next.js 14 with App Router
- Tailwind CSS for styling
- Radix UI primitives
- `class-variance-authority` for component variants
- Dark mode by default (`className="dark"`)

## Key Design Decisions

1. **OpenTelemetry is mandatory** — all traces flow through OTLP. This teaches real observability engineering.

2. **ClickHouse for traces** — not Postgres. ClickHouse handles high-ingest analytics workloads.

3. **Evaluators are pluggable** — `BaseEvaluator` interface with `evaluate(trace_data) -> EvalResult`. Easy to add new evaluators.

4. **Reflection loop evaluation is the differentiator** — most tools don't visualize or measure reasoning retries. This one does.

5. **Regression diffs are CI-native** — every change runs benchmarks. Deployment is blocked on critical regressions.

## Build & Run

### Full Stack (Docker)
```bash
cd infra/docker && docker-compose up -d
```

### API Only
```bash
cd apps/api && uvicorn src.main:app --reload
```

### Dashboard Only
```bash
cd apps/dashboard && npm run dev
```

### Install Python Packages
```bash
for pkg in shared sdk evals reliability; do
  pip install -e packages/$pkg
done
```

## Testing

```bash
pytest packages/ apps/ --cov=packages
```

## Adding a New Evaluator

1. Create `packages/evals/src/evaluators/my_evaluator.py`
2. Inherit from `BaseEvaluator`
3. Implement `default_threshold()` and `evaluate()`
4. Register in `packages/evals/src/__init__.py`
5. Add to `apps/api/src/main.py` eval queue

## Adding a New Benchmark

1. Create `benchmarks/<category>/my_suite.py`
2. Define test cases with expected outcomes
3. Export to JSON with `export_to_json()`
4. Register in regression runner

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RELIABILITY_API_ENDPOINT` | `http://localhost:8000/v1/traces` | Trace ingestion endpoint |
| `RELIABILITY_ENVIRONMENT` | `development` | Environment tag |
| `CLICKHOUSE_HOST` | `localhost` | ClickHouse server |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | - | OpenTelemetry endpoint |

## Important Notes

- Do NOT commit `.env` files
- Do NOT run `git commit` unless explicitly asked
- Update this file when adding new layers or changing conventions
- All evaluators must be deterministic (low temperature for judges)
- The SDK must never crash user code — exporter failures are logged, not raised

## Model Configuration

Default judge model: Qwen3 32B via Ollama
Fast eval model: Ministral 8B via Ollama
Embeddings: bge-m3

Configure via `JudgeConfig` when instantiating evaluators.
