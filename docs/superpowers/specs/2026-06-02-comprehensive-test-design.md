# 废水虚假排放监测系统 - 综合测试设计

**日期**: 2026-06-02
**状态**: 设计已完成，待实施
**作者**: Claude + User

---

## 目标

验证2026-06-02架构重构（6-agent → 4-agent）的正确性，确保：
- 新增模块功能正常（ConsensusEngine、ViolationDetector、数据感知模块、处置执行模块）
- 原有功能未被破坏（回归测试）
- 边界情况和错误处理得到验证（全面评估）

---

## 测试范围

### 5个测试层

| 层级 | 测试项 | 预计耗时 |
|-----|-------|---------|
| ConfigTestLayer | 3个配置文件 | 2s |
| UnitTestLayer | 10个核心模块 | 15s |
| IntegrationTestLayer | 3个集成测试 | 20s |
| E2ETestLayer | pytest集成套件 | 15s |
| StreamTestLayer | Flask实时流（可选） | 8s |

**总计**: ~60秒（不含可选层）

---

## 脚本架构

```
run_comprehensive_tests.py
├── TestRunner（协调器）
├── 5个TestLayer子类
├── 3个Reporter子类
└── Utils工具函数
```

### TestLayer接口

```python
class TestLayer:
    """测试层基类"""
    @abstractmethod
    def run(self) -> List[TestResult]: pass

    @abstractmethod
    def name(self) -> str: pass
```

### TestResult结构

```python
@dataclass
class TestResult:
    layer: str              # 所属层级
    test_name: str          # 测试名称
    passed: bool            # 是否通过
    error: Optional[str]    # 错误信息
    duration: float         # 耗时（秒）
```

---

## 测试层级详情

### 1. ConfigTestLayer

验证配置文件可正确加载且内容符合预期。

| 测试项 | 验证内容 |
|-------|---------|
| agent_registry.yaml | 4个智能体、任务映射 |
| consensus_config.yaml | 3个场景、权重有效 |
| rule_config.yaml | 4种违规、2个过滤规则 |

### 2. UnitTestLayer

验证核心模块可导入且基础配置正确。

| 模块 | 验证内容 |
|-----|---------|
| DataAcquisitionModule | 导入成功、支持源列表 |
| DataDecompositionModule | 导入成功、8类数据映射 |
| TimeAlignmentModule | 导入成功、默认滞后2h |
| DataCleaningModule | 导入成功、有效范围定义 |
| StandardizationModule | 导入成功、字段映射表 |
| ViolationDetector | 规则加载、过滤规则加载 |
| AlertClassifier | 导入成功、阈值配置 |
| WorkOrderGenerator | 导入成功、计数器初始化 |
| ConsensusEngine | 导入成功、场景枚举 |
| ActionExecutor | 导入成功、渠道列表 |

### 3. IntegrationTestLayer

验证模块间协作。

| 测试项 | 验证内容 |
|-------|---------|
| DynamicOrchestrator | 创建执行计划、智能体调度 |
| 数据流集成 | 获取→检测→分级→融合 |
| ExecutionControl | 本地模式初始化 |

### 4. E2ETestLayer

运行现有pytest集成测试套件。

```bash
pytest tests/integration/ -v --tb=short
```

### 5. StreamTestLayer（可选）

验证Flask中间件（需要Flask运行中）。

| 测试项 | 验证内容 |
|-------|---------|
| /health | 200 OK |
| /metrics | 可访问 |
| /api/dual-stream | 可接收数据 |

---

## 报告生成

### 输出格式

1. **Terminal** - 实时输出，带✅/❌标记
2. **HTML** - 可视化报告，可展开详情
3. **JSON** - 机器可读，供CI/CD集成

### 报告结构

```json
{
  "summary": {
    "total_tests": 25,
    "passed": 23,
    "failed": 2,
    "skipped": 0,
    "duration": "58s",
    "timestamp": "2026-06-02T15:30:00"
  },
  "layers": [...],
  "failures": [...]
}
```

---

## 执行流程

```
1. 初始化
   - 创建test_reports/目录
   - 解析命令行参数

2. 顺序执行5个测试层
   - TerminalReporter实时输出
   - 失败记录跳过（continue-on-fail）
   - 不因单层失败中断

3. 生成报告
   - 汇总统计
   - 生成HTML
   - 生成JSON
   - 输出最终汇总

4. 返回退出码
   - 0: 全部通过
   - 1: 有失败
```

### 命令行参数

```
python run_comprehensive_tests.py [选项]

--skip-stream      跳过实时流测试
--verbose          详细输出
--output-dir DIR   报告目录（默认test_reports/）
--stop-on-fail     遇到失败停止（默认继续）
```

---

## 错误处理

| 错误类型 | 处理方式 |
|---------|---------|
| 配置文件不存在 | 记录失败，继续 |
| 模块导入失败 | 记录失败，继续 |
| 测试异常 | 捕获异常，记录堆栈，继续 |
| Flask未启动 | StreamTestLayer标记跳过 |

---

## 文件结构

```
E:\project\Ecological_env\
├── run_comprehensive_tests.py          # 主测试脚本
├── test_reports/                       # 报告目录
│   ├── report_*.html
│   └── report_*.json
└── docs/superpowers/specs/
    └── 2026-06-02-comprehensive-test-design.md
```

---

## 依赖项

- `pytest` - 现有集成测试
- `yaml` - 配置解析
- `jinja2` - HTML模板

---

## 实施计划

详见实施计划文档（由writing-plans技能生成）。
