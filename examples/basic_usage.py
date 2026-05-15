"""Example: Instrumenting a simple agent with the Reliability SDK.

This example shows how to trace a simple RAG-based agent.
"""

from reliability_sdk import Tracer, OpenTelemetryExporter, HTTPExporter
from reliability_shared.types.core import (
    ModelMetadata,
    TokenUsage,
    RetrievalResult,
)


def example_basic_tracing():
    """Basic trace example."""
    tracer = Tracer(service_name="example-agent")
    tracer.add_exporter(ConsoleExporter(pretty=True))
    
    with tracer.trace("simple_query", agent_name="qa_bot") as builder:
        # Simulate LLM call
        tracer.record_llm_call(
            prompt="What is machine learning?",
            completion="Machine learning is...",
            model_metadata=ModelMetadata(
                model_name="qwen3-32b",
                provider="ollama",
                temperature=0.7,
            ),
            token_usage=TokenUsage(prompt_tokens=5, completion_tokens=50),
            latency_ms=1200,
        )
    
    print("Trace complete!")


def example_rag_agent():
    """RAG agent with full instrumentation."""
    tracer = Tracer(service_name="rag-agent")
    tracer.add_exporter(ConsoleExporter(pretty=True))
    
    with tracer.trace("rag_query", agent_name="knowledge_bot"):
        # Step 1: Retrieval
        retrievals = [
            RetrievalResult(
                query="machine learning",
                source="ml_textbook.pdf",
                content="Machine learning is a subset of AI...",
                score=0.95,
                rank=0,
            ),
            RetrievalResult(
                query="machine learning",
                source="wiki_ml",
                content="ML algorithms build models based on sample data...",
                score=0.87,
                rank=1,
            ),
        ]
        
        tracer.record_retrieval(
            query="machine learning",
            results=retrievals,
            latency_ms=150,
        )
        
        # Step 2: LLM generation
        context = "\n".join([r.content for r in retrievals])
        tracer.record_llm_call(
            prompt=f"Context: {context}\nQuestion: What is machine learning?",
            completion="Machine learning is a method of data analysis...",
            model_metadata=ModelMetadata(
                model_name="qwen3-32b",
                provider="ollama",
            ),
            token_usage=TokenUsage(prompt_tokens=150, completion_tokens=80),
            latency_ms=2100,
        )
    
    print("RAG trace complete!")


def example_reflection_loop():
    """Agent with reflection loop."""
    tracer = Tracer(service_name="reflective-agent")
    tracer.add_exporter(ConsoleExporter(pretty=True))
    
    with tracer.trace("complex_task", agent_name="planner"):
        # Initial attempt
        tracer.record_llm_call(
            prompt="Plan a trip to Japan",
            completion="Day 1: Tokyo, Day 2: Kyoto...",
            model_metadata=ModelMetadata(model_name="gpt-4", provider="openai"),
            latency_ms=3000,
        )
        
        # Reflection 1: Detect issue
        tracer.record_reflection(
            iteration=1,
            reflection_type="verification",
            input_context="Plan has budget issues",
            output_decision="Need to reduce costs",
            confidence=0.7,
            triggered_retry=True,
        )
        
        # Retry with correction
        tracer.record_llm_call(
            prompt="Plan a budget trip to Japan under $2000",
            completion="Day 1: Tokyo (hostel), Day 2: Kyoto (bus)...",
            model_metadata=ModelMetadata(model_name="gpt-4", provider="openai"),
            latency_ms=3500,
        )
        
        # Reflection 2: Verify improvement
        tracer.record_reflection(
            iteration=2,
            reflection_type="verification",
            input_context="Budget plan check",
            output_decision="Within budget, proceed",
            confidence=0.92,
            triggered_retry=False,
        )
    
    print("Reflection trace complete!")


class ConsoleExporter:
    """Simple console exporter for example."""
    
    def __init__(self, pretty=True):
        self.pretty = pretty
    
    def export(self, trace):
        from reliability_sdk.exporters.otel import ConsoleExporter as RealExporter
        exporter = RealExporter(pretty=self.pretty)
        exporter.export(trace)


if __name__ == "__main__":
    print("=" * 60)
    print("Example 1: Basic Tracing")
    print("=" * 60)
    example_basic_tracing()
    
    print("\n" + "=" * 60)
    print("Example 2: RAG Agent")
    print("=" * 60)
    example_rag_agent()
    
    print("\n" + "=" * 60)
    print("Example 3: Reflection Loop")
    print("=" * 60)
    example_reflection_loop()
