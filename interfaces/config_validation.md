# 配置验证规范

## 版本信息

- **版本**: v1.0
- **创建日期**: 2026-05-15
- **适用范围**: 全局配置、子智能体注册表、专利配置

## 一、概述

### 1.1 目的

定义配置文件的验证规则，确保：

1. 配置文件格式正确
2. 配置值在合理范围内
3. 配置之间保持一致性
4. 配置与代码实现匹配

### 1.2 配置文件清单

| 文件 | 用途 | 格式 |
|------|------|------|
| `config/config.yaml` | 全局配置 | YAML |
| `shared/configs/config.v2.yaml` | 统一配置（新） | YAML |
| `shared/configs/subagent_registry.json` | 子智能体注册表 | JSON |
| `shared/configs/skill_registry.json` | 技能注册表 | JSON |
| `shared/configs/patent_config.yaml` | 专利参数配置 | YAML |
| `shared/configs/validation_rules.yaml` | 验证规则 | YAML |

## 二、配置文件规范

### 2.1 统一配置格式 (config.v2.yaml)

```yaml
# ========== 系统基础信息 ==========
system:
  name: "废水虚假排放智能监测系统"
  version: "2.1.0"
  environment: "development"  # development, testing, production

# ========== 主智能体配置 ==========
master_agent:
  enabled: true
  class: "MasterAgentLayer"
  module: "master_agent_layer"
  config:
    # 结果复用配置
    result_reuse_enabled: true
    max_cache_size: 1000
    cache_ttl: 3600

    # 任务处理配置
    max_concurrent_tasks: 10
    task_timeout: 300

    # LLM配置
    llm_model: "claude-opus-4-7"
    llm_temperature: 0.0
    llm_max_tokens: 4096

# ========== 任务编排层配置 ==========
task_orchestration:
  enabled: true
  max_parallel_tasks: 5
  default_timeout: 30
  retry_policy:
    max_retries: 3
    backoff_factor: 2
    retry_on_timeout: true

# ========== 子智能体配置 ==========
subagents:
  data_governance_agent:
    id: "data-governance-agent"
    name: "数据治理子智能体"
    class: "DataGovernanceAgent"
    enabled: true
    priority: 1
    timeout: 30
    config:
      data_sources: ["csv", "api"]
      max_data_size: 1000000

  feature_analysis_agent:
    id: "feature-analysis-agent"
    name: "特征与关系分析子智能体"
    class: "FeatureAnalysisAgent"
    enabled: true
    priority: 2
    timeout: 30
    config:
      feature_extraction_methods: ["statistical", "frequency"]

  anomaly_detection_agent:
    id: "anomaly-detection-agent"
    name: "异常检测子智能体"
    class: "AnomalyDetectionAgent"
    enabled: true
    priority: 3
    timeout: 60
    config:
      algorithms: ["isolation_forest", "one_class_svm"]
      threshold: 0.7

  rule_reasoning_agent:
    id: "rule-reasoning-agent"
    name: "规则推理子智能体"
    class: "RuleReasoningAgent"
    enabled: true
    priority: 4
    timeout: 30
    config:
      regulation_sources: ["gb18918", "hj915"]

# ========== 数据源配置 ==========
data_sources:
  csv:
    enabled: true
    path: "data/"
    encoding: "utf-8"

  api:
    enabled: false
    base_url: ""
    timeout: 30

# ========== 缓存配置 ==========
cache:
  type: "file"  # file, redis, memory
  file:
    path: "shared/cache/"
    max_size_mb: 1024

# ========== 日志配置 ==========
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  format: "detailed"
  file:
    enabled: true
    path: "logs/"
    rotation: "daily"
```

### 2.2 验证规则格式

