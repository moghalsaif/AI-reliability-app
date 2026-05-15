"""FastAPI application for trace ingestion and management."""

from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket
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
        username=config.clickhouse_username,
        password=config.clickhouse_password,
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
            await check_reliability_thresholds()
        except Exception as e:
            import logging
            logging.getLogger("reliability_api").error(f"Alert engine error: {e}")
        await asyncio.sleep(30)


async def check_reliability_thresholds() -> None:
    """Check reliability metrics against thresholds and send alerts."""
    try:
        # Get recent reliability metrics
        metrics = await db_client.execute(
            """
            SELECT 
                avg(success_rate) as avg_success_rate,
                avg(hallucination_rate) as avg_hallucination_rate,
                avg(tool_accuracy) as avg_tool_accuracy,
                count() as sample_count
            FROM reliability_metrics
            WHERE timestamp >= now() - INTERVAL 1 HOUR
            """
        )
        
        if not metrics or not metrics[0]:
            return
        
        m = metrics[0]
        
        # Thresholds
        thresholds = {
            "success_rate": {"min": 0.90, "severity": "P0"},
            "hallucination_rate": {"max": 0.10, "severity": "P1"},
            "tool_accuracy": {"min": 0.85, "severity": "P1"},
        }
        
        alerts_to_insert = []
        
        # Check success rate
        if m.get("avg_success_rate", 1.0) < thresholds["success_rate"]["min"]:
            alerts_to_insert.append({
                "alert_id": f"alert-{uuid.uuid4().hex[:8]}",
                "trace_id": "system",
                "alert_type": "threshold_breach",
                "severity": thresholds["success_rate"]["severity"],
                "message": f"Success rate dropped to {m['avg_success_rate']:.2%} (threshold: {thresholds['success_rate']['min']:.0%})",
                "metric_name": "success_rate",
                "metric_value": m["avg_success_rate"],
                "threshold": thresholds["success_rate"]["min"],
                "timestamp": datetime.utcnow(),
            })
        
        # Check hallucination rate
        if m.get("avg_hallucination_rate", 0.0) > thresholds["hallucination_rate"]["max"]:
            alerts_to_insert.append({
                "alert_id": f"alert-{uuid.uuid4().hex[:8]}",
                "trace_id": "system",
                "alert_type": "threshold_breach",
                "severity": thresholds["hallucination_rate"]["severity"],
                "message": f"Hallucination rate increased to {m['avg_hallucination_rate']:.2%} (threshold: {thresholds['hallucination_rate']['max']:.0%})",
                "metric_name": "hallucination_rate",
                "metric_value": m["avg_hallucination_rate"],
                "threshold": thresholds["hallucination_rate"]["max"],
                "timestamp": datetime.utcnow(),
            })
        
        # Check tool accuracy
        if m.get("avg_tool_accuracy", 1.0) < thresholds["tool_accuracy"]["min"]:
            alerts_to_insert.append({
                "alert_id": f"alert-{uuid.uuid4().hex[:8]}",
                "trace_id": "system",
                "alert_type": "threshold_breach",
                "severity": thresholds["tool_accuracy"]["severity"],
                "message": f"Tool accuracy dropped to {m['avg_tool_accuracy']:.2%} (threshold: {thresholds['tool_accuracy']['min']:.0%})",
                "metric_name": "tool_accuracy",
                "metric_value": m["avg_tool_accuracy"],
                "threshold": thresholds["tool_accuracy"]["min"],
                "timestamp": datetime.utcnow(),
            })
        
        # Insert alerts into ClickHouse
        for alert in alerts_to_insert:
            await db_client.execute(
                """
                INSERT INTO alerts (
                    alert_id, trace_id, alert_type, severity,
                    message, metric_name, metric_value, threshold, timestamp
                ) VALUES
                """,
                tuple(alert.values())
            )
            
            # Send Slack notification if configured
            await send_slack_alert(alert)
            
    except Exception as e:
        import logging
        logging.getLogger("reliability_api").error(f"Threshold check error: {e}")


