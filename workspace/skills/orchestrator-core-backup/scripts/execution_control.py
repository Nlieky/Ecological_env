#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行控制模块 - 负责任务执行和 LLM 协调

职责：
1. 接收执行计划
2. LLM 驱动的子智能体协调
3. 执行状态监控
4. 异常处理（不静默回退）
5. 结果收集和传递

不负责：
- 任务规划（由 dynamic_orchestrator.py 负责）
- 意图解析（由 task_receiving_and_parsing.py 负责）

说明：此脚本由主智能体（大模型）调用，用于实际驱动子智能体
执行任务，监控执行进度，处理超时、失败等异常情况。

扩展功能：支持大模型协调子智能体
- 大模型读取子智能体完整身份（SKILL.md, AGENTS.md, SOUL.md, MEMORY.md）
- 大模型调用已开发脚本（subagents/*/skills/*/scripts/*.py）
- 大模型协调4个子智能体按顺序执行

性能优化 TODO:
- 当前每个工作流约需12个LLM调用（3.6-12秒延迟）
- 优化方向：
  1. 缓存脚本选择决策（避免重复LLM调用）
  2. 对简单结构化输出跳过LLM分析
  3. 并行运行独立的子智能体
- 影响：实时监控响应速度和系统可扩展性
"""

import logging
import asyncio
import json
import os
import re
import yaml
from pathlib import Path

# 导入LLM错误类
from shared.configs.llm_errors import LLMError, LLMConfigError
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import time

# Import dynamic orchestrator for task planning and agent coordination
from dynamic_orchestrator import DynamicOrchestrator, ExecutionPlan, ExecutionMode

# 项目路径 - 尝试多种方式找到项目根目录
# 注意：从 execution_control.py 到项目根目录需要5层 parent
possible_roots = [
    Path(__file__).resolve().parent.parent.parent.parent.parent,  # 5层 = Ecological_env
    Path.cwd(),
    Path(__file__).parent.parent.parent.parent.parent,  # 备用：未解析的5层
]

for root in possible_roots:
    if (root / "workspace").exists() and (root / "subagents").exists():
        project_root = root
        break
else:
    # 最后的备用方案：使用resolve()确保是绝对路径
    project_root = Path(__file__).resolve().parent.parent.parent.parent.parent

# 不再配置logging，由主应用统一配置
logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ExecutionPhase(Enum):
    """执行阶段"""
    INITIALIZING = "initializing"
    DISPATCHING = "dispatching"
    EXECUTING = "executing"
    COLLECTING = "collecting"
    FINALIZING = "finalizing"


@dataclass
class ExecutionResult:
    """执行结果"""
    task_id: str
    agent_id: str
    status: ExecutionStatus

    # 结果数据
    output_data: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    error_code: str = ""

    # 时间信息
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0.0

    # 执行信息
    retry_count: int = 0
    timeout_seconds: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "status": self.status.value,
            "output_data": self.output_data,
            "error_message": self.error_message,
            "error_code": self.error_code,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "retry_count": self.retry_count,
            "timeout_seconds": self.timeout_seconds
        }


@dataclass
class ExecutionReport:
    """执行报告"""
    flow_id: str
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    timeout_tasks: int

    # 详细结果
    task_results: Dict[str, ExecutionResult] = field(default_factory=dict)

    # 汇总信息
    start_time: str = ""
    end_time: str = ""
    total_duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "flow_id": self.flow_id,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "timeout_tasks": self.timeout_tasks,
            "task_results": {tid: r.to_dict() for tid, r in self.task_results.items()},
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_duration_seconds": self.total_duration_seconds
        }


class ExecutionControlError(Exception):
    """执行控制异常"""
    pass


class TaskTimeoutError(ExecutionControlError):
    """任务超时异常"""
    pass


# ==================== 大模型协调子智能体模块 ====================

@dataclass
class SubAgentIdentity:
    """子智能体身份信息"""
    agent_id: str
    agent_name: str
    skill_path: Path
    identity_files: Dict[str, str] = field(default_factory=dict)  # SKILL.md, AGENTS.md, SOUL.md, MEMORY.md
    script_paths: List[Path] = field(default_factory=list)  # 已开发脚本路径

    def get_identity_summary(self) -> str:
        """获取身份摘要（用于大模型提示）"""
        parts = [f"=== {self.agent_name} ({self.agent_id}) ==="]
        for name, content in self.identity_files.items():
            if content:
                parts.append(f"\n## {name}\n{content[:300]}..." if len(content) > 300 else f"\n## {name}\n{content}")
        return "\n".join(parts)


class SubAgentIdentityLoader:
    """子智能体身份加载器"""

    # 子智能体配置 - 与 agent_registry.yaml 保持一致
    SUB_AGENTS = {
        "multi-dimensional-data-perception-agent": {
            "name": "多维数据感知子智能体",
            "skill_module": "data-perception-core",
            "scripts": ["data_acquisition.py", "time_alignment.py", "data_cleaning.py", "standardization.py", "data_decomposition.py", "__init__.py"],
            "recommended_script": "__init__.py",
            "path": "multi-dimensional-data-perception-agent"
        },
        "anomaly-detection-agent": {
            "name": "异常检测子智能体",
            "skill_module": "anomaly-detection-core",
            "scripts": ["__init__.py", "operator_adapter.py", "anomaly_scorer.py", "pattern_recognizer.py", "confidence_evaluator.py", "violation_detector.py"],
            "recommended_script": "__init__.py",
            "path": "anomaly-detection-agent"
        },
        "rule-reasoning-agent": {
            "name": "规则推理子智能体",
            "skill_module": "rule-reasoning-core",
            "scripts": ["expert_reasoner.py", "regulation_matcher.py", "process_validator.py", "violation_generator.py"],
            "recommended_script": "expert_reasoner.py",
            "path": "rule-reasoning-agent"
        },
        "disposition-execution-agent": {
            "name": "研判预警与处置执行子智能体",
            "skill_module": "disposition-execution-core",
            "scripts": ["alert_classifier.py", "work_order_generator.py", "action_executor.py", "report_generator.py", "consensus_engine.py", "__init__.py"],
            "recommended_script": "alert_classifier.py",
            "path": "disposition-execution-agent"
        }
    }

    def __init__(self, project_root: Path = None):
        """初始化加载器"""
        if project_root is None:
            # 5层 parent 到达项目根目录 (E:\project\Ecological_env)
            project_root = Path(__file__).resolve().parent.parent.parent.parent.parent

        self.project_root = project_root
        self.subagents_dir = project_root / "subagents"
        self._identity_cache: Dict[str, SubAgentIdentity] = {}

    def load_agent_identity(self, agent_id: str) -> Optional[SubAgentIdentity]:
        """
        加载子智能体身份

        Args:
            agent_id: 子智能体ID

        Returns:
            SubAgentIdentity对象
        """
        if agent_id in self._identity_cache:
            return self._identity_cache[agent_id]

        if agent_id not in self.SUB_AGENTS:
            print(f"[IDENTITY] 未知子智能体: {agent_id}")
            return None

        config = self.SUB_AGENTS[agent_id]
        # 使用配置中的 path 字段，如果没有则回退到 agent_id
        agent_path = config.get("path", agent_id)
        agent_dir = self.subagents_dir / agent_path

        # 身份文件路径
        identity_files = {
            "SKILL.md": agent_dir / "skills" / config["skill_module"] / "SKILL.md",
            "AGENTS.md": agent_dir / "AGENTS.md",
            "SOUL.md": agent_dir / "SOUL.md",
            "MEMORY.md": agent_dir / "MEMORY.md"
        }

        # 读取身份文件
        identity_content = {}
        for name, path in identity_files.items():
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        identity_content[name] = f.read()
                    print(f"[IDENTITY] 已加载 {agent_id}/{name}")
                except Exception as e:
                    print(f"[IDENTITY] 无法加载 {path}: {e}")
                    identity_content[name] = ""

        # 脚本路径
        scripts_dir = agent_dir / "skills" / config["skill_module"] / "scripts"
        script_paths = []
        if scripts_dir.exists():
            for script_name in config["scripts"]:
                script_path = scripts_dir / script_name
                if script_path.exists():
                    script_paths.append(script_path)

        identity = SubAgentIdentity(
            agent_id=agent_id,
            agent_name=config["name"],
            skill_path=agent_dir / "skills" / config["skill_module"],
            identity_files=identity_content,
            script_paths=script_paths
        )

        self._identity_cache[agent_id] = identity
        return identity

    def get_all_agents(self) -> List[str]:
        """获取所有子智能体ID"""
        return list(self.SUB_AGENTS.keys())


class LLMAgentCoordinator:
    """
    大模型子智能体协调器

    职责：
    1. 读取子智能体完整身份（SKILL.md, AGENTS.md, SOUL.md, MEMORY.md）
    2. 理解任务需求
    3. 调用已开发脚本完成任务
    4. 传递结果到下一个子智能体
    """

    def __init__(self, llm_client=None, project_root: Path = None):
        """
        初始化协调器

        Args:
            llm_client: 大模型客户端（可选）
            project_root: 项目根路径
        """
        self.identity_loader = SubAgentIdentityLoader(project_root)
        self.llm_client = llm_client
        # 5层 parent 到达项目根目录 (E:\project\Ecological_env)
        self.project_root = project_root or Path(__file__).resolve().parent.parent.parent.parent.parent
        # 加载LLM配置
        self.llm_config = self._load_llm_config()
        print("[COORD] 大模型子智能体协调器初始化完成")

    def coordinate_agent_execution(self, agent_id: str, task: Dict[str, Any],
                                   previous_results: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        协调子智能体执行任务

        优先使用 LLM 协调，失败时回退到本地规则模式

        Args:
            agent_id: 子智能体ID
            task: 任务信息
            previous_results: 前序子智能体的执行结果

        Returns:
            执行结果
        """
        # 1. 加载子智能体身份
        identity = self.identity_loader.load_agent_identity(agent_id)
        if not identity:
            return {
                "status": "error",
                "error": f"无法加载子智能体身份: {agent_id}"
            }

        print(f"[COORD] 协调 {identity.agent_name} 执行任务: {task.get('task_id')}")

        # 2. 选择协调模式（必须使用 LLM）
        if self.llm_client is None:
            raise LLMConfigError(
                "LLM 客户端未初始化，无法协调子智能体执行",
                details={"agent": identity.agent_name, "task": task.get("task_id")}
            )

        print(f"[COORD] 使用 LLM 协调模式")
        return self._llm_coordinate_agent(identity, task, previous_results)

    def _load_llm_config(self) -> dict:
        """
        从 llm_config.yaml 加载完整的LLM配置

        Returns:
            dict: LLM配置字典，包含subagent_configs等配置
        """
        config_path = self.project_root / "shared" / "configs" / "llm_config.yaml"

        if not config_path.exists():
            logger.warning(f"[CONFIG] LLM配置文件不存在: {config_path}")
            return {"subagent_configs": {}}

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            print(f"[CONFIG] 已加载LLM配置")
            return config
        except Exception as e:
            logger.error(f"[CONFIG] 加载LLM配置失败: {e}")
            return {"subagent_configs": {}}

    def _get_subagent_config(self, agent_id: str) -> dict:
        """
        获取指定子智能体的LLM配置

        Args:
            agent_id: 子智能体ID

        Returns:
            dict: 子智能体的LLM配置，包含system_prompt、model等
        """
        if not hasattr(self, 'llm_config') or not self.llm_config:
            self.llm_config = self._load_llm_config()

        subagent_configs = self.llm_config.get('subagent_configs', {})
        config = subagent_configs.get(agent_id, {})

        # 检查是否启用
        if not config.get('enabled', True):
            logger.warning(f"[CONFIG] 子智能体 {agent_id} 的LLM功能未启用，使用默认配置")
            return {}

        # 验证必要字段
        if 'system_prompt' not in config:
            logger.warning(f"[CONFIG] 子智能体 {agent_id} 缺少system_prompt配置")

        if 'model' not in config:
            logger.info(f"[CONFIG] 子智能体 {agent_id} 未指定模型，使用primary")
            config['model'] = 'primary'

        return config

    def _get_subagent_system_prompt(self, agent_id: str) -> str:
        """
        获取子智能体的system_prompt

        Args:
            agent_id: 子智能体ID

        Returns:
            str: 子智能体的系统提示词，如果配置缺失则返回主智能体提示词
        """
        config = self._get_subagent_config(agent_id)

        if not config:
            # 回退到主智能体提示词
            return self._build_master_agent_system_prompt()

        system_prompt = config.get('system_prompt', '')

        if not system_prompt:
            logger.warning(f"[CONFIG] 子智能体 {agent_id} 未配置system_prompt，使用主智能体提示词")
            return self._build_master_agent_system_prompt()

        return system_prompt

    def _get_subagent_model(self, agent_id: str) -> str:
        """
        获取子智能体的专用模型配置

        Args:
            agent_id: 子智能体ID

        Returns:
            str: 模型类型（fast/primary/analysis），默认为primary
        """
        config = self._get_subagent_config(agent_id)

        if not config:
            # 默认使用主模型
            return 'primary'

        model_key = config.get('model', 'primary')

        # 验证模型配置有效
        valid_models = ['fast', 'primary', 'analysis']
        if model_key not in valid_models:
            logger.warning(f"[CONFIG] 无效的模型配置: {model_key}，使用primary")
            return 'primary'

        return model_key

    def _build_master_agent_system_prompt(self) -> str:
        """构建主智能体系统提示词"""
        workspace = self.project_root / "workspace"

        # 读取主智能体身份文件
        identity_files = {
            "IDENTITY.md": workspace / "IDENTITY.md",
            "AGENTS.md": workspace / "AGENTS.md",
            "SOUL.md": workspace / "SOUL.md",
            "MEMORY.md": workspace / "MEMORY.md"
        }

        parts = ["你是废水虚假排放智能监测系统的主智能体。\n"]

        for name, path in identity_files.items():
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # 限制长度避免token过多
                        if len(content) > 1000:
                            content = content[:1000] + "\n...(已截断)"
                        parts.append(f"## {name}\n{content}\n")
                        print(f"[PROMPT] 已加载 {name} 到系统提示词")
                except Exception as e:
                    print(f"[PROMPT] 无法加载 {name}: {e}")

        return "\n".join(parts)

    def _llm_coordinate_agent(self, identity: SubAgentIdentity,
                              task: Dict[str, Any],
                              previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        完全 LLM 驱动的协调

        流程：
        1. LLM 读取身份文件
        2. LLM 理解任务和前序结果
        3. LLM 决定调用哪个脚本
        4. 根据 LLM 决策执行脚本
        5. LLM 分析执行结果
        """

        # 1. 获取子智能体专属系统提示词
        agent_id = identity.agent_id
        system_prompt = self._get_subagent_system_prompt(agent_id)
        print(f"[LLM] 使用 {agent_id} 专属系统提示词")

        # 2. 获取子智能体身份摘要
        identity_summary = self._build_identity_summary(identity)
        print(f"[LLM] 子智能体身份摘要已构建，长度: {len(identity_summary)} 字符")

        # 3. 获取可用脚本信息
        scripts_info = self._get_available_scripts(identity)
        print(f"[LLM] 可用脚本: {list(scripts_info.keys())}")

        # 增强日志
        print(f"[LLM] 子智能体: {agent_id}")
        print(f"[LLM] 使用配置: model={self._get_subagent_model(agent_id)}, system_prompt长度={len(system_prompt)}")

        # 4. 构建决策 prompt

        # 确定推荐脚本（从配置中获取）
        agent_config = self.identity_loader.SUB_AGENTS.get(identity.agent_id, {})
        recommended_script = agent_config.get("recommended_script")

        # 获取实际的时间范围
        actual_start_time = task.get('metadata', {}).get('start_time', 'N/A')
        actual_end_time = task.get('metadata', {}).get('end_time', 'N/A')

        decision_prompt = f"""
你是{identity.agent_name}，请完成以下任务。

{identity_summary}

## 当前任务
任务类型: {task.get('description', '实时监测数据分析')}
数据量: {task.get('metadata', {}).get('data_count', 1)}条时间序列数据

**重要：数据实际时间范围**
- 开始时间: {actual_start_time}
- 结束时间: {actual_end_time}

## 可用脚本
```json
{json.dumps(scripts_info, ensure_ascii=False, indent=2)}
```

## 请决策
选择合适的脚本。

**关键约束**:
1. **不要修改时间范围**：数据已在内存中，你只需要处理它，不要指定start_time/end_time参数
2. 系统会自动将时序数据转换为标准data格式并注入到脚本中
3. 你只需要指定脚本名称即可

{"推荐: 优先使用 " + recommended_script if recommended_script else ""}

请返回 JSON 格式：
```json
{{
  "script": "pipeline.py",
  "params": {{}},
  "reasoning": "选择原因"
}}
```
"""

        try:
            # 4.5 获取子智能体专用模型
            model_type = self._get_subagent_model(agent_id)
            print(f"[LLM] {agent_id} 使用模型: {model_type}")

            # 5. LLM 决策
            print(f"[LLM] 请求 {identity.agent_name} 决策...")
            decision_response = self.llm_client.chat(
                message=decision_prompt,
                system_prompt=system_prompt,
                model_type=model_type,
                temperature=0.0
            )

            print(f"[LLM] 决策响应: {decision_response[:300]}...")

            # 5. 解析 LLM 决策
            decision = self._parse_llm_decision(decision_response)

            # 6. 根据 LLM 决策执行脚本
            script_result = self._execute_script_by_decision(decision, identity, task)

            # 7. LLM 分析结果
            final_result = self._llm_analyze_result(
                identity, task, decision, script_result, previous_results
            )

            return final_result

        except LLMError as e:
            logger.error(f"[LLM] LLM 协调失败: {e.message}")
            # 向用户明确提示错误
            raise LLMError(
                f"LLM 子智能体协调失败: {e.message}",
                details={"agent": identity.get("name", identity.get("agent_id", "unknown")), "task": task}
            ) from e
        except Exception as e:
            logger.error(f"[LLM] 未知错误: {e}")
            import traceback
            traceback.print_exc()
            raise LLMError(f"LLM 协调失败: {str(e)}")

    def _local_coordinate_agent(self, identity: SubAgentIdentity,
                                task: Dict[str, Any],
                                previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """本地规则模式（回退方案）"""
        # 使用默认决策直接执行脚本
        agent_config = self.identity_loader.SUB_AGENTS.get(identity.agent_id, {})
        recommended_script = agent_config.get("recommended_script", "__init__.py")

        # 构建默认决策
        decision = {
            "script": recommended_script,
            "params": {
                "start_time": task.get("metadata", {}).get("start_time", ""),
                "end_time": task.get("metadata", {}).get("end_time", "")
            },
            "reasoning": f"使用默认脚本 {recommended_script}"
        }

        print(f"[LOCAL] 本地规则模式，使用默认脚本: {recommended_script}")

        # 执行脚本
        return self._execute_script_by_decision(decision, identity, task)

    def _build_identity_summary(self, identity: SubAgentIdentity) -> str:
        """
        构建子智能体身份摘要

        将子智能体的完整身份文件（IDENTITY.md、AGENTS.md、SKILL.md、MEMORY.md）
        整合成一个摘要，传递给 LLM
        """
        summary_parts = []

        # 1. 身份卡片（IDENTITY.md）
        if 'IDENTITY.md' in identity.identity_files:
            summary_parts.append(f"""
### 身份卡片（IDENTITY.md）
{identity.identity_files['IDENTITY.md']}
""")

        # 2. 任务说明（AGENTS.md）- 最重要的部分
        if 'AGENTS.md' in identity.identity_files:
            summary_parts.append(f"""
### 任务说明（AGENTS.md）
{identity.identity_files['AGENTS.md']}
""")

        # 3. 技能说明（SKILL.md）
        if 'SKILL.md' in identity.identity_files:
            skill_content = identity.identity_files['SKILL.md']
            # 限制 SKILL.md 长度
            if len(skill_content) > 1000:
                skill_content = skill_content[:1000] + "\n...(内容过长，已截断)"
            summary_parts.append(f"""
### 技能说明（SKILL.md）
{skill_content}
""")

        # 4. 专业记忆（MEMORY.md）
        if 'MEMORY.md' in identity.identity_files:
            memory_content = identity.identity_files['MEMORY.md']
            # 限制 MEMORY.md 长度
            if len(memory_content) > 800:
                memory_content = memory_content[:800] + "\n...(内容过长，已截断)"
            summary_parts.append(f"""
### 专业记忆（MEMORY.md）
{memory_content}
""")

        return "".join(summary_parts)

    def _get_available_scripts(self, identity: SubAgentIdentity) -> Dict[str, Any]:
        """获取子智能体的可用脚本信息"""
        scripts = {}
        for script_path in identity.script_paths:
            try:
                # 尝试读取脚本文档字符串
                with open(script_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 提取文档字符串
                    doc_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
                    description = doc_match.group(1).strip() if doc_match else script_path.stem
                    # 限制长度
                    if len(description) > 200:
                        description = description[:200] + "..."
            except Exception as e:
                description = f"{script_path.stem} (读取失败: {e})"

            scripts[script_path.name] = {
                "path": str(script_path),
                "description": description,
                "module": script_path.stem
            }
        return scripts

    def _get_script_description(self, script_path: Path) -> str:
        """获取脚本的描述信息"""
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
                doc_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
                if doc_match:
                    desc = doc_match.group(1).strip()
                    return desc[:200] if len(desc) > 200 else desc
        except Exception:
            pass
        return script_path.stem

    def _parse_llm_decision(self, response: str) -> Dict[str, Any]:
        """解析 LLM 的决策响应"""
        try:
            # 尝试提取 JSON
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                decision = json.loads(json_match.group(1))
            else:
                # 尝试直接解析
                decision = json.loads(response)

            print(f"[LLM] 决策解析成功: {decision.get('script', 'N/A')}")
            return decision

        except json.JSONDecodeError as e:
            print(f"[LLM] JSON 解析失败: {e}，使用文本分析")
            # 文本分析回退
            return {
                "script": None,
                "params": {},
                "reasoning": response[:500],
                "raw_response": response
            }

    def _extract_processed_data(self, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """从agent执行结果中提取处理后的数据"""
        if result.get("status") != "success":
            return None

        # 从 result.result 中提取数据
        script_result = result.get("result", {})

        # 如果result本身就是字典（直接来自脚本）
        if isinstance(script_result, dict):
            # 检查是否有标准输出格式
            if "values" in script_result and "timestamps" in script_result:
                # 这是pipeline.py的标准输出格式
                return {
                    "timestamps": script_result.get("timestamps", []),
                    "values": script_result.get("values", {}),
                    "flags": script_result.get("flags", {}),
                    "units": script_result.get("units", {}),
                    "quality_report": script_result.get("quality_report", {})
                }
            # 检查是否有data字段
            elif "data" in script_result:
                return script_result["data"]
            # 检查是否有features字段（特征分析agent输出）
            elif "features" in script_result or "correlations" in script_result:
                return script_result
            # 检查是否有anomalies字段（异常检测agent输出）
            elif "anomalies" in script_result or "has_anomaly" in script_result:
                return script_result

        return None

    def _execute_script_by_decision(self, decision: Dict[str, Any],
                                    identity: SubAgentIdentity,
                                    task: Dict[str, Any]) -> Dict[str, Any]:
        """根据 LLM 决策执行脚本"""
        script_name = decision.get("script")
        params = decision.get("params", {})

        if not script_name:
            print("[LLM] 未指定脚本，使用默认处理")
            return {
                "status": "success",
                "agent_id": identity.agent_id,
                "message": "LLM 未选择脚本，使用默认处理",
                "result": {}
            }

        # ========== 数据注入策略 ==========
        # 优先使用前一个agent处理后的数据，否则使用原始metadata数据
        data_to_inject = None

        # 1. 检查是否有前一个agent的处理后数据
        if "processed_data" in task:
            data_to_inject = task["processed_data"]
            print(f"[DATA-FLOW] 使用前一个agent的处理后数据")

        # 2. 否则，检查metadata中的原始时序数据
        elif task.get("metadata"):
            metadata = task["metadata"]
            if metadata.get("influent_timeseries") or metadata.get("effluent_timeseries"):
                # 构建标准data格式
                data_values = {}

                # 需要跳过的非数值字段（包括时间戳）
                skip_keys = {"监测时间", "timestamp", "time", "时间"}

                # 处理进水数据
                influent_ts = metadata.get("influent_timeseries", [])
                if influent_ts and len(influent_ts) > 0:
                    sample = influent_ts[0]
                    for key in sample.keys():
                        if key in skip_keys:
                            continue
                        # 提取并转换为数值
                        values = []
                        for record in influent_ts:
                            val = record.get(key)
                            # 尝试转换为数值，失败或为None时使用0.0
                            if val is None:
                                values.append(0.0)
                            else:
                                try:
                                    values.append(float(val))
                                except (ValueError, TypeError):
                                    values.append(0.0)
                        data_values[f"influent_{key}"] = values

                # 处理出水数据
                effluent_ts = metadata.get("effluent_timeseries", [])
                if effluent_ts and len(effluent_ts) > 0:
                    sample = effluent_ts[0]
                    for key in sample.keys():
                        if key in skip_keys:
                            continue
                        # 提取并转换为数值
                        values = []
                        for record in effluent_ts:
                            val = record.get(key)
                            # 尝试转换为数值，失败或为None时使用0.0
                            if val is None:
                                values.append(0.0)
                            else:
                                try:
                                    values.append(float(val))
                                except (ValueError, TypeError):
                                    values.append(0.0)
                        data_values[f"effluent_{key}"] = values

                if data_values:
                    data_to_inject = {"values": data_values}
                    print(f"[AUTO-INJECT] 自动注入时序数据: {len(data_values)}个指标（含timestamp）, 每个指标{len(influent_ts)}条")

        # 3. 如果有数据要注入，添加到params中
        if data_to_inject and "data" not in params:
            params["data"] = data_to_inject
            print(f"[AUTO-INJECT] 已将data注入到params，params现在包含: {list(params.keys())}")
        elif "data" in params:
            print(f"[AUTO-INJECT] params中已有data参数")
        else:
            print(f"[AUTO-INJECT] 没有数据要注入，data_to_inject={data_to_inject is not None}")

        # ========== 查找脚本路径 ==========
        script_path = None
        for sp in identity.script_paths:
            if sp.name == script_name or sp.stem == script_name:
                script_path = sp
                break

        if not script_path:
            print(f"[ERROR] 脚本未找到: {script_name}，无法执行")
            return {"status": "error", "message": f"脚本未找到: {script_name}"}

        print(f"[LLM] 执行脚本: {script_path.name}")
        return self._dynamic_execute_script(script_path, params, task, identity)

    def _dynamic_execute_script(self, script_path: Path,
                               params: Dict[str, Any],
                               task: Dict[str, Any],
                               identity: SubAgentIdentity) -> Dict[str, Any]:
        """动态执行 Python 脚本

        支持多种调用方式：
        1. 标准函数：main(), run(), process(), execute()
        2. 特定命名函数：run_<agent>(), process_data(), analyze() 等
        3. 类实例化：模块中的主要类并调用其方法

        支持包内模块的相对导入：
        - 检测脚本所在包结构（查找__init__.py）
        - 正确设置模块的__package__属性
        """
        import importlib.util
        import sys
        import inspect

        script_dir = script_path.parent
        script_name = script_path.stem

        # 清除可能存在的缓存模块，确保加载最新代码
        # 使用更精确的匹配规则
        cache_patterns = [
            f"{script_name}",
            f"scripts.{script_name}",
            f"{script_name}.__init__",
            "rule_reasoning_core.scripts",
            "anomaly_detection_core.scripts",
            "feature_analysis_core.scripts",
            "data_governance_core.scripts"
        ]
        cache_keys_to_remove = []
        for pattern in cache_patterns:
            cache_keys_to_remove.extend([k for k in sys.modules.keys() if pattern in k])

        # 清除缓存（使用pop避免KeyError）
        removed_keys = []
        for key in cache_keys_to_remove:
            if key in sys.modules:
                del sys.modules[key]
                removed_keys.append(key)

        if removed_keys:
            print(f"[LLM] 清除缓存模块: {removed_keys[:5]}...")  # 只显示前5个
        script_name = script_path.stem

        try:
            # === 特殊处理：__init__.py 文件 ===
            if script_name == "__init__":
                # __init__.py 是包的入口文件，需要作为包模块加载
                # 包名是脚本所在目录的父目录名称
                # 例如：scripts/__init__.py -> feature_analysis_core.scripts

                # 向上查找包根目录
                package_root = None
                package_parts = []
                current_dir = script_dir

                # 从 scripts 目录向上找到 skill 根目录
                while current_dir.exists():
                    if (current_dir / "__init__.py").exists():
                        package_parts.insert(0, current_dir.name)
                        parent = current_dir.parent
                        # 检查父目录是否有 SKILL.md（skill根目录标志）
                        if (parent / "SKILL.md").exists():
                            package_root = parent
                            break
                        current_dir = parent
                    else:
                        break

                if package_root is not None and package_parts:
                    # 构建完整模块名
                    module_name = ".".join(package_parts)
                    root_str = str(package_root)

                    if root_str not in sys.path:
                        sys.path.insert(0, root_str)

                    print(f"[LLM] 加载 __init__.py 作为包模块: {module_name}")

                    # 使用包名加载
                    spec = importlib.util.spec_from_file_location(module_name, script_path)
                    if spec is None or spec.loader is None:
                        raise ImportError(f"无法加载 __init__.py: {script_path}")

                    module = importlib.util.module_from_spec(spec)
                    module.__package__ = ".".join(package_parts[:-1]) if len(package_parts) > 1 else None
                    spec.loader.exec_module(module)

                    # 注册到sys.modules
                    sys.modules[module_name] = module
                    sys.modules[f"{module_name}.__init__"] = module

                    # 准备参数并调用
                    call_params = {**params}
                    if "task" not in call_params:
                        call_params["task"] = task
                    if "data" not in call_params and "data" in task:
                        call_params["data"] = task["data"]

                    # 调试日志
                    print(f"[LLM] __init__.py 准备传递参数: {list(call_params.keys())}")

                    # 尝试调用入口函数
                    for func_name in ['main', 'run', 'process', 'execute']:
                        if hasattr(module, func_name):
                            func = getattr(module, func_name)
                            if callable(func):
                                import inspect
                                sig = inspect.signature(func)
                                print(f"[LLM] __init__.py.{func_name} 签名参数: {list(sig.parameters.keys())}")

                                filtered_params = {}
                                for name, param in sig.parameters.items():
                                    if name in call_params:
                                        filtered_params[name] = call_params[name]
                                    elif param.kind == inspect.Parameter.VAR_KEYWORD:
                                        filtered_params.update(call_params)

                                print(f"[LLM] 调用 __init__.py.{func_name}(), 参数: {list(filtered_params.keys())}")
                                result = func(**filtered_params)
                                return self._format_success_result(identity.agent_id, "__init__.py", result)

                    # 如果没有入口函数，返回错误
                    return {
                        "status": "error",
                        "agent_id": identity.agent_id,
                        "script": "__init__.py",
                        "error": "__init__.py 没有标准入口函数（main/run/process/execute）"
                    }

            # === 正常脚本处理流程 ===
            # === 检测包结构并设置正确的导入路径 ===
            # 查找包的根目录（包含__init__.py的目录）
            package_root = None
            package_parts = []
            current_dir = script_dir

            # 向上遍历查找包根目录
            while current_dir.exists():
                init_file = current_dir / "__init__.py"
                if init_file.exists():
                    package_parts.insert(0, current_dir.name)
                    package_root = current_dir.parent
                    current_dir = current_dir.parent
                else:
                    break

            # 如果找到了包结构，设置正确的导入路径
            if package_parts and package_root is not None:
                package_name = ".".join(package_parts)
                # 添加包根目录到sys.path
                root_str = str(package_root)
                if root_str not in sys.path:
                    sys.path.insert(0, root_str)

                # 添加scripts目录到sys.path（用于同一目录内的导入）
                scripts_dir = script_dir
                if str(scripts_dir) not in sys.path:
                    sys.path.insert(0, str(scripts_dir))

                print(f"[LLM] 检测到包结构: {package_name}, 根目录: {root_str}")

                # === 预加载同级模块（避免相对导入时的循环依赖）===
                # 对于 pipeline.py，先加载 data_acquisition, time_alignment 等
                sibling_modules = ['data_acquisition', 'time_alignment', 'data_cleaning', 'standardization', 'data_decomposition', 'data_pipeline']
                for sibling in sibling_modules:
                    sibling_path = script_dir / f"{sibling}.py"
                    if sibling_path.exists() and f"{package_name}.{sibling}" not in sys.modules:
                        try:
                            sibling_spec = importlib.util.spec_from_file_location(
                                f"{package_name}.{sibling}", sibling_path
                            )
                            if sibling_spec and sibling_spec.loader:
                                sibling_module = importlib.util.module_from_spec(sibling_spec)
                                sibling_module.__package__ = package_name
                                sibling_spec.loader.exec_module(sibling_module)
                                sys.modules[f"{package_name}.{sibling}"] = sibling_module
                                print(f"[LLM] 预加载依赖: {sibling}")
                        except Exception as e:
                            print(f"[LLM] 预加载 {sibling} 失败: {e}")

                # 使用完整模块名加载
                module_name = f"{package_name}.{script_name}"
                spec = importlib.util.spec_from_file_location(module_name, script_path)
                if spec is None or spec.loader is None:
                    raise ImportError(f"无法加载脚本: {script_path}")

                module = importlib.util.module_from_spec(spec)
                # 设置__package__以支持相对导入
                module.__package__ = package_name

                # === 执行模块（依赖已预加载，可以安全执行）===
                spec.loader.exec_module(module)

                # 注册到sys.modules
                sys.modules[module_name] = module
                sys.modules[script_name] = module
            else:
                # 没有包结构，按普通脚本处理
                if str(script_dir) not in sys.path:
                    sys.path.insert(0, str(script_dir))

                spec = importlib.util.spec_from_file_location(script_name, script_path)
                if spec is None or spec.loader is None:
                    raise ImportError(f"无法加载脚本: {script_path}")

                module = importlib.util.module_from_spec(spec)
                sys.modules[script_name] = module

                # 执行模块加载
                spec.loader.exec_module(module)

            # 准备参数
            call_params = {**params}
            if "task" not in call_params:
                call_params["task"] = task
            # 添加data参数（从task.data提取）
            if "data" not in call_params and "data" in task:
                call_params["data"] = task["data"]

            # 调试日志：显示所有准备传递的参数
            print(f"[LLM] 准备传递参数: {list(call_params.keys())}")
            if "data" in call_params:
                data_param = call_params["data"]
                if isinstance(data_param, dict):
                    print(f"[LLM] data参数包含字段: {list(data_param.keys())[:5]}...")
                else:
                    print(f"[LLM] data参数类型: {type(data_param)}")

            # 定义安全调用函数（参数过滤）
            def safe_call(func, **kwargs):
                """安全调用函数，只传递匹配的参数"""
                import inspect
                try:
                    sig = inspect.signature(func)
                    print(f"[LLM] 函数 {func.__name__} 的签名参数: {list(sig.parameters.keys())}")
                    # 过滤出函数接受的参数
                    filtered_params = {}
                    for name, param in sig.parameters.items():
                        if name in kwargs:
                            filtered_params[name] = kwargs[name]
                        elif param.kind == inspect.Parameter.VAR_KEYWORD:
                            # 接受 **kwargs
                            filtered_params.update(kwargs)
                        elif param.default == inspect.Parameter.empty and name not in kwargs:
                            # 必需参数缺失
                            print(f"[LLM] 缺少必需参数: {name}")

                    print(f"[LLM] 调用函数: {func.__name__}(), 参数: {list(filtered_params.keys())}")
                    return func(**filtered_params)
                except TypeError as e:
                    logger.error(f"[LLM] 函数调用失败: {e}")
                    raise

            # === 1. 尝试标准入口函数 ===
            for func_name in ['main', 'run', 'process', 'execute']:
                if hasattr(module, func_name):
                    func = getattr(module, func_name)
                    if callable(func):
                        result = safe_call(func, **call_params)
                        return self._format_success_result(identity.agent_id, script_name, result)

            # === 2. 尝试特定命名函数 ===
            # 根据脚本名猜测可能的函数名
            possible_functions = [
                f'run_{script_name}',  # run_data_cleaning
                f'process_{script_name}',  # process_data_cleaning
                f'{script_name}_main',  # data_cleaning_main
                'detect_anomalies',  # anomaly-detection 特定
                'apply_rules',  # rule-reasoning 特定
                'classify_alert',  # disposition-execution 特定
            ]

            for func_name in possible_functions:
                if hasattr(module, func_name):
                    func = getattr(module, func_name)
                    if callable(func):
                        result = safe_call(func, **call_params)
                        return self._format_success_result(identity.agent_id, script_name, result)

            # === 3. 尝试类实例化 ===
            # 查找主类（通常以Module, Processor, Detector等结尾）
            main_class = None
            for attr_name in dir(module):
                if attr_name.startswith('_'):
                    continue
                attr = getattr(module, attr_name)
                if inspect.isclass(attr) and attr_name.endswith(('Module', 'Processor', 'Detector', 'Analyzer', 'Reasoner')):
                    main_class = attr
                    break

            if main_class:
                print(f"[LLM] 实例化类: {main_class.__name__}")
                # 尝试无参数实例化
                try:
                    instance = main_class()
                except TypeError:
                    # 尝试传递配置参数
                    instance = main_class(config=call_params.get('config', {}))

                # 查找可调用方法
                for method_name in ['process', 'run', 'execute', 'analyze', 'detect', 'apply']:
                    if hasattr(instance, method_name):
                        method = getattr(instance, method_name)
                        if callable(method):
                            result = safe_call(method, **call_params)
                            return self._format_success_result(identity.agent_id, script_name, result)

            # === 4. 所有尝试失败 ===
            print(f"[LLM] 脚本 {script_name} 没有可调用的入口函数或类")
            return {
                "status": "error",
                "agent_id": identity.agent_id,
                "script": script_name,
                "error": f"脚本没有标准入口函数（main/run/process/execute）或可实例化的主类",
                "available_attributes": [a for a in dir(module) if not a.startswith('_')],
                "llm_coordinated": True
            }

        except Exception as e:
            logger.error(f"[LLM] 脚本执行失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "agent_id": identity.agent_id,
                "script": script_name,
                "error": str(e),
                "llm_coordinated": True
            }

    def _format_success_result(self, agent_id: str, script_name: str, result: Any) -> Dict[str, Any]:
        """格式化成功结果"""
        return {
            "status": "success",
            "agent_id": agent_id,
            "script": script_name,
            "result": result if isinstance(result, dict) else {"output": result},
            "llm_coordinated": True
        }

    def _llm_analyze_result(self, identity: SubAgentIdentity,
                           task: Dict[str, Any],
                           decision: Dict[str, Any],
                           script_result: Dict[str, Any],
                           previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """让 LLM 分析脚本执行结果"""
        # 如果脚本执行失败，直接返回错误结果，不要让LLM处理
        if script_result.get("status") == "error":
            print(f"[LLM] 脚本执行失败，跳过LLM分析，直接返回错误结果")
            return script_result

        # 先检查脚本结果是否包含处理后的数据
        # 如果有，直接返回脚本结果，不要让LLM覆盖它
        if self._extract_processed_data(script_result):
            print(f"[LLM] {identity.agent_id}脚本已输出处理后的数据，跳过LLM分析")
            return script_result

        # 辅助函数：过滤不可JSON序列化的对象
        def _filter_serializable(obj: Any, max_depth: int = 3, current_depth: int = 0) -> Any:
            """递归过滤不可序列化的对象"""
            if current_depth >= max_depth:
                return str(type(obj).__name__) if not isinstance(obj, (str, int, float, bool, type(None))) else obj

            if isinstance(obj, dict):
                return {k: _filter_serializable(v, max_depth, current_depth + 1) for k, v in obj.items()
                       if not k.startswith('_')}  # 跳过私有字段
            elif isinstance(obj, (list, tuple)):
                return [_filter_serializable(item, max_depth, current_depth + 1) for item in obj]
            elif isinstance(obj, (str, int, float, bool, type(None))):
                return obj
            else:
                # 对于DataFrame、numpy数组等，返回类型信息
                return f"<{type(obj).__name__} object>"

        system_prompt = self._build_master_agent_system_prompt()

        # 过滤不可序列化的对象
        safe_task = _filter_serializable(task)
        safe_script_result = _filter_serializable(script_result)
        safe_previous_results = _filter_serializable(previous_results) if previous_results else None

        analysis_prompt = f"""
你是{identity.agent_name}，请分析脚本执行结果。

## 执行的决策
{json.dumps(decision, ensure_ascii=False, indent=2)}

## 脚本执行结果
{json.dumps(safe_script_result, ensure_ascii=False, indent=2)}

## 前序结果
{json.dumps(safe_previous_results, ensure_ascii=False, indent=2) if safe_previous_results else "无"}

## 任务信息
{json.dumps(safe_task, ensure_ascii=False, indent=2)}

请分析执行结果，返回结构化的输出：
```json
{{
  "status": "success",
  "agent_id": "{identity.agent_id}",
  "analysis": "你的分析",
  "result": {{"保留原始脚本结果中的数据"}},
  "next_step": "下一步建议（可选）"
}}
```

**重要**：如果script_result中包含result字段且有values/timestamps等数据，请完整保留它们。
"""

        try:
            print(f"[LLM] 分析{identity.agent_name}的执行结果")
            response = self.llm_client.chat(
                message=analysis_prompt,
                system_prompt=system_prompt,
                model_type="primary",
                temperature=0.0
            )

            # 解析响应
            try:
                json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                if json_match:
                    final_result = json.loads(json_match.group(1))
                else:
                    final_result = json.loads(response)

                final_result["llm_coordinated"] = True

                # 如果LLM没有返回result字段，使用原始脚本结果
                if "result" not in final_result and "result" in script_result:
                    final_result["result"] = script_result["result"]

                print(f"[LLM] 结果分析完成")
                return final_result

            except json.JSONDecodeError:
                # JSON 解析失败，返回原始脚本结果
                print(f"[LLM] JSON解析失败，返回原始脚本结果")
                return script_result

        except Exception as e:
            logger.error(f"[LLM] 结果分析失败: {e}")
            # 直接返回脚本结果
            return script_result

    def _prepare_execution_context(self, identity: SubAgentIdentity,
                                   task: Dict[str, Any],
                                   previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """准备执行上下文"""
        context = {
            "agent_id": identity.agent_id,
            "agent_name": identity.agent_name,
            "task_id": task.get("task_id", ""),
            "task_name": task.get("task_name", ""),
            "category": task.get("category", ""),
            "input_params": {},
        }

        # 从task中提取input_params
        for param in task.get("input_params", []):
            name = param.get("name")
            value = param.get("value")
            context["input_params"][name] = value

        # 添加前序结果
        if previous_results:
            context["previous_results"] = previous_results

        return context

    def _execute_agent_task(self, identity: SubAgentIdentity,
                            context: Dict[str, Any]) -> Dict[str, Any]:
        """执行子智能体任务"""
        agent_id = identity.agent_id
        category = context.get("category", "")

        print(f"[COORD] 执行 {agent_id} 任务，类别: {category}")

        try:
            # 根据子智能体类型调用相应脚本
            if agent_id == "multi-dimensional-data-perception-agent":
                return self._execute_data_perception(identity, context)
            elif agent_id == "data-governance-agent":  # 兼容旧名称
                print("[COORD] data-governance-agent已废弃，请使用multi-dimensional-data-perception-agent")
                return self._execute_data_perception(identity, context)
            elif agent_id == "anomaly-detection-agent":
                return self._execute_anomaly_detection(identity, context)
            elif agent_id == "rule-reasoning-agent":
                return self._execute_rule_reasoning(identity, context)
            elif agent_id == "disposition-execution-agent":
                return self._execute_disposition_execution(identity, context)
            else:
                return {
                    "status": "error",
                    "error": f"未知子智能体: {agent_id}"
                }
        except Exception as e:
            logger.error(f"[COORD] 执行失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "error": str(e)
            }

    def _execute_data_perception(self, identity: SubAgentIdentity,
                                context: Dict[str, Any]) -> Dict[str, Any]:
        """执行多维数据感知任务（新架构）"""
        # 导入数据感知脚本
        scripts_dir = identity.skill_path / "scripts"
        import sys
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))

        try:
            # 尝试使用 data_decomposition 进行数据分解
            from data_decomposition import decompose_data

            # 获取输入参数
            input_params = context.get("input_params", {})
            effluent_data = input_params.get("effluent_data", {})

            if effluent_data:
                # 执行数据分解
                result = decompose_data(effluent_data)

                return {
                    "status": "success",
                    "agent_id": identity.agent_id,
                    "result": {
                        "cleaned_data": result.get("cleaned_data", {}),
                        "decomposition": result.get("decomposition", {})
                    },
                    "processed_data": result.get("cleaned_data", {}),
                    "decomposition_info": result.get("decomposition", {})
                }
        except ImportError:
            print("[DATA_PERCEPTION] data_decomposition不可用")

        # 备用方案：使用 data_cleaning
        try:
            from data_cleaning import DataCleaningModule

            input_params = context.get("input_params", {})
            data = context.get("data", {})

            if data:
                cleaner = DataCleaningModule()

                # 清洗进水数据
                influent_cleaned = cleaner.clean_water_quality_data(data.get("influent", []))
                # 清洗出水数据
                effluent_cleaned = cleaner.clean_water_quality_data(data.get("effluent", []))

                cleaned = {
                    "influent": influent_cleaned.get("cleaned_data", []),
                    "effluent": effluent_cleaned.get("cleaned_data", []),
                    "quality_report": {
                        "influent": influent_cleaned.get("quality_report", {}),
                        "effluent": effluent_cleaned.get("quality_report", {})
                    }
                }

                return {
                    "status": "success",
                    "agent_id": identity.agent_id,
                    "result": {
                        "cleaned_data": cleaned,
                        "quality_report": cleaned.get("quality_report", {})
                    },
                    "processed_data": cleaned
                }
        except Exception as e:
            print(f"[DATA_PERCEPTION] data_cleaning error: {e}")

        # 简化处理：直接返回数据
        input_params = context.get("input_params", {})
        return {
            "status": "success",
            "agent_id": identity.agent_id,
            "result": {},
            "processed_data": {}
        }

    def _execute_anomaly_detection(self, identity: SubAgentIdentity,
                                    context: Dict[str, Any]) -> Dict[str, Any]:
        """执行异常检测任务"""
        input_params = context.get("input_params", {})
        previous_results = context.get("previous_results", {})

        # 获取特征数据
        features = previous_results.get("features", {})

        # 法规限值
        limits = {
            "pH": (6.0, 9.0),
            "COD": (None, 50.0),
            "TN": (None, 15.0),
            "NH3-N": (None, 5.0),
            "TP": (None, 0.5)
        }

        anomalies = []

        for indicator, feat in features.items():
            if indicator in limits:
                min_val, max_val = limits[indicator]
                value = feat.get("max", feat.get("mean", 0))

                if max_val is not None and value > max_val:
                    anomalies.append({
                        "indicator": indicator,
                        "value": value,
                        "type": "exceedance",
                        "limit": max_val
                    })

                if min_val is not None and value < min_val:
                    anomalies.append({
                        "indicator": indicator,
                        "value": value,
                        "type": "below_limit",
                        "limit": min_val
                    })

                # 恒定值检测
                std = feat.get("std", 1)
                if std < 0.1:
                    anomalies.append({
                        "indicator": indicator,
                        "value": feat.get("mean", 0),
                        "type": "constant_value",
                        "std": std,
                        "suspicion": "high"
                    })

        return {
            "status": "success",
            "agent_id": identity.agent_id,
            "has_anomaly": len(anomalies) > 0,
            "anomalies": anomalies
        }

    def _execute_rule_reasoning(self, identity: SubAgentIdentity,
                                 context: Dict[str, Any]) -> Dict[str, Any]:
        """执行规则推理任务"""
        previous_results = context.get("previous_results", {})
        anomalies = previous_results.get("anomalies", [])

        violations = []

        for anom in anomalies:
            violation_type = anom.get("type", "unknown")

            if violation_type == "exceedance":
                violations.append({
                    "type": "exceedance",
                    "level": "high",
                    "indicator": anom.get("indicator"),
                    "message": f"{anom.get('indicator')}超标: {anom.get('value')} > {anom.get('limit')}",
                    "legal_reference": "GB18918-2002一级A标准"
                })
            elif violation_type == "constant_value":
                violations.append({
                    "type": "constant_value",
                    "level": "critical",
                    "indicator": anom.get("indicator"),
                    "message": f"{anom.get('indicator')}恒定值异常（疑似插瓶干扰）",
                    "legal_reference": "水污染防治法第三十九条"
                })

        suspicion_level = "low"
        if any(v.get("level") == "critical" for v in violations):
            suspicion_level = "critical"
        elif any(v.get("level") == "high" for v in violations):
            suspicion_level = "high"
        elif len(violations) > 0:
            suspicion_level = "medium"

        return {
            "status": "success",
            "agent_id": identity.agent_id,
            "has_violation": len(violations) > 0,
            "violations": violations,
            "suspicion_level": suspicion_level
        }

    def _execute_disposition_execution(self, identity: SubAgentIdentity,
                                       context: Dict[str, Any]) -> Dict[str, Any]:
        """执行研判预警与处置任务"""
        previous_results = context.get("previous_results", {})
        violations = previous_results.get("violations", [])
        suspicion_level = previous_results.get("suspicion_level", "low")

        # 生成研判预警和处置方案
        alert_level = "general"
        if suspicion_level == "critical":
            alert_level = "serious"
        elif suspicion_level == "high":
            alert_level = "moderate"

        # 生成工单和处置建议
        actions = []
        for violation in violations:
            vtype = violation.get("type", "unknown")
            if vtype == "exceedance":
                actions.append({
                    "type": "investigation",
                    "priority": "high",
                    "description": f"调查{violation.get('indicator')}超标原因",
                    "deadline": "24小时内"
                })
            elif vtype == "constant_value":
                actions.append({
                    "type": "urgent_inspection",
                    "priority": "critical",
                    "description": "立即现场核查，确认是否存在插瓶干扰",
                    "deadline": "立即"
                })

        return {
            "status": "success",
            "agent_id": identity.agent_id,
            "alert_level": alert_level,
            "suspicion_level": suspicion_level,
            "disposition": {
                "actions": actions,
                "recommendations": [
                    f"当前可疑等级：{suspicion_level}",
                    f"预警等级：{alert_level}",
                    f"建议处置措施：{'立即现场核查' if suspicion_level == 'critical' else '加强监测'}"
                ],
                "work_order_generated": len(actions) > 0
            }
        }

    def _llm_plan_subagent_execution(self, task: Dict[str, Any],
                                     intent_analysis: Any = None) -> Dict[str, Any]:
        """
        第一层LLM：主智能体决策子智能体执行计划

        决定：
        1. 需要调用哪些子智能体
        2. 按什么顺序执行
        3. 每个子智能体的预期输出

        Args:
            task: 任务信息
            intent_analysis: 意图分析结果（可选）

        Returns:
            执行计划字典，包含 selected_agents, execution_plan, reasoning
        """
        if self.llm_client is None:
            print("[L1-LLM] LLM客户端不可用，使用默认执行计划")
            return self._get_default_execution_plan()

        system_prompt = self._build_master_agent_system_prompt()

        # 构建子智能体描述
        agents_description = {}
        for agent_id, config in self.identity_loader.SUB_AGENTS.items():
            agents_description[agent_id] = {
                "name": config["name"],
                "skill_module": config["skill_module"],
                "scripts": config["scripts"]
            }

        decision_prompt = f"""
你是废水虚假排放智能监测主智能体，请为以下任务制定子智能体执行计划。

## 任务信息
```json
{json.dumps(task, ensure_ascii=False, indent=2)}
```

## 可用子智能体
```json
{json.dumps(agents_description, ensure_ascii=False, indent=2)}
```

## 请决策
1. 需要调用哪些子智能体？（必须按以下顺序：数据治理 → 特征分析 → 异常检测 → 规则推理）
2. 每个子智能体的作用是什么？
3. 预期每个子智能体输出什么？

请返回JSON格式：
```json
{{
  "selected_agents": ["子智能体ID1", "子智能体ID2", ...],
  "execution_plan": [
    {{"agent": "multi-dimensional-data-perception-agent", "purpose": "多维数据感知和预处理", "expected_output": "清洗和标准化的数据"}},
    {{"agent": "anomaly-detection-agent", "purpose": "异常检测和模式识别", "expected_output": "异常检测结果"}},
    {{"agent": "rule-reasoning-agent", "purpose": "规则推理和违规判定", "expected_output": "违规判定结果"}},
    {{"agent": "disposition-execution-agent", "purpose": "研判预警和处置执行", "expected_output": "预警信息和处置建议"}}
  ],
  "reasoning": "选择这些子智能体的原因"
}}
```
"""

        try:
            print("[L1-LLM] 请求主智能体决策子智能体执行计划...")
            response = self.llm_client.chat(
                message=decision_prompt,
                system_prompt=system_prompt,
                model_type="primary",
                temperature=0.0
            )
            print(f"[L1-LLM] 执行计划响应: {response[:500]}...")

            plan = self._parse_llm_decision(response)

            # 验证并修正执行计划
            if "execution_plan" not in plan or not plan["execution_plan"]:
                print("[L1-LLM] LLM返回的执行计划无效，使用默认计划")
                return self._get_default_execution_plan()

            print(f"[L1-LLM] 执行计划包含 {len(plan['execution_plan'])} 个子智能体")
            return plan

        except Exception as e:
            logger.error(f"[L1-LLM] 执行计划决策失败: {e}")
            import traceback
            traceback.print_exc()
            return self._get_default_execution_plan()

    def _get_default_execution_plan(self) -> Dict[str, Any]:
        """获取默认执行计划"""
        return {
            "selected_agents": [
                "multi-dimensional-data-perception-agent",
                "anomaly-detection-agent",
                "rule-reasoning-agent",
                "disposition-execution-agent"
            ],
            "execution_plan": [
                {"agent": "multi-dimensional-data-perception-agent", "purpose": "多维数据感知与清洗", "expected_output": "清洗后的数据"},
                {"agent": "anomaly-detection-agent", "purpose": "异常检测", "expected_output": "异常检测结果"},
                {"agent": "rule-reasoning-agent", "purpose": "规则推理和违规判定", "expected_output": "违规判定结果"},
                {"agent": "disposition-execution-agent", "purpose": "研判预警与处置执行", "expected_output": "处置方案"}
            ],
            "reasoning": "默认完整流程，包含所有子智能体（新架构）"
        }

    def _llm_process_agent_output(self, agent_id: str,
                                   raw_output: Dict[str, Any],
                                   next_agent_id: str) -> Dict[str, Any]:
        """
        第一层LLM：主智能体处理子智能体输出

        将子智能体的原始输出转换为适合下一个子智能体的结构化输入

        Args:
            agent_id: 当前子智能体ID
            raw_output: 子智能体的原始输出
            next_agent_id: 下一个子智能体ID

        Returns:
            处理后的结构化输出
        """
        # ========== 优先直接传递处理后的数据 ==========
        # 检查agent是否输出了处理后的数据
        processed_data = self._extract_processed_data(raw_output)
        if processed_data:
            print(f"[L1-LLM] {agent_id}输出了处理后的数据，直接传递给{next_agent_id}，跳过LLM处理")
            return {
                "processed_data": processed_data,
                "status": "success",
                "source_agent": agent_id
            }

        # ========== 如果没有处理后的数据，使用LLM处理 ==========
        if self.llm_client is None:
            print("[L1-LLM] LLM客户端不可用，直接传递原始输出")
            return raw_output

        system_prompt = self._build_master_agent_system_prompt()

        # 获取下一个子智能体的信息
        next_agent_info = self.identity_loader.SUB_AGENTS.get(next_agent_id, {})
        next_agent_name = next_agent_info.get("name", next_agent_id)

        process_prompt = f"""
子智能体 {agent_id} 执行完成，请处理其输出以便传递给下一个子智能体 {next_agent_name}({next_agent_id})。

## 子智能体原始输出
```json
{json.dumps(raw_output, ensure_ascii=False, indent=2)}
```

## 下一个子智能体
- ID: {next_agent_id}
- 名称: {next_agent_name}
- 作用: {next_agent_info.get('skill_module', '未知')}

## 请处理
1. 提取关键信息和数据
2. 结构化整理
3. 删除冗余和无关数据
4. 确保数据格式适合下一个子智能体使用

请返回JSON格式的结构化输出：
```json
{{
  "processed_data": {{...}},  // 处理后的核心数据
  "key_findings": [...],      // 关键发现
  "quality_assessment": {{...}}, // 质量评估
  "summary": "简要总结",       // 处理过程总结
  "for_next_agent": {{...}}   // 专门给下一个子智能体的数据
}}
```
"""

        try:
            print(f"[L1-LLM] 主智能体处理 {agent_id} 输出，准备传递给 {next_agent_id}...")
            response = self.llm_client.chat(
                message=process_prompt,
                system_prompt=system_prompt,
                model_type="primary",
                temperature=0.0
            )
            print(f"[L1-LLM] 输出处理响应: {response[:300]}...")

            processed = self._parse_llm_decision(response)
            print(f"[L1-LLM] 输出处理完成，提取了 {len(processed)} 个字段")
            return processed

        except Exception as e:
            logger.error(f"[L1-LLM] 输出处理失败: {e}")
            import traceback
            traceback.print_exc()
            return raw_output

    def coordinate_all_agents(self, task: Dict[str, Any],
                              analysis_scope: List[str] = None) -> Dict[str, Any]:
        """
        两层LLM驱动的子智能体协调

        第一层LLM（主智能体）：
        1. 决策调用哪些子智能体
        2. 处理子智能体输出并结构化
        3. 将处理后的结果传递给下一个子智能体

        第二层LLM（子智能体内）：
        1. 决策调用哪个脚本
        2. 分析脚本执行结果

        Args:
            task: 主任务
            analysis_scope: 分析范围（可选）

        Returns:
            所有子智能体的执行结果
        """
        results = {}
        # 初始化处理上下文，同时保留原始任务的metadata在顶层（方便第一个agent获取原始数据）
        processed_context = {"original_task": task}
        if "metadata" in task:
            processed_context["metadata"] = task["metadata"]

        # ============ 第一层LLM：主智能体决策执行计划 ============
        # 强制使用完整执行计划（所有4个子智能体）
        if analysis_scope == "full":
            print("[COORD] 强制使用完整执行计划（所有4个子智能体）")
            plan_result = self._get_default_execution_plan()
            agent_sequence = plan_result.get("execution_plan", [])
        elif self.llm_client is not None:
            print("=" * 60)
            print("[L1-LLM] 第一层LLM：主智能体决策子智能体执行计划")
            print("=" * 60)
            plan_result = self._llm_plan_subagent_execution(task)
            agent_sequence = plan_result.get("execution_plan", [])

            if not agent_sequence:
                print("[COORD] LLM返回的执行计划为空，使用默认计划")
                agent_sequence = self._get_default_execution_plan()["execution_plan"]
        else:
            print("[COORD] LLM不可用，使用默认执行计划")
            agent_sequence = self._get_default_execution_plan()["execution_plan"]

        print(f"[COORD] 执行计划包含 {len(agent_sequence)} 个子智能体:")
        for i, step in enumerate(agent_sequence):
            agent_id = step.get("agent", "unknown")
            purpose = step.get("purpose", "未知")
            print(f"  {i+1}. {agent_id}: {purpose}")

        # ============ 按计划执行子智能体 ============
        for i, step in enumerate(agent_sequence):
            agent_id = step.get("agent")
            next_agent_id = agent_sequence[i + 1].get("agent") if i + 1 < len(agent_sequence) else None

            print("")
            print("=" * 60)
            print(f"[COORD] 执行子智能体 {i + 1}/{len(agent_sequence)}: {agent_id}")
            print("=" * 60)

            # ============ 第二层LLM：子智能体内决策 ============
            print(f"[L2-LLM] 第二层LLM：{agent_id} 决策脚本调用...")

            # 如果有前一个agent的处理后数据，传递给当前agent
            if "processed_data" in processed_context:
                print(f"[DATA-FLOW] 当前agent将使用前一个agent的处理后数据")

            result = self.coordinate_agent_execution(
                agent_id,
                task=processed_context,  # 传递累积的、处理后的上下文
                previous_results=None
            )

            results[agent_id] = result

            # ============ 数据流处理：提取当前agent的处理后数据 ==========
            processed_data = self._extract_processed_data(result)

            # 保留当前agent的原始输出
            processed_context[f"{agent_id}_raw_output"] = result

            if processed_data:
                print(f"[DATA-FLOW] {agent_id} 输出了处理后的数据，准备传递给下一个agent")
                # 更新processed_context中的processed_data，供下一个agent使用
                processed_context["processed_data"] = processed_data

                # 如果有处理后的数据，跳过LLM处理（避免数据被修改）
                if next_agent_id:
                    print(f"[L1-LLM] 跳过LLM处理，直接传递处理后的数据给{next_agent_id}")
            else:
                print(f"[DATA-FLOW] {agent_id} 没有输出处理后的数据（或输出格式不标准）")

                # ============ 第一层LLM：主智能体处理输出（仅当没有处理后的数据时） ============
                if next_agent_id and self.llm_client is not None and result.get("status") == "success":
                    print("")
                    print(f"[L1-LLM] 第一层LLM：主智能体处理 {agent_id} 输出")

                    processed_output = self._llm_process_agent_output(
                        agent_id, result, next_agent_id
                    )

                    # 如果LLM处理输出了解析后的processed_data，使用它
                    if "processed_data" in processed_output:
                        processed_context["processed_data"] = processed_output["processed_data"]

                    processed_context[f"{agent_id}_processed"] = processed_output
                    processed_context["last_processed"] = processed_output

                    print(f"[L1-LLM] 处理完成")

            # 如果执行失败，中断流程
            if result.get("status") == "error":
                logger.error(f"[COORD] 子智能体 {agent_id} 执行失败，中断流程")
                break

        print("")
        print("=" * 60)
        print(f"[COORD] 所有子智能体执行完成: {len(results)} 个")
        print("=" * 60)

        return results


class ExecutionControlModule:
    """执行控制模块"""

    def __init__(self, llm_client=None):
        """初始化执行控制模块"""
        self.name = "执行控制模块"
        self.version = "2.0.0"

        # 执行记录
        self.active_executions: Dict[str, Dict[str, Any]] = {}
        self.execution_history: List[ExecutionReport] = []

        # 子智能体客户端（兼容旧接口）
        self.agent_clients: Dict[str, Any] = {}

        # 大模型协调器（核心）
        self.llm_coordinator = LLMAgentCoordinator(llm_client, project_root)

        # 动态编排器（任务规划与智能体协调）
        self.orchestrator = DynamicOrchestrator()

        print(f"[INIT] {self.name} v{self.version} initialized")
        print(f"[INIT] 大模型协调器已启用")
        print(f"[INIT] 动态编排器已集成")

    def register_agent_client(self, agent_id: str, client: Any):
        """
        注册子智能体客户端

        Args:
            agent_id: 子智能体ID
            client: 客户端对象（可以是HTTP客户端、gRPC客户端等）
        """
        self.agent_clients[agent_id] = client
        print(f"[REGISTER] Agent client registered: {agent_id}")

    async def execute_task(self, task: Dict[str, Any],
                          allocation: Dict[str, Any],
                          callback: Optional[Callable] = None) -> ExecutionResult:
        """
        执行单个任务

        Args:
            task: 结构化任务
            allocation: 资源分配结果
            callback: 完成回调函数

        Returns:
            ExecutionResult: 执行结果
        """
        task_id = task["task_id"]
        agent_id = allocation["agent_id"]
        timeout = allocation.get("estimated_duration", task.get("timeout_seconds", 300))

        result = ExecutionResult(
            task_id=task_id,
            agent_id=agent_id,
            status=ExecutionStatus.PENDING,
            timeout_seconds=timeout
        )

        try:
            print(f"[EXECUTE] Starting task {task_id} on agent {agent_id}")

            # 更新状态
            result.status = ExecutionStatus.RUNNING
            result.start_time = datetime.now().isoformat()

            # 记录活跃执行
            self.active_executions[task_id] = {
                "task": task,
                "allocation": allocation,
                "start_time": datetime.now()
            }

            # 实际执行（这里模拟执行，实际需要调用子智能体）
            output_data = await self._dispatch_to_agent(task, allocation, timeout)

            # 执行成功
            result.status = ExecutionStatus.COMPLETED
            result.output_data = output_data
            result.end_time = datetime.now().isoformat()

            # 计算执行时间
            start = datetime.fromisoformat(result.start_time)
            end = datetime.fromisoformat(result.end_time)
            result.duration_seconds = (end - start).total_seconds()

            print(f"[EXECUTE] Task {task_id} completed in {result.duration_seconds:.2f}s")

        except asyncio.TimeoutError:
            result.status = ExecutionStatus.TIMEOUT
            result.error_message = f"Task timeout after {timeout}s"
            result.end_time = datetime.now().isoformat()
            logger.error(f"[TIMEOUT] Task {task_id} timeout")

        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error_message = str(e)
            result.error_code = type(e).__name__
            result.end_time = datetime.now().isoformat()
            logger.error(f"[ERROR] Task {task_id} failed: {e}")

        finally:
            # 清理活跃执行记录
            if task_id in self.active_executions:
                del self.active_executions[task_id]

            # 调用回调
            if callback:
                await callback(result)

        return result

    async def _dispatch_to_agent(self, task: Dict[str, Any],
                                 allocation: Dict[str, Any],
                                 timeout: int) -> Dict[str, Any]:
        """
        分发任务到子智能体（使用大模型协调器）

        大模型协调子智能体流程：
        1. 读取子智能体完整身份（SKILL.md, AGENTS.md, SOUL.md, MEMORY.md）
        2. 理解任务需求
        3. 调用已开发脚本完成任务
        4. 返回执行结果
        """
        agent_id = allocation["agent_id"]

        print(f"[DISPATCH] 分发任务到 {agent_id}")

        # 使用大模型协调器执行任务
        # 注意：这里是同步调用，实际在异步上下文中运行
        result = self.llm_coordinator.coordinate_agent_execution(
            agent_id, task
        )

        return {
            "agent_id": agent_id,
            "task_id": task["task_id"],
            "result": result.get("status", "unknown"),
            "data": result,
            "timestamp": datetime.now().isoformat()
        }

    async def execute_stage(self, stage: Dict[str, Any],
                           tasks: Dict[str, Dict[str, Any]],
                           allocations: Dict[str, Dict[str, Any]]) -> List[ExecutionResult]:
        """
        执行一个阶段（并行执行阶段内所有任务）

        Args:
            stage: 执行阶段
            tasks: 任务字典
            allocations: 资源分配字典

        Returns:
            List[ExecutionResult]: 执行结果列表
        """
        stage_id = stage["stage_id"]
        task_ids = stage["tasks"]
        execution_mode = stage.get("execution_mode", "parallel")

        print(f"[STAGE] Executing stage {stage_id} with {len(task_ids)} tasks ({execution_mode})")

        if execution_mode == "parallel":
            # 并行执行
            coroutines = []
            for task_id in task_ids:
                if task_id in tasks and task_id in allocations:
                    coro = self.execute_task(tasks[task_id], allocations[task_id])
                    coroutines.append(coro)

            results = await asyncio.gather(*coroutines, return_exceptions=True)

            # 处理异常
            execution_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    # 创建失败结果
                    task_id = task_ids[i]
                    execution_results.append(ExecutionResult(
                        task_id=task_id,
                        agent_id=allocations[task_id]["agent_id"],
                        status=ExecutionStatus.FAILED,
                        error_message=str(result)
                    ))
                else:
                    execution_results.append(result)

        else:
            # 串行执行
            execution_results = []
            for task_id in task_ids:
                if task_id in tasks and task_id in allocations:
                    result = await self.execute_task(tasks[task_id], allocations[task_id])
                    execution_results.append(result)

                    # 如果任务失败且不允许继续，则停止
                    if result.status == ExecutionStatus.FAILED:
                        print(f"[STAGE] Task {task_id} failed, stopping stage")
                        break

        return execution_results

    async def execute_flow(self, flow: Dict[str, Any],
                          allocations: Dict[str, Dict[str, Any]]) -> ExecutionReport:
        """
        执行完整的任务流

        Args:
            flow: 任务流
            allocations: 资源分配字典

        Returns:
            ExecutionReport: 执行报告
        """
        flow_id = flow["flow_id"]
        tasks = flow["tasks"]
        stages = flow["stages"]

        print(f"[FLOW] Starting flow execution: {flow_id}")

        report = ExecutionReport(
            flow_id=flow_id,
            total_tasks=len(tasks),
            completed_tasks=0,
            failed_tasks=0,
            timeout_tasks=0,
            start_time=datetime.now().isoformat()
        )

        try:
            # 按阶段执行
            for stage in stages:
                results = await self.execute_stage(stage, tasks, allocations)

                # 记录结果
                for result in results:
                    report.task_results[result.task_id] = result

                    if result.status == ExecutionStatus.COMPLETED:
                        report.completed_tasks += 1
                    elif result.status == ExecutionStatus.TIMEOUT:
                        report.timeout_tasks += 1
                    else:
                        report.failed_tasks += 1

                # 检查是否需要中止（过多失败）
                if report.failed_tasks > report.total_tasks * 0.5:
                    logger.error(f"[FLOW] Too many failures, aborting flow")
                    break

        except Exception as e:
            logger.error(f"[FLOW] Flow execution error: {e}")

        finally:
            report.end_time = datetime.now().isoformat()
            start = datetime.fromisoformat(report.start_time)
            end = datetime.fromisoformat(report.end_time)
            report.total_duration_seconds = (end - start).total_seconds()

            # 保存历史记录
            self.execution_history.append(report)

            print(f"[FLOW] Flow completed: {report.completed_tasks}/{report.total_tasks} tasks successful")

        return report

    def execute_plan(self, plan: ExecutionPlan, dry_run: bool = False) -> Dict[str, Any]:
        """执行执行计划

        Args:
            plan: DynamicOrchestrator创建的执行计划
            dry_run: 是否仅模拟执行

        Returns:
            执行结果字典
        """
        print(f"[PLAN] 执行计划: task_type={plan.task_type}, mode={plan.execution_mode.value}, agents={len(plan.agents)}")

        if dry_run:
            return {
                "status": "dry_run",
                "agents_planned": len(plan.agents),
                "execution_mode": plan.execution_mode.value,
                "agents": [a.id for a in plan.agents],
                "task_type": plan.task_type
            }

        results = {}
        for idx, agent_task in enumerate(plan.agents):
            agent_id = agent_task.id

            print(f"[PLAN] 执行智能体 {idx + 1}/{len(plan.agents)}: {agent_id}")

            # 调用子智能体的逻辑
            result = self._execute_agent(agent_id, agent_task)
            results[agent_id] = result

            # 如果不是并行模式，传递结果给下一个智能体
            if plan.execution_mode != ExecutionMode.PARALLEL and idx < len(plan.agents) - 1:
                next_agent = plan.agents[idx + 1]
                # 更新下一个智能体的输入数据
                if result.get("status") == "success" and "processed_data" in result:
                    next_agent.input_data.update(result["processed_data"])
                    print(f"[PLAN] 传递处理后的数据给 {next_agent.id}")

        return {
            "status": "completed",
            "results": results,
            "agents_executed": len(results),
            "task_type": plan.task_type
        }

    def _execute_agent(self, agent_id: str, agent_task: Any) -> Dict[str, Any]:
        """执行单个子智能体任务

        Args:
            agent_id: 子智能体ID
            agent_task: AgentTask对象

        Returns:
            执行结果字典
        """
        # 构建任务字典
        task = {
            "task_id": agent_task.id,
            "agent_id": agent_id,
            "task_name": agent_task.name,
            "data": agent_task.input_data,
            "config": agent_task.config,
            "metadata": {
                "description": f"执行 {agent_task.name} 任务"
            }
        }

        # 使用大模型协调器执行
        try:
            result = self.llm_coordinator.coordinate_agent_execution(
                agent_id=agent_id,
                task=task,
                previous_results=None
            )
            return result
        except Exception as e:
            logger.error(f"[PLAN] 智能体 {agent_id} 执行失败: {e}")
            return {
                "status": "error",
                "agent_id": agent_id,
                "error": str(e)
            }

    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务执行

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否成功取消
        """
        if task_id in self.active_executions:
            # 实际实现中需要向子智能体发送取消请求
            del self.active_executions[task_id]
            print(f"[CANCEL] Task {task_id} cancelled")
            return True
        return False

    def get_active_executions(self) -> List[Dict[str, Any]]:
        """获取活跃执行列表"""
        return [
            {
                "task_id": task_id,
                "agent_id": info["allocation"]["agent_id"],
                "duration_seconds": (datetime.now() - info["start_time"]).total_seconds()
            }
            for task_id, info in self.active_executions.items()
        ]

    def get_execution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取执行历史"""
        history = self.execution_history[-limit:]
        return [r.to_dict() for r in reversed(history)]

    def get_statistics(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        if not self.execution_history:
            return {"message": "No execution history"}

        total_flows = len(self.execution_history)
        total_tasks = sum(r.total_tasks for r in self.execution_history)
        successful_tasks = sum(r.completed_tasks for r in self.execution_history)

        return {
            "total_flows": total_flows,
            "total_tasks": total_tasks,
            "successful_tasks": successful_tasks,
            "success_rate": successful_tasks / total_tasks if total_tasks > 0 else 0,
            "avg_duration_seconds": sum(r.total_duration_seconds for r in self.execution_history) / total_flows
        }


# 便捷函数，供主智能体调用
async def execute_single_task(task: Dict[str, Any],
                             allocation: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行单个任务（便捷函数，异步）

    Args:
        task: 结构化任务
        allocation: 资源分配

    Returns:
        Dict: 执行结果字典
    """
    module = ExecutionControlModule()
    result = await module.execute_task(task, allocation)
    return result.to_dict()


def execute_single_task_sync(task: Dict[str, Any],
                            allocation: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行单个任务（便捷函数，同步包装）

    Args:
        task: 结构化任务
        allocation: 资源分配

    Returns:
        Dict: 执行结果字典
    """
    return asyncio.run(execute_single_task(task, allocation))


async def execute_task_flow(flow: Dict[str, Any],
                           allocations: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    执行任务流（便捷函数，异步）

    Args:
        flow: 任务流
        allocations: 资源分配字典

    Returns:
        Dict: 执行报告字典
    """
    module = ExecutionControlModule()
    report = await module.execute_flow(flow, allocations)
    return report.to_dict()


def execute_task_flow_sync(flow: Dict[str, Any],
                          allocations: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    执行任务流（便捷函数，同步包装）

    Args:
        flow: 任务流
        allocations: 资源分配字典

    Returns:
        Dict: 执行报告字典
    """
    return asyncio.run(execute_task_flow(flow, allocations))


if __name__ == "__main__":
    # 测试代码
    test_task = {
        "task_id": "task_000001",
        "task_name": "数据获取",
        "category": "data_acquisition",
        "timeout_seconds": 60
    }

    test_allocation = {
        "task_id": "task_000001",
        "agent_id": "multi-dimensional-data-perception-agent",
        "agent_name": "多维数据感知子智能体",
        "match_score": 0.95,
        "match_reasons": ["能力匹配", "状态可用"],
        "estimated_duration": 30
    }

    # 同步测试
    result = execute_single_task_sync(test_task, test_allocation)
    print(json.dumps(result, indent=2, ensure_ascii=False))
