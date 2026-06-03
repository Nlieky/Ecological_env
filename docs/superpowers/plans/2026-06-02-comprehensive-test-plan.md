# 综合测试脚本实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建 `run_comprehensive_tests.py` 综合测试脚本，自动化验证4-agent架构重构的正确性，生成终端+HTML+JSON三种格式的测试报告。

**Architecture:** 单一测试脚本，采用TestLayer抽象层级设计，TestRunner协调执行，三种Reporter分别生成不同格式的报告。

**Tech Stack:** Python 3.10+, yaml, jinja2, pytest

---

## 文件结构概览

### 新建文件
- `run_comprehensive_tests.py` - 主测试脚本（约500行）
- `test_reports/` - 报告输出目录（运行时自动创建）

### 依赖项
- `yaml` - 配置文件解析
- `jinja2` - HTML模板渲染
- `pytest` - 现有集成测试执行

---

## 阶段1: 基础框架搭建（20分钟）

### Task 1: 创建测试脚本基础结构

**Files:**
- Create: `run_comprehensive_tests.py`

- [ ] **Step 1: 创建基础框架和导入**

```python
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

    print(f"开始执行综合测试 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"报告目录: {args.output_dir}")
    print("=" * 60)

    # TODO: 执行测试层级
    # TODO: 生成报告

    return ExitCode.SUCCESS.value


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: 运行验证基础结构**

```bash
cd E:\project\Ecological_env
python run_comprehensive_tests.py --help
```

Expected: 显示帮助信息

- [ ] **Step 3: 提交**

```bash
git add run_comprehensive_tests.py
git commit -m "test: add comprehensive test script foundation"
```

---

### Task 2: 实现TestLayer抽象基类

**Files:**
- Modify: `run_comprehensive_tests.py`

- [ ] **Step 1: 添加TestLayer基类**

```python
# 在imports后添加

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
            status = "✅" if passed else "❌"
            print(f"  {status} {test_name} ({duration:.2f}s)")
            if error:
                print(f"     错误: {error}")
```

- [ ] **Step 2: 运行验证语法**

```bash
cd E:\project\Ecological_env
python -c "from run_comprehensive_tests import TestLayer; print('✅ TestLayer imported')"
```

Expected: ✅ TestLayer imported

- [ ] **Step 3: 提交**

```bash
git add run_comprehensive_tests.py
git commit -m "test: add TestLayer base class"
```

---

## 阶段2: 配置层测试实现（15分钟）

### Task 3: 实现ConfigTestLayer

**Files:**
- Modify: `run_comprehensive_tests.py`

- [ ] **Step 1: 实现ConfigTestLayer类**

```python
# 在TestLayer类后添加

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
```

- [ ] **Step 2: 添加临时测试代码到main()**

```python
# 在main()中TODO前添加

    # 测试ConfigTestLayer
    config_layer = ConfigTestLayer(verbose=args.verbose)
    config_results = config_layer.run()
    for r in config_results:
        print(f"{'✅' if r.passed else '❌'} {r.test_name}")
```

- [ ] **Step 3: 运行验证**

```bash
cd E:\project\Ecological_env
python run_comprehensive_tests.py
```

Expected: 显示3个配置文件的测试结果

- [ ] **Step 4: 移除临时测试代码**

删除刚添加到main()的测试代码

- [ ] **Step 5: 提交**

```bash
git add run_comprehensive_tests.py
git commit -m "test: implement ConfigTestLayer"
```

---

## 阶段3: 单元测试层实现（20分钟）

### Task 4: 实现UnitTestLayer

**Files:**
- Modify: `run_comprehensive_tests.py`

- [ ] **Step 1: 实现UnitTestLayer类**

```python
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
```

- [ ] **Step 2: 临时测试验证**

```bash
cd E:\project\Ecological_env
python -c "
from run_comprehensive_tests import UnitTestLayer
layer = UnitTestLayer(verbose=True)
results = layer.run()
print(f'通过: {sum(1 for r in results if r.passed)}/{len(results)}')
"
```

Expected: 显示模块测试结果

- [ ] **Step 3: 提交**

```bash
git add run_comprehensive_tests.py
git commit -m "test: implement UnitTestLayer"
```

---

## 阶段4: 集成测试层实现（15分钟）

### Task 5: 实现IntegrationTestLayer

**Files:**
- Modify: `run_comprehensive_tests.py`

- [ ] **Step 1: 实现IntegrationTestLayer类**

```python
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

        # 测试2: 数据流导入验证
        start = time.time()
        try:
            from data_acquisition import DataAcquisitionModule
            from violation_detector import ViolationDetector
            from alert_classifier import AlertClassifier
            from consensus_engine import ConsensusEngine

            self._add_result("数据流模块导入", True, duration=time.time() - start)
        except Exception as e:
            self._add_result("数据流模块导入", False, f"{type(e).__name__}: {str(e)}", time.time() - start)

        # 测试3: ExecutionControl
        start = time.time()
        try:
            from execution_control import ExecutionControlModule

            control = ExecutionControlModule(llm_client=None)
            self._add_result("ExecutionControl 初始化", True, duration=time.time() - start)
        except Exception as e:
            self._add_result("ExecutionControl 初始化", False, f"{type(e).__name__}: {str(e)}", time.time() - start)

        return self.results
