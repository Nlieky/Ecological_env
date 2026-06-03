# run_comprehensive_tests.py
"""
废水虚假排放监测系统 - 综合测试脚本

自动化验证4-agent架构重构的正确性，生成多格式测试报告。
"""
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import argparse

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


class ExitCode(Enum):
    """测试退出码"""
    SUCCESS = 0
    FAILURES = 1


@dataclass
class TestResult:
    """单个测试结果"""
    layer: str              # 所属层级名称
    test_name: str          # 测试名称
    passed: bool            # 是否通过
    error: Optional[str] = None  # 错误信息
    duration: float = 0.0   # 耗时（秒）
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer": self.layer,
            "test_name": self.test_name,
            "passed": self.passed,
            "error": self.error,
            "duration": self.duration,
            "timestamp": self.timestamp
        }


@dataclass
class LayerSummary:
    """层级汇总"""
    name: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration: float = 0.0
    results: List[TestResult] = field(default_factory=list)


class TestLayer:
    """测试层抽象基类"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[TestResult] = []

    def name(self) -> str:
        """返回层级名称"""
        raise NotImplementedError

    def description(self) -> str:
        """返回层级描述"""
        raise NotImplementedError

    def run(self) -> List[TestResult]:
        """执行测试，返回结果列表"""
        raise NotImplementedError

    def _add_result(self, test_name: str, passed: bool, error: str = None, duration: float = 0.0):
        """添加测试结果"""
        result = TestResult(
            layer=self.name(),
            test_name=test_name,
            passed=passed,
            error=error,
            duration=duration
        )
        self.results.append(result)

        if self.verbose:
            status = "[OK]" if passed else "[FAIL]"
            print(f"  {status} {test_name} ({duration:.2f}s)")
            if error:
                print(f"     错误: {error}")


class ConfigTestLayer(TestLayer):
    """配置文件验证层"""

    def name(self) -> str:
        return "ConfigTestLayer"

    def description(self) -> str:
        return "验证配置文件可正确加载"

    def run(self) -> List[TestResult]:
        """执行配置文件测试"""
        import yaml

        print(f"\n[1/5] {self.description()}...")

        configs = {
            "agent_registry.yaml": "shared/configs/agent_registry.yaml",
            "consensus_config.yaml": "shared/configs/consensus_config.yaml",
            "rule_config.yaml": "shared/configs/rule_config.yaml"
        }

        for name, path in configs.items():
            start = time.time()
            try:
                config_path = PROJECT_ROOT / path
                if not config_path.exists():
                    self._add_result(
                        f"{name} 加载",
                        False,
                        f"文件不存在: {path}",
                        time.time() - start
                    )
                    continue

                with open(config_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)

                # 验证内容
                if name == "agent_registry.yaml":
                    agents = data.get('agents', {})
                    if len(agents) != 4:
                        self._add_result(
                            f"{name} 验证",
                            False,
                            f"智能体数量错误: 期望4，实际{len(agents)}",
                            time.time() - start
                        )
                        continue

                self._add_result(f"{name} 加载", True, duration=time.time() - start)

            except Exception as e:
                self._add_result(
                    f"{name} 处理",
                    False,
                    f"{type(e).__name__}: {str(e)}",
                    time.time() - start
                )

        return self.results


class UnitTestLayer(TestLayer):
    """核心模块单元测试层"""

    def name(self) -> str:
        return "UnitTestLayer"

    def description(self) -> str:
        return "验证核心模块可导入且配置正确"

    def run(self) -> List[TestResult]:
        """执行单元测试"""
        print(f"\n[2/5] {self.description()}...")

        # 定义要测试的模块
        modules = [
            ("DataAcquisitionModule",
             "subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/data_acquisition.py",
             lambda m: hasattr(m, 'supported_sources')),
            ("DataDecompositionModule",
             "subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/data_decomposition.py",
             lambda m: hasattr(m, 'data_type_mapping')),
            ("TimeAlignmentModule",
             "subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/time_alignment.py",
             lambda m: hasattr(m, 'default_lag_hours')),
            ("DataCleaningModule",
             "subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/data_cleaning.py",
             lambda m: hasattr(m, 'valid_ranges')),
            ("StandardizationModule",
             "subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/standardization.py",
             lambda m: hasattr(m, 'field_mapping')),
            ("ViolationDetector",
             "subagents/rule-reasoning-agent/skills/rule-reasoning-core/scripts/violation_detector.py",
             lambda m: hasattr(m, 'rules')),
            ("AlertClassifier",
             "subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/alert_classifier.py",
             lambda m: hasattr(m, 'thresholds')),
            ("WorkOrderGenerator",
             "subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/work_order_generator.py",
             lambda m: hasattr(m, 'work_order_counter')),
            ("ConsensusEngine",
             "subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/consensus_engine.py",
             lambda m: hasattr(m, 'config')),
            ("ActionExecutor",
             "subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/action_executor.py",
             lambda m: hasattr(m, 'channels')),
        ]

        for name, script_path, validator in modules:
            start = time.time()
            try:
                # 动态导入
                import importlib.util
                spec = importlib.util.spec_from_file_location(name, PROJECT_ROOT / script_path)
                if spec is None or spec.loader is None:
                    self._add_result(f"{name} 导入", False, f"无法加载脚本: {script_path}", time.time() - start)
                    continue

                module = importlib.util.module_from_spec(spec)
                sys.modules[name] = module
                spec.loader.exec_module(module)

                # 验证关键属性
                if validator(module):
                    self._add_result(f"{name} 验证", True, duration=time.time() - start)
                else:
                    self._add_result(f"{name} 验证", False, "缺少关键属性", time.time() - start)

            except Exception as e:
                self._add_result(
                    f"{name} 处理",
                    False,
                    f"{type(e).__name__}: {str(e)}",
                    time.time() - start
                )

        return self.results


class IntegrationTestLayer(TestLayer):
    """模块集成测试层"""

    def name(self) -> str:
        return "IntegrationTestLayer"

    def description(self) -> str:
        return "验证模块间协作"

    def run(self) -> List[TestResult]:
        """执行集成测试"""
        print(f"\n[3/5] {self.description()}...")

        # 测试1: DynamicOrchestrator
        start = time.time()
        try:
            sys.path.insert(0, str(PROJECT_ROOT / "workspace/skills/orchestrator-core/scripts"))
            from dynamic_orchestrator import DynamicOrchestrator

            orchestrator = DynamicOrchestrator()
            agent_count = len(orchestrator.available_agents)
            task_mappings = len(orchestrator.task_type_mapping)

            if agent_count == 4 and task_mappings > 0:
                self._add_result("DynamicOrchestrator 验证", True, duration=time.time() - start)
            else:
                self._add_result(
                    "DynamicOrchestrator 验证",
                    False,
                    f"智能体数: {agent_count} (期望4), 任务映射: {task_mappings}",
                    time.time() - start
                )
        except Exception as e:
            self._add_result("DynamicOrchestrator 验证", False, f"{type(e).__name__}: {str(e)}", time.time() - start)

        # 测试2: 创建执行计划
        start = time.time()
        try:
            task = {
                "task_type": "violation_detection",
                "data": {"influent": {"pH": 7.5}, "effluent": {"pH": 7.8}}
            }
            plan = orchestrator.create_execution_plan(task)

            if len(plan.agents) == 4:
                self._add_result("创建执行计划", True, duration=time.time() - start)
            else:
                self._add_result(
                    "创建执行计划",
                    False,
                    f"智能体数量错误: {len(plan.agents)} (期望4)",
                    time.time() - start
                )
        except Exception as e:
            self._add_result("创建执行计划", False, f"{type(e).__name__}: {str(e)}", time.time() - start)

        # 测试3: 数据流模块导入（暂时跳过）
        self._add_result(
            "数据流模块导入",
            False,
            "跳过（模块尚未实现）",
            0.0
        )

        # 测试4: ExecutionControl（暂时跳过）
        self._add_result(
            "ExecutionControl 初始化",
            False,
            "跳过（模块尚未实现）",
            0.0
        )

        return self.results


class E2ETestLayer(TestLayer):
    """端到端测试层"""

    def name(self) -> str:
        return "E2ETestLayer"

    def description(self) -> str:
        return "运行pytest集成测试套件"

    def run(self) -> List[TestResult]:
        """执行端到端测试"""
        print(f"\n[4/5] {self.description()}...")

        try:
            import subprocess

            start = time.time()
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/integration/", "-v", "--tb=no", "-q"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=60
            )

            duration = time.time() - start

            # 解析pytest输出
            output = result.stdout + result.stderr
            passed = result.returncode == 0

            self._add_result(
                "pytest集成测试",
                passed,
                error=None if passed else f"测试失败，退出码: {result.returncode}",
                duration=duration
            )

            if self.verbose and not passed:
                # 显示最后几行错误
                lines = output.split('\n')
                print("  失败详情:")
                for line in lines[-10:]:
                    if line.strip():
                        print(f"    {line}")

        except subprocess.TimeoutExpired:
            self._add_result("pytest集成测试", False, "测试超时（60秒）", 60.0)
        except Exception as e:
            self._add_result("pytest集成测试", False, f"{type(e).__name__}: {str(e)}", 0.0)

        return self.results


class StreamTestLayer(TestLayer):
    """实时流测试层（可选）"""

    def name(self) -> str:
        return "StreamTestLayer"

    def description(self) -> str:
        return "验证Flask中间件（可选）"

    def run(self, skip: bool = False) -> List[TestResult]:
        """执行实时流测试"""
        print(f"\n[5/5] {self.description()}...")

        if skip:
            self._add_result("Flask实时流测试", False, "跳过（--skip-stream）", 0.0)
            return self.results

        try:
            import requests
            base_url = "http://localhost:5000"

            start = time.time()
            # 测试health端点
            try:
                response = requests.get(f"{base_url}/health", timeout=5)
                if response.status_code == 200:
                    self._add_result("Flask /health", True, duration=time.time() - start)
                else:
                    self._add_result("Flask /health", False, f"状态码: {response.status_code}", time.time() - start)
            except requests.exceptions.ConnectionError:
                self._add_result("Flask连接", False, "Flask服务未启动，使用--skip-stream跳过", time.time() - start)
            except Exception as e:
                self._add_result("Flask测试", False, f"{type(e).__name__}: {str(e)}", time.time() - start)

        except ImportError:
            self._add_result("Flask测试", False, "requests库未安装", 0.0)

        return self.results


class TestRunner:
    """测试协调器"""

    def __init__(self, verbose: bool = False, skip_stream: bool = False):
        self.verbose = verbose
        self.skip_stream = skip_stream
        self.layers: List[TestLayer] = []
        self.report: Optional["TestReport"] = None

    def register_layer(self, layer: TestLayer):
        """注册测试层"""
        self.layers.append(layer)

    def run(self, stop_on_fail: bool = False) -> "TestReport":
        """执行所有测试"""
        all_results: List[TestResult] = []
        failures: List[TestResult] = []
        layer_summaries: List[LayerSummary] = []

        for layer in self.layers:
            start_time = time.time()

            # 特殊处理StreamTestLayer
            if isinstance(layer, StreamTestLayer):
                results = layer.run(skip=self.skip_stream)
            else:
                results = layer.run()

            layer_duration = time.time() - start_time

            # 汇总层级结果
            summary = LayerSummary(
                name=layer.name(),
                total=len(results),
                passed=sum(1 for r in results if r.passed),
                failed=sum(1 for r in results if not r.passed and not r.error.startswith("跳过")),
                skipped=sum(1 for r in results if r.error and "跳过" in r.error),
                duration=layer_duration,
                results=results
            )
            layer_summaries.append(summary)

            # 收集失败
            for r in results:
                all_results.append(r)
                if not r.passed and not (r.error and "跳过" in r.error):
                    failures.append(r)

            # 打印层级结果
            status = "OK" if summary.failed == 0 else "!!"
            print(f"{status} {summary.name} ({summary.passed}/{summary.total} 通过, {layer_duration:.1f}s)")

            # 如果需要失败停止
            if stop_on_fail and summary.failed > 0:
                print(f"\n!! 测试停止: {summary.name} 发现失败")
                break

        # 生成报告
        total_tests = len(all_results)
        total_passed = sum(1 for r in all_results if r.passed)
        total_failed = len(failures)
        total_skipped = sum(1 for r in all_results if r.error and "跳过" in r.error)

        self.report = TestReport(
            summary={
                "total_tests": total_tests,
                "passed": total_passed,
                "failed": total_failed,
                "skipped": total_skipped,
                "duration": f"{sum(l.duration for l in layer_summaries):.1f}s",
                "timestamp": datetime.now().isoformat()
            },
            layers=layer_summaries,
            failures=failures
        )

        return self.report


class Reporter:
    """报告生成器基类"""

    def generate(self, report: "TestReport", output_dir: Path):
        """生成报告"""
        pass


class TerminalReporter(Reporter):
    """终端输出报告"""

    def generate(self, report: "TestReport", output_dir: Path):
        """生成终端输出"""
        print("\n" + "=" * 60)
        print("  测试汇总")
        print("=" * 60)
        print(f"  总测试数: {report.summary['total_tests']}")
        print(f"  通过: {report.summary['passed']}")
        print(f"  失败: {report.summary['failed']}")
        print(f"  跳过: {report.summary['skipped']}")
        print(f"  耗时: {report.summary['duration']}")
        print("=" * 60)

        if report.failures:
            print("\n  失败详情:")
            for f in report.failures:
                print(f"    X [{f.layer}] {f.test_name}")
                if f.error:
                    print(f"       {f.error}")


class JSONReporter(Reporter):
    """JSON格式报告"""

    def generate(self, report: "TestReport", output_dir: Path):
        """生成JSON报告"""
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f"report_{timestamp}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)

        print(f"\n  JSON报告: {output_file}")


class HTMLReporter(Reporter):
    """HTML格式报告"""

    def generate(self, report: "TestReport", output_dir: Path):
        """生成HTML报告"""
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f"report_{timestamp}.html"

        html_content = self._render_html(report)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"  HTML报告: {output_file}")

    def _render_html(self, report: "TestReport") -> str:
        """渲染HTML内容"""
        summary = report.summary

        # 生成层级HTML
        layers_html = ""
        for layer in report.layers:
            status_color = "#28a745" if layer.failed == 0 else "#dc3545"
            layers_html += f"""
            <div class="layer">
                <h3 style="color: {status_color}">{layer.name} - {layer.passed}/{layer.total} 通过</h3>
                <p>耗时: {layer.duration:.1f}s | 失败: {layer.failed} | 跳过: {layer.skipped}</p>
                <table class="results-table">
                    <tr><th>测试</th><th>状态</th><th>耗时</th></tr>
            """
            for result in layer.results:
                status = "OK 通过" if result.passed else f"X 失败: {result.error}"
                layers_html += f"""
                    <tr>
                        <td>{result.test_name}</td>
                        <td>{status}</td>
                        <td>{result.duration:.2f}s</td>
                    </tr>
                """
            layers_html += "</table></div>"

        # 完整HTML模板
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>测试报告 - {summary['timestamp']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        h1 {{ color: #333; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .summary-card {{ flex: 1; padding: 15px; background: #f8f9fa; border-radius: 5px; text-align: center; }}
        .summary-card h3 {{ margin: 0; font-size: 32px; }}
        .summary-card p {{ margin: 5px 0 0; color: #666; }}
        .layer {{ margin: 20px 0; padding: 15px; background: #fafafa; border-radius: 5px; }}
        .results-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        .results-table th {{ text-align: left; padding: 8px; background: #e9ecef; }}
        .results-table td {{ padding: 8px; border-bottom: 1px solid #dee2e6; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>废水虚假排放监测系统 - 测试报告</h1>
        <p>生成时间: {summary['timestamp']}</p>
        <div class="summary">
            <div class="summary-card">
                <h3 style="color: #007bff">{summary['total_tests']}</h3>
                <p>总测试数</p>
            </div>
            <div class="summary-card">
                <h3 style="color: #28a745">{summary['passed']}</h3>
                <p>通过</p>
            </div>
            <div class="summary-card">
                <h3 style="color: #dc3545">{summary['failed']}</h3>
                <p>失败</p>
            </div>
            <div class="summary-card">
                <h3 style="color: #6c757d">{summary['skipped']}</h3>
                <p>跳过</p>
            </div>
            <div class="summary-card">
                <h3>{summary['duration']}</h3>
                <p>总耗时</p>
            </div>
        </div>
        {layers_html}
    </div>
</body>
</html>
        """
        return html


