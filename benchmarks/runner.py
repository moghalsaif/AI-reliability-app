"""Benchmark runner and regression test integration."""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any

# Import benchmark datasets
sys.path.insert(0, str(Path(__file__).parent))

from benchmarks.rag.adversarial import export_to_json as export_rag
from benchmarks.agents.suite import export_to_json as export_agents
from benchmarks.memory.stress import export_to_json as export_memory
from benchmarks.tool_use.suite import export_to_json as export_tools


class BenchmarkRegistry:
    """Registry of all benchmark suites."""
    
    def __init__(self):
        self.suites: Dict[str, Any] = {
            "rag": export_rag(),
            "agents": export_agents(),
            "memory": export_memory(),
            "tool_use": export_tools(),
        }
    
    def list_suites(self) -> List[str]:
        return list(self.suites.keys())
    
    def get_suite(self, name: str) -> List[Dict[str, Any]]:
        return self.suites.get(name, [])
    
    def get_all(self) -> Dict[str, List[Dict[str, Any]]]:
        return self.suites
    
    def export_all(self, output_dir: str = "datasets") -> None:
        """Export all benchmarks to JSON files."""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        for name, suite in self.suites.items():
            filepath = Path(output_dir) / f"{name}_benchmark.json"
            with open(filepath, "w") as f:
                json.dump(suite, f, indent=2)
            print(f"Exported {len(suite)} {name} test cases to {filepath}")


def run_all_benchmarks() -> Dict[str, Any]:
    """Run all benchmark suites and return results."""
    registry = BenchmarkRegistry()
    results = {}
    
    for suite_name in registry.list_suites():
        test_cases = registry.get_suite(suite_name)
        print(f"\n{'='*60}")
        print(f"Running {suite_name.upper()} benchmark: {len(test_cases)} tests")
        print(f"{'='*60}")
        
        suite_results = {
            "total": len(test_cases),
            "passed": 0,
            "failed": 0,
            "details": [],
        }
        
        for test in test_cases:
            # Mock run - in real implementation, this would run the agent
            passed = True  # Placeholder
            suite_results["passed" if passed else "failed"] += 1
            suite_results["details"].append({
                "id": test.get("id"),
                "passed": passed,
            })
        
        results[suite_name] = suite_results
    
    return results


if __name__ == "__main__":
    registry = BenchmarkRegistry()
    registry.export_all()
    
    print("\n" + "="*60)
    print("BENCHMARK SUMMARY")
    print("="*60)
    
    for name, suite in registry.get_all().items():
        print(f"\n{name.upper()}: {len(suite)} test cases")
