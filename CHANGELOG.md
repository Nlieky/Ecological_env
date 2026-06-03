# Changelog

All notable changes to the wastewater monitoring system will be documented in this file.

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
| 2.1.0 | 2026-06-02 | Architecture refactor: 6-agent → 4-agent, ConsensusEngine, ViolationDetector |
| 2.0.0 | 2026-05-29 | Initial architecture with orchestrator-core |

---

## Migration Guide for Local Claude

### What Changed on Server
1. **Agent Structure**: 4 agents instead of 6
2. **New Modules**: ConsensusEngine, ViolationDetector, DataPerception, DispositionExecution
3. **Configuration Files**: agent_registry.yaml, consensus_config.yaml, rule_config.yaml
4. **Test Paths**: Updated for new structure

### How to Sync
```bash
# On local machine
cd /path/to/local/Ecological_env
git fetch origin
git pull origin main  # Or appropriate branch
python -m pytest tests/ -v  # Verify all tests pass
```

### Verification
```python
# Test imports work
from subagents.disposition_execution_agent.scripts import ConsensusEngine
from subagents.rule_reasoning_agent.scripts import ViolationDetector
from subagents.multi_dimensional_data_perception_agent.scripts import DataAcquisitionModule

# Verify configuration loads
import yaml
yaml.safe_load(open('shared/configs/agent_registry.yaml'))
yaml.safe_load(open('shared/configs/consensus_config.yaml'))
yaml.safe_load(open('shared/configs/rule_config.yaml'))
```

---

## Commit History (2026-06-01 to 2026-06-02)

### Architecture Refactor (2026-06-02)
- 23e2516 refactor: update integration tests for new agent architecture
- 9c2d562 refactor: migrate feature analysis to anomaly-detection-agent
- a6ae4df refactor: update orchestrator-core scripts for new agent architecture

### Consensus Engine (2026-06-01)
- ebab4a8 docs: update SKILL.md to document implemented consensus_engine module
- 60e020d feat: integrate ConsensusEngine into AlertClassifier
- 313e0c2 test: add unit tests for consensus engine
- b042f7f feat: export ConsensusEngine, FusionResult, SceneType in __init__.py
- 450e39c feat: implement config loading in _load_config method
- 0ace07e feat: add consensus engine configuration file
- bb170de feat: implement dynamic weight adjustment algorithm in adapt_weights method
- 6170004 feat: add consensus engine basic structure

### Violation Detector (2026-06-01)
- bb4e594 feat: implement violation detector with rule engine
- faccf34 fix: enhance rule_config.yaml with metadata section and enable flags

### Data Perception (2026-06-01)
- 58cee95 docs: enhance data-perception-core SKILL.md with YAML frontmatter
- cc17692 fix: enhance error handling and metadata tracking in data perception modules
- b392b1d fix: improve data cleaning and standardization modules
- d87b2f7 feat: implement data cleaning and standardization modules
- 82d520c fix: improve code quality in data_decomposition.py and time_alignment.py
- 33a0390 feat: export data decomposition and time alignment modules in __init__.py
- 1464a13 fix(data-acquisition): add exception handling, input validation
- 13518f1 feat: implement data acquisition module
- f67cff8 fix: standardize multi-dimensional-data-perception-agent identity files

### Dynamic Orchestrator (2026-06-01)
- 28141ed fix: update AGENTS.md with correct 4-agent architecture
- a550483 fix: improve code quality in dynamic_orchestrator.py
- bbcd97b feat: add dynamic orchestrator for master agent

### Disposition Execution (2026-06-01)
- 3fde987 docs: update SKILL.md for action_executor and report_generator
- 10dcee1 refactor: update exports for action_executor and report_generator
- 18cf4da config: add disposition execution configuration
- 5115226 feat: implement ReportGenerator.generate_trend_report
- 8520bd0 feat: implement ReportGenerator.generate_summary_report
- ff07db6 fix: reorganize imports in report_generator.py
- e61ff30 feat: implement ReportGenerator.generate_alert_report()
- 91a6ea1 fix: use real newlines in markdown report generation
- 0097f24 feat: add report data classes
- b58f6ee feat: implement ActionExecutor coordinator
- e3f628c feat: implement RegulatoryPlatformPush channel

### Testing (2026-06-01)
- 0ffcd21 fix: add pytest to requirements and fix test path issue
- 42f2a8f fix: address code quality issues in e2e integration tests
- 5cfe1a4 test: add end-to-end architecture integration tests
- dde5ea3 fix: improve code quality in violation_detector.py
