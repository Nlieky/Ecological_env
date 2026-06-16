# Changelog

All notable changes to the wastewater monitoring system will be documented in this file.

## [2.2.0] - 2026-06-05

### Web界面增强与智能问答系统

**新增 - Web智能查询界面**
- **自然语言查询接口** (`middleware/query_interface.py`)
  - LLM驱动的意图解析（Haiku快速模型）
  - 自动时间范围识别和指标提取
  - 历史数据获取器集成
  - 支持中英文自然语言查询
- **多维度数据感知集成**
  - 自动调用multi-dimensional-data-perception-agent进行数据预处理
  - 时序数据质量控制和标准化
  - 数据分解和多维分类
- **异常检测智能体集成**
  - 自动调用anomaly-detection-agent进行异常分析
  - 支持11种异常模式识别（spike, drop, trend, constant等）
  - 置信度评估和严重度分级
- **LLM报告生成**
  - Sonnet模型生成自然语言监测报告
  - 包含数据概况、异常情况、建议措施

**新增 - Web前端界面**
- **查询面板** (`middleware/static/index.html`)
  - 自然语言输入框
  - 实时状态显示和进度提示
  - 结果展示（摘要+可视化图表）
- **实时监控面板**
  - Grafana仪表板嵌入（iframe集成）
  - 备选跳转按钮
  - 仪表板URL: http://localhost:3000/goto/cfo42tuskodtsf?orgId=1
- **分析报告面板**
  - Chart.js 4.x时序图表可视化
  - 多指标显示（pH、COD、TN、NH3-N、TP）
  - 异常点红色标注
  - 交互式tooltip显示异常详情
  - 图例点击切换指标显示
- **响应式设计**
  - 支持桌面和移动设备
  - 现代化UI设计

**新增 - 图表可视化模块**
- **综合时序图表** (`middleware/static/js/charts.js`)
  - createMultiIndicatorChart: 多指标时序图表
  - createSingleIndicatorChart: 单指标详细图表
  - 异常点自动标注和索引匹配
  - 颜色编码（pH绿色、COD蓝色、TN紫色、NH3-N橙色、TP粉色）
- **数据流处理**
  - API完整时序数据返回（influent + effluent）
  - 异常详情结构化返回（indicator, times, score, pattern, severity）
  - 索引到时间戳自动转换

**新增 - 历史数据获取器**
- **HistoricalDataFetcher** (`middleware/historical_data_fetcher.py`)
  - CSV数据读取（pollution_water_*.csv）
  - 时间范围查询和过滤
  - 数据源选择（influent/effluent/both）
  - 指标筛选（pH、COD、TN、NH3-N、TP）
  - 列名标准化（中文→英文映射）

**配置文件**
- `middleware/.env` - LLM API密钥配置
- `shared/configs/llm_config.yaml` - LLM模型和提示词配置
- `grafana.ini` - allow_embedding配置（支持iframe嵌入）

**API端点**
| 端点 | 方法 | 说明 |
|------|------|------|
| /api/query | POST | 自然语言查询接口 |
| /api/web/query | POST | Web界面查询接口 |
| /api/web/status | GET | 服务状态检查 |
| /api/web/monitoring | GET | 监控数据接口 |

**已验证功能**
- ✅ 自然语言查询解析（中英文）
- ✅ 多指标时序数据可视化
- ✅ 异常点自动标注（索引→时间戳转换）
- ✅ Grafana仪表板嵌入
- ✅ 响应式布局
- ✅ LLM主智能体和子智能体协同分析
- ✅ 分析过程日志终端显示

**技术栈**
- 后端: Python Flask + Anthropic Claude API
- 前端: HTML5 + CSS3 + Vanilla JavaScript
- 图表: Chart.js 4.x
- 监控: Grafana 8.x

---

## [2.1.0] - 2026-06-02

### Major Architecture Refactor (6-agent → 4-agent)

**Removed Agents:**
- `data-governance-agent` - Capabilities merged into multi-dimensional-data-perception-agent
- `feature-analysis-agent` - Capabilities migrated to anomaly-detection-agent

**New Agents:**
- `multi-dimensional-data-perception-agent` - Multi-source data acquisition, time alignment, data cleaning, standardization, decomposition
- `disposition-execution-agent` - Fusion consensus, alert classification, work order generation, action execution

**Updated Agents:**
- `anomaly-detection-agent` - Now includes feature analysis capabilities (time series features, correlation, trend analysis)
- `rule-reasoning-agent` - Enhanced with rule-based violation detector

### Added - Consensus Engine Module
- **ConsensusEngine** (`subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/consensus_engine.py`)
  - Dynamic weight adjustment for anomaly/violation result fusion
  - Scene-based fusion strategies (default, critical, normal)
  - Confidence-based adaptation
  - Comprehensive fusion metadata
- **Configuration** (`shared/configs/consensus_config.yaml`)
  - Base weights for anomaly and violation sources
  - Scene-specific configurations
  - Dynamic adaptation parameters
