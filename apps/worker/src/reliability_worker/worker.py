"""Celery worker for async processing."""

import os
from celery import Celery
from celery.signals import task_prerun, task_postrun

# Redis broker
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = Celery("reliability_worker")
app.conf.update(
    broker_url=redis_url,
    result_backend=redis_url,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    worker_prefetch_multiplier=1,
)


@app.task(bind=True, max_retries=3)
def process_trace(self, trace_data: dict):
    """Process a trace asynchronously."""
    try:
        # 1. Normalize and validate trace
        trace_id = trace_data.get("trace_id", "unknown")
        
        # 2. Store in ClickHouse
        from reliability_api.db.clickhouse import ClickHouseClient
        client = ClickHouseClient()
        
        # 3. Run evaluations
        from reliability_evals import (
            HallucinationEvaluator,
            RAGEvaluator,
            ToolUseEvaluator,
            ReflectionEvaluator,
            MemoryEvaluator,
        )
        
        evaluators = [
            HallucinationEvaluator(),
            RAGEvaluator(),
            ToolUseEvaluator(),
            ReflectionEvaluator(),
            MemoryEvaluator(),
        ]
        
        results = []
        for evaluator in evaluators:
            try:
                result = evaluator.evaluate(trace_data)
                results.append(result.to_dict())
            except Exception as e:
                import logging
                logging.getLogger("reliability_worker").warning(f"Evaluator failed: {e}")
        
        # 4. Compute reliability metrics
        # 5. Check alerts
        # 6. Update trace with computed metrics
        
        return {
            "trace_id": trace_id,
            "status": "processed",
            "eval_count": len(results),
        }
        
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@app.task
def run_reliability_analysis(trace_ids: list):
    """Run reliability analysis on a batch of traces."""
    # Aggregate metrics across traces
    # Compute variance, stability, drift
    pass


@app.task
def run_benchmark(benchmark_id: str):
    """Run a benchmark suite."""
    # Load benchmark config
    # Run test cases
    # Store results
    pass


@app.task
def check_alerts():
    """Run alert detection."""
    # Query recent traces
    # Check thresholds
    # Generate alerts
    pass


@task_prerun.connect
def task_prerun_handler(task_id, task, args, kwargs, **extras):
    import logging
    logging.getLogger("reliability_worker").info(f"Starting task: {task.name}")


@task_postrun.connect
def task_postrun_handler(task_id, task, args, kwargs, retval, state, **extras):
    import logging
    logging.getLogger("reliability_worker").info(f"Task completed: {task.name} ({state})")
