"""
动态编排器 - 负责任务规划和资源分配

职责：
1. 接收用户任务请求
2. 解析任务意图（调用 LLM）
3. 生成执行计划（DAG）
4. 匹配子智能体资源
5. 调用 ExecutionControl 执行任务

不负责：
- 实际的子智能体调用（由 ExecutionControl 负责）
- 结果解释（由 result_interpretation.py 负责）

根据任务类型、数据状态和历史结果，动态决策子智能体组合和执行顺序
"""
import yaml
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum


# Configure logging
logger = logging.getLogger(__name__)

# Constants for agent IDs
DATA_PERCEPTION_AGENT = "multi-dimensional-data-perception-agent"
ANOMALY_DETECTION_AGENT = "anomaly-detection-agent"
RULE_REASONING_AGENT = "rule-reasoning-agent"
DISPOSITION_EXECUTION_AGENT = "disposition-execution-agent"

# Constant for default task type
DEFAULT_TASK_TYPE = "violation_detection"


class ExecutionMode(Enum):
    """执行模式"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HYBRID = "hybrid"


@dataclass
class AgentTask:
    """子智能体任务"""
    id: str
    name: str
    capabilities: List[str]
    script_path: str
    input_data: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)


@dataclass
class ExecutionPlan:
    """执行计划"""
    task_type: str
    execution_mode: ExecutionMode
    agents: List[AgentTask]
    estimated_duration: Optional[int] = None
    parallel_pairs: List[Tuple[str, str]] = field(default_factory=list)


class DynamicOrchestrator:
    """动态编排器"""

    def __init__(self, registry_path: str = "shared/configs/agent_registry.yaml"):
        """初始化动态编排器

        Args:
            registry_path: 子智能体注册表路径
        """
        self.registry_path = Path(registry_path)
        self.available_agents = self._load_agent_registry()
        self.task_type_mapping = self._load_task_mapping()

    def _resolve_config_path(self) -> Path:
        """解析配置文件路径

        Returns:
            Path: 解析后的配置文件路径
        """
        registry_path = self.registry_path
        if not registry_path.exists():
            # 尝试相对于项目根目录的路径
            project_root = Path(__file__).parent.parent.parent.parent.parent
            registry_path = project_root / "shared" / "configs" / "agent_registry.yaml"
        return registry_path

    def _load_agent_registry(self) -> Dict[str, Any]:
        """加载子智能体注册表

        Returns:
            Dict[str, Any]: 智能体注册表字典，失败返回空字典
        """
        registry_path = self._resolve_config_path()

        try:
            with open(registry_path, 'r', encoding='utf-8') as f:
                registry = yaml.safe_load(f)

            if registry is None:
                logger.warning(f"Agent registry file is empty: {registry_path}")
                return {}

            if 'agents' not in registry:
                logger.warning(f"Agent registry missing 'agents' key: {registry_path}")
                return {}

            return registry.get('agents', {})

        except FileNotFoundError:
            logger.error(f"Agent registry file not found: {registry_path}")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML file {registry_path}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error loading agent registry: {e}")
            return {}

    def _load_task_mapping(self) -> Dict[str, List[str]]:
        """加载任务类型与智能体映射

        Returns:
            Dict[str, List[str]]: 任务类型映射，失败返回空字典
        """
        registry_path = self._resolve_config_path()

        try:
            with open(registry_path, 'r', encoding='utf-8') as f:
                registry = yaml.safe_load(f)

            if registry is None:
                logger.warning(f"Agent registry file is empty: {registry_path}")
                return {}

            if 'task_type_mapping' not in registry:
                logger.warning(f"Agent registry missing 'task_type_mapping' key: {registry_path}")
                return {}

            return registry.get('task_type_mapping', {})

        except FileNotFoundError:
            logger.error(f"Agent registry file not found: {registry_path}")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML file {registry_path}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error loading task mapping: {e}")
            return {}

    def _resolve_agent_id(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """解析智能体ID并返回对应的智能体信息

        Args:
            agent_id: 智能体ID（可能包含或不包含"-agent"后缀）

        Returns:
            Optional[Dict[str, Any]]: 智能体信息字典，未找到返回None
        """
        # 先尝试直接匹配（带"-agent"后缀的完整ID）
        base_id = agent_id.replace("-agent", "")
        agent_info = self.available_agents.get(base_id, {})

        if agent_info:
            return agent_info

        # 尝试通过id字段匹配
        for key, value in self.available_agents.items():
            if value.get("id") == agent_id:
                return value

        logger.warning(f"Agent not found: {agent_id}")
        return None

    def create_execution_plan(self, task: Dict[str, Any]) -> ExecutionPlan:
        """创建执行计划

        Args:
            task: 任务字典，包含task_type和data

        Returns:
            ExecutionPlan: 执行计划
        """
        task_type = task.get("task_type", DEFAULT_TASK_TYPE)
        enable_parallel = task.get("enable_parallel", False)

        # 获取该任务类型需要的智能体
        agent_ids = self.task_type_mapping.get(task_type, [])

        # 构建智能体任务列表
        agents = []
        resolved_ids = []  # Track resolved IDs for dependency resolution

        for idx, agent_id in enumerate(agent_ids):
            # 转换为完整ID格式
            full_agent_id = f"{agent_id}-agent" if not agent_id.endswith("-agent") else agent_id
            agent_info = self._resolve_agent_id(full_agent_id)

            if agent_info:
                resolved_id = agent_info.get("id", full_agent_id)
                resolved_ids.append(resolved_id)

                # 使用已解析的ID建立依赖关系
                depends_on = [resolved_ids[idx - 1]] if idx > 0 else []

                agent_task = AgentTask(
                    id=resolved_id,
                    name=agent_info.get("name", full_agent_id),
                    capabilities=agent_info.get("capabilities", []),
                    script_path=agent_info.get("script_path", ""),
                    input_data=task.get("data", {}),
                    depends_on=depends_on
                )
                agents.append(agent_task)
            else:
                logger.warning(f"Skipping unknown agent: {full_agent_id}")

        # 确定执行模式
        execution_mode = self._determine_execution_mode(task_type, agents, enable_parallel)

        # 检测可并行的智能体对
        parallel_pairs = self.detect_parallel_pairs(agents) if execution_mode != ExecutionMode.SEQUENTIAL else []

        return ExecutionPlan(
            task_type=task_type,
            execution_mode=execution_mode,
            agents=agents,
            parallel_pairs=parallel_pairs
        )

    def _determine_execution_mode(self, task_type: str, agents: List[AgentTask], enable_parallel: bool = False) -> ExecutionMode:
        """确定执行模式"""
        if enable_parallel and task_type == "violation_detection":
            return ExecutionMode.HYBRID
        elif enable_parallel:
            return ExecutionMode.PARALLEL
        else:
            return ExecutionMode.SEQUENTIAL

    def detect_parallel_pairs(self, agents: List[AgentTask]) -> List[Tuple[str, str]]:
        """检测可并行执行的智能体对

        基于智能体的依赖关系和能力判断是否可以并行执行
        """
        parallel_pairs = []

        # 数据感知和异常检测可以并行
        agent_ids = [a.id for a in agents]

        if DATA_PERCEPTION_AGENT in agent_ids:
            perception_idx = agent_ids.index(DATA_PERCEPTION_AGENT)
            # 后续的智能体如果有独立数据源，可以并行
            for i in range(perception_idx + 1, len(agents)):
                # 异常检测需要数据感知的输出，所以不能真正并行
                # 但可以预加载资源
                if agents[i].id == ANOMALY_DETECTION_AGENT:
                    # 这两个可以流水线并行
                    parallel_pairs.append((
                        DATA_PERCEPTION_AGENT,
                        ANOMALY_DETECTION_AGENT
                    ))

        return parallel_pairs
