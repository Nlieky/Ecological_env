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
import threading
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
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
# pipeline 现已确定性+快（~30-60s），total_timeout 从 2400s 降回 300s（服务级上限）。
# 必须在 import AIAgent（触发 conversation_loop 加载、读取默认值）之前设置。
# 参数中心：DB 优先读 hermes_total_timeout（未配置时 300）。
# 注意：不能用 `from backend.services.agent_params import get_param`——那会先执行
# backend/services/__init__.py（→ agent_service → 模块级 import AIAgent），破坏
# "先设 env 再 import AIAgent" 的时序。按文件路径直接加载，绕过包 __init__
# （与下方 tool_registration 的既有做法一致）。
# 实情：vendored hermes v0.16 引擎并不读取 HERMES_TOTAL_TIMEOUT env——此设置无害，
# 保留作向前兼容（未来引擎读取时即生效），参数中心同步标注为预留。
import importlib.util as _ilu
_ap_path = project_root / "backend" / "services" / "agent_params.py"
_ap_spec = _ilu.spec_from_file_location("agent_params_standalone", _ap_path)
_ap_mod = _ilu.module_from_spec(_ap_spec)
_ap_spec.loader.exec_module(_ap_mod)
_gp = _ap_mod.get_param
os.environ['HERMES_TOTAL_TIMEOUT'] = str(_gp("hermes_total_timeout", env_key="HERMES_TOTAL_TIMEOUT", default=300))

from shared.framework.hermes_agent.run_agent import AIAgent

# 配置中心 V2 接线：策略表(DB 优先) + 供应商表。放 AIAgent import 之后——
# backend/services/__init__ 会链式 import agent_service(其模块级 import AIAgent)，
# 此时 HERMES_HOME/HERMES_TOTAL_TIMEOUT 已设、AIAgent 已加载(sys.modules 缓存命中)，
# 不破坏上方"先设 env 再 import AIAgent"的时序。
from backend.services.agent_strategy import get_strategy as _gst
from backend.services import llm_providers as _lp

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
    trace: dict = None  # 子智能体调用明细(decision_path + subagent_calls),供后端审计


