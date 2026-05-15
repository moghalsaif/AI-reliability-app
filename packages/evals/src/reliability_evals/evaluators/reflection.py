"""Reflection loop evaluator - YOUR DIFFERENTIATOR.

Measures:
- retry count
- self-correction improvement
- oscillation
- indecision
- loop collapse

This is frontier-level evaluation.
"""

from typing import Any, Dict, List

from ..base import BaseEvaluator, EvalResult


class ReflectionEvaluator(BaseEvaluator):
    """Evaluate reflection and reasoning loop quality.
    
    This is a key differentiator for the AI Reliability Lab.
    """
    
    def default_threshold(self) -> float:
        return 0.70
    
    def evaluate(self, trace_data: Dict[str, Any]) -> EvalResult:
        """Evaluate reflection loops in a trace.
        
        Returns score where 1.0 = healthy reflection, 0.0 = pathological looping.
        """
        spans = trace_data.get("spans", [])
        
        reflection_spans = [s for s in spans if s.get("span_type") == "reflection"]
        
        if not reflection_spans:
            return EvalResult(
                eval_type="reflection",
                score=1.0,  # No reflections = no problems
                passed=True,
                threshold=self.threshold,
                details={"reason": "No reflection spans found"},
            )
        
        # Extract reflection events
        reflections = []
        for span in reflection_spans:
            refl_events = span.get("reflections", [])
            reflections.extend(refl_events)
        
        # 1. Retry density (how many retries per unit of work)
        retry_density = self._calculate_retry_density(reflections, spans)
        
        # 2. Self-correction improvement (did later iterations get better?)
        improvement_score = self._evaluate_improvement(reflections)
        
        # 3. Oscillation detection (flip-flopping between states)
        oscillation_score = self._detect_oscillation(reflections)
        
        # 4. Indecision (high iterations without progress)
        indecision_score = self._detect_indecision(reflections)
        
        # 5. Loop collapse (infinite loop detection)
        collapse_score = self._detect_loop_collapse(reflections)
        
        # Combine metrics
        # Higher score = better
        overall_score = (
            (1.0 - retry_density) * 0.2 +  # Lower retry density is better
            improvement_score * 0.25 +
            oscillation_score * 0.2 +
            indecision_score * 0.15 +
            collapse_score * 0.2
        )
        
        return EvalResult(
            eval_type="reflection",
            score=overall_score,
            passed=overall_score >= self.threshold,
            threshold=self.threshold,
            details={
                "reflection_count": len(reflections),
                "retry_density": retry_density,
                "improvement_score": improvement_score,
                "oscillation_score": oscillation_score,
                "indecision_score": indecision_score,
                "collapse_score": collapse_score,
                "reflections": [
                    {
                        "iteration": r.get("iteration"),
                        "type": r.get("reflection_type"),
                        "confidence": r.get("confidence"),
                        "triggered_retry": r.get("triggered_retry"),
                    }
                    for r in reflections
                ],
            },
        )
    
    def _calculate_retry_density(self, reflections: List[Dict], all_spans: List[Dict]) -> float:
        """Calculate how dense retries are in the trace.
        
        Returns 0.0 (no retries) to 1.0 (every span triggers retry).
        """
        retry_count = sum(1 for r in reflections if r.get("triggered_retry", False))
        total_spans = len(all_spans)
        
        if total_spans == 0:
            return 0.0
        
        return min(retry_count / total_spans, 1.0)
    
    def _evaluate_improvement(self, reflections: List[Dict]) -> float:
        """Evaluate if reflection iterations show improvement.
        
        Looks for increasing confidence or decreasing retries.
        """
        if len(reflections) < 2:
            return 1.0  # Single reflection = no issue
        
        # Sort by iteration
        sorted_refl = sorted(reflections, key=lambda r: r.get("iteration", 0))
        
        # Check confidence trend
        confidences = [r.get("confidence", 0.5) for r in sorted_refl]
        
        if len(confidences) < 2:
            return 0.8
        
        # Linear regression on confidence
        n = len(confidences)
        x = list(range(n))
        
        mean_x = sum(x) / n
        mean_y = sum(confidences) / n
        
        numerator = sum((x[i] - mean_x) * (confidences[i] - mean_y) for i in range(n))
        denominator = sum((x[i] - mean_x) ** 2 for i in range(n))
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        # Positive slope = improving confidence (good)
        # Map slope to score: -0.5 -> 0.0, 0.0 -> 0.5, +0.5 -> 1.0
        improvement = (slope + 0.5) * 1.0
        return min(max(improvement, 0.0), 1.0)
    
    def _detect_oscillation(self, reflections: List[Dict]) -> float:
        """Detect if reflections are oscillating (flip-flopping).
        
        Returns 1.0 = no oscillation, 0.0 = severe oscillation.
        """
        if len(reflections) < 3:
            return 1.0
        
        # Check for alternating decisions
        sorted_refl = sorted(reflections, key=lambda r: r.get("iteration", 0))
        decisions = [r.get("output_decision", "") for r in sorted_refl]
        
        if not any(d for d in decisions):
            return 1.0
        
        # Count direction changes
        changes = 0
        for i in range(1, len(decisions)):
            if decisions[i] != decisions[i - 1]:
                changes += 1
        
        change_rate = changes / (len(decisions) - 1)
        
        # High change rate = oscillation
        # Map: 0.0 -> 1.0, 0.5 -> 0.5, 1.0 -> 0.0
        stability = 1.0 - change_rate
        return stability
    
    def _detect_indecision(self, reflections: List[Dict]) -> float:
        """Detect indecision (many iterations with low confidence).
        
        Returns 1.0 = decisive, 0.0 = paralyzed by indecision.
        """
        if not reflections:
            return 1.0
        
        # High iteration count with low average confidence = indecision
        avg_confidence = sum(r.get("confidence", 0.5) for r in reflections) / len(reflections)
        iteration_count = max(r.get("iteration", 0) for r in reflections)
        
        # Penalize many iterations with low confidence
        indecision = (1.0 - avg_confidence) * min(iteration_count / 5.0, 1.0)
        
        return max(0.0, 1.0 - indecision)
    
    def _detect_loop_collapse(self, reflections: List[Dict]) -> float:
        """Detect if reflections collapsed into an infinite loop.
        
        Signs: very high iterations, identical decisions, no confidence change.
        
        Returns 1.0 = no collapse, 0.0 = collapsed.
        """
        if len(reflections) < 5:
            return 1.0  # Not enough data
        
        sorted_refl = sorted(reflections, key=lambda r: r.get("iteration", 0))
        
        # Check for identical outputs in later iterations
        decisions = [r.get("output_decision", "") for r in sorted_refl[-5:]]
        confidences = [r.get("confidence", 0.0) for r in sorted_refl[-5:]]
        
        # If last 5 are identical and confidence is flat, likely collapsed
        all_same = len(set(decisions)) == 1
        confidence_variance = self._variance(confidences)
        
        if all_same and confidence_variance < 0.01:
            return 0.1  # Collapsed
        
        # High iteration count is suspicious
        max_iter = max(r.get("iteration", 0) for r in reflections)
        if max_iter > 10:
            return 0.5  # Warning
        
        return 1.0
    
    @staticmethod
    def _variance(values: List[float]) -> float:
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / len(values)
