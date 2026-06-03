# 研判预警与处置执行模块设计

> **创建日期**: 2026-06-01
> **状态**: 待审核
> **优先级**: 中

## 目标

为 disposition-execution-agent 实现行动执行和报告生成功能，完成从违规识别到处置执行的闭环。

## 背景当前已实现：
- alert_classifier.py - 预警分级
- work_order_generator.py - 工单生成

待实现：
- action_executor.py - 多渠道推送
- report_generator.py - 报告生成

## 架构设计

### 模块一：action_executor.py

#### 接口抽象

```python
class PushChannel(ABC):
    """推送渠道抽象基类"""
    
    @abstractmethod
    def execute(self, work_order: Dict[str, Any]) -> ExecutionResult:
        """执行推送操作
        
        Args:
            work_order: 工单数据
            
        Returns:
            ExecutionResult: 执行结果（成功/失败状态）
        """
        pass
    
    @abstractmethod
    def get_channel_name(self) -> str:
        """获取渠道名称"""
        pass
```

#### 具体实现类

1. **RegulatoryPlatformPush** - 监管平台推送
   - 功能：调用监管平台 API
   - 输入：work_order
   - 输出：API 响应状态
   - 错误处理：API 失败时返回失败结果，记录日志

2. **FeishuPush** - 飞书推送
   - 功能：调用飞书机器人 Webhook
   - 输入：work_order 转换为飞书消息格式
   - 输出：发送状态
   - 错误处理：Webhook 失败时返回失败结果，记录日志

3. **LocalArchive** - 本地归档
   - 功能：保存到 `/shared/outputs/work_orders/`
   - 输入：work_order
   - 输出：文件路径
   - 错误处理：文件写入失败时返回失败结果，记录日志

#### 执行器

```python
class ActionExecutor:
    """行动执行器 - 协调多个推送渠道"""
    
    def __init__(self):
        self.channels = {
            "platform": RegulatoryPlatformPush(),
            "feishu": FeishuPush(),
            "archive": LocalArchive()
        }
    
    def execute(
        self, 
        work_order: Dict[str, Any], 
        selected_channels: List[str]
    ) -> Dict[str, ExecutionResult]:
        """执行多渠道推送
        
        Args:
            work_order: 工单数据
            selected_channels: 选择的推送渠道列表
            
        Returns:
            Dict[str, ExecutionResult]: 各渠道的执行结果
        """
```

#### 返回值结构

```python
@dataclass
class ExecutionResult:
    success: bool
    channel: str
    message: str
    data: Any = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
```

### 模块二：report_generator.py

#### 报告生成器

```python
class ReportGenerator:
    """报告生成器"""
    
    def generate_alert_report(
        self, 
        work_order: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> AlertReport:
        """生成单个预警的详细报告
        
        Args:
            work_order: 工单数据
            context: 上下文信息（历史数据、趋势等）
            
        Returns:
            AlertReport: 预警报告
        """
    
    def generate_summary_report(
        self, 
        work_orders: List[Dict[str, Any]], 
        time_range: Tuple[str, str]
    ) -> SummaryReport:
        """生成汇总报告
        
        Args:
            work_orders: 工单列表
            time_range: 时间范围
            
        Returns:
            SummaryReport: 汇总报告
        """
    
    def generate_trend_report(
        self, 
        historical_data: List[Dict[str, Any]], 
        indicators: List[str]
    ) -> TrendReport:
        """生成趋势分析报告
        
        Args:
            historical_data: 历史数据
            indicators: 需要分析的指标列表
            
        Returns:
            TrendReport: 趋势报告
        """
```

#### 报告数据结构