async def send_slack_alert(alert: dict) -> None:
    """Send alert to Slack webhook if configured."""
    import os
    import aiohttp
    
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return
    
    severity_emoji = {
        "P0": "🔴",
        "P1": "🟠",
        "P2": "🟡",
        "P3": "🔵",
    }
    
    payload = {
        "text": f"{severity_emoji.get(alert['severity'], '⚪')} AI Reliability Alert: {alert['severity']}",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Reliability Threshold Breach: {alert['metric_name']}",
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Severity:*\n{alert['severity']}"},
                    {"type": "mrkdwn", "text": f"*Metric:*\n{alert['metric_name']}"},
                    {"type": "mrkdwn", "text": f"*Current Value:*\n{alert['metric_value']:.2%}"},
                    {"type": "mrkdwn", "text": f"*Threshold:*\n{alert['threshold']:.2%}"},
                ]
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*{alert['message']}*"}
            },
        ]
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as resp:
                if resp.status != 200:
                    logging.getLogger("reliability_api").warning(f"Slack alert failed: {resp.status}")
    except Exception as e:
        logging.getLogger("reliability_api").error(f"Slack send error: {e}")


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
        # Filter trace data to only include valid Trace fields
        from reliability_shared.types.core import Trace, SpanStatus
        from datetime import datetime
        valid_fields = {"trace_id", "name", "start_time", "end_time", "status",
                       "session_id", "user_id", "agent_name", "environment",
                       "version", "success", "error_message", "attributes", "tags"}
        filtered_trace = {k: v for k, v in request.trace.items() if k in valid_fields}
        
        # Convert datetime strings to datetime objects
        for field in ["start_time", "end_time"]:
            if field in filtered_trace and isinstance(filtered_trace[field], str):
                try:
                    filtered_trace[field] = datetime.fromisoformat(filtered_trace[field].replace("Z", "+00:00"))
                except ValueError:
                    filtered_trace[field] = datetime.utcnow()
        
        # Convert status string to enum if needed
        if "status" in filtered_trace and isinstance(filtered_trace["status"], str):
            try:
                filtered_trace["status"] = SpanStatus(filtered_trace["status"])
            except ValueError:
                filtered_trace["status"] = SpanStatus.OK
        
        # Store in ClickHouse
        await db_client.insert_trace(Trace(**filtered_trace))
        
        # Broadcast to WebSocket clients
        await broadcast_trace_update({
            "trace_id": trace_id,
            "agent_name": filtered_trace.get("agent_name"),
            "status": filtered_trace.get("status", "ok"),
            "success": filtered_trace.get("success", True),
            "timestamp": datetime.utcnow().isoformat(),
        })
        
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


@app.post("/v1/seed")
async def seed_demo_data():
    """Insert demo data for testing."""
    from datetime import datetime, timedelta
    import uuid
    import random

    agents = ["contract_agent", "support_bot", "research_assistant", "code_reviewer"]
    
    # Insert demo traces
    for i in range(20):
        trace_id = f"trace-{uuid.uuid4().hex[:8]}"
        agent = random.choice(agents)
        success = random.random() > 0.15
        latency = random.uniform(500, 5500)
        spans = random.randint(3, 15)
        
        await db_client.execute("""
        INSERT INTO traces (
            trace_id, name, start_time, end_time, duration_ms,
            status, agent_name, environment, success,
            error_message, span_count, total_tokens, total_latency_ms, tags, attributes
        ) VALUES
        """, (
            trace_id,
            f"{agent}_run_{i}",
            datetime.utcnow() - timedelta(minutes=i*5),
            datetime.utcnow() - timedelta(minutes=i*5) + timedelta(milliseconds=latency),
            latency,
            "success" if success else "error",
            agent,
            "development",
            success,
            None if success else "Simulated error for testing",
            spans,
            random.randint(100, 2000),
            latency,
            ["demo", agent],
            '{"demo": true}',
        ))
    
    # Insert demo reliability metrics
    for i in range(30):
        await db_client.execute("""
        INSERT INTO reliability_metrics (
            metric_id, trace_id, run_id, agent_name,
            success_rate, hallucination_rate, variance_score,
            retry_density, cost_per_success, latency_p95,
            context_retention, tool_accuracy, timestamp
        ) VALUES
        """, (
            f"metric-{uuid.uuid4().hex[:8]}",
            f"trace-{uuid.uuid4().hex[:8]}",
            f"run-{i}",
            random.choice(agents),
            random.uniform(0.75, 0.98),
            random.uniform(0.01, 0.12),
            random.uniform(0.05, 0.25),
            random.uniform(0.0, 0.3),
            random.uniform(0.01, 0.1),
            random.uniform(800, 4000),
            random.uniform(0.7, 0.95),
            random.uniform(0.75, 0.98),
            datetime.utcnow() - timedelta(days=i),
        ))
    
    # Insert demo alerts
    alert_types = ["hallucination", "tool_error", "loop_collapse", "memory_poison", "latency_spike"]
    severities = ["P0", "P1", "P2", "P3"]
    for i in range(5):
        await db_client.execute("""
        INSERT INTO alerts (
            alert_id, trace_id, alert_type, severity,
            message, metric_name, metric_value, threshold, timestamp
        ) VALUES
        """, (
            f"alert-{uuid.uuid4().hex[:8]}",
            f"trace-{uuid.uuid4().hex[:8]}",
            random.choice(alert_types),
            random.choice(severities),
            f"Demo alert {i+1}: threshold exceeded",
            "success_rate",
            random.uniform(0.5, 0.9),
            0.95,
            datetime.utcnow() - timedelta(hours=i*2),
        ))
    
    return {"status": "seeded", "traces": 20, "metrics": 30, "alerts": 5}


