"""Integration wrappers for popular AI frameworks.

Supports:
- LangGraph
- OpenAI SDK
- LiteLLM
- Ollama
- CrewAI
- AutoGen
"""

from __future__ import annotations

import functools
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar, cast

from reliability_shared.types.core import (
    ModelMetadata,
    TokenUsage,
    Span,
    SpanType,
)
from reliability_shared.utils import generate_span_id
from ..core.tracer import Tracer, TraceContext


F = TypeVar("F", bound=Callable[..., Any])


def instrument_llm(
    tracer: Optional[Tracer] = None,
    model_name: Optional[str] = None,
    provider: Optional[str] = None,
) -> Callable[[F], F]:
    """Decorator to instrument LLM calls.
    
    Usage:
        @instrument_llm(model_name="gpt-4", provider="openai")
        def my_llm_call(prompt):
            return openai_client.chat.completions.create(...)
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            active_tracer = tracer or _get_default_tracer()
            if not active_tracer:
                return func(*args, **kwargs)
            
            # Extract prompt from args/kwargs
            prompt = _extract_prompt(args, kwargs)
            
            meta = ModelMetadata(
                model_name=model_name or kwargs.get("model", "unknown"),
                provider=provider or "unknown",
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens"),
            )
            
            start = time.time()
            try:
                result = func(*args, **kwargs)
                latency = (time.time() - start) * 1000
                
                # Extract token usage from common response formats
                token_usage = _extract_token_usage(result)
                
                active_tracer.record_llm_call(
                    prompt=prompt,
                    completion=_extract_completion(result),
                    model_metadata=meta,
                    token_usage=token_usage,
                    latency_ms=latency,
                )
                
                return result
            except Exception as e:
                latency = (time.time() - start) * 1000
                span = active_tracer.record_llm_call(
                    prompt=prompt,
                    completion=None,
                    model_metadata=meta,
                    latency_ms=latency,
                )
                span.status = SpanType.LLM  # Mark as error
                raise
        
        return cast(F, wrapper)
    return decorator


def instrument_tool(
    tracer: Optional[Tracer] = None,
    tool_name: Optional[str] = None,
) -> Callable[[F], F]:
    """Decorator to instrument tool/function calls."""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            active_tracer = tracer or _get_default_tracer()
            if not active_tracer:
                return func(*args, **kwargs)
            
            name = tool_name or func.__name__
            start = time.time()
            retry_count = 0  # TODO: detect retries
            
            try:
                result = func(*args, **kwargs)
                latency = (time.time() - start) * 1000
                
                active_tracer.record_tool_call(
                    tool_name=name,
                    parameters=_args_to_dict(args, kwargs, func),
                    result=result,
                    latency_ms=latency,
                    retry_count=retry_count,
                )
                
                return result
            except Exception as e:
                latency = (time.time() - start) * 1000
                active_tracer.record_tool_call(
                    tool_name=name,
                    parameters=_args_to_dict(args, kwargs, func),
                    error=str(e),
                    latency_ms=latency,
                    retry_count=retry_count,
                )
                raise
        
        return cast(F, wrapper)
    return decorator


def instrument_retrieval(
    tracer: Optional[Tracer] = None,
) -> Callable[[F], F]:
    """Decorator to instrument retrieval operations."""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(query: str, *args: Any, **kwargs: Any) -> Any:
            active_tracer = tracer or _get_default_tracer()
            if not active_tracer:
                return func(query, *args, **kwargs)
            
            start = time.time()
            result = func(query, *args, **kwargs)
            latency = (time.time() - start) * 1000
            
            # Convert result to RetrievalResult objects
            retrievals = _convert_to_retrievals(result, query)
            
            active_tracer.record_retrieval(
                query=query,
                results=retrievals,
                latency_ms=latency,
            )
            
            return result
        
        return cast(F, wrapper)
    return decorator


class LangGraphIntegration:
    """Integration with LangGraph workflows."""
    
    def __init__(self, tracer: Tracer):
        self.tracer = tracer
    
    def instrument_graph(self, graph: Any) -> Any:
        """Instrument a LangGraph workflow.
        
        Usage:
            integration = LangGraphIntegration(tracer)
            instrumented_graph = integration.instrument_graph(my_graph)
        """
        # LangGraph nodes are functions
        # We wrap each node to create spans
        if hasattr(graph, "nodes"):
            for node_name, node_func in graph.nodes.items():
                graph.nodes[node_name] = self._wrap_node(node_name, node_func)
        
        # Also wrap the graph.invoke method
        original_invoke = graph.invoke
        
        @functools.wraps(original_invoke)
        def wrapped_invoke(state: Any, *args: Any, **kwargs: Any) -> Any:
            with self.tracer.trace(
                name=f"langgraph.{graph.name if hasattr(graph, 'name') else 'workflow'}",
                agent_name="langgraph",
                graph_type="langgraph",
            ):
                return original_invoke(state, *args, **kwargs)
        
        graph.invoke = wrapped_invoke
        return graph
    
    def _wrap_node(self, node_name: str, node_func: Callable) -> Callable:
        @functools.wraps(node_func)
        def wrapper(state: Any, *args: Any, **kwargs: Any) -> Any:
            builder = TraceContext.current_span()
            if builder is None:
                return node_func(state, *args, **kwargs)
            
            # Start a span for this node
            from reliability_shared.types.core import SpanType
            span = builder.start_span(
                name=f"node.{node_name}",
                span_type=SpanType.AGENT,
                input=state,
            )
            
            try:
                result = node_func(state, *args, **kwargs)
                builder.end_span(span, output=result)
                return result
            except Exception as e:
                builder.end_span(span, error=e)
                raise
        
        return wrapper


class OpenAIIntegration:
    """Integration with OpenAI SDK."""
    
    def __init__(self, tracer: Tracer):
        self.tracer = tracer
    
    def instrument_client(self, client: Any) -> Any:
        """Instrument an OpenAI client.
        
        Usage:
            integration = OpenAIIntegration(tracer)
            instrumented_client = integration.instrument_client(openai_client)
        """
        original_chat_completions_create = client.chat.completions.create
        
        @functools.wraps(original_chat_completions_create)
        def wrapped_create(*args: Any, **kwargs: Any) -> Any:
            prompt = _extract_messages(kwargs.get("messages", []))
            model = kwargs.get("model", "unknown")
            
            meta = ModelMetadata(
                model_name=model,
                provider="openai",
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens"),
            )
            
            start = time.time()
            try:
                response = original_chat_completions_create(*args, **kwargs)
                latency = (time.time() - start) * 1000
                
                token_usage = None
                if hasattr(response, "usage"):
                    token_usage = TokenUsage(
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        total_tokens=response.usage.total_tokens,
                    )
                
                self.tracer.record_llm_call(
                    prompt=prompt,
                    completion=_extract_completion(response),
                    model_metadata=meta,
                    token_usage=token_usage,
                    latency_ms=latency,
                )
                
                return response
            except Exception as e:
                latency = (time.time() - start) * 1000
                span = self.tracer.record_llm_call(
                    prompt=prompt,
                    completion=None,
                    model_metadata=meta,
                    latency_ms=latency,
                )
                span.attributes["error.type"] = type(e).__name__
                span.attributes["error.message"] = str(e)
                raise
        
        client.chat.completions.create = wrapped_create
        return client


class LiteLLMIntegration:
    """Integration with LiteLLM."""
    
    def __init__(self, tracer: Tracer):
        self.tracer = tracer
    
    def instrument(self) -> None:
        """Instrument LiteLLM completion/chat_completion calls."""
        try:
            import litellm
            original_completion = litellm.completion
            
            @functools.wraps(original_completion)
            def wrapped_completion(*args: Any, **kwargs: Any) -> Any:
                model = kwargs.get("model", "unknown")
                messages = kwargs.get("messages", [])
                
                meta = ModelMetadata(
                    model_name=model,
                    provider=kwargs.get("custom_llm_provider", "litellm"),
                    temperature=kwargs.get("temperature", 0.7),
                )
                
                start = time.time()
                response = original_completion(*args, **kwargs)
                latency = (time.time() - start) * 1000
                
                token_usage = None
                if hasattr(response, "usage"):
                    token_usage = TokenUsage(
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        total_tokens=response.usage.total_tokens,
                    )
                
                self.tracer.record_llm_call(
                    prompt=messages,
                    completion=response.choices[0].message.content if response.choices else None,
                    model_metadata=meta,
                    token_usage=token_usage,
                    latency_ms=latency,
                )
                
                return response
            
            litellm.completion = wrapped_completion
            
        except ImportError:
            pass


# Helper functions

def _get_default_tracer() -> Optional[Tracer]:
    """Get the currently active tracer from context."""
    trace = TraceContext.current_trace()
    if trace:
        # Create a temporary tracer bound to the current trace
        tracer = Tracer()
        return tracer
    return None


def _extract_prompt(args: tuple, kwargs: dict) -> Any:
    """Extract prompt from function arguments."""
    if args:
        return args[0]
    return kwargs.get("prompt", kwargs.get("messages", kwargs.get("input", None)))


def _extract_completion(response: Any) -> Any:
    """Extract completion from response."""
    if hasattr(response, "choices") and response.choices:
        return response.choices[0].message.content if hasattr(response.choices[0], "message") else response.choices[0].text
    if hasattr(response, "content"):
        return response.content
    return response


def _extract_token_usage(response: Any) -> Optional[TokenUsage]:
    """Extract token usage from response."""
    if hasattr(response, "usage") and response.usage:
        return TokenUsage(
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
        )
    return None


def _extract_messages(messages: List[Any]) -> List[Dict[str, Any]]:
    """Convert messages to serializable format."""
    result = []
    for msg in messages:
        if isinstance(msg, dict):
            result.append(msg)
        elif hasattr(msg, "model_dump"):
            result.append(msg.model_dump())
        elif hasattr(msg, "role") and hasattr(msg, "content"):
            result.append({"role": msg.role, "content": msg.content})
    return result


def _args_to_dict(args: tuple, kwargs: dict, func: Callable) -> Dict[str, Any]:
    """Convert function arguments to a serializable dictionary."""
    import inspect
    sig = inspect.signature(func)
    params = list(sig.parameters.keys())
    
    result = {}
    for i, arg in enumerate(args):
        if i < len(params):
            result[params[i]] = arg
    result.update(kwargs)
    
    # Sanitize - remove non-serializable objects
    cleaned = {}
    for k, v in result.items():
        try:
            import json
            json.dumps(v)
            cleaned[k] = v
        except (TypeError, ValueError):
            cleaned[k] = str(v)
    return cleaned


def _convert_to_retrievals(result: Any, query: str) -> List[Any]:
    """Convert raw retrieval result to RetrievalResult objects."""
    from reliability_shared.types.core import RetrievalResult
    
    retrievals = []
    if isinstance(result, list):
        for i, item in enumerate(result):
            if isinstance(item, dict):
                retrievals.append(RetrievalResult(
                    query=query,
                    source=item.get("source", item.get("metadata", {}).get("source", "unknown")),
                    content=str(item.get("content", item.get("text", ""))),
                    score=item.get("score", 0.0),
                    rank=i,
                ))
            else:
                retrievals.append(RetrievalResult(
                    query=query,
                    source="unknown",
                    content=str(item),
                    score=0.0,
                    rank=i,
                ))
    return retrievals
