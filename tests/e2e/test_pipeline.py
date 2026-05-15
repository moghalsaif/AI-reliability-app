"""End-to-end test: SDK trace → API → ClickHouse → Dashboard verification."""

from __future__ import annotations

import asyncio
import sys
import time
import uuid
from datetime import datetime

import requests


def test_full_pipeline() -> bool:
    """Run the complete end-to-end pipeline test."""
    api_base = "http://localhost:8000"
    
    # 1. Verify API is healthy
    print("Step 1: Checking API health...")
    try:
        resp = requests.get(f"{api_base}/health", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        assert data["status"] == "healthy", f"API not healthy: {data}"
        print(f"  ✓ API healthy: {data['version']}")
    except Exception as e:
        print(f"  ✗ API health check failed: {e}")
        return False
    
    # 2. Send a trace via SDK-style HTTP call
    print("Step 2: Sending trace to API...")
    trace_id = f"e2e-test-{uuid.uuid4().hex[:8]}"
    trace_payload = {
        "trace": {
            "trace_id": trace_id,
            "name": "e2e_test_trace",
            "start_time": datetime.utcnow().isoformat(),
            "end_time": datetime.utcnow().isoformat(),
            "status": "success",
            "agent_name": "e2e_agent",
            "environment": "test",
            "success": True,
            "span_count": 5,
            "total_tokens": 100,
            "total_latency_ms": 1200.0,
            "tags": ["e2e"],
            "attributes": {"test": True},
        },
        "source": "e2e_test",
    }
    
    try:
        resp = requests.post(f"{api_base}/v1/traces", json=trace_payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        assert data["status"] == "accepted", f"Trace not accepted: {data}"
        print(f"  ✓ Trace accepted: {data['trace_id']}")
    except Exception as e:
        print(f"  ✗ Trace ingestion failed: {e}")
        return False
    
    # 3. Wait for trace to be processed
    print("Step 3: Waiting for trace processing...")
    time.sleep(2)
    
    # 4. Query trace back from API
    print("Step 4: Querying trace from API...")
    try:
        resp = requests.get(f"{api_base}/v1/traces?limit=10", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        traces = data.get("traces", [])
        trace_ids = [t["trace_id"] for t in traces]
        assert trace_id in trace_ids, f"Trace {trace_id} not found in query results"
        print(f"  ✓ Trace found in API query ({len(traces)} total traces)")
    except Exception as e:
        print(f"  ✗ Trace query failed: {e}")
        return False
    
    # 5. Verify trace in ClickHouse directly
    print("Step 5: Verifying trace in ClickHouse...")
    try:
        resp = requests.get(
            "http://localhost:8123/",
            params={
                "query": f"SELECT count() FROM reliability_lab.traces WHERE trace_id = '{trace_id}'",
                "password": "reliability_lab_pass",
            },
            timeout=10,
        )
        resp.raise_for_status()
        count = int(resp.text.strip())
        assert count >= 1, f"Trace not found in ClickHouse"
        print(f"  ✓ Trace confirmed in ClickHouse")
    except Exception as e:
        print(f"  ✗ ClickHouse verification failed: {e}")
        return False
    
    # 6. Verify reliability metrics are computed
    print("Step 6: Checking reliability metrics...")
    try:
        resp = requests.get(f"{api_base}/v1/metrics/reliability", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        metrics = data.get("metrics", {})
        assert "avg_success_rate" in metrics, "Missing success rate metric"
        print(f"  ✓ Reliability metrics available: success_rate={metrics.get('avg_success_rate', 0):.2%}")
    except Exception as e:
        print(f"  ✗ Reliability metrics check failed: {e}")
        return False
    
    # 7. Verify dashboard can fetch data (API endpoints are reachable)
    print("Step 7: Verifying dashboard data endpoints...")
    try:
        for endpoint in ["/v1/traces", "/v1/metrics/reliability", "/v1/alerts"]:
            resp = requests.get(f"{api_base}{endpoint}?limit=5", timeout=10)
            resp.raise_for_status()
        print(f"  ✓ All dashboard endpoints responding")
    except Exception as e:
        print(f"  ✗ Dashboard endpoint check failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("END-TO-END TEST PASSED ✓")
    print("=" * 50)
    return True


if __name__ == "__main__":
    success = test_full_pipeline()
    sys.exit(0 if success else 1)