@app.get("/v1/benchmarks")
async def list_benchmarks():
    """List available benchmark suites."""
    return {
        "benchmarks": [
            {
                "id": "rag-001",
                "name": "RAG Adversarial",
                "category": "rag",
                "status": "completed",
                "progress": 100,
                "tests_total": 250,
                "tests_passed": 238,
                "avg_score": 0.87,
                "last_run": "2 hours ago",
            },
            {
                "id": "agent-001",
                "name": "Multi-Step Agent",
                "category": "agents",
                "status": "running",
                "progress": 65,
                "tests_total": 100,
                "tests_passed": 0,
                "avg_score": 0,
                "last_run": "Running...",
            },
            {
                "id": "mem-001",
                "name": "Long-Context Memory",
                "category": "memory",
                "status": "completed",
                "progress": 100,
                "tests_total": 150,
                "tests_passed": 142,
                "avg_score": 0.91,
                "last_run": "5 hours ago",
            },
            {
                "id": "tool-001",
                "name": "Tool Failure Sim",
                "category": "tool_use",
                "status": "completed",
                "progress": 100,
                "tests_total": 200,
                "tests_passed": 185,
                "avg_score": 0.83,
                "last_run": "1 day ago",
            },
        ]
    }


@app.get("/v1/reflections/{trace_id}")
async def get_trace_reflections(trace_id: str):
    """Get reflection data for a trace from spans."""
    spans = await db_client.execute(
        f"SELECT span_id, name, reflections, retry_count, status FROM spans WHERE trace_id = '{trace_id}'"
    )
    
    reflections = []
    for span in spans or []:
        if span.get("reflections"):
            import json
            try:
                refl_data = json.loads(span["reflections"])
                for r in refl_data:
                    reflections.append({
                        "span_id": span["span_id"],
                        "span_name": span["name"],
                        "iteration": r.get("iteration", 1),
                        "reflection_type": r.get("type", "self_check"),
                        "confidence": r.get("confidence", 0.5),
                        "triggered_retry": r.get("triggered_retry", False),
                        "retry_count": span.get("retry_count", 0),
                        "status": span.get("status", "unknown"),
                    })
            except json.JSONDecodeError:
                pass
    
    return {"trace_id": trace_id, "reflections": reflections, "total_reflections": len(reflections)}


# WebSocket connections for real-time updates
connected_websockets: set = set()

@app.websocket("/v1/ws/traces")
async def websocket_traces(websocket: WebSocket):
    """WebSocket endpoint for real-time trace updates."""
    await websocket.accept()
    connected_websockets.add(websocket)
    try:
        while True:
            # Keep connection alive and wait for client messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except Exception:
        pass
    finally:
        connected_websockets.discard(websocket)


async def broadcast_trace_update(trace_data: dict) -> None:
    """Broadcast a trace update to all connected WebSocket clients."""
    import json
    disconnected = set()
    for ws in connected_websockets:
        try:
            await ws.send_text(json.dumps({
                "type": "trace_update",
                "data": trace_data,
            }))
        except Exception:
            disconnected.add(ws)
    for ws in disconnected:
        connected_websockets.discard(ws)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "database": "connected" if db_client else "disconnected",
    }
