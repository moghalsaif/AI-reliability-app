"""Tests for reflection evaluator."""

import pytest
from reliability_evals.evaluators.reflection import ReflectionEvaluator


def test_reflection_evaluator_no_reflections():
    evaluator = ReflectionEvaluator()
    trace_data = {"spans": []}
    result = evaluator.evaluate(trace_data)
    
    assert result.passed is True
    assert result.score == 1.0


def test_reflection_evaluator_oscillation():
    evaluator = ReflectionEvaluator()
    trace_data = {
        "spans": [
            {
                "span_id": "span-1",
                "span_type": "reflection",
                "reflections": [
                    {
                        "iteration": 1,
                        "reflection_type": "verification",
                        "input_context": "check A",
                        "output_decision": "choose A",
                        "confidence": 0.6,
                        "triggered_retry": True,
                    },
                    {
                        "iteration": 2,
                        "reflection_type": "verification",
                        "input_context": "check B",
                        "output_decision": "choose B",
                        "confidence": 0.55,
                        "triggered_retry": True,
                    },
                    {
                        "iteration": 3,
                        "reflection_type": "verification",
                        "input_context": "check A again",
                        "output_decision": "choose A",
                        "confidence": 0.5,
                        "triggered_retry": True,
                    },
                ],
            }
        ]
    }
    result = evaluator.evaluate(trace_data)
    
    assert result.eval_type == "reflection"
    assert result.score < 0.9  # Should detect oscillation
    assert "oscillation_score" in result.details


def test_reflection_evaluator_improvement():
    evaluator = ReflectionEvaluator()
    trace_data = {
        "spans": [
            {
                "span_id": "span-1",
                "span_type": "reflection",
                "reflections": [
                    {
                        "iteration": 1,
                        "reflection_type": "self-correction",
                        "input_context": "error found",
                        "output_decision": "fix attempt 1",
                        "confidence": 0.6,
                        "triggered_retry": True,
                    },
                    {
                        "iteration": 2,
                        "reflection_type": "verification",
                        "input_context": "verify fix",
                        "output_decision": "improved fix",
                        "confidence": 0.85,
                        "triggered_retry": False,
                    },
                ],
            }
        ]
    }
    result = evaluator.evaluate(trace_data)
    
    assert result.score > 0.7  # Good improvement pattern