@dataclass
class TestReport:
    """完整测试报告"""
    summary: Dict[str, Any]
    layers: List[LayerSummary]
    failures: List[TestResult]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "layers": [
                {
                    "name": layer.name,
                    "status": "passed" if layer.failed == 0 else "failed",
                    "total": layer.total,
                    "passed": layer.passed,
                    "failed": layer.failed,
                    "skipped": layer.skipped,
                    "duration": f"{layer.duration:.1f}s",
                    "tests": [r.to_dict() for r in layer.results]
                }
                for layer in self.layers
            ],
            "failures": [f.to_dict() for f in self.failures],
            "timestamp": self.timestamp
        }


def main():
    """主入口"""
    parser = argparse.ArgumentParser(description="废水监测系统综合测试")
    parser.add_argument("--skip-stream", action="store_true", help="跳过实时流测试")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    parser.add_argument("--output-dir", default="test_reports", help="报告输出目录")
    parser.add_argument("--stop-on-fail", action="store_true", help="遇到失败立即停止")
    args = parser.parse_args()

    print("=" * 60)
    print("  废水虚假排放监测系统 - 综合测试")
    print("=" * 60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"报告目录: {args.output_dir}")

    # 创建测试运行器
    runner = TestRunner(verbose=args.verbose, skip_stream=args.skip_stream)

    # 注册所有测试层
    runner.register_layer(ConfigTestLayer(verbose=args.verbose))
    runner.register_layer(UnitTestLayer(verbose=args.verbose))
    runner.register_layer(IntegrationTestLayer(verbose=args.verbose))
    runner.register_layer(E2ETestLayer(verbose=args.verbose))
    runner.register_layer(StreamTestLayer(verbose=args.verbose))

    # 执行测试
    report = runner.run(stop_on_fail=args.stop_on_fail)

    # 生成报告
    output_path = PROJECT_ROOT / args.output_dir

    terminal_reporter = TerminalReporter()
    terminal_reporter.generate(report, output_path)

    json_reporter = JSONReporter()
    json_reporter.generate(report, output_path)

    html_reporter = HTMLReporter()
    html_reporter.generate(report, output_path)

    print(f"\n{'=' * 60}")
    print(f"测试完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 60}")

    # 返回退出码
    return ExitCode.FAILURES.value if report.summary['failed'] > 0 else ExitCode.SUCCESS.value


if __name__ == "__main__":
    sys.exit(main())
