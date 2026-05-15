"""RAG evaluator - measures retrieval relevance, context precision, and answer grounding.

Inspired by RAGAS and DeepEval.
"""

from typing import Any, Dict, List

from ..base import BaseEvaluator, EvalResult


class RAGEvaluator(BaseEvaluator):
    """Evaluate RAG (Retrieval-Augmented Generation) quality."""
    
    def default_threshold(self) -> float:
        return 0.70
    
    def evaluate(self, trace_data: Dict[str, Any]) -> EvalResult:
        """Evaluate RAG quality in a trace.
        
        Returns score where 1.0 = perfect RAG, 0.0 = failed RAG.
        """
        spans = trace_data.get("spans", [])
        
        retrieval_scores = []
        context_precision_scores = []
        answer_relevance_scores = []
        
        details = {
            "retrieval_scores": [],
            "context_precision": [],
            "answer_relevance": [],
            "overall_per_query": [],
        }
        
        for span in spans:
            if span.get("span_type") == "retrieval":
                query = span.get("input", "")
                retrievals = span.get("retrievals", [])
                
                if not retrievals:
                    continue
                
                # 1. Retrieval relevance
                relevance = self._evaluate_retrieval_relevance(query, retrievals)
                retrieval_scores.append(relevance)
                
                # 2. Context precision (are top results most relevant?)
                precision = self._evaluate_context_precision(query, retrievals)
                context_precision_scores.append(precision)
                
                # 3. Answer relevance (if there's a subsequent LLM span)
                answer_relevance = self._evaluate_answer_relevance(span, spans)
                if answer_relevance is not None:
                    answer_relevance_scores.append(answer_relevance)
                
                details["retrieval_scores"].append({
                    "query": query[:100],
                    "relevance": relevance,
                    "precision": precision,
                    "num_results": len(retrievals),
                })
        
        if not retrieval_scores:
            return EvalResult(
                eval_type="rag",
                score=0.5,
                passed=False,
                threshold=self.threshold,
                details={"reason": "No retrieval spans found"},
            )
        
        # Combine metrics
        avg_relevance = sum(retrieval_scores) / len(retrieval_scores)
        avg_precision = sum(context_precision_scores) / len(context_precision_scores) if context_precision_scores else 0.5
        avg_answer_relevance = sum(answer_relevance_scores) / len(answer_relevance_scores) if answer_relevance_scores else 0.5
        
        overall_score = (
            avg_relevance * 0.4 +
            avg_precision * 0.3 +
            avg_answer_relevance * 0.3
        )
        
        return EvalResult(
            eval_type="rag",
            score=overall_score,
            passed=overall_score >= self.threshold,
            threshold=self.threshold,
            details={
                "avg_relevance": avg_relevance,
                "avg_precision": avg_precision,
                "avg_answer_relevance": avg_answer_relevance,
                **details,
            },
        )
    
    def _evaluate_retrieval_relevance(self, query: str, retrievals: List[Dict]) -> float:
        """Evaluate how relevant retrieved documents are to the query.
        
        Uses semantic similarity between query and retrieved content.
        """
        if not retrievals:
            return 0.0
        
        scores = []
        for retrieval in retrievals:
            content = retrieval.get("content", "")
            if not content:
                continue
            
            similarity = self._compute_semantic_similarity(query, content)
            scores.append(similarity)
        
        if not scores:
            return 0.0
        
        # Weight by rank (top results should be more relevant)
        weighted_scores = []
        for i, score in enumerate(scores):
            weight = 1.0 / (i + 1)  # Higher weight for earlier results
            weighted_scores.append(score * weight)
        
        return sum(weighted_scores) / sum(1.0 / (i + 1) for i in range(len(scores)))
    
    def _evaluate_context_precision(self, query: str, retrievals: List[Dict]) -> float:
        """Evaluate if the most relevant documents are ranked highest.
        
        Returns 1.0 if ranking is perfect, lower if relevant docs are buried.
        """
        if len(retrievals) <= 1:
            return 1.0
        
        # Compute relevance scores
        relevance_scores = []
        for retrieval in retrievals:
            content = retrieval.get("content", "")
            score = self._compute_semantic_similarity(query, content) if content else 0.0
            relevance_scores.append(score)
        
        # Check if scores are monotonically decreasing (ideal)
        ideal_order = sorted(range(len(relevance_scores)), key=lambda i: relevance_scores[i], reverse=True)
        actual_order = list(range(len(relevance_scores)))
        
        # Kendall tau distance (simplified)
        inversions = 0
        for i in range(len(ideal_order)):
            for j in range(i + 1, len(ideal_order)):
                if actual_order.index(ideal_order[i]) > actual_order.index(ideal_order[j]):
                    inversions += 1
        
        max_inversions = len(relevance_scores) * (len(relevance_scores) - 1) / 2
        precision = 1.0 - (inversions / max_inversions) if max_inversions > 0 else 1.0
        
        return precision
    
    def _evaluate_answer_relevance(self, retrieval_span: Dict, all_spans: List[Dict]) -> float:
        """Evaluate if the generated answer is relevant to the query and context.
        
        Looks for subsequent LLM spans that use this retrieval.
        """
        retrieval_idx = all_spans.index(retrieval_span) if retrieval_span in all_spans else -1
        if retrieval_idx < 0 or retrieval_idx >= len(all_spans) - 1:
            return None
        
        # Find next LLM span
        for span in all_spans[retrieval_idx + 1:]:
            if span.get("span_type") in ["llm", "completion", "agent"]:
                query = retrieval_span.get("input", "")
                answer = span.get("output", "")
                if not answer:
                    return None
                
                # Semantic similarity between query and answer
                query_answer_sim = self._compute_semantic_similarity(query, answer)
                
                # Check if answer uses retrieved context
                retrievals = retrieval_span.get("retrievals", [])
                retrieval_text = " ".join([r.get("content", "") for r in retrievals])
                context_usage = self._compute_semantic_similarity(answer, retrieval_text) if retrieval_text else 0.5
                
                return (query_answer_sim * 0.5 + context_usage * 0.5)
        
        return None
