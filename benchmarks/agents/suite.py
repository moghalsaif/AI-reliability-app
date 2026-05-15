"""Agent Benchmark Dataset

Tests multi-step agent reasoning, tool use, planning, and recovery.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class AgentTestCase:
    id: str
    description: str
    initial_state: Dict[str, Any]
    expected_steps: List[str]
    expected_tools: List[str]
    expected_outcome: str
    max_steps: int
    difficulty: str
    category: str  # planning, tool_use, recovery, reasoning


# Planning tests
PLANNING_TESTS = [
    AgentTestCase(
        id="agent-plan-001",
        description="Book a flight with hotel and car rental",
        initial_state={"user_request": "I need to fly to NYC next week and stay for 3 days"},
        expected_steps=[
            "search_flights",
            "select_flight",
            "search_hotels",
            "select_hotel",
            "search_car_rentals",
            "confirm_booking",
        ],
        expected_tools=["flight_search", "hotel_search", "car_rental_search", "booking"],
        expected_outcome="Confirmed booking with all three reservations",
        max_steps=10,
        difficulty="medium",
        category="planning",
    ),
    AgentTestCase(
        id="agent-plan-002",
        description="Research topic and write summary",
        initial_state={"user_request": "Research quantum computing advances in 2024"},
        expected_steps=[
            "search_web",
            "read_articles",
            "synthesize_information",
            "write_summary",
            "cite_sources",
        ],
        expected_tools=["web_search", "reader", "writer"],
        expected_outcome="Comprehensive summary with citations",
        max_steps=8,
        difficulty="medium",
        category="planning",
    ),
]

# Tool use tests
TOOL_USE_TESTS = [
    AgentTestCase(
        id="agent-tool-001",
        description="Correct tool selection under ambiguity",
        initial_state={"user_request": "What's the weather like?"},
        expected_steps=["detect_location", "get_weather"],
        expected_tools=["location_detector", "weather_api"],
        expected_outcome="Current weather for user's location",
        max_steps=3,
        difficulty="easy",
        category="tool_use",
    ),
    AgentTestCase(
        id="agent-tool-002",
        description="Handle tool failure gracefully",
        initial_state={
            "user_request": "Send email to team",
            "tool_failures": {"email_sender": "connection_error"},
        },
        expected_steps=["attempt_email", "retry", "fallback_to_slack"],
        expected_tools=["email_sender", "slack_notifier"],
        expected_outcome="Message sent via fallback channel",
        max_steps=5,
        difficulty="hard",
        category="recovery",
    ),
]

# Recovery tests
RECOVERY_TESTS = [
    AgentTestCase(
        id="agent-recovery-001",
        description="Recover from hallucinated tool result",
        initial_state={
            "user_request": "Calculate compound interest",
            "injected_hallucination": True,
        },
        expected_steps=[
            "attempt_calculation",
            "detect_inconsistency",
            "recalculate",
            "verify_result",
        ],
        expected_tools=["calculator", "validator"],
        expected_outcome="Correct calculation after self-correction",
        max_steps=6,
        difficulty="hard",
        category="recovery",
    ),
]

# Reasoning tests
REASONING_TESTS = [
    AgentTestCase(
        id="agent-reason-001",
        description="Multi-step logical deduction",
        initial_state={
            "user_request": "If A implies B, and B implies C, does A imply C?",
        },
        expected_steps=["parse_logical_statements", "apply_transitivity", "derive_conclusion"],
        expected_tools=["logic_engine"],
        expected_outcome="Yes, by transitivity of implication",
        max_steps=4,
        difficulty="medium",
        category="reasoning",
    ),
]

ALL_AGENT_TESTS = (
    PLANNING_TESTS +
    TOOL_USE_TESTS +
    RECOVERY_TESTS +
    REASONING_TESTS
)


def export_to_json() -> List[Dict[str, Any]]:
    return [
        {
            "id": tc.id,
            "description": tc.description,
            "initial_state": tc.initial_state,
            "expected_steps": tc.expected_steps,
            "expected_tools": tc.expected_tools,
            "expected_outcome": tc.expected_outcome,
            "max_steps": tc.max_steps,
            "difficulty": tc.difficulty,
            "category": tc.category,
        }
        for tc in ALL_AGENT_TESTS
    ]


if __name__ == "__main__":
    import json
    data = export_to_json()
    with open("agent_benchmark.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f"Exported {len(data)} agent benchmark test cases")