- **Integration** - Integrated into AlertClassifier for intelligent fusion

### Added - Violation Detection Module
- **ViolationDetector** (`subagents/rule-reasoning-agent/skills/rule-reasoning-core/scripts/violation_detector.py`)
  - Rule-based violation matching
  - Four violation types: bottle_interference, artificial_fitting, dilution_discharge, malicious_evasion
  - False positive filtering (equipment shutdown, backwash scenarios)
  - Confidence scoring
- **Configuration** (`shared/configs/rule_config.yaml`)
  - Violation rules with conditions and legal references
  - False positive filters
  - Priority ordering

### Added - Data Perception Modules
All modules in `subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/`:
- `data_acquisition.py` - Multi-source data acquisition (CSV, API, database)
- `data_decomposition.py` - Multi-dimensional data classification (8 data types)
- `time_alignment.py` - Time lag handling for influent/effluent alignment
- `data_cleaning.py` - Data quality control (missing values, anomaly detection)
- `standardization.py` - Field name mapping and format standardization

### Added - Disposition Execution Modules
All modules in `subagents/disposition-execution-agent/skills/disposition-execution-core/scripts/`:
- `alert_classifier.py` - Three-level alert classification (general, moderate, serious)
- `work_order_generator.py` - Work order generation with traceback, inspection points, legal references
- `action_executor.py` - Multi-channel execution (regulatory platform, Feishu, archive)
- `report_generator.py` - Alert and trend report generation
- `consensus_engine.py` - Fusion consensus algorithm

### Added - Master Agent Components
- **DynamicOrchestrator** (`workspace/skills/orchestrator-core/scripts/dynamic_orchestrator.py`)
  - Agent registry loading
  - Task type to agent mapping
  - Execution plan generation
  - Parallel execution detection
- **Agent Registry** (`shared/configs/agent_registry.yaml`)
  - All four sub-agents registered with capabilities
  - Task type mappings (violation_detection, analysis_query, historical_review, alert_response)
  - Execution mode definitions

### Changed - Orchestrator Core
Updated `workspace/skills/orchestrator-core/scripts/execution_control.py`:
- Integrated DynamicOrchestrator for agent coordination
- Updated SUB_AGENTS configuration for new agent paths
- Renamed methods (_execute_data_governance → _execute_data_perception)
- Updated LLM prompts for new agent names and capabilities

### Changed - Integration Tests
- Updated all integration tests for new 4-agent architecture
- Added `tests/integration/test_e2e_architecture.py` - End-to-end architecture validation
- Updated `tests/test_master_agent.py` - Master agent tests with new agents
- Updated test paths and imports throughout

### Fixed
- Added pytest to requirements.txt and fixed test import paths
- Improved error handling in data perception modules
- Enhanced code quality across violation_detector and data modules
- Standardized error reporting in data acquisition

### Test Results
- Consensus engine tests: 10/10 passing ✅
- E2E architecture tests: 4/4 passing ✅
- Full pipeline tests: 3/3 passing ✅

---

## [2.0.0] - 2026-05-29

### Initial Architecture
- 6-agent system: master + 5 sub-agents
- Orchestrator-core pipeline with LLM coordination
- Data governance, feature analysis, anomaly detection, rule reasoning, disposition execution

---

## Version History Summary

| Version | Date | Major Changes |
|---------|------|---------------|
| 2.2.0 | 2026-06-05 | Web界面增强、自然语言查询、图表可视化、Grafana集成 |
| 2.1.0 | 2026-06-02 | Architecture refactor: 6-agent → 4-agent, ConsensusEngine, ViolationDetector |
| 2.0.0 | 2026-05-29 | Initial architecture with orchestrator-core |

---

## Commit History (2026-06-05)

### Web界面与智能问答 (2026-06-05)
- feat: 实现自然语言查询接口（LLM驱动）
- feat: 添加历史数据获取器
- feat: 实现Web前端界面（查询、监控、分析报告面板）
- feat: 添加Chart.js时序图表可视化
- feat: 集成Grafana仪表板
- fix: 异常点索引到时间戳转换
- fix: 图表异常点标注显示
- refactor: 优化图表样式和布局
- test: 验证智能问答功能（主智能体+子智能体协同）

### Project Cleanup (2026-06-05)
- chore: 删除多余的测试文件和临时文件
- chore: 删除Python缓存文件
- chore: 更新项目文档

---

## Migration Guide

### Web界面部署
```bash
# 1. 配置LLM API
cd middleware
cp .env.example .env
# 编辑.env添加API密钥

# 2. 启动查询接口
python query_interface.py

# 3. 启动监控服务
python app_orchestrator.py

# 4. 访问Web界面
http://localhost:8080

# 5. 配置Grafana（如需嵌入）
# 编辑 grafana.ini 设置 allow_embedding = true
```

### 示例查询
- "检测最近一周数据异常情况"
- "analyze pH COD anomalies in past 24 hours"
- "查看昨天总氮和总磷的趋势"
