"""Tool Use Benchmark Dataset

Tests tool selection, parameter validity, error recovery, and retry behavior.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class ToolTestCase:
    id: str
    description: str
    context: str
    available_tools: List[Dict[str, Any]]
    expected_tool: str
    expected_parameters: Dict[str, Any]
    inject_errors: Optional[List[str]]  # timeout, invalid_param, rate_limit, etc.
    expected_recovery: Optional[str]
    difficulty: str


# Tool selection tests
SELECTION_TESTS = [
    ToolTestCase(
        id="tool-sel-001",
        description="Select weather tool for weather query",
        context="What's the temperature in Tokyo?",
        available_tools=[
            {"name": "weather_api", "description": "Get weather for a location"},
            {"name": "search", "description": "Search the web"},
            {"name": "calculator", "description": "Perform calculations"},
        ],
        expected_tool="weather_api",
        expected_parameters={"location": "Tokyo", "metric": "temperature"},
        inject_errors=None,
        expected_recovery=None,
        difficulty="easy",
    ),
    ToolTestCase(
        id="tool-sel-002",
        description="Ambiguous query requires reasoning",
        context="I need to know about something in the sky that's bright today",
        available_tools=[
            {"name": "weather_api", "description": "Get weather data"},
            {"name": "astronomy", "description": "Get astronomical data"},
            {"name": "news", "description": "Get news"},
        ],
        expected_tool="weather_api",
        expected_parameters={"query": "sky brightness"},
        inject_errors=None,
        expected_recovery=None,
        difficulty="medium",
    ),
    ToolTestCase(
        id="tool-sel-003",
        description="Multi-tool plan required",
        context="Book me a flight to NYC and find a hotel",
        available_tools=[
            {"name": "flight_search", "description": "Search flights"},
            {"name": "hotel_search", "description": "Search hotels"},
            {"name": "book_flight", "description": "Book a flight"},
            {"name": "book_hotel", "description": "Book a hotel"},
        ],
        expected_tool="flight_search",
        expected_parameters={"destination": "NYC"},
        inject_errors=None,
        expected_recovery=None,
        difficulty="hard",
    ),
]

# Parameter validation tests
PARAMETER_TESTS = [
    ToolTestCase(
        id="tool-param-001",
        description="Valid parameters for calculator",
        context="Calculate compound interest on $1000 at 5% for 10 years",
        available_tools=[
            {"name": "calculator", "description": "Calculate mathematical expressions"},
        ],
        expected_tool="calculator",
        expected_parameters={
            "principal": 1000,
            "rate": 0.05,
            "years": 10,
            "operation": "compound_interest",
        },
        inject_errors=None,
        expected_recovery=None,
        difficulty="medium",
    ),
    ToolTestCase(
        id="tool-param-002",
        description="Handle missing required parameter",
        context="Search for restaurants",
        available_tools=[
            {"name": "restaurant_search", "description": "Search restaurants by location"},
        ],
        expected_tool="restaurant_search",
        expected_parameters={"location": "current", "cuisine": None},
        inject_errors=["missing_param"],
        expected_recovery="ask_for_location",
        difficulty="medium",
    ),
]

# Error recovery tests
RECOVERY_TESTS = [
    ToolTestCase(
        id="tool-recovery-001",
        description="Timeout recovery with retry",
        context="Get stock price for AAPL",
        available_tools=[
            {"name": "stock_api", "description": "Get stock prices"},
        ],
        expected_tool="stock_api",
        expected_parameters={"symbol": "AAPL"},
        inject_errors=["timeout"],
        expected_recovery="retry_with_backoff",
        difficulty="medium",
    ),
    ToolTestCase(
        id="tool-recovery-002",
        description="Rate limit with fallback",
        context="Translate 'hello' to French",
        available_tools=[
            {"name": "google_translate", "description": "Google Translate API"},
            {"name": "deepl_translate", "description": "DeepL Translate API"},
        ],
        expected_tool="google_translate",
        expected_parameters={"text": "hello", "target": "fr"},
        inject_errors=["rate_limit"],
        expected_recovery="switch_to_deepl",
        difficulty="hard",
    ),
    ToolTestCase(
        id="tool-recovery-003",
        description="Invalid schema with correction",
        context="Search for articles about AI",
        available_tools=[
            {"name": "article_search", "description": "Search articles", "parameters": {"query": "string", "date_range": "string"}},
        ],
        expected_tool="article_search",
        expected_parameters={"query": "AI", "date_range": "2024"},
        inject_errors=["invalid_schema"],
        expected_recovery="fix_schema_and_retry",
        difficulty="hard",
    ),
]

# Retry behavior tests
RETRY_TESTS = [
    ToolTestCase(
        id="tool-retry-001",
        description="Excessive retries detection",
        context="Get weather",
        available_tools=[
            {"name": "weather_api", "description": "Get weather"},
        ],
        expected_tool="weather_api",
        expected_parameters={},
        inject_errors=["timeout", "timeout", "timeout", "timeout", "timeout"],
        expected_recovery="fail_gracefully",
        difficulty="hard",
    ),
]

ALL_TOOL_TESTS = (
    SELECTION_TESTS +
    PARAMETER_TESTS +
    RECOVERY_TESTS +
    RETRY_TESTS
)


def export_to_json() -> List[Dict[str, Any]]:
    return [
        {
            "id": tc.id,
            "description": tc.description,
            "context": tc.context,
            "expected_tool": tc.expected_tool,
            "expected_parameters": tc.expected_parameters,
            "inject_errors": tc.inject_errors,
            "expected_recovery": tc.expected_recovery,
            "difficulty": tc.difficulty,
        }
        for tc in ALL_TOOL_TESTS
    ]


if __name__ == "__main__":
    import json
    data = export_to_json()
    with open("tool_benchmark.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f"Exported {len(data)} tool use benchmark test cases")
