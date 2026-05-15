"""FastAPI application for trace ingestion and management."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from reliability_shared.types.core import Trace, TelemetryBatch
from reliability_shared.config import ReliabilityConfig


# Pydantic models for API
class TraceIngestRequest(BaseModel):
    """Request model for trace ingestion."""
    trace: Dict[str, Any]
    source: str = "sdk"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TraceIngestResponse(BaseModel):
    """Response model for trace ingestion."""
    trace_id: str
    status: str
    message: str


class TraceQueryParams(BaseModel):
    """Query parameters for trace search."""
    agent_name: Optional[str] = None
    environment: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    success_only: bool = False
    limit: int = 100


class EvaluationResult(BaseModel):
    """Evaluation result model."""
    eval_id: str
    trace_id: str
    eval_type: str
    score: float
    passed: bool
    threshold: float
    details: Dict[str, Any]


class ReliabilityMetrics(BaseModel):
    """Reliability metrics model."""
    trace_id: str
    run_id: str
    success_rate: float
    hallucination_rate: float
    variance_score: float
    retry_density: float
    cost_per_success: float
    latency_p95: float
    context_retention: float
    tool_accuracy: float


class Alert(BaseModel):
    """Alert model."""
    alert_id: str
    trace_id: str
    alert_type: str
    severity: str
    message: str
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    acknowledged: bool = False
    timestamp: datetime


# Global state
config = ReliabilityConfig.from_env()
db_client = None
redis_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global db_client, redis_client
    
    # Initialize database
    from .db.clickhouse import ClickHouseClient
    db_client = ClickHouseClient(
        host=config.clickhouse_host,
        port=config.clickhouse_port,
        database=config.clickhouse_database,
    )
    await db_client.connect()
    await db_client.init_schema()
    
    # Initialize Redis
    import redis.asyncio as redis
    redis_client = redis.from_url(config.redis_url)
    
    # Start background tasks
    asyncio.create_task(process_eval_queue())
    asyncio.create_task(process_reliability_analysis())
    asyncio.create_task(process_alert_engine())
    
    yield
    
    # Cleanup
    if redis_client:
        await redis_client.close()


app = FastAPI(
    title="AI Reliability Lab API",
    description="Infrastructure platform for agent reliability engineering",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Background task handlers
async def process_eval_queue():
    """Process evaluation queue from Redis."""
    while True:
        try:
            if redis_client:
                # Pop from eval queue
                item = await redis_client.lpop("eval_queue")
                if item:
                    data = json.loads(item)
                    await run_evaluations(data["trace_id"], data["trace_data"])
        except Exception as e:
            import logging
            logging.getLogger("reliability_api").error(f"Eval queue error: {e}")
        await asyncio.sleep(1)


async def process_reliability_analysis():
    """Run periodic reliability analysis."""
    while True:
        try:
            # Process traces that need reliability metrics
            pass
        except Exception as e:
            import logging
            logging.getLogger("reliability_api").error(f"Reliability analysis error: {e}")
        await asyncio.sleep(60)


async def process_alert_engine():
    """Run alert detection engine."""
    while True:
        try:
            # Check for anomalies and generate alerts
            pass
        except Exception as e:
            import logging
            logging.getLogger("reliability_api").error(f"Alert engine error: {e}")
        await asyncio.sleep(30)


async def run_evaluations(trace_id: str, trace_data: Dict[str, Any]) -> List[EvaluationResult]:
    """Run all evaluators on a trace."""
    from reliability_evals import HallucinationEvaluator, RAGEvaluator, ToolUseEvaluator, ReflectionEvaluator, MemoryEvaluator
    
    evaluators = [
        ("hallucination", HallucinationEvaluator()),
        ("rag", RAGEvaluator()),
        ("tool_use", ToolUseEvaluator()),
        ("reflection", ReflectionEvaluator()),
        ("memory", MemoryEvaluator()),
    ]
    
    results = []
    for eval_type, evaluator in evaluators:
        try:
            result = evaluator.evaluate(trace_data)
            results.append(EvaluationResult(
                eval_id=f"{trace_id}_{eval_type}",
                trace_id=trace_id,
                eval_type=eval_type,
                score=result.score,
                passed=result.passed,
                threshold=result.threshold,
                details=result.details,
            ))
        except Exception as e:
            import logging
            logging.getLogger("reliability_api").error(f"Evaluator {eval_type} failed: {e}")
    
    # Store results in ClickHouse
    for result in results:
        await db_client.execute("""
        INSERT INTO evaluations (eval_id, trace_id, eval_type, score, passed, threshold, details, timestamp)
        VALUES
        """, {"values": [(
            result.eval_id,
            result.trace_id,
            result.eval_type,
            result.score,
            result.passed,
            result.threshold,
            json.dumps(result.details),
            datetime.utcnow(),
        )]})
    
    return results


# API Endpoints
@app.post("/v1/traces", response_model=TraceIngestResponse)
async def ingest_trace(request: TraceIngestRequest, background_tasks: BackgroundTasks):
    """Ingest a trace from the SDK."""
    trace_id = request.trace.get("trace_id", "unknown")
    
    try:
        # Store in ClickHouse
        await db_client.insert_trace(Trace(**request.trace))
        
        # Queue for evaluation
        if redis_client and config.enable_evaluations:
            await redis_client.rpush("eval_queue", json.dumps({
                "trace_id": trace_id,
                "trace_data": request.trace,
            }))
        
        return TraceIngestResponse(
            trace_id=trace_id,
            status="accepted",
            message="Trace ingested successfully",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/traces/batch")
async def ingest_batch(batch: TelemetryBatch):
    """Ingest a batch of traces."""
    results = []
    for trace in batch.traces:
        try:
            await db_client.insert_trace(trace)
            results.append({"trace_id": trace.trace_id, "status": "accepted"})
        except Exception as e:
            results.append({"trace_id": trace.trace_id, "status": "error", "error": str(e)})
    
    return {"results": results}


@app.get("/v1/traces")
async def list_traces(
    agent_name: Optional[str] = None,
    environment: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100,
):
    """List traces with filtering."""
    traces = await db_client.query_traces(
        agent_name=agent_name,
        environment=environment,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )
    return {"traces": traces, "count": len(traces)}


@app.get("/v1/traces/{trace_id}")
async def get_trace(trace_id: str):
    """Get a single trace by ID."""
    traces = await db_client.query_traces()
    for trace in traces:
        if trace.get("trace_id") == trace_id:
            return trace
    raise HTTPException(status_code=404, detail="Trace not found")


@app.get("/v1/traces/{trace_id}/spans")
async def get_trace_spans(trace_id: str):
    """Get all spans for a trace."""
    spans = await db_client.execute(
        f"SELECT * FROM spans WHERE trace_id = '{trace_id}' ORDER BY start_time"
    )
    return {"spans": spans or []}


@app.get("/v1/traces/{trace_id}/evaluations")
async def get_trace_evaluations(trace_id: str):
    """Get all evaluations for a trace."""
    evaluations = await db_client.execute(
        f"SELECT * FROM evaluations WHERE trace_id = '{trace_id}' ORDER BY timestamp"
    )
    return {"evaluations": evaluations or []}


@app.get("/v1/metrics/reliability")
async def get_reliability_metrics(
    agent_name: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
):
    """Get aggregated reliability metrics."""
    metrics = await db_client.execute(
        f"""
        SELECT 
            avg(success_rate) as avg_success_rate,
            avg(hallucination_rate) as avg_hallucination_rate,
            avg(variance_score) as avg_variance_score,
            avg(latency_p95) as avg_latency_p95,
            avg(tool_accuracy) as avg_tool_accuracy
        FROM reliability_metrics
        WHERE 1=1
        {"AND agent_name = '" + agent_name + "'" if agent_name else ""}
        {"AND timestamp >= '" + start_time.isoformat() + "'" if start_time else ""}
        {"AND timestamp <= '" + end_time.isoformat() + "'" if end_time else ""}
        """
    )
    return {"metrics": metrics[0] if metrics else {}}


@app.get("/v1/alerts")
async def list_alerts(
    severity: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    limit: int = 100,
):
    """List alerts with filtering."""
    conditions = ["1=1"]
    if severity:
        conditions.append(f"severity = '{severity}'")
    if acknowledged is not None:
        conditions.append(f"acknowledged = {acknowledged}")
    
    alerts = await db_client.execute(
        f"SELECT * FROM alerts WHERE {' AND '.join(conditions)} ORDER BY timestamp DESC LIMIT {limit}"
    )
    return {"alerts": alerts or []}


@app.post("/v1/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Acknowledge an alert."""
    await db_client.execute(
        f"ALTER TABLE alerts UPDATE acknowledged = true WHERE alert_id = '{alert_id}'"
    )
    return {"status": "acknowledged"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "database": "connected" if db_client else "disconnected",
    }
