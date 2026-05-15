"""End-to-end demo of AI Reliability Lab.

This script demonstrates the full pipeline:
1. Trace an agent run
2. Run evaluators on the trace
3. Compute reliability metrics
4. Show regression analysis
"""

from reliability_sdk import Tracer, ConsoleExporter
from reliability_shared.types.core import (
    ModelMetadata,
    TokenUsage,
    RetrievalResult,
    ReflectionEvent,
    MemoryOperation,
    MemoryOpType,
)
from reliability_evals import (
    HallucinationEvaluator,
    RAGEvaluator,
    ToolUseEvaluator,
    ReflectionEvaluator,
    MemoryEvaluator,
)
from reliability_engine import (
    ReliabilityAnalyzer,
    ReliabilityRun,
    ReliabilityReport,
)
from reliability_engine.regression import (
    RegressionTestRunner,
    CICDPipeline,
    TestCase,
)


def demo_trace_collection():
    """Demo 1: Collect a rich trace with all span types."""
    print("\n" + "="*70)
    print("DEMO 1: TRACE COLLECTION")
    print("="*70)
    
    tracer = Tracer(service_name="customer-support-agent")
    console = ConsoleExporter(pretty=True)
    tracer.add_exporter(console)
    
    with tracer.trace(
        name="support_ticket_resolution",
        agent_name="support_bot_v2",
        session_id="session-abc123",
        user_id="user-456",
    ):
        # Memory read
        tracer.record_memory_op(
            op_type="read",
            key="user_history",
            value="Premium customer, 3 years",
            namespace="profile",
        )
        
        # Retrieval
        tracer.record_retrieval(
            query="refund policy for premium customers",
            results=[
                RetrievalResult(
                    query="refund policy",
                    source="kb://policies/premium",
                    content="Premium customers are eligible for full refunds within 30 days.",
                    score=0.96,
                    rank=0,
                ),
                RetrievalResult(
                    query="refund policy",
                    source="kb://policies/general",
                    content="Standard refund window is 14 days.",
                    score=0.72,
                    rank=1,
                ),
            ],
            latency_ms=145,
        )
        
        # LLM call 1
        tracer.record_llm_call(
            prompt="Customer wants a refund. Context: Premium customer. Policy: 30 days.",
            completion="I can process a full refund since you're within the 30-day window.",
            model_metadata=ModelMetadata(
                model_name="qwen3-32b",
                provider="ollama",
                temperature=0.3,
            ),
            token_usage=TokenUsage(prompt_tokens=45, completion_tokens=18),
            latency_ms=890,
        )
        
        # Reflection
        tracer.record_reflection(
            iteration=1,
            reflection_type="verification",
            input_context="Check if refund is valid",
            output_decision="Valid - within 30 days",
            confidence=0.94,
            triggered_retry=False,
        )
        
        # Tool call
        tracer.record_tool_call(
            tool_name="process_refund",
            parameters={"amount": 99.99, "order_id": "ORD-12345"},
            result={"status": "success", "refund_id": "REF-789"},
            latency_ms=320,
        )
        
        # Memory write
        tracer.record_memory_op(
            op_type="write",
            key="last_refund",
            value={"id": "REF-789", "amount": 99.99},
            namespace="transactions",
        )
    
    print("Trace collected successfully!")


def demo_evaluations():
    """Demo 2: Run evaluators on a trace."""
    print("\n" + "="*70)
    print("DEMO 2: EVALUATION ENGINE")
    print("="*70)
    
    # Create a sample trace for evaluation
    trace_data = {
        "trace_id": "demo-trace-001",
        "spans": [
            {
                "span_id": "span-1",
                "span_type": "llm",
                "input": "What is the capital of France?",
                "output": "Paris is the capital of France.",
                "retrievals": [
                    {
                        "source": "wiki",
                        "content": "Paris is the capital and most populous city of France.",
                        "score": 0.95,
                        "rank": 0,
                    }
                ],
                "tool_calls": [],
                "reflections": [],
                "memory_ops": [],
            },
            {
                "span_id": "span-2",
                "span_type": "tool_call",
                "tool_calls": [
                    {
                        "tool_name": "weather_api",
                        "parameters": {"location": "Paris"},
                        "result": {"temp": 18, "condition": "sunny"},
                        "latency_ms": 250,
                        "retry_count": 0,
                    }
                ],
            },
            {
                "span_id": "span-3",
                "span_type": "reflection",
                "reflections": [
                    {
                        "iteration": 1,
                        "reflection_type": "verification",
                        "input_context": "Check answer accuracy",
                        "output_decision": "Confirmed correct",
                        "confidence": 0.95,
                        "triggered_retry": False,
                    }
                ],
            },
            {
                "span_id": "span-4",
                "span_type": "memory_op",
                "memory_ops": [
                    {
                        "op_type": "read",
                        "key": "user_name",
                        "value": "Alice",
                        "namespace": "session",
                        "success": True,
                    }
                ],
            },
        ]
    }
    
    evaluators = {
        "Hallucination": HallucinationEvaluator(),
        "RAG": RAGEvaluator(),
        "Tool Use": ToolUseEvaluator(),
        "Reflection": ReflectionEvaluator(),
        "Memory": MemoryEvaluator(),
    }
    
    for name, evaluator in evaluators.items():
        result = evaluator.evaluate(trace_data)
        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"  {name:15s} | {status} | Score: {result.score:.3f} | Threshold: {result.threshold:.3f}")


