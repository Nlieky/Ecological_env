#!/usr/bin/env python
"""
废水监测系统 - 主智能体服务启动脚本

提供独立的HTTP服务接口，管理主智能体AIAgent实例和子智能体。
服务端口：8642（可通过环境变量AGENT_PORT配置）
"""

import os
import sys
import logging
import time
import uuid
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

# 添加项目根目录到路径
project_root = Path(__file__).parents[1]
sys.path.insert(0, str(project_root))

# 加载环境变量
load_dotenv()

# 切断对系统 HERMES_HOME（可能指向 D:\Hermes 旧 home）的依赖：显式重定向到项目根，
# 使 hermes 的 env_loader 加载本项目 .env，而非 D:\Hermes\.env。
os.environ['HERMES_HOME'] = str(project_root)

from shared.framework.hermes_agent.run_agent import AIAgent

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QueryRequest(BaseModel):
    """查询请求模型"""
    query: str
    session_id: str = None


class QueryResponse(BaseModel):
    """查询响应模型"""
    content: str
    session_id: str
    timestamp: str
    success: bool
    error: str = None


class AgentService:
    """主智能体服务管理器 - 性能优化版"""

    def __init__(self):
        """初始化主智能体服务"""
        self.master_agent: AIAgent = None
        self.project_root = Path(__file__).parents[1]
        # 会话历史存储：session_id -> messages列表
        self.session_histories: Dict[str, list] = {}
        # 查询缓存：提升性能
        self.query_cache: Dict[str, Dict] = {}
        self.cache_duration = 300  # 5分钟缓存

    def initialize(self):
        """初始化主智能体实例"""
        try:
            # 从环境变量获取LLM配置
            model = os.getenv("LLM_MODEL", "ctgu-vlm")
            base_url = os.getenv("LLM_BASE_URL", "http://172.16.12.41:30000/v1")
            api_key = os.getenv("LLM_API_KEY", "")

            logger.info(f"初始化主智能体: model={model}, base_url={base_url}")

            # 创建主智能体AIAgent实例
            # 关键：使用identity_path="workspace"加载主智能体身份文件
            self.master_agent = AIAgent(
                model=model,
                base_url=base_url,
                api_key=api_key,
                identity_path="workspace",  # 关键参数：加载主智能体身份文件
                load_soul_identity=True
            )

            # 设置最大迭代次数为15（4子智能体pipeline需要更多轮次）
            if hasattr(self.master_agent, 'max_iterations'):
                self.master_agent.max_iterations = 15
                logger.info("✅ 设置最大迭代次数为15")

            # 注册orchestrator工具到AIAgent
            try:
                # 修复导入路径：使用orchestrator-core而非orchestrator_core
                import importlib.util
                tool_reg_path = self.project_root / "workspace" / "skills" / "orchestrator-core" / "scripts" / "tool_registration.py"
                spec = importlib.util.spec_from_file_location("tool_registration", tool_reg_path)
                tool_reg_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(tool_reg_module)

                tool_reg_module.register_orchestrator_tools(self.master_agent)
                logger.info("✅ Orchestrator工具注册成功")
            except Exception as e:
                logger.warning(f"⚠️ Orchestrator工具注册失败: {e}")
                import traceback
                traceback.print_exc()

            logger.info("✅ 主智能体初始化成功")
            return True

        except Exception as e:
            logger.error(f"❌ 主智能体初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _get_cache_key(self, query: str) -> str:
        """生成查询缓存键"""
        import hashlib
        return hashlib.md5(query.encode()).hexdigest()[:16]

    def _check_cache(self, query: str) -> Dict[str, Any]:
        """检查查询缓存"""
        cache_key = self._get_cache_key(query)
        if cache_key in self.query_cache:
            cached = self.query_cache[cache_key]
            # 检查缓存是否过期
            import time
            if time.time() - cached['timestamp'] < self.cache_duration:
                logger.info(f"缓存命中: {query[:30]}...")
                return cached['result']
        return None

    def _update_cache(self, query: str, result: Dict[str, Any]):
        """更新查询缓存"""
        cache_key = self._get_cache_key(query)
        self.query_cache[cache_key] = {
            'result': result,
            'timestamp': time.time()
        }

    def _quick_response(self, query: str) -> Dict[str, Any]:
        """快速响应常见查询（性能优化）"""
        import re
        query_lower = query.lower()

        # 常见查询快速响应
        quick_responses = {
            r'你好|介绍|是谁': "我是废水监测系统的智能助手。我可以帮您查询监测数据、检测异常、判定违规和生成预警。请告诉我您的具体需求。",
            r'状态|健康|运行': "系统运行正常。主智能体服务在线，数据监测功能正常，子智能体调用就绪。",
            r'帮助|功能|能做什么': "我可以：\n1. 查询实时监测数据\n2. 检测水质异常\n3. 判定违规类型\n4. 生成预警报告\n5. 提供处置建议",
            r'谢谢|感谢': "不客气！如果您还有其他问题，请随时提问。"
        }

        for pattern, response in quick_responses.items():
            if re.search(pattern, query_lower):
                return {
                    "success": True,
                    "content": response,
                    "session_id": f"quick_{int(time.time())}",
                    "timestamp": datetime.now().isoformat(),
                    "cached": False,
                    "quick_response": True
                }

        return None

    def process_query(self, query: str, session_id: str = None) -> Dict[str, Any]:
        """处理查询请求 - 性能优化版"""
        import time
        from datetime import datetime

        start_time = time.time()

        try:
            # 1. 快速响应检查（性能优化）
            quick_result = self._quick_response(query)
            if quick_result:
                return quick_result

            # 2. 缓存检查（性能优化）
            cached_result = self._check_cache(query)
            if cached_result:
                cached_result['cached'] = True
                cached_result['timestamp'] = datetime.now().isoformat()
                return cached_result

            # 3. 正常处理流程
            if not self.master_agent:
                return {
                    "success": False,
                    "error": "主智能体未初始化"
                }

            # 处理session_id
            if session_id is None:
                # 生成新的session_id
                session_id = f"session_{int(time.time())}_{uuid.uuid4().hex[:8]}"
                conversation_history = None
            else:
                # 使用现有的会话历史
                conversation_history = self.session_histories.get(session_id)

            logger.info(f"处理查询: session={session_id}, query={query[:50]}...")

            # 调用主智能体，传递会话历史
            result = self.master_agent.run_conversation(
                user_message=query,
                conversation_history=conversation_history,
                task_id=session_id
            )

            # 更新会话历史（保存完整的对话）
            if "messages" in result:
                self.session_histories[session_id] = result["messages"]

            # 提取响应内容
            if isinstance(result, dict):
                content = result.get("final_response", str(result))
            else:
                content = str(result) if result else ""

            elapsed = time.time() - start_time
            logger.info(f"查询完成: session={session_id}, 耗时={elapsed:.2f}s, 消息数={len(result.get('messages', []))}")

            # 构建响应
            response = {
                "success": True,
                "content": content,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "message_count": len(result.get("messages", [])),
                "cached": False,
                "quick_response": False
            }

            # 更新缓存（仅缓存成功的响应）
            self._update_cache(query, response)

            return response

        except Exception as e:
            logger.error(f"查询失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }


# 全局服务实例
agent_service = AgentService()

# 创建FastAPI应用
app = FastAPI(
    title="废水监测主智能体服务",
    description="提供主智能体HTTP接口，管理AIAgent实例和子智能体调用",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """服务启动时初始化主智能体"""
    logger.info("正在启动主智能体服务...")

    # 初始化主智能体
    if not agent_service.initialize():
        logger.error("主智能体初始化失败，服务启动中止")
        raise Exception("主智能体初始化失败")

    # 输出服务信息
    port = int(os.getenv("AGENT_PORT", "8642"))
    logger.info(f"✅ 主智能体服务启动成功，监听端口: {port}")


@app.get("/")
async def root():
    """服务根路径"""
    return {
        "service": "废水监测主智能体服务",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "POST /query": "执行查询",
            "GET /health": "健康检查",
            "GET /status": "服务状态"
        }
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {
        "status": "healthy",
        "agent_initialized": agent_service.master_agent is not None
    }


@app.get("/status")
async def status():
    """服务状态"""
    return {
        "service": "running",
        "agent_ready": agent_service.master_agent is not None,
        "model": os.getenv("LLM_MODEL", ""),
        "base_url": os.getenv("LLM_BASE_URL", "")
    }


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """执行查询

    Args:
        request: 查询请求，包含query内容

    Returns:
        QueryResponse: 查询响应
    """
    result = agent_service.process_query(
        query=request.query,
        session_id=request.session_id
    )

    if result.get("success"):
        return QueryResponse(
            content=result["content"],
            session_id=result["session_id"],
            timestamp=result["timestamp"],
            success=True
        )
    else:
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "查询失败")
        )


def main():
    """主函数：启动服务"""
    # 获取配置
    port = int(os.getenv("AGENT_PORT", "8642"))
    host = os.getenv("AGENT_HOST", "0.0.0.0")

    logger.info(f"启动主智能体服务: {host}:{port}")

    # 启动FastAPI服务
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
