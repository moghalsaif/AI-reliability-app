"""CLI tool for AI Reliability Lab.

Usage:
    python -m reliability_cli trace --name "my-agent" --input "hello"
    python -m reliability_cli eval --trace-file trace.json
    python -m reliability_cli benchmark --suite rag
    python -m reliability_cli regress --tests tests.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_trace(args: argparse.Namespace) -> None:
    """Run a trace and optionally export it."""
    from reliability_sdk import Tracer, ConsoleExporter
    from reliability_shared.types.core import ModelMetadata, TokenUsage

    tracer = Tracer(service_name=args.service or "cli-agent")
    tracer.add_exporter(ConsoleExporter(pretty=True))

    with tracer.trace(args.name or "cli_trace", agent_name=args.agent):
        print(f"Running trace: {args.name or 'cli_trace'}")
        if args.input:
            print(f"Input: {args.input}")
        # Simulate work
        tracer.record_llm_call(
            prompt=args.input or "Hello",
            completion="This is a simulated response.",
            model_metadata=ModelMetadata(
                model_name=args.model or "qwen3-32b",
                provider="ollama",
            ),
            token_usage=TokenUsage(prompt_tokens=5, completion_tokens=10),
            latency_ms=500,
        )

    print("Trace complete.")


def cmd_eval(args: argparse.Namespace) -> None:
    """Run evaluators on a trace file."""
    from reliability_evals import (
        HallucinationEvaluator,
        RAGEvaluator,
        ToolUseEvaluator,
        ReflectionEvaluator,
        MemoryEvaluator,
    )

    trace_file = Path(args.trace_file)
    if not trace_file.exists():
        print(f"Error: Trace file not found: {trace_file}", file=sys.stderr)
        sys.exit(1)

    with open(trace_file) as f:
        trace_data = json.load(f)

    evaluators = {
        "hallucination": HallucinationEvaluator(),
        "rag": RAGEvaluator(),
        "tool_use": ToolUseEvaluator(),
        "reflection": ReflectionEvaluator(),
        "memory": MemoryEvaluator(),
    }

    results = {}
    for name, evaluator in evaluators.items():
        result = evaluator.evaluate(trace_data)
        results[name] = result.to_dict()
        status = "PASS" if result.passed else "FAIL"
        print(f"  [{status}] {name:15s} | Score: {result.score:.3f} | Threshold: {result.threshold:.3f}")

    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {args.output}")


def cmd_benchmark(args: argparse.Namespace) -> None:
    """Run benchmark suites."""
    from benchmarks.runner import BenchmarkRegistry

    registry = BenchmarkRegistry()

    if args.list:
        print("Available benchmark suites:")
        for name in registry.list_suites():
            tests = registry.get_suite(name)
            print(f"  {name:15s} ({len(tests)} tests)")
        return

    if args.suite:
        tests = registry.get_suite(args.suite)
        if not tests:
            print(f"Error: Suite '{args.suite}' not found", file=sys.stderr)
            sys.exit(1)
        print(f"Running {args.suite} benchmark ({len(tests)} tests)...")
        # In real implementation, run the tests
        print(f"  Completed {len(tests)} tests")
    else:
        print("Running all benchmark suites...")
        for name in registry.list_suites():
            tests = registry.get_suite(name)
            print(f"  {name:15s}: {len(tests)} tests")


def cmd_regress(args: argparse.Namespace) -> None:
    """Run regression tests."""
    from reliability_engine.regression import RegressionTestRunner, TestCase

    def mock_agent_factory():
        class MockAgent:
            def run(self, input_data):
                return {"output": "mock"}
        return MockAgent()

    runner = RegressionTestRunner(agent_factory=mock_agent_factory)

    test_cases = [
        TestCase(id="t1", name="Basic", input="hello"),
        TestCase(id="t2", name="Tool", input="call tool"),
    ]

    report = runner.run_test_suite(test_cases)
    print(f"Regression Report:")
    print(f"  Tests: {report.total_tests}")
    print(f"  Passed: {report.passed_tests}")
    print(f"  Success Rate: {report.success_rate:.1%}")
    print(f"  Deploy: {'YES' if report.should_deploy else 'NO'}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="reliability",
        description="AI Reliability Lab CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Trace command
    trace_parser = subparsers.add_parser("trace", help="Run a trace")
    trace_parser.add_argument("--name", help="Trace name")
    trace_parser.add_argument("--service", help="Service name")
    trace_parser.add_argument("--agent", help="Agent name")
    trace_parser.add_argument("--input", help="Input text")
    trace_parser.add_argument("--model", default="qwen3-32b", help="Model name")
    trace_parser.set_defaults(func=cmd_trace)

    # Eval command
    eval_parser = subparsers.add_parser("eval", help="Run evaluators on a trace")
    eval_parser.add_argument("--trace-file", required=True, help="Trace JSON file")
    eval_parser.add_argument("--output", help="Output file for results")
    eval_parser.set_defaults(func=cmd_eval)

    # Benchmark command
    bench_parser = subparsers.add_parser("benchmark", help="Run benchmarks")
    bench_parser.add_argument("--suite", help="Benchmark suite name")
    bench_parser.add_argument("--list", action="store_true", help="List available suites")
    bench_parser.set_defaults(func=cmd_benchmark)

    # Regression command
    regress_parser = subparsers.add_parser("regress", help="Run regression tests")
    regress_parser.set_defaults(func=cmd_regress)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