```

- [ ] **Step 2: 提交**

```bash
git add run_comprehensive_tests.py
git commit -m "test: implement IntegrationTestLayer"
```

---

## 阶段5: 端到端测试层实现（15分钟）

### Task 6: 实现E2ETestLayer

**Files:**
- Modify: `run_comprehensive_tests.py`

- [ ] **Step 1: 实现E2ETestLayer类**

```python
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
```

- [ ] **Step 2: 提交**

```bash
git add run_comprehensive_tests.py
git commit -m "test: implement E2ETestLayer"
```

---

## 阶段6: 实时流测试层实现（10分钟）

### Task 7: 实现StreamTestLayer

**Files:**
- Modify: `run_comprehensive_tests.py`

- [ ] **Step 1: 实现StreamTestLayer类**

```python
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
```

- [ ] **Step 2: 提交**

```bash
git add run_comprehensive_tests.py
git commit -m "test: implement StreamTestLayer"
```

---

## 阶段7: TestRunner协调器实现（10分钟）

### Task 8: 实现TestRunner

**Files:**
- Modify: `run_comprehensive_tests.py`

- [ ] **Step 1: 实现TestRunner类**

```python
class TestRunner:
    """测试协调器"""

    def __init__(self, verbose: bool = False, skip_stream: bool = False):
        self.verbose = verbose
        self.skip_stream = skip_stream
        self.layers: List[TestLayer] = []
        self.report: Optional[TestReport] = None

    def register_layer(self, layer: TestLayer):
        """注册测试层"""
        self.layers.append(layer)

    def run(self, stop_on_fail: bool = False) -> TestReport:
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
            status = "✅" if summary.failed == 0 else "⚠️ "
            print(f"{status} {summary.name} ({summary.passed}/{summary.total} 通过, {layer_duration:.1f}s)")

            # 如果需要失败停止
            if stop_on_fail and summary.failed > 0:
                print(f"\n⚠️  测试停止: {summary.name} 发现失败")
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
```

- [ ] **Step 2: 提交**

```bash
git add run_comprehensive_tests.py
git commit -m "test: implement TestRunner coordinator"
```

---

## 阶段8: 报告生成器实现（20分钟）

### Task 9: 实现Reporter类

**Files:**
- Modify: `run_comprehensive_tests.py`

- [ ] **Step 1: 实现Reporter基类和子类**

```python
class Reporter:
    """报告生成器基类"""
    def generate(self, report: TestReport, output_dir: Path): pass


class TerminalReporter(Reporter):
    """终端输出报告"""

    def generate(self, report: TestReport, output_dir: Path):
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
                print(f"    ❌ [{f.layer}] {f.test_name}")
                if f.error:
                    print(f"       {f.error}")


class JSONReporter(Reporter):
    """JSON格式报告"""

    def generate(self, report: TestReport, output_dir: Path):
        """生成JSON报告"""
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f"report_{timestamp}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)

        print(f"\n  JSON报告: {output_file}")


class HTMLReporter(Reporter):
    """HTML格式报告"""

    def generate(self, report: TestReport, output_dir: Path):
        """生成HTML报告"""
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f"report_{timestamp}.html"

        html_content = self._render_html(report)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"  HTML报告: {output_file}")

    def _render_html(self, report: TestReport) -> str:
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
                status = "✅ 通过" if result.passed else f"❌ 失败: {result.error}"
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
```

- [ ] **Step 2: 提交**

```bash
git add run_comprehensive_tests.py
git commit -m "test: implement Reporters (Terminal, JSON, HTML)"
```

---

## 阶段9: 主函数完善（10分钟）

### Task 10: 完善main()函数

**Files:**
- Modify: `run_comprehensive_tests.py`

- [ ] **Step 1: 替换main()函数为完整实现**

```python
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
    return ExitCode.FAIL.value if report.summary['failed'] > 0 else ExitCode.SUCCESS.value
