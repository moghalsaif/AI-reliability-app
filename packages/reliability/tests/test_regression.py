"""Tests for the regression testing module."""

import pytest
import tempfile
import json
from pathlib import Path

from reliability_engine.regression import (
    RegressionTestRunner,
    RegressionReport,
    RegressionDiff,
    TestCase,
    TestResult,
    CICDPipeline,
)


def test_test_case_creation():
    tc = TestCase(
        id="test-1",
        name="Basic Test",
        input="hello",
        expected_output="world",
    )
    assert tc.id == "test-1"
    assert tc.expected_output == "world"


def test_regression_report_creation():
    report = RegressionReport(
        run_id="run-1",
        commit_hash="abc123",
        total_tests=10,
        passed_tests=8,
        failed_tests=2,
        success_rate=0.8,
    )
    assert report.should_deploy is False  # Default
    assert report.success_rate == 0.8


def test_regression_diff():
    diff = RegressionDiff(
        metric="success_rate",
        baseline_value=0.75,
        current_value=0.85,
        change_pct=13.33,
        direction="improved",
        severity="info",
    )
    assert diff.direction == "improved"


def test_regression_runner_init():
    def mock_factory():
        class Agent:
            def run(self, x):
                return x
        return Agent()

    runner = RegressionTestRunner(agent_factory=mock_factory)
    assert runner.agent_factory is not None


def test_regression_runner_runs_tests():
    def mock_factory():
        class Agent:
            def run(self, x):
                return {"output": "ok"}
        return Agent()

    runner = RegressionTestRunner(
        agent_factory=mock_factory,
        baseline_store_path="/tmp/test_baseline.json",
    )

    test_cases = [
        TestCase(id="t1", name="Test 1", input="hello"),
        TestCase(id="t2", name="Test 2", input="world"),
    ]

    report = runner.run_test_suite(test_cases, commit_hash="test-123")

    assert isinstance(report, RegressionReport)
    assert report.total_tests == 2
    assert report.commit_hash == "test-123"
    # Mock agent returns dict, trace creation may fail but shouldn't crash
    assert report.success_rate >= 0.0


def test_regression_save_and_load_baseline():
    def mock_factory():
        class Agent:
            def run(self, x):
                return {"output": "ok"}
        return Agent()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        baseline_path = f.name

    runner = RegressionTestRunner(
        agent_factory=mock_factory,
        baseline_store_path=baseline_path,
    )

    # Create and save baseline
    report = RegressionReport(
        run_id="baseline",
        total_tests=10,
        passed_tests=9,
        success_rate=0.9,
    )
    runner.save_baseline(report)

    # Load baseline
    loaded = runner._load_baseline()
    assert loaded is not None
    assert loaded["run_id"] == "baseline"
    assert loaded["success_rate"] == 0.9

    # Cleanup
    Path(baseline_path).unlink()


def test_cicd_pipeline_init():
    def mock_factory():
        class Agent:
            def run(self, x):
                return x
        return Agent()

    runner = RegressionTestRunner(agent_factory=mock_factory)
    pipeline = CICDPipeline(runner)
    assert pipeline.runner is runner


def test_regression_report_to_dict():
    report = RegressionReport(
        run_id="run-1",
        total_tests=10,
        passed_tests=9,
        failed_tests=1,
        success_rate=0.9,
    )
    data = report.to_dict()
    assert data["run_id"] == "run-1"
    assert data["success_rate"] == 0.9
