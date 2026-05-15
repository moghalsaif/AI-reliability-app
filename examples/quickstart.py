"""Quick Start: Instrument a simple RAG agent with AI Reliability Lab.

This script shows exactly how to use the SDK to instrument a real agent.
Run this to see the full pipeline in action.
"""

from reliability_sdk import Tracer, ConsoleExporter, HTTPExporter
from reliability_shared.types.core import (
    ModelMetadata, TokenUsage, RetrievalResult, ReflectionEvent, MemoryOperation
)


def mock_retrieve(query: str):
    """Mock retrieval function."""
    return [
        {"source": "kb_001", "content": f"Info about {query}", "score": 0.95},
        {"source": "kb_002", "content": f"More about {query}", "score": 0.82},
    ]


def mock_llm_call(prompt: str):
    """Mock LLM call."""
    return {
        "completion": f"Answer based on: {prompt[:50]}...",
        "tokens": {"prompt": len(prompt.split()), "completion": 20},
        "model": "gpt-4",
    }


def mock_tool_call(name: str, params: dict):
    """Mock tool execution."""
    return {"status": "success", "result": f"{name} executed"}


def main():
    print("=" * 70)
    print("AI RELIABILITY LAB — QUICK START")
    print("=" * 70)
    print()
    print("This script demonstrates how to instrument a RAG agent.")
    print()

    # Step 1: Create a tracer
    tracer = Tracer(service_name="quickstart-agent")
    
    # Add console exporter (see traces in terminal)
    tracer.add_exporter(ConsoleExporter(pretty=True))
    
    # Optionally add HTTP exporter to send to API
    # tracer.add_exporter(HTTPExporter(endpoint="http://localhost:8000/v1/traces"))

    # Step 2: Define the agent
    def my_rag_agent(query: str):
        """A simple RAG agent with reflection."""
        
        # 2a. Read from memory
        tracer.record_memory_op(
            op_type="read",
            key="user_preferences",
            value={"tier": "premium", "language": "en"},
            namespace="profile",
        )
        
        # 2b. Retrieve relevant documents
        docs = mock_retrieve(query)
        tracer.record_retrieval(
            query=query,
            results=[
                RetrievalResult(
                    query=query,
                    source=doc["source"],
                    content=doc["content"],
                    score=doc["score"],
                    rank=i,
                )
                for i, doc in enumerate(docs)
            ],
            latency_ms=145,
        )
        
        # 2c. Generate response with LLM
        context = "\n".join(d["content"] for d in docs)
        prompt = f"Query: {query}\nContext: {context}"
        llm_result = mock_llm_call(prompt)
        
        tracer.record_llm_call(
            prompt=prompt,
            completion=llm_result["completion"],
            model_metadata=ModelMetadata(
                model_name=llm_result["model"],
                provider="openai",
                temperature=0.7,
            ),
            token_usage=TokenUsage(
                prompt_tokens=llm_result["tokens"]["prompt"],
                completion_tokens=llm_result["tokens"]["completion"],
            ),
            latency_ms=1200,
        )
        
        # 2d. Reflection loop (self-correction)
        tracer.record_reflection(
            iteration=1,
            reflection_type="verification",
            input_context="Check if answer is grounded in context",
            output_decision="Answer is supported by retrieved docs",
            confidence=0.91,
            triggered_retry=False,
        )
        
        # 2e. Tool call (e.g., log interaction)
        tracer.record_tool_call(
            tool_name="log_interaction",
            parameters={"query": query, "response": llm_result["completion"]},
            result={"logged": True},
            latency_ms=50,
        )
        
        # 2f. Write to memory
        tracer.record_memory_op(
            op_type="write",
            key="last_query",
            value=query,
            namespace="session",
        )
        
        return llm_result["completion"]

    # Step 3: Run the agent inside a trace
    print("Running agent with tracing enabled...")
    print()
    
    with tracer.trace("user_query", agent_name="rag_bot", user_id="user-123"):
        answer = my_rag_agent("What is machine learning?")
    
    print()
    print("=" * 70)
    print("AGENT COMPLETE")
    print("=" * 70)
    print()
    print(f"Answer: {answer}")
    print()
    print("The trace above contains:")
    print("  - Memory reads/writes")
    print("  - Document retrieval with scores")
    print("  - LLM call with tokens and latency")
    print("  - Reflection/verification step")
    print("  - Tool call with parameters and result")
    print()
    print("This trace is automatically sent to:")
    print("  - Console (pretty-printed above)")
    print("  - API (if HTTP exporter configured)")
    print("  - OpenTelemetry (if OTLP exporter configured)")
    print()
    print("Next steps:")
    print("  1. Start the API: cd apps/api && uvicorn src.main:app --reload")
    print("  2. Start the dashboard: cd apps/dashboard && npm run dev")
    print("  3. View traces at http://localhost:3000")
    print("  4. Run evaluators: python cli.py eval --trace-file trace.json")
    print()


if __name__ == "__main__":
    main()