```

- [ ] **Step 2: 提交**

```bash
git add run_comprehensive_tests.py
git commit -m "test: complete main() function"
```

---

## 阶段10: 最终测试和文档（10分钟）

### Task 11: 运行完整测试并验证

**Files:**
- Test: `run_comprehensive_tests.py`

- [ ] **Step 1: 运行完整测试（跳过实时流）**

```bash
cd E:\project\Ecological_env
python run_comprehensive_tests.py --skip-stream --verbose
```

Expected: 显示所有测试层的进度和最终汇总

- [ ] **Step 2: 验证报告生成**

```bash
# 检查报告文件
dir test_reports\
# 应该看到 report_*.html 和 report_*.json
```

Expected: 两个报告文件已生成

- [ ] **Step 3: 验证help命令**

```bash
python run_comprehensive_tests.py --help
```

Expected: 显示所有命令行选项

- [ ] **Step 4: 提交最终版本**

```bash
git add run_comprehensive_tests.py
git commit -m "test: complete comprehensive test script"
```

---

### Task 12: 创建使用文档

**Files:**
- Create: `docs/test_guide.md`

- [ ] **Step 1: 编写测试使用文档**

```markdown
# 综合测试使用指南

## 快速开始

### 基本测试（推荐）

```bash
cd E:\project\Ecological_env
python run_comprehensive_tests.py --skip-stream
```

### 详细输出

```bash
python run_comprehensive_tests.py --skip-stream --verbose
```

### 完整测试（含Flask）

```bash
# 先启动Flask（另一个终端）
cd middleware
python app_orchestrator.py

# 运行测试
python run_comprehensive_tests.py
```

## 命令行选项

| 选项 | 说明 |
|-----|------|
| `--skip-stream` | 跳过实时流测试（推荐，Flask未启动时） |
| `--verbose` | 显示详细测试输出 |
| `--output-dir DIR` | 指定报告输出目录（默认test_reports/） |
| `--stop-on-fail` | 遇到失败立即停止 |

## 报告位置

测试完成后，报告生成在 `test_reports/` 目录：
- `report_YYYYMMDD_HHMMSS.html` - HTML可视化报告
- `report_YYYYMMDD_HHMMSS.json` - JSON机器可读报告

## 测试层级

1. **ConfigTestLayer** - 配置文件验证
2. **UnitTestLayer** - 核心模块单元测试
3. **IntegrationTestLayer** - 模块集成测试
4. **E2ETestLayer** - pytest集成测试套件
5. **StreamTestLayer** - Flask实时流测试（可选）

## 故障排查

### 模块导入失败

检查Python路径是否正确，确保在项目根目录执行。

### pytest测试失败

查看详细输出：`python run_comprehensive_tests.py --verbose`

### Flask测试跳过

这是正常的，Flask未启动时StreamTestLayer会自动跳过。
```

- [ ] **Step 2: 提交文档**

```bash
git add docs/test_guide.md
git commit -m "docs: add comprehensive test usage guide"
```

---

## 验收标准

完成所有任务后，系统应该具备以下能力：

1. ✅ 单一脚本 `run_comprehensive_tests.py` 可执行所有测试
2. ✅ 5个测试层按顺序执行
3. ✅ 失败测试被记录但不会中断执行（默认）
4. ✅ 生成终端+HTML+JSON三种格式报告
5. ✅ 支持 `--skip-stream` 跳过Flask测试
6. ✅ 支持 `--verbose` 详细输出
7. ✅ 支持 `--stop-on-fail` 失败停止
8. ✅ 支持 `--output-dir` 自定义报告目录
9. ✅ 测试报告保存在 `test_reports/` 目录
10. ✅ HTML报告可打开查看

---

## 总计任务数

- 阶段1（基础框架）: 2个任务
- 阶段2（配置层）: 1个任务
- 阶段3（单元层）: 1个任务
- 阶段4（集成层）: 1个任务
- 阶段5（E2E层）: 1个任务
- 阶段6（流测试层）: 1个任务
- 阶段7（协调器）: 1个任务
- 阶段8（报告器）: 1个任务
- 阶段9（主函数）: 1个任务
- 阶段10（最终测试）: 2个任务

**总计: 12个任务，预计耗时: 2小时**