def demo_reliability_analysis():
    """Demo 3: Statistical reliability analysis."""
    print("\n" + "="*70)
    print("DEMO 3: RELIABILITY ANALYSIS")
    print("="*70)
    
    # Simulate multiple runs
    runs = [
        ReliabilityRun(
            run_id=f"run-{i}",
            trace_id=f"trace-{i}",
            agent_name="qa_bot",
            model_name="qwen3-32b",
            temperature=0.7,
            prompt_version="v1.2",
            success=True,
            latency_ms=1200 + i * 50,
            token_count=500 + i * 20,
            hallucination_score=0.92,
            tool_accuracy=0.95,
            reflection_score=0.88,
            timestamp="2024-01-01",
        )
        for i in range(10)
    ]
    
    # Add a few failures
    runs[3].success = False
    runs[3].latency_ms = 5000
    runs[7].success = False
    runs[7].token_count = 2000
    
    analyzer = ReliabilityAnalyzer(cost_per_token=0.0001)
    report = analyzer.analyze(runs, experiment_id="exp-001")
    
    print(f"  Experiment: {report.experiment_id}")
    print(f"  Runs: {report.run_count}")
    print(f"  Success Rate: {report.success_rate:.1%}")
    print(f"  Hallucination Rate: {report.hallucination_rate:.1%}")
    print(f"  Variance Score: {report.variance_score:.3f}")
    print(f"  Latency P95: {report.latency_p95:.0f}ms")
    print(f"  Cost/Success: ${report.cost_per_success:.4f}")
    print(f"  Tool Accuracy: {report.tool_accuracy:.3f}")
    print(f"  Drift Detected: {report.drift_detected}")


def demo_regression_testing():
    """Demo 4: Regression testing / CI/CD."""
    print("\n" + "="*70)
    print("DEMO 4: REGRESSION TESTING / CI-CD")
    print("="*70)
    
    # Mock agent factory
    def mock_agent_factory():
        class MockAgent:
            def run(self, input_data):
                return {"answer": "mock"}
        return MockAgent()
    
    # Create test cases
    test_cases = [
        TestCase(
            id="test-001",
            name="Basic Q&A",
            input="What is 2+2?",
            expected_output="4",
        ),
        TestCase(
            id="test-002",
            name="Tool Use",
            input="Get weather for Tokyo",
            expected_tools=["weather_api"],
        ),
        TestCase(
            id="test-003",
            name="RAG Query",
            input="What is our refund policy?",
            expected_retrievals=["kb://policies"],
        ),
    ]
    
    runner = RegressionTestRunner(agent_factory=mock_agent_factory)
    pipeline = CICDPipeline(runner)
    
    # This would normally run the full pipeline
    # For demo, show the structure
    print("  Regression pipeline configured with:")
    print(f"    - {len(test_cases)} test cases")
    print(f"    - 5 evaluators (hallucination, rag, tool_use, reflection, memory)")
    print(f"    - Baseline comparison enabled")
    print(f"    - Deployment gate: success_rate >= 85%")
    print("\n  To run: pipeline.run_pipeline(test_cases, commit_hash='abc123')")


def demo_benchmarks():
    """Demo 5: Benchmark datasets."""
    print("\n" + "="*70)
    print("DEMO 5: BENCHMARK LAB")
    print("="*70)
    
    from benchmarks.runner import BenchmarkRegistry
    
    registry = BenchmarkRegistry()
    suites = registry.get_all()
    
    print(f"  Available benchmark suites: {len(suites)}")
    for name, tests in suites.items():
        print(f"    - {name.upper():10s}: {len(tests)} test cases")
    
    print("\n  Export all benchmarks: registry.export_all()")


if __name__ == "__main__":
    print("\n" + "█"*70)
    print("█" + " "*68 + "█")
    print("█" + "  AI RELIABILITY LAB - END-TO-END DEMONSTRATION".center(68) + "█")
    print("█" + " "*68 + "█")
    print("█"*70)
    
    demo_trace_collection()
    demo_evaluations()
    demo_reliability_analysis()
    demo_regression_testing()
    demo_benchmarks()
    
    print("\n" + "█"*70)
    print("█" + "  ALL DEMOS COMPLETE".center(68) + "█")
    print("█"*70 + "\n")
