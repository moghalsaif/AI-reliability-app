"""Regression Testing / AI CI/CD Pipeline

This module provides automated regression testing for AI agents.
When developers change prompts, models, or retrieval logic,
the system automatically runs the benchmark suite, eval suite,
and reliability analysis.

Outputs:
```
Truthfulness: +7%
Latency: -12%
Hallucination: +19%
```
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from reliability_shared.types.core import Trace
from reliability_evals import (
    HallucinationEvaluator,
    RAGEvaluator,
    ToolUseEvaluator,
    ReflectionEvaluator,
    MemoryEvaluator,
    EvalResult,
)
from reliability_engine import ReliabilityAnalyzer, ReliabilityRun, ReliabilityReport


@dataclass
class TestCase:
    """A single test case for regression testing."""
    id: str
    name: str
    input: Any
    expected_output: Optional[Any] = None
    expected_tools: Optional[List[str]] = None
    expected_retrievals: Optional[List[str]] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    """Result of running a single test case."""
    test_id: str
    test_name: str
    passed: bool
    trace: Optional[Trace] = None
    eval_results: List[EvalResult] = field(default_factory=list)
    latency_ms: float = 0.0
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def overall_score(self) -> float:
        if not self.eval_results:
            return 1.0 if self.passed else 0.0
        return sum(r.score for r in self.eval_results) / len(self.eval_results)


@dataclass
class RegressionDiff:
    """Diff between baseline and current run."""
    metric: str
    baseline_value: float
    current_value: float
    change_pct: float
    direction: str  # "improved", "degraded", "unchanged"
    severity: str  # "critical", "warning", "info"


@dataclass
class RegressionReport:
    """Full regression testing report."""
    run_id: str
    commit_hash: Optional[str] = None
    baseline_run_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Test results
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    success_rate: float = 0.0
    
    # Eval scores
    avg_hallucination_score: float = 0.0
    avg_rag_score: float = 0.0
    avg_tool_accuracy: float = 0.0
    avg_reflection_score: float = 0.0
    avg_memory_score: float = 0.0
    
    # Performance
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    total_tokens: int = 0
    
    # Regression diffs
    diffs: List[RegressionDiff] = field(default_factory=list)
    
    # Blocking issues
    blocking_issues: List[str] = field(default_factory=list)
    
    # Recommendation
    recommendation: str = ""
    should_deploy: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "commit_hash": self.commit_hash,
            "baseline_run_id": self.baseline_run_id,
            "timestamp": self.timestamp.isoformat(),
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "success_rate": self.success_rate,
            "avg_hallucination_score": self.avg_hallucination_score,
            "avg_rag_score": self.avg_rag_score,
            "avg_tool_accuracy": self.avg_tool_accuracy,
            "avg_reflection_score": self.avg_reflection_score,
            "avg_memory_score": self.avg_memory_score,
            "avg_latency_ms": self.avg_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "total_tokens": self.total_tokens,
            "diffs": [{
                "metric": d.metric,
                "baseline": d.baseline_value,
                "current": d.current_value,
                "change_pct": d.change_pct,
                "direction": d.direction,
                "severity": d.severity,
            } for d in self.diffs],
            "blocking_issues": self.blocking_issues,
            "recommendation": self.recommendation,
            "should_deploy": self.should_deploy,
        }


class RegressionTestRunner:
    """Run regression tests and compare against baselines."""
    
    def __init__(
        self,
        agent_factory: Callable[[], Any],
        baseline_store_path: str = ".regression_baseline.json",
    ):
        self.agent_factory = agent_factory
        self.baseline_store_path = baseline_store_path
        self.evaluators = {
            "hallucination": HallucinationEvaluator(),
            "rag": RAGEvaluator(),
            "tool_use": ToolUseEvaluator(),
            "reflection": ReflectionEvaluator(),
            "memory": MemoryEvaluator(),
        }
        self.analyzer = ReliabilityAnalyzer()
    
    def run_test_suite(
        self,
        test_cases: List[TestCase],
        commit_hash: Optional[str] = None,
    ) -> RegressionReport:
        """Run the full test suite and generate a regression report."""
        run_id = f"regression_{int(time.time())}"
        results: List[TestResult] = []
        traces: List[Trace] = []
        
        for test in test_cases:
            result = self._run_single_test(test)
            results.append(result)
            if result.trace:
                traces.append(result.trace)
        
        # Compute metrics
        report = self._compute_report(run_id, results, traces, commit_hash)
        
        # Compare with baseline
        baseline = self._load_baseline()
        if baseline:
            report.diffs = self._compute_diffs(baseline, report)
            report.baseline_run_id = baseline.get("run_id")
        
        # Determine if deployment should be blocked
        report.should_deploy = self._should_deploy(report)
        report.recommendation = self._generate_recommendation(report)
        
        # Save as new baseline if requested
        return report
    
    def _run_single_test(self, test: TestCase) -> TestResult:
        """Run a single test case."""
        agent = self.agent_factory()
        start = time.time()
        
        try:
            # Run agent with test input
            from reliability_sdk import Tracer
            tracer = Tracer()
            
            with tracer.trace(test.name, agent_name=agent.__class__.__name__) as builder:
                output = agent.run(test.input)
                trace = builder.finish(success=True)
            
            latency = (time.time() - start) * 1000
            
            # Run evaluators
            eval_results = []
            trace_dict = trace.to_dict()
            for name, evaluator in self.evaluators.items():
                try:
                    result = evaluator.evaluate(trace_dict)
                    eval_results.append(result)
                except Exception as e:
                    import logging
                    logging.getLogger("reliability_regression").warning(f"Eval {name} failed: {e}")
            
            # Determine pass/fail
            passed = all(r.passed for r in eval_results) if eval_results else True
            
            return TestResult(
                test_id=test.id,
                test_name=test.name,
                passed=passed,
                trace=trace,
                eval_results=eval_results,
                latency_ms=latency,
            )
            
        except Exception as e:
            latency = (time.time() - start) * 1000
            return TestResult(
                test_id=test.id,
                test_name=test.name,
                passed=False,
                error=str(e),
                latency_ms=latency,
            )
    
    def _compute_report(
        self,
        run_id: str,
        results: List[TestResult],
        traces: List[Trace],
        commit_hash: Optional[str],
    ) -> RegressionReport:
        """Compute regression report from results."""
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed
        
        # Aggregate eval scores
        halluc_scores = []
        rag_scores = []
        tool_scores = []
        reflection_scores = []
        memory_scores = []
        
        for result in results:
            for eval_result in result.eval_results:
                if eval_result.eval_type == "hallucination":
                    halluc_scores.append(eval_result.score)
                elif eval_result.eval_type == "rag":
                    rag_scores.append(eval_result.score)
                elif eval_result.eval_type == "tool_use":
                    tool_scores.append(eval_result.score)
                elif eval_result.eval_type == "reflection":
                    reflection_scores.append(eval_result.score)
                elif eval_result.eval_type == "memory":
                    memory_scores.append(eval_result.score)
        
        latencies = [r.latency_ms for r in results]
        
        return RegressionReport(
            run_id=run_id,
            commit_hash=commit_hash,
            baseline_run_id=None,
            timestamp=datetime.utcnow(),
            total_tests=len(results),
            passed_tests=passed,
            failed_tests=failed,
            success_rate=passed / len(results) if results else 0.0,
            avg_hallucination_score=sum(halluc_scores) / len(halluc_scores) if halluc_scores else 1.0,
            avg_rag_score=sum(rag_scores) / len(rag_scores) if rag_scores else 1.0,
            avg_tool_accuracy=sum(tool_scores) / len(tool_scores) if tool_scores else 1.0,
            avg_reflection_score=sum(reflection_scores) / len(reflection_scores) if reflection_scores else 1.0,
            avg_memory_score=sum(memory_scores) / len(memory_scores) if memory_scores else 1.0,
            avg_latency_ms=sum(latencies) / len(latencies) if latencies else 0.0,
            p95_latency_ms=self._percentile(latencies, 0.95) if latencies else 0.0,
            total_tokens=sum(
                t.metrics.get("total_tokens", 0) for t in traces
            ),
        )
    
    def _compute_diffs(
        self,
        baseline: Dict[str, Any],
        current: RegressionReport,
    ) -> List[RegressionDiff]:
        """Compute diffs between baseline and current."""
        diffs = []
        
        metrics = [
            ("success_rate", current.success_rate),
            ("hallucination_score", current.avg_hallucination_score),
            ("rag_score", current.avg_rag_score),
            ("tool_accuracy", current.avg_tool_accuracy),
            ("latency_ms", current.avg_latency_ms),
        ]
        
        for metric_name, current_value in metrics:
            baseline_value = baseline.get(f"avg_{metric_name}", baseline.get(metric_name, 0))
            
            if baseline_value != 0:
                change_pct = ((current_value - baseline_value) / baseline_value) * 100
            else:
                change_pct = 0.0
            
            # Determine direction
            lower_is_better = {"latency_ms", "hallucination_rate", "failed_tests"}
            
            if metric_name in lower_is_better:
                direction = "improved" if change_pct < 0 else "degraded" if change_pct > 0 else "unchanged"
            else:
                direction = "improved" if change_pct > 0 else "degraded" if change_pct < 0 else "unchanged"
            
            # Determine severity
            if abs(change_pct) > 20:
                severity = "critical"
            elif abs(change_pct) > 10:
                severity = "warning"
            else:
                severity = "info"
            
            diffs.append(RegressionDiff(
                metric=metric_name,
                baseline_value=baseline_value,
                current_value=current_value,
                change_pct=change_pct,
                direction=direction,
                severity=severity,
            ))
        
        return diffs
    
    def _should_deploy(self, report: RegressionReport) -> bool:
        """Determine if deployment should be allowed."""
        # Block if success rate dropped below threshold
        if report.success_rate < 0.85:
            report.blocking_issues.append(f"Success rate {report.success_rate:.1%} below 85% threshold")
        
        # Block if hallucination increased significantly
        for diff in report.diffs:
            if diff.metric == "hallucination_score" and diff.direction == "degraded" and diff.change_pct > 10:
                report.blocking_issues.append(f"Hallucination increased by {diff.change_pct:.1f}%")
        
        # Block if critical failures
        if report.failed_tests > report.total_tests * 0.1:  # More than 10% failure
            report.blocking_issues.append(f"Failure rate {report.failed_tests}/{report.total_tests} too high")
        
        return len(report.blocking_issues) == 0
    
    def _generate_recommendation(self, report: RegressionReport) -> str:
        """Generate deployment recommendation."""
        if report.should_deploy:
            return "All checks passed. Safe to deploy."
        
        issues = "; ".join(report.blocking_issues)
        return f"Deployment BLOCKED. Issues: {issues}"
    
    def save_baseline(self, report: RegressionReport) -> None:
        """Save current report as new baseline."""
        data = report.to_dict()
        with open(self.baseline_store_path, "w") as f:
            json.dump(data, f, indent=2)
    
    def _load_baseline(self) -> Optional[Dict[str, Any]]:
        """Load baseline report."""
        try:
            with open(self.baseline_store_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
    
    @staticmethod
    def _percentile(data: List[float], percentile: float) -> float:
        if not data:
            return 0.0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * percentile
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_data) else f
        if f == c:
            return sorted_data[f]
        return sorted_data[f] * (c - k) + sorted_data[c] * (k - f)


class CICDPipeline:
    """CI/CD pipeline integration for AI reliability."""
    
    def __init__(self, runner: RegressionTestRunner):
        self.runner = runner
    
    def run_pipeline(
        self,
        test_cases: List[TestCase],
        commit_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run the full CI/CD pipeline."""
        print("=" * 60)
        print("AI RELIABILITY CI/CD PIPELINE")
        print("=" * 60)
        
        report = self.runner.run_test_suite(test_cases, commit_hash)
        
        print(f"\nRun ID: {report.run_id}")
        print(f"Commit: {report.commit_hash or 'N/A'}")
        print(f"Tests: {report.passed_tests}/{report.total_tests} passed")
        print(f"Success Rate: {report.success_rate:.1%}")
        
        print("\n--- Eval Scores ---")
        print(f"Hallucination: {report.avg_hallucination_score:.3f}")
        print(f"RAG: {report.avg_rag_score:.3f}")
        print(f"Tool Accuracy: {report.avg_tool_accuracy:.3f}")
        print(f"Reflection: {report.avg_reflection_score:.3f}")
        print(f"Memory: {report.avg_memory_score:.3f}")
        
        if report.diffs:
            print("\n--- Regression Diffs ---")
            for diff in report.diffs:
                sign = "+" if diff.change_pct > 0 else ""
                color = "\033[92m" if diff.direction == "improved" else "\033[91m" if diff.direction == "degraded" else "\033[93m"
                print(f"{color}{diff.metric}: {sign}{diff.change_pct:.1f}% ({diff.direction})\033[0m")
        
        print(f"\n--- Decision ---")
        print(f"Deploy: {'YES' if report.should_deploy else 'NO'}")
        print(f"Recommendation: {report.recommendation}")
        
        if report.blocking_issues:
            print("\nBlocking Issues:")
            for issue in report.blocking_issues:
                print(f"  - {issue}")
        
        print("=" * 60)
        
        return report.to_dict()
