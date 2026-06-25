"""
Test suite runner for multi-agent system.

Runs all test modules and generates comprehensive report.
"""

import sys
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple


class TestRunner:
    """Test suite runner with reporting."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results: Dict[str, dict] = {}
        self.start_time = datetime.now()

    def run_test_module(self, module_path: Path, module_name: str) -> Tuple[bool, str]:
        """Run a single test module."""
        print(f"\n{'='*70}")
        print(f"Running: {module_name}")
        print(f"{'='*70}")

        start = time.perf_counter()
        try:
            result = subprocess.run(
                [sys.executable, str(module_path)],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per module
            )

            elapsed = time.perf_counter() - start
            success = result.returncode == 0

            # Extract summary from output
            output_lines = result.stdout.split('\n')
            summary = self._extract_summary(output_lines)

            self.results[module_name] = {
                "success": success,
                "duration_seconds": elapsed,
                "returncode": result.returncode,
                "summary": summary,
                "stdout": result.stdout,
                "stderr": result.stderr
            }

            status = "[PASS]" if success else "[FAIL]"
            print(f"{status} {module_name} ({elapsed:.2f}s)")

            if summary:
                print(f"  Summary: {summary}")

            if not success and result.stderr:
                print(f"\nError output:")
                print(result.stderr[:500])  # First 500 chars

            return success, summary

        except subprocess.TimeoutExpired:
            print(f"[TIMEOUT] {module_name} exceeded 300 seconds")
            self.results[module_name] = {
                "success": False,
                "duration_seconds": 300,
                "error": "timeout"
            }
            return False, "timeout"

        except Exception as e:
            print(f"[ERROR] Failed to run {module_name}: {e}")
            self.results[module_name] = {
                "success": False,
                "error": str(e)
            }
            return False, str(e)

    def _extract_summary(self, output_lines: List[str]) -> str:
        """Extract test summary from output."""
        for line in reversed(output_lines):
            if "Results:" in line or "passed" in line.lower():
                return line.strip()
        return ""

    def run_all_tests(self) -> bool:
        """Run all test modules."""
        print("="*70)
        print("Multi-Agent System Test Suite")
        print("="*70)
        print(f"Started at: {self.start_time.isoformat()}")
        print(f"Project root: {self.project_root}")

        # Define test modules
        test_modules = [
            ("tests/integration/test_e2e_workflow.py", "E2E Workflow Tests"),
            ("tests/integration/test_error_scenarios.py", "Error Scenario Tests"),
            ("tests/performance/test_benchmarks.py", "Performance Benchmarks"),
        ]

        all_passed = True

        for module_path, module_name in test_modules:
            full_path = self.project_root / module_path
            if not full_path.exists():
                print(f"[SKIP] {module_name} - file not found: {module_path}")
                continue

            success, _ = self.run_test_module(full_path, module_name)
            if not success:
                all_passed = False

        return all_passed

    def generate_report(self) -> Dict:
        """Generate comprehensive test report."""
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()

        passed_count = sum(1 for r in self.results.values() if r.get("success"))
        failed_count = len(self.results) - passed_count

        report = {
            "timestamp": end_time.isoformat(),
            "duration_seconds": total_duration,
            "total_tests": len(self.results),
            "passed": passed_count,
            "failed": failed_count,
            "success_rate": f"{(passed_count/len(self.results)*100):.1f}%" if self.results else "N/A",
            "modules": self.results
        }

        return report

    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*70)
        print("TEST SUITE SUMMARY")
        print("="*70)

        passed_count = sum(1 for r in self.results.values() if r.get("success"))
        failed_count = len(self.results) - passed_count

        print(f"\nTotal modules: {len(self.results)}")
        print(f"Passed: {passed_count}")
        print(f"Failed: {failed_count}")

        if self.results:
            success_rate = (passed_count / len(self.results)) * 100
            print(f"Success rate: {success_rate:.1f}%")

        print("\nModule Results:")
        for name, result in self.results.items():
            status = "[PASS]" if result.get("success") else "[FAIL]"
            duration = result.get("duration_seconds", 0)
            print(f"  {status} {name} ({duration:.2f}s)")

        if failed_count > 0:
            print("\n" + "="*70)
            print("FAILED MODULES DETAILS:")
            print("="*70)
            for name, result in self.results.items():
                if not result.get("success"):
                    print(f"\n{name}:")
                    print(f"  Error: {result.get('error', 'Unknown')}")
                    if result.get("stderr"):
                        print(f"  Stderr: {result['stderr'][:200]}")

    def save_report(self, output_path: Path):
        """Save test report to JSON file."""
        report = self.generate_report()

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\nReport saved to: {output_path}")


def main():
    """Main entry point."""
    project_root = Path(__file__).parent.parent

    runner = TestRunner(project_root)

    # Run all tests
    all_passed = runner.run_all_tests()

    # Print summary
    runner.print_summary()

    # Save report
    report_path = project_root / "tests" / "test_results" / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    runner.save_report(report_path)

    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