class AgentService:
    """主智能体服务管理器 - 性能优化版"""

    def __init__(self):
        """初始化主智能体服务"""
        self.master_agent: AIAgent = None
        self.project_root = Path(__file__).parents[1]
        # 会话历史存储：session_id -> messages列表
        self.session_histories: Dict[str, list] = {}
        # 会话→上一轮 session 目录的映射：同一对话多轮追问时，把上一轮的子智能体结果
        # 文件(data_result/anomaly_result/...)续传进本轮新目录，让"那有没有异常"这类
        # 追问能直接链式消费上一轮取的数据（像正常多轮对话有上下文）。不同会话不续传。
        self._session_dirs: Dict[str, str] = {}
        # 查询缓存：提升性能
        self.query_cache: Dict[str, Dict] = {}
        self.cache_duration = 300  # 5分钟缓存
        # master_agent 是单例共享，run_conversation 会改它的内部状态（messages/session_id），
        # 并发查询会串台。用锁串行化对 master_agent 的访问（配合 /query 走线程池）。
        self._agent_lock = threading.Lock()
        self._agent_lock_timeout = 300  # 排队超过 5 分钟直接返回"忙"，不无限等

    def initialize(self):
        """初始化主智能体实例"""
        try:
            # LLM 读取链:策略 default_llm_provider → providers 表行 → get_param/env 兜底
            model = _gp("llm_model", env_key="LLM_MODEL", default="ctgu-vlm")
            base_url = _gp("llm_base_url", env_key="LLM_BASE_URL", default="http://172.16.12.41:30000/v1")
            api_key = _gp("llm_api_key", env_key="LLM_API_KEY", default="")
            try:
                _lp.seed_defaults()
                _prov = _lp.resolve_default()
                if _prov:
                    model, base_url, api_key = _prov["model"], _prov["base_url"], _prov["api_key"]
                    logger.info(f"使用默认供应商: {_prov['name']}")
            except Exception as _e:
                logger.warning(f"provider 解析失败,走 env/get_param 兜底: {_e}")

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

            # 设置最大迭代次数（4子智能体pipeline需要更多轮次；参数中心可调）
            if hasattr(self.master_agent, 'max_iterations'):
                self.master_agent.max_iterations = _gp("master_max_iterations", default=15)
                logger.info(f"✅ 设置最大迭代次数为 {self.master_agent.max_iterations}")

            # MCP 工具发现(配置中心·MCP tab 写 config.yaml 的 mcp_servers)。
            # upstream 已把 import 副作用移除(#16856),必须显式调;失败不拖垮主智能体。
            mcp_toolsets = []
            try:
                if str(project_root / "shared" / "framework" / "hermes-agent") not in sys.path:
                    sys.path.insert(0, str(project_root / "shared" / "framework" / "hermes-agent"))
                from tools.mcp_tool import discover_mcp_tools, _load_mcp_config
                _mcp_cfg = _load_mcp_config()
                mcp_toolsets = [f"mcp-{n}" for n, c in _mcp_cfg.items()
                                if str(c.get("enabled", True)).lower() != "false"]
                if mcp_toolsets:
                    _names = discover_mcp_tools()
                    logger.info(f"MCP 已连接: {mcp_toolsets}, 工具 {_names}")
            except Exception as _e:
                logger.warning(f"MCP 发现失败(跳过): {_e}")

            # 注册orchestrator工具到AIAgent
            try:
                # 修复导入路径：使用orchestrator-core而非orchestrator_core
                import importlib.util
                tool_reg_path = self.project_root / "skills" / "orchestrator-core" / "scripts" / "tool_registration.py"
                spec = importlib.util.spec_from_file_location("tool_registration", tool_reg_path)
                tool_reg_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(tool_reg_module)

                tool_reg_module.register_orchestrator_tools(self.master_agent)
                # 保留 tool_registration 模块引用，供 /query/stream 设置进度队列
                self._tool_reg = tool_reg_module
                logger.info("✅ Orchestrator工具注册成功")
            except Exception as e:
                logger.warning(f"⚠️ Orchestrator工具注册失败: {e}")
                import traceback
                traceback.print_exc()

            # MCP 工具进 agent.tools(第 1 层,conversation_loop 只认 agent.tools)。
            # 放 tool_registration 精简之后执行,避免被 _KEEP_NAMES 过滤掉。
            # registry API(vendored tools/registry.py 实测):get_tool_names_for_toolset(name)
            # + get_definitions(tool_names: Set[str])——按工具集名取名再取 schema。
            try:
                from tools.registry import registry as _reg
                _mcp_names: set = set()
                for _ts in mcp_toolsets:
                    _mcp_names.update(_reg.get_tool_names_for_toolset(_ts))
                _mcp_defs = _reg.get_definitions(_mcp_names) if _mcp_names else []
                if _mcp_defs:
                    self.master_agent.tools.extend(_mcp_defs)
                    logger.info(f"MCP 工具已挂载: {[t['function']['name'] for t in _mcp_defs]}")
            except Exception as _e:
                logger.warning(f"MCP 工具挂载失败: {_e}")

            # 风格策略注入句柄:每次 run_conversation 前调用(策略即时生效,见 _apply_style_strategy)
            self._apply_style = lambda: _apply_style_strategy(self.master_agent)

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

        # 只保留纯问候/感谢的整句匹配；去掉"状态|运行|帮助|功能"等会误命中
        # 真实查询（如"出水运行数据""指标功能"）的正则，避免抢答。
        quick_responses = {
            r'^(你好|您好|hi|hello|介绍一下你自己|你是谁|你是)!*$': "我是废水监测系统的智能助手。我可以帮您查询监测数据、检测异常、判定违规和生成预警。请告诉我您的具体需求。",
            r'^(谢谢|感谢|多谢)!*$': "不客气！如果您还有其他问题，请随时提问。"
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

    def _fresh_session_dir(self, session_id: str = None) -> str:
        """为本次查询分配一个独立的 session 目录。

        一次查询内的 4 个子智能体(data→anomaly→rule→disposition)共享这一个目录做
        链式传递；但【跨查询不复用】。之前 SESSION_DIR 写进进程级 os.environ、被
        所有查询共享，导致上一次查询的 *_result.json 残留污染本次（典型：问"一周"
        却读到上次"24小时"的结果）。这里在每次查询开头强制换新目录。
        这是 scratch 中转通道的隔离，不影响 ①对话历史/④Hermes session DB/⑤MEMORY.md
        这些正当记忆（它们仍按 session_id / 框架机制各自保留）。

        【续传(2026-07-29)】同一会话(conversation, 同一 session_id)的多轮追问，把
        上一轮的子智能体结果文件拷进本轮新目录——让"那这些有没有异常"这类追问能直接
        链式消费上一轮取的数据，像正常多轮对话一样有数据上下文，不必重新取数。
        不同会话(session_id 不同)不拷→天然隔离；换时间段的追问由主智能体重新调①覆盖。
        """
        import shutil
        sessions_root = project_root / "sessions"
        sessions_root.mkdir(parents=True, exist_ok=True)
        sd = sessions_root / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        sd.mkdir(parents=True, exist_ok=True)
        # 续传：同一会话才把上一轮结果文件拷过来（不同会话天然隔离）
        if session_id and session_id in self._session_dirs:
            prev = Path(self._session_dirs[session_id])
            if prev.exists() and prev.resolve() != sd.resolve():
                carried = []
                for fname in ("data_result.json", "anomaly_result.json",
                              "rule_reasoning_result.json", "disposition_result.json"):
                    src = prev / fname
                    if src.exists():
                        shutil.copy2(src, sd / fname)
                        carried.append(fname)
                if carried:
                    logger.info(f"[session] 续传会话 {session_id} 上一轮结果 {carried} → {sd.name}")
        self._session_dirs[session_id] = str(sd)
        os.environ['SESSION_DIR'] = str(sd)
        logger.info(f"[session] 新查询 session 目录: {sd}")
        return str(sd)

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

            # 2. 缓存已禁用：编排链路非确定性 + 数据会变，缓存会把上次(可能错的)结果固化
            #    （典型：重复问"一周"一直返回上次因 session 复用拿到的"24小时"）。
            # cached_result = self._check_cache(query)
            # if cached_result:
            #     cached_result['cached'] = True
            #     cached_result['timestamp'] = datetime.now().isoformat()
            #     return cached_result

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

            # 调用主智能体（加锁串行化，避免并发查询串台；排队超时直接返回"忙"）
            if not self._agent_lock.acquire(timeout=self._agent_lock_timeout):
                return {"success": False, "error": "服务繁忙：主智能体正被占用（排队超时），请稍后重试"}
            # 挂进度队列收集 call_subagent 调用（让阻塞 /query 也能回传子智能体 trace，供审计）
            import queue as _q
            _trace_q = _q.Queue()
            _tool_reg = getattr(self, "_tool_reg", None)
            if _tool_reg is not None:
                _tool_reg._current_progress_queue = _trace_q
            try:
                self._fresh_session_dir(session_id)  # 同一会话续传上轮结果文件，跨会话隔离
                _apply_style_strategy(self.master_agent)   # /query 路径:风格策略即时生效
                result = self.master_agent.run_conversation(
                    user_message=query,
                    conversation_history=conversation_history,
                    task_id=session_id
                )
            finally:
                if _tool_reg is not None:
                    _tool_reg._current_progress_queue = None
                self._agent_lock.release()

            # 更新会话历史（保存完整的对话）
            if "messages" in result:
                self.session_histories[session_id] = result["messages"]

            # 提取响应内容
            if isinstance(result, dict):
                content = result.get("final_response", str(result))
            else:
                content = str(result) if result else ""

            # 从进度队列收集子智能体调用（与流式 query_stream 的 progress 解析一致）
            _decision_order = []
            _sub_starts = {}
            _subagent_calls = []
            while not _trace_q.empty():
                evt = _trace_q.get_nowait()
                if not isinstance(evt, dict) or evt.get("type") != "progress":
                    continue
                sub = evt.get("subagent")
                stage = evt.get("stage")
                if sub and stage == "start":
                    _sub_starts[sub] = time.time()
                    if sub not in _decision_order:
                        _decision_order.append(sub)
                elif sub and stage == "done":
                    _s = _sub_starts.pop(sub, None)
                    _subagent_calls.append({
                        "subagent_name": sub,
                        "status": "success",
                        "summary": evt.get("summary", ""),
                        "execution_time_ms": int((time.time() - _s) * 1000) if _s else 0,
                        "skill_calls": evt.get("skill_calls") or [],
                        "evidence": evt.get("evidence") or {},
                        "chartData": evt.get("chartData"),
                    })

            elapsed = time.time() - start_time
            logger.info(f"查询完成: session={session_id}, 耗时={elapsed:.2f}s, 消息数={len(result.get('messages', []))}, 子智能体={len(_subagent_calls)}")

            # 构建响应（含 trace，供后端记录到审计）
            response = {
                "success": True,
                "content": content,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "message_count": len(result.get("messages", [])),
                "cached": False,
                "quick_response": False,
                "trace": {
                    "decision_path": _decision_order,
                    "subagent_calls": _subagent_calls,
                }
            }

            # 缓存已禁用（见上方说明），不再 _update_cache
            # self._update_cache(query, response)

            return response

        except Exception as e:
            logger.error(f"查询失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }


def _apply_style_strategy(agent):
    """回答风格策略 → ephemeral_system_prompt(运行时每次 API 调用拼接,立即生效,
    不污染 _cached_system_prompt 缓存)。空策略不设置。"""
    try:
        parts = []
        if _gst("language_constraint") == "zh":
            parts.append("回答必须使用中文。")
        if _gst("conclusion_first", True):
            parts.append("回答结论先行；数据用表格呈现；细节后置。")
        if _gst("confidence_labeling", True):
            parts.append("判定类结论必须标注置信级别（疑似/确认）。")
        stop = _gst("orchestration_stop_level", "auto")
        if stop and stop != "auto":
            _cap = {"data": "①数据感知", "anomaly": "②异常检测", "violation": "③规则推理"}[stop]
            parts.append(f"编排上限：本次最多推进到{_cap}即停，不自动调用更深层子智能体。")
        if parts:
            agent.ephemeral_system_prompt = "【执行策略】\n" + "\n".join(f"- {p}" for p in parts)
        else:
            agent.ephemeral_system_prompt = None
    except Exception as e:
        logger.warning(f"风格策略注入失败(忽略): {e}")


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
def query(request: QueryRequest):
    """执行查询

    说明：用 sync def（而非 async def）。process_query 内部 run_conversation 是阻塞的
    （完整 pipeline ~30-60s）。若用 async def 直接调，会冻住整个事件循环，导致 /health、
    /status 及其它查询全部卡住。sync def 由 FastAPI 自动丢进线程池执行，事件循环保持畅通。
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
            success=True,
            trace=result.get("trace")
        )
    else:
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "查询失败")
        )


@app.post("/query/stream")
def query_stream(request: QueryRequest):
    """流式查询（SSE）：实时返回 子智能体调用进度 + 最终回答逐字。

    事件（data: {json}\\n\\n）：
      {"type":"progress","subagent":"...","stage":"start|done","summary":"..."}
      {"type":"delta","text":"..."}   最终回答逐字
      {"type":"done","content":"...","session_id":"..."}
      {"type":"error","message":"..."}
    保留 /query（阻塞）向后兼容；进度经 tool_registration 模块级 _current_progress_queue
    （靠 _agent_lock 串行化保证安全），逐字经 run_conversation 的 stream_callback。
    """
    import queue as _q
    import json as _json
    q = _q.Queue()
    session_id = request.session_id or f"session_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    tool_reg = getattr(agent_service, "_tool_reg", None)

    def worker():
        # 挂队列到 tool_registration 模块全局，让 call_subagent handler（在 executor 线程）吐进度
        if tool_reg is not None:
            tool_reg._current_progress_queue = q
        if not agent_service._agent_lock.acquire(timeout=agent_service._agent_lock_timeout):
            q.put({"type": "error", "message": "服务繁忙：主智能体正被占用（排队超时），请稍后重试"})
            return
        try:
            agent_service._fresh_session_dir(session_id)  # 同一会话续传上轮结果文件，跨会话隔离
            _apply_style_strategy(agent_service.master_agent)   # /query/stream 路径:风格策略即时生效
            history = agent_service.session_histories.get(session_id)
            result = agent_service.master_agent.run_conversation(
                user_message=request.query,
                conversation_history=history,
                task_id=session_id,
                stream_callback=lambda text: q.put({"type": "delta", "text": text}),
            )
            if isinstance(result, dict) and "messages" in result:
                agent_service.session_histories[session_id] = result["messages"]
            content = result.get("final_response", str(result)) if isinstance(result, dict) else (str(result) if result else "")
            q.put({"type": "done", "content": content, "session_id": session_id})
        except Exception as e:
            logger.error(f"流式查询失败: {e}")
            q.put({"type": "error", "message": str(e)})
        finally:
            if tool_reg is not None:
                tool_reg._current_progress_queue = None
            agent_service._agent_lock.release()

    threading.Thread(target=worker, daemon=True).start()

    def gen():
        while True:
            try:
                evt = q.get(timeout=1.0)
            except Exception:
                yield ": keepalive\n\n"  # 队列空（还在跑），SSE 注释行防连接 idle
                continue
            # action 事件透传：progress 事件带 action 字段时，拆成独立的 action 事件发给前端
            if evt.get("type") == "progress" and evt.get("action"):
                action_evt = {"type": "action", "actionData": evt["action"]}
                yield f"data: {_json.dumps(action_evt, ensure_ascii=False)}\n\n"
            yield f"data: {_json.dumps(evt, ensure_ascii=False)}\n\n"
            if evt.get("type") in ("done", "error"):
                break

    return StreamingResponse(gen(), media_type="text/event-stream")


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
