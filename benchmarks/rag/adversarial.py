"""RAG Adversarial Benchmark Dataset

Tests retrieval-augmented generation systems with adversarial queries.
Includes: contradiction, entailment, paraphrase, negation tests.
"""

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class RAGTestCase:
    id: str
    query: str
    expected_sources: List[str]
    expected_answer: str
    adversarial_type: str  # contradiction, entailment, paraphrase, negation
    difficulty: str  # easy, medium, hard
    metadata: Dict[str, Any]


# Contradiction tests - queries that test if system can detect contradictions
CONTRADICTION_TESTS = [
    RAGTestCase(
        id="rag-contra-001",
        query="What is the population of Tokyo? The document says 14 million but also states it's 37 million.",
        expected_sources=["tokyo_demographics"],
        expected_answer="The document contains a contradiction. The Greater Tokyo Area has ~37M, but Tokyo proper has ~14M.",
        adversarial_type="contradiction",
        difficulty="medium",
        metadata={"topic": "demographics", "language": "en"},
    ),
    RAGTestCase(
        id="rag-contra-002",
        query="Is water boiling point 100°C or 90°C according to the documents?",
        expected_sources=["physics_ref", "chemistry_ref"],
        expected_answer="The documents contradict: one states 100°C at sea level, another incorrectly states 90°C.",
        adversarial_type="contradiction",
        difficulty="easy",
        metadata={"topic": "science", "language": "en"},
    ),
]

# Entailment tests - queries requiring logical inference
ENTAILMENT_TESTS = [
    RAGTestCase(
        id="rag-entail-001",
        query="If all cats are mammals and all mammals are warm-blooded, what can we conclude about cats?",
        expected_sources=["biology_taxonomy"],
        expected_answer="Cats are warm-blooded, by transitive entailment.",
        adversarial_type="entailment",
        difficulty="easy",
        metadata={"topic": "logic", "language": "en"},
    ),
    RAGTestCase(
        id="rag-entail-002",
        query="The company revenue grew 20% in Q1 and 30% in Q2. What was the total growth?",
        expected_sources=["financial_reports"],
        expected_answer="This requires multiplicative compounding: 1.20 * 1.30 = 1.56, so 56% total growth.",
        adversarial_type="entailment",
        difficulty="hard",
        metadata={"topic": "finance", "requires_math": True},
    ),
]

# Paraphrase tests - same meaning, different wording
PARAPHRASE_TESTS = [
    RAGTestCase(
        id="rag-para-001",
        query="What are the advantages of using renewable energy sources?",
        expected_sources=["renewable_energy", "sustainability"],
        expected_answer="Benefits include reduced emissions, sustainability, and cost reduction over time.",
        adversarial_type="paraphrase",
        difficulty="easy",
        metadata={"topic": "energy", "original_query": "Why should we use renewable energy?"},
    ),
]

# Negation tests - handling negated queries
NEGATION_TESTS = [
    RAGTestCase(
        id="rag-neg-001",
        query="Which animals are NOT mammals?",
        expected_sources=["biology_taxonomy"],
        expected_answer="Birds, reptiles, amphibians, fish, and insects are not mammals.",
        adversarial_type="negation",
        difficulty="medium",
        metadata={"topic": "biology"},
    ),
]

# Multi-hop tests - requiring multiple retrieval steps
MULTIHOP_TESTS = [
    RAGTestCase(
        id="rag-hop-001",
        query="What is the capital of the country where the Eiffel Tower is located?",
        expected_sources=["eiffel_tower", "france"],
        expected_answer="Paris",
        adversarial_type="multihop",
        difficulty="easy",
        metadata={"hops": 2, "topic": "geography"},
    ),
    RAGTestCase(
        id="rag-hop-002",
        query="Who wrote the book that the movie 'The Shining' is based on?",
        expected_sources=["the_shining_movie", "stephen_king"],
        expected_answer="Stephen King",
        adversarial_type="multihop",
        difficulty="easy",
        metadata={"hops": 2, "topic": "entertainment"},
    ),
]

ALL_RAG_TESTS = (
    CONTRADICTION_TESTS +
    ENTAILMENT_TESTS +
    PARAPHRASE_TESTS +
    NEGATION_TESTS +
    MULTIHOP_TESTS
)


def export_to_json() -> List[Dict[str, Any]]:
    """Export all test cases to JSON format."""
    return [
        {
            "id": tc.id,
            "query": tc.query,
            "expected_sources": tc.expected_sources,
            "expected_answer": tc.expected_answer,
            "adversarial_type": tc.adversarial_type,
            "difficulty": tc.difficulty,
            "metadata": tc.metadata,
        }
        for tc in ALL_RAG_TESTS
    ]


if __name__ == "__main__":
    import json
    data = export_to_json()
    with open("rag_benchmark.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f"Exported {len(data)} RAG benchmark test cases")
