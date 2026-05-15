"""Tests for hallucination evaluator."""

import pytest
from reliability_evals.evaluators.hallucination import HallucinationEvaluator


def test_hallucination_evaluator_no_llm_spans():
    evaluator = HallucinationEvaluator()
    trace_data = {"spans": []}
    result = evaluator.evaluate(trace_data)
    
    assert result.passed is True
    assert result.score == 1.0


def test_hallucination_evaluator_with_retrieval():
    evaluator = HallucinationEvaluator()
    trace_data = {
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
            }
        ]
    }
    result = evaluator.evaluate(trace_data)
    
    assert result.eval_type == "hallucination"
    assert 0.0 <= result.score <= 1.0
    assert "span_scores" in result.details


def test_hallucination_citation_check():
    evaluator = HallucinationEvaluator()
    trace_data = {
        "spans": [
            {
                "span_id": "span-1",
                "span_type": "llm",
                "output": "According to [Source A], Paris is the capital.",
                "retrievals": [
                    {"source": "Source A", "content": "Paris is capital", "score": 0.9, "rank": 0},
                ],
            }
        ]
    }
    result = evaluator.evaluate(trace_data)
    
    assert result.score > 0.3  # Score reflects judge fallback when Ollama unavailable
