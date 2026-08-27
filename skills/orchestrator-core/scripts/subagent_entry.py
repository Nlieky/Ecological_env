#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""子智能体共享入口（标准化接口，实现 interfaces/subagent_protocol.md）。

设计：子智能体是独立 LLM 智能体——LLM 读自己的技能说明(SKILL.md)、据任务选择并调用
对应脚本，脚本（调 shared 算子/知识）干真正的数据处理，结果写回公共会话区。

**共享入口**：本脚本只有一份，由 call_subagent 以 subprocess 启动；通过环境变量定位
"是哪个子智能体"：
  - HERMES_HOME = 该子智能体目录（身份 SOUL/AGENTS/MEMORY + skills/ 从这里读）
  - SUBAGENT_NAME = 子智能体名（兜底从目录名推）
  - SESSION_DIR = 公共会话区（task.json / *_result.json）
不再为每个子智能体复制一份 entry.py（旧设计 4 份重复，DRY 问题）。

防瞎逛：靠 HERMES_HOME 作用域(skill_view 只翻该子智能体 skill,边界清晰,不会满库乱翻)
+ 开 skills/terminal 工具 + 低迭代上限。2026-07-27 验证 4/4 子智能体(LLM 用 hermes 原生
skill_view 读 SKILL.md → terminal 跑脚本,2-3 次工具调用即完成,无一瞎逛)。
预加载妥协(_preload_skill_md)已移除——根因是当年没设 HERMES_HOME 作用域,不是模型问题。
"""
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# === 步骤 1: 子智能体目录由 call_subagent 通过 HERMES_HOME 传入 ===
AGENT_DIR = Path(os.environ.get("HERMES_HOME", ".")).resolve()
os.environ['HERMES_HOME'] = str(AGENT_DIR)
DEFAULT_SUBAGENT_NAME = AGENT_DIR.name.removesuffix("-agent")  # 目录名兜底，如 anomaly-detection-agent→anomaly-detection

# === 步骤 2: 导入 Hermes AIAgent（与主智能体同款路径） ===
project_root = AGENT_DIR.parent.parent  # subagents/<name> → ... → 项目根
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
try:
    from shared.framework.hermes_agent.run_agent import AIAgent
except ImportError as e:
    print(f"[ERROR] Failed to import Hermes AIAgent: {e}", file=sys.stderr)
    sys.exit(1)

# === 步骤 3: 配置日志 ===
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout)], force=True)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
logger = logging.getLogger(__name__)

# === 步骤 4: 结果文件名（与 call_subagent.py 一致） ===
RESULT_FILE_NAMES = {
    "anomaly-detection": "anomaly_result.json",
    "multi-dimensional-data-perception": "data_result.json",
    "rule-reasoning": "rule_reasoning_result.json",
    "disposition-execution": "disposition_result.json",
}


def load_task(session_dir: Optional[str]) -> Optional[Dict[str, Any]]:
    if not session_dir:
        return None
    task_file = Path(session_dir) / "task.json"
    if not task_file.exists():
        return None
    try:
        return json.loads(task_file.read_text(encoding='utf-8'))
    except Exception as e:
        logger.error(f"[LOAD] task 解析失败: {e}")
        return None


def write_result(session_dir: str, result: Dict[str, Any], filename: str) -> bool:
    try:
        result_file = Path(session_dir).resolve() / filename
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"[WRITE] 已写入结果: {result_file}")
        return True
    except Exception as e:
        logger.error(f"[WRITE] 写入结果失败: {e}")
        return False



def _read_script_result(session_dir, result_filename):
    """只读本子智能体自己的结果文件。

    缺失/无效时返回 None——**不再 glob 其他 *_result.json 顶替**。
    旧实现会 glob 全部 *_result.json 并返回第一个像样的，导致某子智能体没跑出
    自己结果时（典型：处置 LLM 没跑 run_disposition.py），静默把异常/数据结果
    当成它的结果返回，把"失败"伪装成"成功"。改为只认自己的文件，失败就让它失败。
    """
    if not session_dir:
        return None
    p = Path(session_dir).resolve() / result_filename
    if not p.exists():
        return None
    try:
        loaded = json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return None
    if not isinstance(loaded, dict) or loaded.get("status") == "failed":
        return None
    inner = loaded.get("result")
    if isinstance(inner, dict) or "data" in loaded or "statistics" in loaded:
        return loaded
    return None


def _extract_skill_calls(response) -> list:
    """从 run_conversation 的 messages 提取 skill 工具调用(skill_view/skills_list/skill_manage)。
    OpenAI 格式: assistant message.tool_calls=[{function:{name,arguments}}]。
    """
    if not isinstance(response, dict):
        return []
    skill_calls = []
    for msg in response.get("messages", []):
        if not isinstance(msg, dict) or msg.get("role") != "assistant":
            continue
        for tc in (msg.get("tool_calls") or []):
            fn = (tc.get("function") or {}).get("name")
            if fn not in ("skill_view", "skills_list", "skill_manage"):
                continue
            args_raw = (tc.get("function") or {}).get("arguments") or ""
            try:
                args = json.loads(args_raw) if isinstance(args_raw, str) else (args_raw or {})
            except Exception:
                args = {}
            skill_calls.append({"tool": fn, "skill": args.get("name", "")})
    return skill_calls


def run_subagent() -> Dict[str, Any]:
    session_dir = os.getenv('SESSION_DIR')
    subagent_name = os.getenv('SUBAGENT_NAME', DEFAULT_SUBAGENT_NAME)
    logger.info(f"[START] 子智能体={subagent_name} SESSION_DIR={session_dir} HERMES_HOME={AGENT_DIR}")

    task = load_task(session_dir)
    if not task:
        error_result = {"task_id": "unknown", "status": "failed",
                        "error": "Failed to load task", "timestamp": datetime.now().isoformat()}
        if session_dir:
            write_result(session_dir, error_result, RESULT_FILE_NAMES.get(subagent_name, "result.json"))
        return error_result
    task_id = task.get('task_id', 'unknown')

    # 【实验】不预加载 SKILL.md，让 LLM 用 hermes 原生 skills_list/skill_view 在
    # HERMES_HOME 作用域下读自己的技能(验证「作用域清晰」能否消除瞎逛)
    user_message = (
        f"任务：{task.get('task', '')}\n\n"
        f"你是 {subagent_name} 子智能体。执行步骤：\n"
        "1. 用 skills_list 查看你的可用技能，用 skill_view 读取相关技能的 SKILL.md\n"
        "2. 严格按 SKILL.md 的说明，用 terminal 运行其指定的脚本\n"
        "3. 脚本产出结果文件后即停止\n"
        "注意：技能已限定为你的作用域(只含与你相关的)，直接选用即可，不要反复翻阅。\n"
        "⚠️ 评判成功的唯一标准：你用 terminal 运行了脚本并产出结果文件。"
        "禁止只回复\"我已就绪\"/\"等待指令\"/\"我将执行\"之类的确认就结束——"
        "那会被判为任务失败。读完 SKILL.md 后必须立刻调用 terminal 运行脚本。\n\n"
        "环境已确认（不要再用 echo/ls 验证）：\n"
        f"- HERMES_HOME = {AGENT_DIR}（你的技能在 $HERMES_HOME/skills/ 下）\n"
        f"- SESSION_DIR = {session_dir}（上游结果文件在这里，脚本自动读）\n"
        "直接用 SKILL.md 里给的命令运行脚本。"
    )

    try:
        # LLM 配置：参数中心 DB 优先 → env（default 层保留原 OPENAI_* 兜底，与原 or 链一致）
        try:
            from backend.services.agent_params import get_param as _gp
        except Exception:
            _gp = lambda key, env_key=None, default=None: os.environ.get(env_key, default) if env_key else default
        llm_base_url = _gp("llm_base_url", env_key="LLM_BASE_URL",
                           default=os.environ.get('OPENAI_BASE_URL'))
        llm_api_key = _gp("llm_api_key", env_key="LLM_API_KEY",
                          default=os.environ.get('OPENAI_API_KEY'))
        llm_model = _gp("llm_model", env_key="LLM_MODEL", default="ctgu-vlm")
        if not llm_api_key:
            raise ValueError("LLM_API_KEY 或 OPENAI_API_KEY 环境变量未设置")

        logger.info(f"[LLM] 开始处理任务: {task_id}")
        _smi = _gp("subagent_max_iterations", default=8)
        agent = AIAgent(
            base_url=llm_base_url, api_key=llm_api_key, model=llm_model,
            load_soul_identity=True, skip_context_files=False, skip_memory=False,
            enabled_toolsets=["skills", "terminal"], session_id=task_id, max_iterations=_smi,
        )
        response = agent.run_conversation(user_message)
        logger.info(f"[LLM] 任务完成")

        result_filename = RESULT_FILE_NAMES.get(subagent_name, "result.json")
        result = _read_script_result(session_dir, result_filename)

        # 自愈：ctgu-vlm 偶尔读完 skill_view 后直接回"我已就绪"就结束（finish_reason=stop），
        # 压根没调 terminal 跑脚本 → 没产出结果文件。检测到此情况时，复用同一会话追加一条
        # 硬指令再跑一轮，逼 LLM 真正用 terminal 执行脚本。比让主智能体重试更省（不必重建
        # agent、不必重新 skill_view；技能说明已在 history 里）。2026-07-28 trace 实证：
        # 首轮只 skill_view 后"就绪"finish，主智能体简化重试才成功——把那次重试下沉到这里。
        if result is None:
            # LLM 没产出结果文件（通常"读了 skill 没执行脚本"）。不自愈（自愈给命令是 hack：
            # hermes 第二轮 run_conversation history=0 不继承，且时间窗不准）。直接 failed，
            # 让主智能体决定重试或如实告知用户。
            final_text = response.get('final_response', '') if isinstance(response, dict) else str(response)
            logger.warning(f"[WARN] 未产出 {result_filename}（LLM 可能读了 skill 没执行脚本），标记 failed")
            result = {"task_id": task_id, "status": "failed",
                      "error": f"subagent did not produce {result_filename}; "
                               f"LLM likely did not run its canonical script",
                      "final_response": final_text,
                      "timestamp": datetime.now().isoformat()}
        else:
            logger.info(f"[LLM] 回传脚本结构化结果")

    except Exception as e:
        logger.error(f"[LLM] 执行失败: {e}", exc_info=True)
        result = {"task_id": task_id, "status": "failed", "error": str(e),
                  "timestamp": datetime.now().isoformat()}

    if session_dir:
        result_filename = RESULT_FILE_NAMES.get(subagent_name, "result.json")
        if not isinstance(result, dict):
            result = {"task_id": task_id, "status": "completed", "result": result,
                      "timestamp": datetime.now().isoformat()}
        result["task_id"] = task_id
        result["skill_calls"] = _extract_skill_calls(locals().get("response"))
        write_result(session_dir, result, result_filename)
    return result


if __name__ == "__main__":
    _r = run_subagent()
    # 结果已写入文件后，立即强制退出——跳过 Hermes bg-review 后台线程（子智能体不需要
    # 技能审查，那是为持久化 agent 设计的）。bg-review 每次浪费 ~20-30s LLM 调用 +
    # 等待线程退出。os._exit 不等后台线程，直接终止进程。
    _exit_code = 0 if (isinstance(_r, dict) and _r.get("status") != "failed") else 1
    import os as _os
    _os._exit(_exit_code)
