"""Tool use evaluator - checks correct tool selection, parameter validity, and redundant retries.

VERY important for agent reliability.
"""

from typing import Any, Dict, List

from ..base import BaseEvaluator, EvalResult


class ToolUseEvaluator(BaseEvaluator):
    """Evaluate tool use quality in agent traces."""
    
    def default_threshold(self) -> float:
        return 0.90  # Tool use should be highly accurate
    
    def evaluate(self, trace_data: Dict[str, Any]) -> EvalResult:
        """Evaluate tool usage in a trace.
        
        Returns score where 1.0 = perfect tool use, 0.0 = completely broken.
        """
        spans = trace_data.get("spans", [])
        
        tool_scores = []
        tool_details = []
        
        for span in spans:
            if span.get("span_type") == "tool_call":
                tool_calls = span.get("tool_calls", [])
                
                for tool_call in tool_calls:
                    tool_name = tool_call.get("tool_name", "")
                    parameters = tool_call.get("parameters", {})
                    error = tool_call.get("error")
                    retry_count = tool_call.get("retry_count", 0)
                    latency_ms = tool_call.get("latency_ms", 0)
                    
                    # 1. Error rate
                    error_score = 0.0 if error else 1.0
                    
                    # 2. Retry efficiency (penalize excessive retries)
                    retry_score = max(0.0, 1.0 - (retry_count * 0.25))
                    
                    # 3. Parameter validity
                    param_score = self._evaluate_parameters(tool_name, parameters)
                    
                    # 4. Tool selection appropriateness
                    context = span.get("input", "")
                    selection_score = self._evaluate_tool_selection(context, tool_name)
                    
                    # Combine scores
                    combined = (
                        error_score * 0.4 +
                        retry_score * 0.2 +
                        param_score * 0.2 +
                        selection_score * 0.2
                    )
                    
                    tool_scores.append(combined)
                    tool_details.append({
                        "tool_name": tool_name,
                        "error": error is not None,
                        "retry_count": retry_count,
                        "latency_ms": latency_ms,
                        "error_score": error_score,
                        "retry_score": retry_score,
                        "param_score": param_score,
                        "selection_score": selection_score,
                        "combined": combined,
                    })
        
        if not tool_scores:
            return EvalResult(
                eval_type="tool_use",
                score=1.0,  # No tools used = no errors
                passed=True,
                threshold=self.threshold,
                details={"reason": "No tool calls found"},
            )
        
        # Overall: average, but heavily penalize errors
        avg_score = sum(tool_scores) / len(tool_scores)
        error_rate = sum(1 for d in tool_details if d["error"]) / len(tool_details)
        
        # If any tool completely failed, heavily penalize
        if error_rate > 0.2:
            avg_score *= (1.0 - error_rate)
        
        return EvalResult(
            eval_type="tool_use",
            score=avg_score,
            passed=avg_score >= self.threshold,
            threshold=self.threshold,
            details={
                "tool_count": len(tool_scores),
                "error_rate": error_rate,
                "avg_retries": sum(d["retry_count"] for d in tool_details) / len(tool_details),
                "avg_latency_ms": sum(d["latency_ms"] for d in tool_details) / len(tool_details),
                "tools": tool_details,
            },
        )
    
    def _evaluate_parameters(self, tool_name: str, parameters: Dict) -> float:
        """Evaluate parameter validity for a tool call.
        
        Basic heuristics - can be extended with tool schemas.
        """
        if not parameters:
            return 0.5  # Neutral if no params
        
        score = 1.0
        
        # Check for empty required-looking params
        for key, value in parameters.items():
            if value is None or value == "" or value == []:
                # Penalize empty values (might be valid, but suspicious)
                score -= 0.1
            
            # Check for obviously wrong types
            if key.endswith("_id") and not isinstance(value, (str, int)):
                score -= 0.2
            
            if key.endswith("_count") and not isinstance(value, int):
                score -= 0.2
        
        return max(0.0, score)
    
    def _evaluate_tool_selection(self, context: str, tool_name: str) -> float:
        """Evaluate if the right tool was selected for the context.
        
        Uses simple heuristic matching - can be enhanced with LLM judge.
        """
        if not context:
            return 0.8  # Give benefit of doubt
        
        context_lower = str(context).lower()
        tool_lower = tool_name.lower()
        
        # Simple keyword matching
        keyword_map = {
            "search": ["find", "look", "search", "where", "what is", "information"],
            "calculate": ["compute", "math", "sum", "total", "count", "calculate"],
            "fetch": ["get", "retrieve", "download", "pull"],
            "write": ["save", "store", "write", "create", "update"],
            "send": ["email", "message", "notify", "alert", "send"],
        }
        
        for category, keywords in keyword_map.items():
            if category in tool_lower:
                matches = sum(1 for kw in keywords if kw in context_lower)
                if matches > 0:
                    return min(0.8 + (matches * 0.1), 1.0)
                else:
                    return 0.5  # Tool selected but no matching keywords
        
        return 0.8  # Unknown tool - neutral score