```yaml
# ========== 系统基础信息验证 ==========
system:
  required_fields:
    - version
    - environment

  validation_rules:
    version:
      pattern: "^\\d+\\.\\d+\\.\\d+$"
      error_message: "版本号格式应为 x.y.z"

    environment:
      allowed_values: ["development", "testing", "production"]
      error_message: "环境必须是 development, testing 或 production"

# ========== 主智能体配置验证 ==========
master_agent:
  validation_rules:
    max_concurrent_tasks:
      type: "integer"
      min_value: 1
      max_value: 100
      error_message: "最大并发任务数必须在 1-100 之间"

    cache_ttl:
      type: "integer"
      min_value: 60
      max_value: 86400
      error_message: "缓存过期时间必须在 60-86400 秒之间"

# ========== 子智能体配置验证 ==========
subagents:
  required_fields:
    - id
    - name
    - class
    - enabled
    - priority

  validation_rules:
    priority:
      type: "integer"
      min_value: 1
      max_value: 10
      error_message: "优先级必须在 1-10 之间"

    timeout:
      type: "integer"
      min_value: 10
      max_value: 600
      error_message: "超时时间必须在 10-600 秒之间"

# ========== 专利参数验证 ==========
patent:
  result_reuse:
    jaccard_threshold:
      type: "float"
      min_value: 0.0
      max_value: 1.0
      error_message: "Jaccard阈值必须在 0-1 之间"

    semantic_threshold:
      type: "float"
      min_value: 0.0
      max_value: 1.0
      error_message: "语义相似度阈值必须在 0-1 之间"
```

## 三、配置一致性验证

### 3.1 跨文件一致性检查

| 检查项 | 涉及文件 | 说明 |
|--------|---------|------|
| 子智能体ID一致性 | config.v2.yaml, subagent_registry.json | ID必须匹配 |
| 技能注册一致性 | skill_registry.json, subagents/*/skills/ | 注册技能必须存在 |
| 专利参数一致性 | patent_config.yaml, 代码实现 | 阈值必须一致 |

### 3.2 命名规范

| 对象类型 | 命名规则 | 示例 |
|---------|---------|------|
| 子智能体ID | 小写+连字符 | `data-governance-agent` |
| 配置键 | 小写+下划线 | `max_concurrent_tasks` |
| 状态值 | 小写+下划线 | `idle`, `busy` |
| 错误码 | 大写+下划线 | `AGENT_TIMEOUT` |

## 四、配置加载流程

```
启动系统
    ↓
加载 config.v2.yaml
    ↓
验证配置格式和内容
    ↓
┌─ 通过 ─────────┐
│                 ↓
│          加载子智能体注册表
│                 ↓
│          验证子智能体配置一致性
│                 ↓
│          加载专利配置
│                 ↓
│          验证专利参数
│                 ↓
│          加载技能注册表
│                 ↓
│          验证技能配置
│                 ↓
│          标记配置加载完成
└─────────────────┘
    ↓
系统就绪
```

## 五、配置验证API

### 5.1 单文件验证

```python
def validate_config_file(file_path: str) -> Dict[str, Any]:
    """
    验证单个配置文件

    Returns:
        {
            "valid": bool,
            "errors": List[str],
            "warnings": List[str]
        }
    """
    pass
```

### 5.2 全局配置验证

```python
def validate_all_configs() -> Dict[str, Any]:
    """
    验证所有配置文件

    Returns:
        {
            "valid": bool,
            "files": {
                "config.v2.yaml": {...},
                "subagent_registry.json": {...},
                ...
            },
            "consistency_check": {...}
        }
    """
    pass
```

### 5.3 配置一致性检查

```python
def check_config_consistency() -> Dict[str, Any]:
    """
    检查配置文件之间的一致性

    Returns:
        {
            "consistent": bool,
            "issues": List[str]
        }
    """
    pass
```

## 六、错误处理

### 6.1 验证错误级别

| 级别 | 说明 | 处理方式 |
|------|------|----------|
| ERROR | 严重错误，系统无法启动 | 记录错误，终止启动 |
| WARNING | 警告，使用默认值 | 记录警告，继续启动 |
| INFO | 信息，仅提示 | 静默处理 |

### 6.2 常见错误

| 错误代码 | 说明 | 处理建议 |
|---------|------|----------|
| CONFIG_FILE_NOT_FOUND | 配置文件不存在 | 检查文件路径 |
| CONFIG_FORMAT_ERROR | 配置格式错误 | 检查YAML/JSON语法 |
| CONFIG_VALUE_INVALID | 配置值无效 | 检查配置值范围 |
| CONFIG_INCONSISTENT | 配置不一致 | 检查跨文件配置 |

## 七、附录

### 7.1 配置文件示例

见 `shared/configs/examples/` 目录：

- `config.v2.example.yaml`
- `subagent_registry.example.json`
- `patent_config.example.yaml`

### 7.2 相关文档

- [状态管理规范](state_management.md)
- [子智能体通信协议](subagent_protocol.md)
- [技能接口规范](skill_interface.md)
