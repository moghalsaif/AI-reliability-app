"""Base evaluator interface for the AI Reliability Lab."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EvalResult:
    """Result of an evaluation."""
    eval_type: str
    score: float  # 0.0 to 1.0
    passed: bool
    threshold: float
    details: Dict[str, Any] = field(default_factory=dict)
    model_judge: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "eval_type": self.eval_type,
            "score": self.score,
            "passed": self.passed,
            "threshold": self.threshold,
            "details": self.details,
            "model_judge": self.model_judge,
        }


@dataclass
class JudgeConfig:
    """Configuration for LLM judge."""
    model_name: str = "qwen3-32b"
    provider: str = "ollama"  # or openai, litellm
    temperature: float = 0.1  # Low temp for consistency
    max_tokens: int = 2048
    api_key: Optional[str] = None
    api_base: Optional[str] = None


class BaseEvaluator(ABC):
    """Base class for all evaluators."""
    
    def __init__(self, threshold: Optional[float] = None, judge_config: Optional[JudgeConfig] = None):
        self.threshold = threshold or self.default_threshold()
        self.judge_config = judge_config or JudgeConfig()
    
    @abstractmethod
    def default_threshold(self) -> float:
        """Return the default threshold for this evaluator."""
        pass
    
    @abstractmethod
    def evaluate(self, trace_data: Dict[str, Any]) -> EvalResult:
        """Evaluate a trace and return results."""
        pass
    
    def _call_judge(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Call an LLM judge for evaluation.
        
        This uses the configured judge model (default: Qwen3 32B via Ollama).
        """
        import requests
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        if self.judge_config.provider == "ollama":
            response = requests.post(
                f"{self.judge_config.api_base or 'http://localhost:11434'}/api/chat",
                json={
                    "model": self.judge_config.model_name,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": self.judge_config.temperature,
                    },
                },
            )
            result = response.json()
            return result["message"]["content"]
        
        elif self.judge_config.provider == "openai":
            import openai
            client = openai.OpenAI(
                api_key=self.judge_config.api_key,
                base_url=self.judge_config.api_base,
            )
            response = client.chat.completions.create(
                model=self.judge_config.model_name,
                messages=messages,
                temperature=self.judge_config.temperature,
                max_tokens=self.judge_config.max_tokens,
            )
            return response.choices[0].message.content
        
        else:
            # Generic HTTP fallback
            raise ValueError(f"Unsupported provider: {self.judge_config.provider}")
    
    def _parse_judge_score(self, response: str) -> float:
        """Parse a numeric score from judge response."""
        import re
        # Look for score patterns like "Score: 0.85" or "0.85/1.0"
        matches = re.findall(r'(\d+\.?\d*)', response)
        if matches:
            score = float(matches[0])
            # Normalize if it's out of 10 or 100
            if score > 1.0 and score <= 10.0:
                score = score / 10.0
            elif score > 10.0 and score <= 100.0:
                score = score / 100.0
            return min(max(score, 0.0), 1.0)
        return 0.5  # Default if no score found
    
    def _compute_semantic_similarity(self, text1: str, text2: str) -> float:
        """Compute semantic similarity using embeddings.
        
        Uses bge-m3 embedding model.
        """
        try:
            # Try to use sentence-transformers if available
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('BAAI/bge-m3')
            embeddings = model.encode([text1, text2])
            
            import numpy as np
            similarity = np.dot(embeddings[0], embeddings[1]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            )
            return float(similarity)
        except ImportError:
            # Fallback to simple token overlap
            tokens1 = set(text1.lower().split())
            tokens2 = set(text2.lower().split())
            if not tokens1 or not tokens2:
                return 0.0
            intersection = tokens1 & tokens2
            return len(intersection) / max(len(tokens1), len(tokens2))


class CompositeEvaluator(BaseEvaluator):
    """Evaluator that combines multiple sub-evaluators."""
    
    def __init__(self, evaluators: List[BaseEvaluator], aggregation: str = "weighted_avg"):
        self.evaluators = evaluators
        self.aggregation = aggregation
        super().__init__(threshold=0.0)
    
    def default_threshold(self) -> float:
        return 0.7
    
    def evaluate(self, trace_data: Dict[str, Any]) -> EvalResult:
        results = []
        for evaluator in self.evaluators:
            try:
                result = evaluator.evaluate(trace_data)
                results.append(result)
            except Exception as e:
                import logging
                logging.getLogger("reliability_evals").warning(f"Sub-evaluator failed: {e}")
        
        if not results:
            return EvalResult(
                eval_type="composite",
                score=0.0,
                passed=False,
                threshold=self.threshold,
            )
        
        # Aggregate scores
        if self.aggregation == "weighted_avg":
            score = sum(r.score for r in results) / len(results)
        elif self.aggregation == "min":
            score = min(r.score for r in results)
        elif self.aggregation == "product":
            score = 1.0
            for r in results:
                score *= r.score
        else:
            score = sum(r.score for r in results) / len(results)
        
        passed = score >= self.threshold and all(r.passed for r in results)
        
        return EvalResult(
            eval_type="composite",
            score=score,
            passed=passed,
            threshold=self.threshold,
            details={
                "sub_results": [r.to_dict() for r in results],
                "aggregation": self.aggregation,
            },
        )
