"""
智能体服务 - 封装 AIAgent 调用逻辑

使用自定义 AIAgent (shared/framework/hermes_agent) 而非原生 hermes-agent
"""
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# 导入自定义 AIAgent
try:
    from shared.framework.hermes_agent.run_agent import AIAgent
    CUSTOM_AIAGENT_AVAILABLE = True
except ImportError as e:
    logging.warning(f"自定义 AIAgent 导入失败: {e}")
    CUSTOM_AIAGENT_AVAILABLE = False
    # 备用：尝试导入原生 hermes-agent
    try:
        from run_agent import AIAgent
    except ImportError:
        AIAgent = None

from backend.models.query import QueryResponse
from backend.utils.loggers import generate_session_id

logger = logging.getLogger(__name__)


class AgentService:
    """智能体服务 - 封装所有 AIAgent 调用逻辑"""

    def __init__(self):
        self.agent_cache: Dict[str, Any] = {}
        self.project_dir = Path("E:/project/Ecological_env").resolve()
        self._ensure_correct_directory()

    def _ensure_correct_directory(self):
        """确保在正确的工作目录"""
        current_cwd = os.getcwd()
        if current_cwd != str(self.project_dir):
            logger.info(f"切换目录: {current_cwd} -> {self.project_dir}")
            os.chdir(self.project_dir)

    def _check_identity_files(self) -> bool:
        """检查身份文件是否存在"""
        identity_path = self.project_dir / "workspace"
        required_files = [
            "IDENTITY.md",
            "SOUL.md",
            "AGENTS.md",
            "MEMORY.md",
            "USER.md",
            "TOOLS.md",
            "HEARTBEAT.md"
        ]

        missing = []
        for filename in required_files:
            if not (identity_path / filename).exists():
                missing.append(filename)

        if missing:
            logger.warning(f"缺少身份文件: {missing}")
            return False

        logger.info("所有身份文件检查通过")
        return True

    def get_agent(self, session_id: Optional[str] = None) -> Any:
        """
        获取或创建 AIAgent 实例

        Args:
            session_id: 会话ID（可选）

        Returns:
            AIAgent 实例

        Raises:
            ImportError: AIAgent 不可用
        """
        if AIAgent is None:
            raise ImportError("AIAgent 不可用，请检查 shared/framework/hermes_agent 或 hermes-agent 安装")

        # 使用缓存
        if session_id and session_id in self.agent_cache:
            return self.agent_cache[session_id]

        # 确保在正确目录
        self._ensure_correct_directory()

        # 读取环境变量
        base_url = os.environ.get("LLM_BASE_URL", "http://172.16.12.41:30000/v1")
        model = os.environ.get("LLM_MODEL", "ctgu-vlm")
        provider = os.environ.get("LLM_PROVIDER", "custom")
        api_key = os.environ.get("LLM_API_KEY", "")

        logger.info(f"创建 AIAgent: model={model}, base_url={base_url}")

        # 检查自定义版本是否可用
        if CUSTOM_AIAGENT_AVAILABLE:
            logger.info("✅ 使用自定义 AIAgent (shared/framework/hermes_agent)")
        else:
            logger.warning("⚠️ 使用原生 hermes-agent AIAgent")

        # 创建 AIAgent
        agent = AIAgent(
            base_url=base_url,
            api_key=api_key,
            model=model,
            provider=provider,
            load_soul_identity=True,      # 加载 workspace/SOUL.md
            skip_context_files=False,     # 加载 AGENTS.md、MEMORY.md 等
            enabled_toolsets=["orchestrator", "skills", "terminal"],
            max_iterations=10,             # 限制迭代次数避免超时
            quiet_mode=False,              # 启用日志以便调试
            session_id=session_id,
        )

        # 缓存实例
        if session_id:
            self.agent_cache[session_id] = agent

        logger.info(f"AIAgent 实例创建成功: session_id={session_id}")
        return agent

    def process_query(
        self,
        query: str,
        session_id: Optional[str] = None
    ) -> QueryResponse:
        """
        处理查询并返回完整响应

        Args:
            query: 用户查询
            session_id: 会话ID（可选，如未提供则生成）

        Returns:
            QueryResponse 响应对象

        Raises:
            ImportError: AIAgent 不可用
            Exception: 智能体调用失败
        """
        import time

        start_time = time.time()

        # 生成 session_id
        if not session_id:
            session_id = generate_session_id()

        try:
            logger.info(f"处理查询: session={session_id}, query={query[:50]}...")

            # 获取 agent
            agent = self.get_agent(session_id)

            # 调用智能体
            response = agent.run_conversation(
                user_message=query,
                conversation_history=None
            )

            # 提取响应内容
            if isinstance(response, dict):
                content = response.get('final_response', str(response))
                chart_data = response.get('chart')
            else:
                content = str(response) if response else ""
                chart_data = None

            # 计算耗时
            elapsed = time.time() - start_time
            logger.info(f"查询完成: session={session_id}, 耗时={elapsed:.2f}s")

            # 构建响应
            return QueryResponse(
                content=content,
                session_id=session_id,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                chartData=chart_data,
                decision_path=[],  # 可以后续实现
                sub_agent_calls=[],
                data_sources=[],
                reasoning={
                    "intent": "query",
                    "model": os.environ.get("LLM_MODEL", "ctgu-vlm"),
                    "custom_aiagent": CUSTOM_AIAGENT_AVAILABLE
                },
                metadata={
                    "model": os.environ.get("LLM_MODEL", "ctgu-vlm"),
                    "base_url": os.environ.get("LLM_BASE_URL", ""),
                    "load_soul_identity": True,
                    "skip_context_files": False,
                    "elapsed_seconds": elapsed
                }
            )

        except Exception as e:
            logger.error(f"查询失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
