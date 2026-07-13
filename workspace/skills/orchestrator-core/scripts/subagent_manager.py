# workspace/skills/orchestrator-core/scripts/subagent_manager.py
"""子智能体实例管理器

负责创建、管理和销毁子智能体实例
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SubagentManager:
    """子智能体实例管理器

    管理所有子智能体的生命周期，包括创建、获取和销毁
    """

    # 子智能体配置
    SUBAGENT_CONFIGS = {
        "multi-dimensional-data-perception-agent": {
            "path": "subagents/multi-dimensional-data-perception-agent",
            "description": "多维数据感知子智能体"
        },
        "anomaly-detection-agent": {
            "path": "subagents/anomaly-detection-agent",
            "description": "异常检测子智能体"
        },
        "rule-reasoning-agent": {
            "path": "subagents/rule-reasoning-agent",
            "description": "规则推理子智能体"
        },
        "disposition-execution-agent": {
            "path": "subagents/disposition-execution-agent",
            "description": "研判预警与处置执行子智能体"
        }
    }

    def __init__(self, project_root: Path | str = None):
        """初始化子智能体管理器

        Args:
            project_root: 项目根目录路径
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.subagents: Dict[str, object] = {}
        self._initialized = False

    def create_subagents(self, model: str = None, base_url: str = None, api_key: str = None):
        """创建所有子智能体实例

        Args:
            model: LLM模型名称
            base_url: API基础URL
            api_key: API密钥
        """
        if self._initialized:
            logger.warning("Subagents already initialized, skipping")
            return

        try:
            from run_agent import AIAgent

            for name, config in self.SUBAGENT_CONFIGS.items():
                try:
                    identity_path = self.project_root / config["path"]

                    # 验证identity_path是否存在
                    if not identity_path.exists():
                        logger.warning(f"Identity path not found: {identity_path}")
                        continue

                    # 创建子智能体实例
                    subagent = AIAgent(
                        model=model,
                        base_url=base_url,
                        api_key=api_key,
                        identity_path=identity_path,
                        load_soul_identity=True,
                        skip_context_files=True,  # 子智能体只加载身份文件
                        skip_memory=True,  # 子智能体有自己的记忆
                        quiet_mode=True,  # 子智能体静默模式
                    )

                    self.subagents[name] = subagent
                    logger.info(f"Created subagent: {name}")

                except Exception as e:
                    logger.error(f"Failed to create subagent {name}: {e}")

            self._initialized = True
            logger.info(f"Initialized {len(self.subagents)} subagents")

        except ImportError as e:
            logger.error(f"Failed to import AIAgent: {e}")
            raise

    def get_subagent(self, name: str) -> Optional[object]:
        """获取子智能体实例

        Args:
            name: 子智能体名称

        Returns:
            子智能体实例，如果不存在则返回None
        """
        if not self._initialized:
            logger.warning("Subagents not initialized, call create_subagents() first")
            return None

        return self.subagents.get(name)

    def get_all_subagents(self) -> Dict[str, object]:
        """获取所有子智能体实例

        Returns:
            所有子智能体实例的字典
        """
        return self.subagents.copy()

    def list_subagents(self) -> list[str]:
        """列出所有已创建的子智能体名称

        Returns:
            子智能体名称列表
        """
        return list(self.subagents.keys())

    def is_subagent_available(self, name: str) -> bool:
        """检查子智能体是否可用

        Args:
            name: 子智能体名称

        Returns:
            子智能体是否可用
        """
        return name in self.subagents

    def shutdown(self):
        """关闭所有子智能体实例

        清理资源，释放连接
        """
        for name, subagent in self.subagents.items():
            try:
                # 如果子智能体有shutdown方法，调用它
                if hasattr(subagent, 'shutdown'):
                    subagent.shutdown()
                logger.info(f"Shutdown subagent: {name}")
            except Exception as e:
                logger.error(f"Error shutting down subagent {name}: {e}")

        self.subagents.clear()
        self._initialized = False