```python
@dataclass
class AlertReport:
    """预警报告"""
    report_id: str
    generated_at: str
    alert_level: str
    violation_type: str
    confidence: float
    
    # 报告内容
    data_traceback: Dict[str, Any]
    inspection_points: List[Dict[str, Any]]
    legal_references: List[str]
    recommended_actions: List[str]
    
    # 趋势图表数据（可选）
    trend_data: Optional[Dict[str, Any]] = None

@dataclass
class SummaryReport:
    """汇总报告"""
    report_id: str
    generated_at: str
    time_range: Tuple[str, str]
    total_alerts: int
    by_level: Dict[str, int]
    by_type: Dict[str, int]
    top_enterprises: List[Dict[str, Any]]

@dataclass
class TrendReport:
    """趋势分析报告"""
    report_id: str
    generated_at: str
    time_range: Tuple[str, str]
    indicators: List[str]
    trend_data: Dict[str, List[Dict[str, Any]]]
    analysis: str
    anomalies: List[Dict[str, Any]]
```

#### 输出格式

- JSON（机器可读）- 默认
- Markdown（人类可读）- 通过 to_markdown() 方法转换
- 未来扩展：HTML/PDF

## 数据流

### 完整工作流

```
anomaly_result (异常检测)
    ↓
violation_result (违规判定)
    ↓
alert (alert_classifier) → {level, fused_confidence, ...}
    ↓
work_order (work_order_generator) → {id, inspection_points, ...}
    ↓
    ├─→ action_executor → {feishu: Success, platform: Failed}
    └─→ report_generator → {alert_report, summary_report}
```

### 与现有代码集成

在 `execution_control.py` 的工作流中：

```python
# 1. 获取违规判定结果
violation_result = self._execute_agent("rule-reasoning-agent", task)

# 2. 预警分级
alert = alert_classifier.classify_alert(anomaly_result, violation_result)

# 3. 生成工单
work_order = work_order_generator.generate_work_order(alert, context)

# 4. 执行推送 (新增)
executor = ActionExecutor()
results = executor.execute(work_order, channels=["feishu", "archive"])

# 5. 生成报告 (新增)
report_gen = ReportGenerator()
alert_report = report_gen.generate_alert_report(work_order, context)
```

## 文件结构

```
subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/
├── __init__.py (更新导出)
├── alert_classifier.py (已存在)
├── work_order_generator.py (已存在)
├── action_executor.py (新增)
└── report_generator.py (新增)

tests/subagents/
├── test_action_executor.py (新增)
└── test_report_generator.py (新增)
```

## 测试策略

### action_executor 测试

1. 测试各渠道的 execute() 方法
2. 测试多渠道并行执行
3. 测试错误处理（渠道失败不影响其他渠道）
4. 测试返回值结构

### report_generator 测试

1. 测试预警报告生成
2. 测试汇总报告生成
3. 测试趋势报告生成
4. 测试 Markdown 转换
5. 测试空数据处理

## 依赖关系

### 外部依赖（未来扩展）

- 飞书机器人 Webhook URL（配置文件）
- 监管平台 API（配置文件）
- 数据库（历史趋势数据）

### 内部依赖

- work_order_generator（输入）
- alert_classifier（上下文）

## 配置项

```yaml
# shared/configs/disposition_config.yaml (新增)
action_executor:
  feishu:
    webhook_url: "${FEISHU_WEBHOOK_URL}"
    enabled: true
  platform:
    api_url: "${PLATFORM_API_URL}"
    api_key: "${PLATFORM_API_KEY}"
    enabled: false  # 默认关闭
  archive:
    output_dir: "/shared/outputs/work_orders/"
    enabled: true

report_generator:
  output_dir: "/shared/outputs/reports/"
  formats:
    - json
    - markdown
  include_trend_charts: true
```

## 实施优先级

1. **高优先级**: action_executor.py + LocalArchive
2. **中优先级**: report_generator.py (AlertReport + SummaryReport)
3. **低优先级**: TrendReport + 外部渠道集成

## 未来扩展

1. 异步推送（使用 asyncio 或消息队列）
2. 报告模板可配置（支持 HTML/PDF）
3. 推送重试机制
4. 报告定时生成（cron 任务）
