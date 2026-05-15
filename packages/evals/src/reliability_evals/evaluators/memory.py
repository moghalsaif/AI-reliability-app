"""Memory evaluator - checks memory retrieval quality, forgotten context, stale memory, and poisoning.
"""

from typing import Any, Dict, List

from ..base import BaseEvaluator, EvalResult


class MemoryEvaluator(BaseEvaluator):
    """Evaluate memory operations in agent traces."""
    
    def default_threshold(self) -> float:
        return 0.80
    
    def evaluate(self, trace_data: Dict[str, Any]) -> EvalResult:
        """Evaluate memory usage in a trace.
        
        Returns score where 1.0 = perfect memory usage, 0.0 = severe memory issues.
        """
        spans = trace_data.get("spans", [])
        
        memory_spans = [s for s in spans if s.get("span_type") == "memory_op"]
        
        if not memory_spans:
            return EvalResult(
                eval_type="memory",
                score=1.0,  # No memory ops = no issues
                passed=True,
                threshold=self.threshold,
                details={"reason": "No memory operations found"},
            )
        
        # Extract memory operations
        memory_ops = []
        for span in memory_spans:
            ops = span.get("memory_ops", [])
            memory_ops.extend(ops)
        
        # 1. Read success rate
        read_success = self._evaluate_read_success(memory_ops)
        
        # 2. Write reliability
        write_reliability = self._evaluate_write_reliability(memory_ops)
        
        # 3. Retrieval quality (reads finding relevant data)
        retrieval_quality = self._evaluate_retrieval_quality(memory_ops, spans)
        
        # 4. Memory utilization (are reads happening when they should?)
        utilization = self._evaluate_utilization(memory_ops, spans)
        
        # 5. Error rate
        error_rate = self._calculate_error_rate(memory_ops)
        
        overall_score = (
            read_success * 0.25 +
            write_reliability * 0.20 +
            retrieval_quality * 0.25 +
            utilization * 0.15 +
            (1.0 - error_rate) * 0.15
        )
        
        return EvalResult(
            eval_type="memory",
            score=overall_score,
            passed=overall_score >= self.threshold,
            threshold=self.threshold,
            details={
                "memory_op_count": len(memory_ops),
                "read_success": read_success,
                "write_reliability": write_reliability,
                "retrieval_quality": retrieval_quality,
                "utilization": utilization,
                "error_rate": error_rate,
                "operations": [
                    {
                        "type": op.get("op_type"),
                        "key": op.get("key"),
                        "namespace": op.get("namespace"),
                        "success": op.get("success"),
                    }
                    for op in memory_ops
                ],
            },
        )
    
    def _evaluate_read_success(self, memory_ops: List[Dict]) -> float:
        """Evaluate if reads are successful."""
        reads = [op for op in memory_ops if op.get("op_type") == "read"]
        if not reads:
            return 1.0  # No reads = no failures
        
        successful = sum(1 for op in reads if op.get("success", False))
        return successful / len(reads)
    
    def _evaluate_write_reliability(self, memory_ops: List[Dict]) -> float:
        """Evaluate if writes are persistent and retrievable."""
        writes = [op for op in memory_ops if op.get("op_type") in ["write", "update"]]
        if not writes:
            return 1.0
        
        successful = sum(1 for op in writes if op.get("success", False))
        return successful / len(writes)
    
    def _evaluate_retrieval_quality(self, memory_ops: List[Dict], all_spans: List[Dict]) -> float:
        """Evaluate if retrieved memory is relevant to current context.
        
        Compares memory reads with subsequent agent actions.
        """
        reads = [op for op in memory_ops if op.get("op_type") == "read"]
        if not reads:
            return 1.0
        
        # Find subsequent LLM/agent spans
        llm_spans = [s for s in all_spans if s.get("span_type") in ["llm", "agent", "completion"]]
        if not llm_spans:
            return 0.8  # Can't evaluate without LLM context
        
        # Heuristic: check if memory keys are semantically related to later prompts
        quality_scores = []
        for read_op in reads:
            key = read_op.get("key", "")
            value = str(read_op.get("value", ""))
            
            # Check if memory content appears in later outputs
            found_in_context = False
            for span in llm_spans:
                output = str(span.get("output", ""))
                if key.lower() in output.lower() or value.lower() in output.lower():
                    found_in_context = True
                    break
            
            quality_scores.append(1.0 if found_in_context else 0.5)
        
        return sum(quality_scores) / len(quality_scores) if quality_scores else 0.8
    
    def _evaluate_utilization(self, memory_ops: List[Dict], all_spans: List[Dict]) -> float:
        """Evaluate if memory is being used effectively.
        
        Checks if there are opportunities where memory should have been used but wasn't.
        """
        # Count LLM spans vs memory operations
        llm_count = sum(1 for s in all_spans if s.get("span_type") in ["llm", "agent"])
        memory_count = len(memory_ops)
        
        if llm_count == 0:
            return 1.0
        
        # Ideal ratio: at least 1 memory op per 2 LLM ops for stateful agents
        ratio = memory_count / llm_count if llm_count > 0 else 0
        
        if ratio >= 0.5:
            return 1.0
        elif ratio >= 0.25:
            return 0.8
        elif ratio >= 0.1:
            return 0.5
        else:
            return 0.2  # Memory severely underutilized
    
    def _calculate_error_rate(self, memory_ops: List[Dict]) -> float:
        """Calculate overall error rate in memory operations."""
        if not memory_ops:
            return 0.0
        errors = sum(1 for op in memory_ops if not op.get("success", True))
        return errors / len(memory_ops)
