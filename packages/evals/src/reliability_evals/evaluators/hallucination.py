"""Hallucination evaluator - detects unsupported claims, contradictions, and fabricated citations.

Methods:
1. LLM judge for claim verification
2. Semantic grounding check (retrieval overlap)
3. Contradiction detection
"""

from typing import Any, Dict, List, Optional

from ..base import BaseEvaluator, EvalResult


class HallucinationEvaluator(BaseEvaluator):
    """Evaluate hallucination in agent outputs."""
    
    def default_threshold(self) -> float:
        return 0.85  # Lower score = more hallucination, so we want high score
    
    def evaluate(self, trace_data: Dict[str, Any]) -> EvalResult:
        """Evaluate hallucination in a trace.
        
        Returns a score where 1.0 = no hallucination, 0.0 = complete hallucination.
        """
        # Extract relevant data from trace
        spans = trace_data.get("spans", [])
        
        hallucination_scores = []
        details = {
            "unsupported_claims": [],
            "fabricated_citations": [],
            "contradictions": [],
            "span_scores": [],
        }
        
        for span in spans:
            span_type = span.get("span_type", "")
            
            if span_type == "llm" or span_type == "completion":
                output = span.get("output", "")
                retrievals = span.get("retrievals", [])
                
                # 1. Semantic grounding check
                grounding_score = self._check_grounding(output, retrievals)
                
                # 2. LLM judge for claim verification
                judge_score = self._judge_hallucination(output, retrievals)
                
                # 3. Citation validation
                citation_score = self._check_citations(output, retrievals)
                
                # Combine scores (weighted)
                span_score = (
                    grounding_score * 0.4 +
                    judge_score * 0.4 +
                    citation_score * 0.2
                )
                
                hallucination_scores.append(span_score)
                details["span_scores"].append({
                    "span_id": span.get("span_id"),
                    "grounding": grounding_score,
                    "judge": judge_score,
                    "citations": citation_score,
                    "combined": span_score,
                })
        
        if not hallucination_scores:
            return EvalResult(
                eval_type="hallucination",
                score=1.0,  # No LLM spans = no hallucination to evaluate
                passed=True,
                threshold=self.threshold,
                details={"reason": "No LLM spans found"},
            )
        
        # Overall score is the minimum (worst case) - strict evaluation
        overall_score = min(hallucination_scores)
        
        # Also check for high variance (inconsistent hallucination)
        import statistics
        if len(hallucination_scores) > 1:
            variance = statistics.variance(hallucination_scores) if len(hallucination_scores) > 1 else 0
            details["score_variance"] = variance
            # Penalize high variance
            if variance > 0.1:
                overall_score *= (1.0 - variance * 0.5)
        
        return EvalResult(
            eval_type="hallucination",
            score=overall_score,
            passed=overall_score >= self.threshold,
            threshold=self.threshold,
            details=details,
            model_judge=self.judge_config.model_name,
        )
    
    def _check_grounding(self, output: str, retrievals: List[Dict]) -> float:
        """Check if output is semantically grounded in retrieval results.
        
        Returns score where 1.0 = fully grounded, 0.0 = completely ungrounded.
        """
        if not retrievals:
            # No retrievals means we can't check grounding
            return 0.8  # Neutral score
        
        # Combine all retrieval content
        retrieval_text = " ".join([r.get("content", "") for r in retrievals])
        if not retrieval_text.strip():
            return 0.8
        
        # Semantic similarity between output and retrievals
        similarity = self._compute_semantic_similarity(output, retrieval_text)
        
        # Check for key phrases from output appearing in retrievals
        output_phrases = self._extract_key_phrases(output)
        grounded_phrases = 0
        for phrase in output_phrases:
            if phrase.lower() in retrieval_text.lower():
                grounded_phrases += 1
        
        phrase_grounding = grounded_phrases / len(output_phrases) if output_phrases else 0.5
        
        # Combine metrics
        score = (similarity * 0.6) + (phrase_grounding * 0.4)
        return min(score, 1.0)
    
    def _judge_hallucination(self, output: str, retrievals: List[Dict]) -> float:
        """Use LLM judge to detect hallucination.
        
        Returns score where 1.0 = no hallucination detected.
        """
        retrieval_text = " ".join([r.get("content", "") for r in retrievals])
        
        system_prompt = """You are a hallucination detection judge. Your task is to evaluate whether an AI response contains hallucinated information - claims that are not supported by the provided context.

Rate the response on a scale of 0.0 to 1.0:
- 1.0: No hallucination. All claims are fully supported by context.
- 0.7-0.9: Minor unsupported claims or slight extrapolation.
- 0.4-0.6: Significant unsupported claims or fabricated details.
- 0.0-0.3: Severe hallucination. Major claims are fabricated or contradict context.

Respond with ONLY a numeric score (e.g., "0.85")."""

        prompt = f"""Context (retrieved information):
{retrieval_text[:2000]}

AI Response:
{output[:2000]}

Rate the hallucination level (0.0-1.0, where 1.0 = no hallucination):"""

        try:
            response = self._call_judge(prompt, system_prompt)
            score = self._parse_judge_score(response)
            return score
        except Exception as e:
            import logging
            logging.getLogger("reliability_evals").warning(f"Hallucination judge failed: {e}")
            return 0.7  # Default neutral score
    
    def _check_citations(self, output: str, retrievals: List[Dict]) -> float:
        """Check if citations in output match retrieved sources.
        
        Returns score where 1.0 = all citations valid.
        """
        import re
        
        # Extract citation patterns like [1], (Source A), etc.
        citation_patterns = [
            r'\[(\d+)\]',  # [1], [2]
            r'\(([^)]+)\)',  # (Source)
            r'according to ([^,]+)',
            r'source[s]?\s*[:\s]+([^,.]+)',
        ]
        
        found_citations = []
        for pattern in citation_patterns:
            matches = re.findall(pattern, output, re.IGNORECASE)
            found_citations.extend(matches)
        
        if not found_citations:
            # No citations claimed - can't be fabricated
            return 1.0
        
        # Check citations against actual sources
        valid_citations = 0
        source_names = [r.get("source", "") for r in retrievals]
        
        for citation in found_citations:
            citation_str = str(citation).lower()
            for source in source_names:
                if citation_str in source.lower() or source.lower() in citation_str:
                    valid_citations += 1
                    break
        
        return valid_citations / len(found_citations) if found_citations else 1.0
    
    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key factual phrases from text for grounding check."""
        import re
        
        # Simple extraction - sentences with numbers, dates, or proper nouns
        sentences = re.split(r'[.!?]+', text)
        key_phrases = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            # Heuristic: sentences with numbers, percentages, dates, or specific claims
            if re.search(r'\d+', sentence) or re.search(r'\b(?:is|are|was|were|has|have|did|does)\b', sentence):
                # Take first 10 words as key phrase
                words = sentence.split()[:10]
                key_phrases.append(" ".join(words))
        
        return key_phrases[:20]  # Limit to top 20
