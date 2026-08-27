# backend/api/v1/agents/config/routes.py
"""智能体配置中心 REST API（spec §3.1）。

分组：实体/身份文件(git快照) / 厂区配置(yaml) / 运行参数(SQLite) / LLM测试 / 服务管理。

⚠️ 路由函数 async/sync 的取舍（Task 3 审查结论，与 /query 踩过的坑同款）：
内部是阻塞 subprocess（git 最坏 90s）/阻塞 HTTP（llm_test 10s）/60s 轮询的，
一律用 **sync def**——FastAPI 自动丢线程池，事件循环不卡；纯内存/单查 DB 的
保持 async def。
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(tags=["智能体配置"])


# ── 实体与身份文件 ─────────────────────────────────────────────
@router.get("/agents/config/entities")
async def list_entities():
    from backend.services.identity_files import list_entities
    return {"success": True, "data": list_entities()}


class FileBody(BaseModel):
    entity: str
    file: str
    content: str
    message: Optional[str] = ""


@router.get("/agents/config/files")
async def read_file(entity: str, file: str):
    from backend.services.identity_files import read_file
    try:
        return {"success": True, "data": read_file(entity, file)}
    except PermissionError as e:
        raise HTTPException(400, str(e))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@router.put("/agents/config/files")
def save_file(body: FileBody):
    """sync def：内部是阻塞 git subprocess（最坏 90s），async 会卡死事件循环。"""
    from backend.services.identity_files import save_file as _save_file
    try:
        r = _save_file(body.entity, body.file, body.content, body.message or "")
        return {"success": True, "data": r}
    except PermissionError as e:
        raise HTTPException(400, str(e))


@router.get("/agents/config/files/history")
def file_history(entity: str, file: str, limit: int = 20):
    """sync def：git log 阻塞 subprocess（最坏 30s 超时），async 会卡事件循环。"""
    from backend.services.identity_files import list_history
    try:
        return {"success": True, "data": list_history(entity, file, limit)}
    except PermissionError as e:
        raise HTTPException(400, str(e))


class RevertBody(BaseModel):
    entity: str
    file: str
    commit: str


@router.post("/agents/config/files/revert")
def revert_file(body: RevertBody):
    """sync def：git checkout 阻塞 subprocess。"""
    from backend.services.identity_files import revert_file as _revert_file
    try:
        return {"success": True, "data": _revert_file(body.entity, body.file, body.commit)}
    except (PermissionError, ValueError) as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))


# ── 厂区配置 ───────────────────────────────────────────────────
@router.get("/agents/config/plants")
async def get_plant_config():
    from backend.services.plant_config_service import load_plant_config
    return {"success": True, "data": load_plant_config()}


class PlantConfigBody(BaseModel):
    hierarchy: Optional[dict] = None
    report_name_map: Optional[dict] = None
    plant_configs: Optional[dict] = None
    plant_aliases: Optional[dict] = None


@router.post("/agents/config/plants/validate")
async def validate_plants(body: PlantConfigBody):
    from backend.services.plant_config_service import validate_config
    return {"success": True, "errors": validate_config(body.model_dump())}


@router.put("/agents/config/plants")
def save_plants(body: PlantConfigBody):
    """sync def：文件写盘 + git 快照 subprocess。"""
    from backend.services.plant_config_service import validate_config, save_config
    errs = validate_config(body.model_dump())
    if errs:
        raise HTTPException(400, detail={"message": "校验失败", "errors": errs})
    return {"success": True, "data": save_config(body.model_dump())}


# ── 运行参数 ───────────────────────────────────────────────────
@router.get("/agents/config/params")
async def get_params():
    from backend.services.agent_params import PARAM_REGISTRY, mask_secret, get_param
    out = []
    for key, spec in PARAM_REGISTRY.items():
        v = get_param(key, env_key=spec.get("env_key"), default=spec.get("default"))
        out.append({"key": key, "value": mask_secret(v) if spec["type"] == "secret" else v,
                    "default": spec.get("default"), "type": spec["type"],
                    "effect": spec["effect"], "reader": spec["reader"], "desc": spec.get("desc", "")})
    return {"success": True, "data": out}


class ParamsBody(BaseModel):
    params: dict  # {key: value}; secret 留空/缺省=不改


@router.put("/agents/config/params")
async def put_params(body: ParamsBody):
    from backend.services.agent_params import PARAM_REGISTRY, set_param
    invalid = [k for k in body.params if k not in PARAM_REGISTRY]
    if invalid:
        raise HTTPException(400, f"未知参数: {invalid}")
    errors = []
    for k, v in body.params.items():
        if PARAM_REGISTRY[k]["type"] == "int":
            try:
                int(v)
            except (TypeError, ValueError):
                errors.append(f"{k} 必须是整数")
        if v is None and PARAM_REGISTRY[k]["type"] != "secret":
            errors.append(f"{k} 不接受 null")
    if errors:
        raise HTTPException(400, detail={"message": "参数校验失败", "errors": errors})
    applied = []
    for k, v in body.params.items():
        if PARAM_REGISTRY[k]["type"] == "secret" and (v is None or v == ""):
            continue  # 密钥空=不改（防清库）
        set_param(k, str(v))
        applied.append(k)
    restart_needed = any(PARAM_REGISTRY[k]["effect"] == "restart" for k in applied)
    return {"success": True, "restart_needed": restart_needed}


# ── LLM 测试连接 ────────────────────────────────────────────────
class LLMTestBody(BaseModel):
    base_url: Optional[str] = None   # 空=用当前生效配置
    model: Optional[str] = None
    api_key: Optional[str] = None


@router.post("/agents/config/llm/test")
def llm_test(body: LLMTestBody):
    """sync def：阻塞 HTTP 调 LLM（timeout 10s）。"""
    import time
    import httpx
    from backend.services.agent_params import get_param
    base_url = body.base_url or get_param("llm_base_url", env_key="LLM_BASE_URL", default="")
    model = body.model or get_param("llm_model", env_key="LLM_MODEL", default="")
    api_key = body.api_key or get_param("llm_api_key", env_key="LLM_API_KEY", default="")
    if not base_url or not model:
        return {"ok": False, "error": "base_url/model 为空"}
    t0 = time.time()
    try:
        r = httpx.post(f"{base_url.rstrip('/')}/chat/completions",
                       headers={"Authorization": f"Bearer {api_key}"},
                       json={"model": model, "messages": [{"role": "user", "content": "hi"}],
                             "max_tokens": 1},
                       timeout=10.0)
        ok = r.status_code == 200
        return {"ok": ok, "latency_ms": int((time.time() - t0) * 1000),
                "error": None if ok else f"HTTP {r.status_code}: {r.text[:150]}"}
    except Exception as e:
        return {"ok": False, "latency_ms": int((time.time() - t0) * 1000), "error": str(e)[:150]}


# ── 服务管理 ───────────────────────────────────────────────────
@router.get("/agents/config/service/status")
def service_status():
    """sync def：psutil/netstat 找 PID + httpx health 探测（3s）都是阻塞调用。"""
    from backend.services.agent_service_control import get_status
    return {"success": True, "data": get_status()}


class RestartBody(BaseModel):
    confirm: bool


@router.post("/agents/config/service/restart")
def service_restart(body: RestartBody):
    """sync def：内部 kill + 60s health 轮询，async 会长时间卡死事件循环。"""
    from backend.services.agent_service_control import restart_agent
    return restart_agent(body.confirm)
