"""
Performance benchmarks for multi-agent system.

Measures response times, resource usage, and throughput.
"""

import os
import sys
import time
import shutil
import statistics
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
# orchestrator-core 是连字符目录,加 scripts 到 path 后直接 import 模块
sys.path.insert(0, str(project_root / "workspace" / "skills" / "orchestrator-core" / "scripts"))

from create_session import create_session  # noqa: E402
try:
    from cleanup_sessions import list_sessions  # noqa: E402
except ImportError:
    list_sessions = None  # 旧函数已不在 cleanup_sessions;benchmark_* 非 pytest 默认跑


def benchmark_session_creation(iterations: int = 100):
    """Benchmark session creation performance."""
    print(f"\n{'='*60}")
    print(f"Benchmark: Session Creation ({iterations} iterations)")
    print(f"{'='*60}")

    times = []
    sessions = []

    for _ in range(iterations):
        start = time.perf_counter()
        session_dir = create_session()
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        sessions.append(Path(session_dir))

    # Calculate statistics
    mean_time = statistics.mean(times)
    median_time = statistics.median(times)
    min_time = min(times)
    max_time = max(times)

    print(f"  Mean: {mean_time*1000:.2f}ms")
    print(f"  Median: {median_time*1000:.2f}ms")
    print(f"  Min: {min_time*1000:.2f}ms")
    print(f"  Max: {max_time*1000:.2f}ms")

    # Cleanup
    for session_path in sessions:
        if session_path.exists():
            shutil.rmtree(session_path)

    return {
        "mean": mean_time,
        "median": median_time,
        "min": min_time,
        "max": max_time
    }


def benchmark_task_file_operations(iterations: int = 1000):
    """Benchmark task file read/write operations."""
    print(f"\n{'='*60}")
    print(f"Benchmark: Task File Operations ({iterations} iterations)")
    print(f"{'='*60}")

    import json
    import tempfile

    times = []
    task_obj = {
        "task_id": "benchmark_task",
        "task": "Benchmark test task",
        "context": {"key": "value"},
        "output_format": "json"
    }

    for _ in range(iterations):
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)

            start = time.perf_counter()

            # Write task
            task_file = session_path / "task.json"
            with open(task_file, "w", encoding="utf-8") as f:
                json.dump(task_obj, f, indent=2, ensure_ascii=False)

            # Read task
            with open(task_file, "r", encoding="utf-8") as f:
                json.load(f)

            elapsed = time.perf_counter() - start
            times.append(elapsed)

    mean_time = statistics.mean(times)
    median_time = statistics.median(times)
    min_time = min(times)
    max_time = max(times)

    print(f"  Mean: {mean_time*1000:.2f}ms")
    print(f"  Median: {median_time*1000:.2f}ms")
    print(f"  Min: {min_time*1000:.2f}ms")
    print(f"  Max: {max_time*1000:.2f}ms")

    return {
        "mean": mean_time,
        "median": median_time,
        "min": min_time,
        "max": max_time
    }


def benchmark_session_listing(iterations: int = 50):
    """Benchmark session listing operations."""
    print(f"\n{'='*60}")
    print(f"Benchmark: Session Listing ({iterations} iterations)")
    print(f"{'='*60}")

    # Create some test sessions
    sessions = []
    for _ in range(10):
        session_dir = create_session()
        sessions.append(Path(session_dir))

    try:
        times = []

        for _ in range(iterations):
            start = time.perf_counter()
            result = list_sessions()
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        mean_time = statistics.mean(times)
        median_time = statistics.median(times)
        min_time = min(times)
        max_time = max(times)

        print(f"  Mean: {mean_time*1000:.2f}ms")
        print(f"  Median: {median_time*1000:.2f}ms")
        print(f"  Min: {min_time*1000:.2f}ms")
        print(f"  Max: {max_time*1000:.2f}ms")

        return {
            "mean": mean_time,
            "median": median_time,
            "min": min_time,
            "max": max_time
        }

    finally:
        # Cleanup
        for session_path in sessions:
            if session_path.exists():
                shutil.rmtree(session_path)


def benchmark_result_file_operations(iterations: int = 1000):
    """Benchmark result file write operations."""
    print(f"\n{'='*60}")
    print(f"Benchmark: Result File Operations ({iterations} iterations)")
    print(f"{'='*60}")

    import json
    import tempfile
    from subagents.subagent_utils import write_result_file

    times = []

    for _ in range(iterations):
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            os.environ["SESSION_DIR"] = str(session_path)
            os.environ["SUBAGENT_NAME"] = "test-agent"

            start = time.perf_counter()

            write_result_file(
                result={"test": "data"},
                status="completed",
                session_dir=session_path
            )

            elapsed = time.perf_counter() - start
            times.append(elapsed)

    mean_time = statistics.mean(times)
    median_time = statistics.median(times)
    min_time = min(times)
    max_time = max(times)

    print(f"  Mean: {mean_time*1000:.2f}ms")
    print(f"  Median: {median_time*1000:.2f}ms")
    print(f"  Min: {min_time*1000:.2f}ms")
    print(f"  Max: {max_time*1000:.2f}ms")

    return {
        "mean": mean_time,
        "median": median_time,
        "min": min_time,
        "max": max_time
    }


def main():
    """Run all benchmarks."""
    print("="*60)
    print("Multi-Agent System Performance Benchmarks")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")

    results = {}

    # Run benchmarks
    try:
        results["session_creation"] = benchmark_session_creation(100)
    except Exception as e:
        print(f"Session creation benchmark failed: {e}")

    try:
        results["task_file_ops"] = benchmark_task_file_operations(1000)
    except Exception as e:
        print(f"Task file operations benchmark failed: {e}")

    try:
        results["result_file_ops"] = benchmark_result_file_operations(1000)
    except Exception as e:
        print(f"Result file operations benchmark failed: {e}")

    try:
        results["session_listing"] = benchmark_session_listing(50)
    except Exception as e:
        print(f"Session listing benchmark failed: {e}")

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    for benchmark_name, metrics in results.items():
        print(f"\n{benchmark_name}:")
        if metrics.get("mean", float('inf')) != float('inf'):
            print(f"  Average time: {metrics['mean']*1000:.2f}ms")
            print(f"  Median time: {metrics['median']*1000:.2f}ms")

    print(f"\nCompleted at: {datetime.now().isoformat()}")

    # Save results to file
    results_file = project_root / "tests" / "performance" / "benchmark_results.json"
    results_file.parent.mkdir(exist_ok=True)

    with open(results_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "results": {k: {kk: f"{vv*1000:.2f}ms" if isinstance(vv, (int, float)) else vv
                              for kk, vv in v.items()}
                      for k, v in results.items()}
        }, f, indent=2)

    print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    main()
