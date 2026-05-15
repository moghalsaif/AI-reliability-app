"""Reliability Engine - statistical reliability analysis for AI agents.

Run the same task many times across models, temperatures, and prompts.
Compute: variance, consistency, stability, reliability.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from reliability_shared.types.core import Trace


@dataclass
class ReliabilityRun:
    """A single run in a reliability experiment."""
    run_id: str
    trace_id: str
    agent_name: str
    model_name: str
    temperature: float
    prompt_version: str
    success: bool
    latency_ms: float
    token_count: int
    hallucination_score: float
    tool_accuracy: float
    reflection_score: float
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "trace_id": self.trace_id,
            "agent_name": self.agent_name,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "prompt_version": self.prompt_version,
            "success": self.success,
            "latency_ms": self.latency_ms,
            "token_count": self.token_count,
            "hallucination_score": self.hallucination_score,
            "tool_accuracy": self.tool_accuracy,
            "reflection_score": self.reflection_score,
            "timestamp": self.timestamp,
        }


@dataclass
class ReliabilityReport:
    """Comprehensive reliability report for an experiment."""
    experiment_id: str
    agent_name: str
    run_count: int
    
    # Core metrics
    success_rate: float = 0.0
    hallucination_rate: float = 0.0
    variance_score: float = 0.0
    retry_density: float = 0.0
    cost_per_success: float = 0.0
    latency_p95: float = 0.0
    context_retention: float = 0.0
    tool_accuracy: float = 0.0
    
    # Statistical measures
    latency_mean: float = 0.0
    latency_std: float = 0.0
    latency_cv: float = 0.0  # Coefficient of variation
    
    token_mean: float = 0.0
    token_std: float = 0.0
    token_cv: float = 0.0
    
    score_mean: float = 0.0
    score_std: float = 0.0
    score_cv: float = 0.0
    
    # Per-model breakdown
    model_breakdown: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Per-temperature breakdown
    temperature_breakdown: Dict[float, Dict[str, float]] = field(default_factory=dict)
    
    # Drift detection
    drift_detected: bool = False
    drift_metric: Optional[str] = None
    drift_magnitude: float = 0.0
    
    # Comparisons
    baseline_comparison: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "agent_name": self.agent_name,
            "run_count": self.run_count,
            "success_rate": self.success_rate,
            "hallucination_rate": self.hallucination_rate,
            "variance_score": self.variance_score,
            "retry_density": self.retry_density,
            "cost_per_success": self.cost_per_success,
            "latency_p95": self.latency_p95,
            "context_retention": self.context_retention,
            "tool_accuracy": self.tool_accuracy,
            "latency_mean": self.latency_mean,
            "latency_std": self.latency_std,
            "latency_cv": self.latency_cv,
            "token_mean": self.token_mean,
            "token_std": self.token_std,
            "token_cv": self.token_cv,
            "score_mean": self.score_mean,
            "score_std": self.score_std,
            "score_cv": self.score_cv,
            "model_breakdown": self.model_breakdown,
            "temperature_breakdown": self.temperature_breakdown,
            "drift_detected": self.drift_detected,
            "drift_metric": self.drift_metric,
            "drift_magnitude": self.drift_magnitude,
        }


class ReliabilityAnalyzer:
    """Analyze reliability across multiple runs."""
    
    def __init__(self, cost_per_token: float = 0.0001):
        self.cost_per_token = cost_per_token
    
    def analyze(self, runs: List[ReliabilityRun], experiment_id: str) -> ReliabilityReport:
        """Analyze a set of runs and produce a reliability report."""
        if not runs:
            return ReliabilityReport(experiment_id=experiment_id, agent_name="unknown", run_count=0)
        
        agent_name = runs[0].agent_name
        report = ReliabilityReport(
            experiment_id=experiment_id,
            agent_name=agent_name,
            run_count=len(runs),
        )
        
        # Success rate
        successes = sum(1 for r in runs if r.success)
        report.success_rate = successes / len(runs)
        
        # Hallucination rate (inverse of average hallucination score)
        halluc_scores = [r.hallucination_score for r in runs]
        report.hallucination_rate = 1.0 - (sum(halluc_scores) / len(halluc_scores) if halluc_scores else 0)
        
        # Latency statistics
        latencies = [r.latency_ms for r in runs]
        report.latency_mean = statistics.mean(latencies)
        report.latency_std = statistics.stdev(latencies) if len(latencies) > 1 else 0
        report.latency_cv = report.latency_std / report.latency_mean if report.latency_mean > 0 else 0
        report.latency_p95 = self._percentile(latencies, 0.95)
        
        # Token statistics
        tokens = [r.token_count for r in runs]
        report.token_mean = statistics.mean(tokens)
        report.token_std = statistics.stdev(tokens) if len(tokens) > 1 else 0
        report.token_cv = report.token_std / report.token_mean if report.token_mean > 0 else 0
        
        # Overall score statistics (composite of all eval scores)
        scores = [(r.hallucination_score + r.tool_accuracy + r.reflection_score) / 3 for r in runs]
        report.score_mean = statistics.mean(scores)
        report.score_std = statistics.stdev(scores) if len(scores) > 1 else 0
        report.score_cv = report.score_std / report.score_mean if report.score_mean > 0 else 0
        
        # Variance score (lower CV = higher consistency = higher reliability)
        report.variance_score = 1.0 - min(report.score_cv, 1.0)
        
        # Cost per success
        total_cost = sum(r.token_count * self.cost_per_token for r in runs)
        report.cost_per_success = total_cost / successes if successes > 0 else float('inf')
        
        # Tool accuracy
        report.tool_accuracy = statistics.mean([r.tool_accuracy for r in runs])
        
        # Retry density (estimated from reflection scores)
        report.retry_density = 1.0 - statistics.mean([r.reflection_score for r in runs])
        
        # Model breakdown
        report.model_breakdown = self._model_breakdown(runs)
        
        # Temperature breakdown
        report.temperature_breakdown = self._temperature_breakdown(runs)
        
        # Drift detection
        report.drift_detected, report.drift_metric, report.drift_magnitude = self._detect_drift(runs)
        
        return report
    
    def _model_breakdown(self, runs: List[ReliabilityRun]) -> Dict[str, Dict[str, float]]:
        """Break down metrics by model."""
        by_model: Dict[str, List[ReliabilityRun]] = {}
        for run in runs:
            by_model.setdefault(run.model_name, []).append(run)
        
        breakdown = {}
        for model, model_runs in by_model.items():
            successes = sum(1 for r in model_runs if r.success)
            latencies = [r.latency_ms for r in model_runs]
            
            breakdown[model] = {
                "run_count": len(model_runs),
                "success_rate": successes / len(model_runs),
                "avg_latency_ms": statistics.mean(latencies),
                "p95_latency_ms": self._percentile(latencies, 0.95),
                "avg_tokens": statistics.mean([r.token_count for r in model_runs]),
            }
        
        return breakdown
    
    def _temperature_breakdown(self, runs: List[ReliabilityRun]) -> Dict[float, Dict[str, float]]:
        """Break down metrics by temperature."""
        by_temp: Dict[float, List[ReliabilityRun]] = {}
        for run in runs:
            by_temp.setdefault(run.temperature, []).append(run)
        
        breakdown = {}
        for temp, temp_runs in by_temp.items():
            successes = sum(1 for r in temp_runs if r.success)
            
            breakdown[temp] = {
                "run_count": len(temp_runs),
                "success_rate": successes / len(temp_runs),
                "avg_hallucination": 1.0 - statistics.mean([r.hallucination_score for r in temp_runs]),
            }
        
        return breakdown
    
    def _detect_drift(self, runs: List[ReliabilityRun]) -> tuple:
        """Detect performance drift across runs.
        
        Returns: (drift_detected, drift_metric, drift_magnitude)
        """
        if len(runs) < 10:
            return False, None, 0.0
        
        # Check for trend in success rate over time
        window_size = max(len(runs) // 5, 5)
        
        # Compare first window vs last window
        first_window = runs[:window_size]
        last_window = runs[-window_size:]
        
        first_success = sum(1 for r in first_window if r.success) / len(first_window)
        last_success = sum(1 for r in last_window if r.success) / len(last_window)
        
        success_drift = abs(last_success - first_success)
        
        # Check latency drift
        first_latencies = [r.latency_ms for r in first_window]
        last_latencies = [r.latency_ms for r in last_window]
        
        first_p95 = self._percentile(first_latencies, 0.95)
        last_p95 = self._percentile(last_latencies, 0.95)
        
        latency_drift = abs(last_p95 - first_p95) / first_p95 if first_p95 > 0 else 0
        
        # Determine if drift is significant
        if success_drift > 0.15:
            return True, "success_rate", success_drift
        elif latency_drift > 0.30:
            return True, "latency", latency_drift
        
        return False, None, 0.0
    
    @staticmethod
    def _percentile(data: List[float], percentile: float) -> float:
        """Compute percentile."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * percentile
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_data) else f
        if f == c:
            return sorted_data[f]
        return sorted_data[f] * (c - k) + sorted_data[c] * (k - f)
    
    def compare_experiments(
        self,
        baseline: ReliabilityReport,
        current: ReliabilityReport,
    ) -> Dict[str, Any]:
        """Compare two reliability experiments.
        
        Returns diff showing changes.
        """
        diff = {
            "experiment_id": current.experiment_id,
            "baseline_id": baseline.experiment_id,
            "metrics": {},
        }
        
        metrics = [
            "success_rate",
            "hallucination_rate",
            "variance_score",
            "latency_p95",
            "tool_accuracy",
            "cost_per_success",
        ]
        
        for metric in metrics:
            baseline_val = getattr(baseline, metric, 0)
            current_val = getattr(current, metric, 0)
            
            if baseline_val != 0:
                change_pct = ((current_val - baseline_val) / baseline_val) * 100
            else:
                change_pct = 0.0
            
            diff["metrics"][metric] = {
                "baseline": baseline_val,
                "current": current_val,
                "change_pct": change_pct,
                "improved": self._is_improvement(metric, current_val, baseline_val),
            }
        
        return diff
    
    def _is_improvement(self, metric: str, current: float, baseline: float) -> bool:
        """Determine if a change is an improvement.
        
        For metrics where lower is better (latency, cost, hallucination), 
        improvement means current < baseline.
        For metrics where higher is better (success, accuracy), 
        improvement means current > baseline.
        """
        lower_is_better = {"hallucination_rate", "latency_p95", "cost_per_success", "retry_density"}
        
        if metric in lower_is_better:
            return current < baseline
        return current > baseline


class ExperimentRunner:
    """Run reliability experiments across configurations."""
    
    def __init__(self, analyzer: ReliabilityAnalyzer):
        self.analyzer = analyzer
        self._runs: List[ReliabilityRun] = []
    
    def add_run(self, run: ReliabilityRun) -> None:
        """Add a run to the experiment."""
        self._runs.append(run)
    
    def run_experiment(
        self,
        experiment_id: str,
        agent_factory: Any,
        test_cases: List[Dict[str, Any]],
        models: List[str],
        temperatures: List[float],
        num_runs_per_config: int = 5,
    ) -> ReliabilityReport:
        """Run a full reliability experiment.
        
        This is the main API for running experiments.
        """
        self._runs.clear()
        
        for test_case in test_cases:
            for model in models:
                for temp in temperatures:
                    for i in range(num_runs_per_config):
                        # Run agent and collect metrics
                        # This is a template - actual implementation depends on agent
                        pass
        
        return self.analyzer.analyze(self._runs, experiment_id)
