"""Example: Instrumenting OpenAI SDK with Reliability SDK."""

from reliability_sdk import Tracer, OpenAIIntegration, ConsoleExporter
from reliability_shared.types.core import ModelMetadata


def example_openai_integration():
    """Example of instrumenting OpenAI client."""
    print("=" * 60)
    print("OpenAI SDK Integration Example")
    print("=" * 60)

    try:
        import openai
    except ImportError:
        print("OpenAI SDK not installed. Install with: pip install openai")
        print("This example shows how the integration would work.")
        return

    tracer = Tracer(service_name="openai-agent")
    tracer.add_exporter(ConsoleExporter(pretty=True))

    # Create and instrument client
    client = openai.OpenAI()
    integration = OpenAIIntegration(tracer)
    instrumented_client = integration.instrument_client(client)

    # Now all chat.completions.create calls are traced
    with tracer.trace("customer_support", agent_name="support_bot"):
        response = instrumented_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is machine learning?"},
            ],
            temperature=0.7,
        )
        print(f"Response: {response.choices[0].message.content}")


def example_litellm_integration():
    """Example of instrumenting LiteLLM."""
    print("\n" + "=" * 60)
    print("LiteLLM Integration Example")
    print("=" * 60)

    try:
        import litellm
    except ImportError:
        print("LiteLLM not installed. Install with: pip install litellm")
        return

    tracer = Tracer(service_name="litellm-agent")
    tracer.add_exporter(ConsoleExporter(pretty=True))

    from reliability_sdk import LiteLLMIntegration
    LiteLLMIntegration(tracer).instrument()

    # Now litellm.completion calls are traced
    with tracer.trace("query", agent_name="qa_bot"):
        response = litellm.completion(
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}],
        )
        print(f"Response: {response.choices[0].message.content}")


def example_langgraph_integration():
    """Example of instrumenting LangGraph."""
    print("\n" + "=" * 60)
    print("LangGraph Integration Example")
    print("=" * 60)

    try:
        from langgraph.graph import StateGraph
    except ImportError:
        print("LangGraph not installed. Install with: pip install langgraph")
        return

    tracer = Tracer(service_name="langgraph-agent")
    tracer.add_exporter(ConsoleExporter(pretty=True))

    from reliability_sdk import LangGraphIntegration

    # Define a simple graph
    builder = StateGraph(dict)

    def node_a(state):
        return {"result": "step_a"}

    def node_b(state):
        return {"result": "step_b"}

    builder.add_node("a", node_a)
    builder.add_node("b", node_b)
    builder.add_edge("a", "b")
    builder.set_entry_point("a")

    graph = builder.compile()

    # Instrument the graph
    integration = LangGraphIntegration(tracer)
    instrumented_graph = integration.instrument_graph(graph)

    # Run
    with tracer.trace("langgraph_workflow"):
        result = instrumented_graph.invoke({"input": "hello"})
        print(f"Result: {result}")


if __name__ == "__main__":
    example_openai_integration()
    example_litellm_integration()
    example_langgraph_integration()
