# backend/api/v1/agents/config/routes.py
"""智能体配置中心 REST API（spec §3.1）。

分组：实体/身份文件(git快照) / 厂区配置(yaml) / 运行参数(SQLite) / LLM测试 / 服务管理。
V2 追加：执行策略(+参数并入) / 技能管理(git快照) / MCP 接入 / LLM供应商。

⚠️ 路由函数 async/sync 的取舍（Task 3 审查结论，与 /query 踩过的坑同款）：
内部是阻塞 subprocess（git 最坏 90s）/阻塞 HTTP（llm_test 10s）/60s 轮询的，
一律用 **sync def**——FastAPI 自动丢线程池，事件循环不卡；纯内存/单查 DB 的
保持 async def。技能的写操作（保存/新建/启停/删除/安装）都带 git 快照 subprocess，
同样 sync def。
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.services.agent_params import PARAM_REGISTRY, get_param, mask_secret
from backend.services.agent_strategy import STRATEGY_REGISTRY

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


# ══════════ V2: 执行策略（参数并入展示，存储仍分域） ══════════
@router.get("/agents/config/strategy")
async def get_strategy_all():
    from backend.services.agent_strategy import list_grouped
    # 运行参数并入策略页展示（存储仍走 agent_params 表,接口不变）
    params = []
    for key, spec in PARAM_REGISTRY.items():
        v = get_param(key, env_key=spec.get("env_key"), default=spec.get("default"))
        params.append({"key": key,
                       "value": mask_secret(v) if spec["type"] == "secret" else v,
                       "default": spec.get("default"), "type": spec["type"],
                       "effect": spec["effect"], "desc": spec.get("desc", "")})
    return {"success": True, "data": {"groups": list_grouped(), "params": params}}


class StrategyBody(BaseModel):
    items: dict  # {key: value}; 空/None=不改（含 secret/ref）


@router.put("/agents/config/strategy")
async def put_strategy(body: StrategyBody):
    from backend.services.agent_strategy import set_strategy
    from backend.services.llm_providers import eligible_default_providers
    invalid = [k for k in body.items if k not in STRATEGY_REGISTRY]
    if invalid:
        raise HTTPException(400, f"未知策略: {invalid}")
    errors = []
    for k, v in body.items.items():
        spec = STRATEGY_REGISTRY[k]
        if v is None or v == "":
            continue  # 空=不改
        if spec["type"] == "enum" and v not in spec.get("choices", ()):
            errors.append(f"{k} 必须是 {spec['choices']} 之一")
        if spec["type"] == "int":
            try:
                int(v)
            except (TypeError, ValueError):
                errors.append(f"{k} 必须是整数")
        if k == "default_llm_provider" and v and v not in eligible_default_providers():
            errors.append(f"供应商 {v} 未通过测试连接,不能设为默认")
    if errors:
        raise HTTPException(400, detail={"message": "策略校验失败", "errors": errors})
    for k, v in body.items.items():
        if v is None or v == "":
            continue
        set_strategy(k, str(v))
    restart_needed = any(STRATEGY_REGISTRY[k]["effect"] == "restart" for k in body.items)
    return {"success": True, "restart_needed": restart_needed}


# ══════════ V2: 技能管理 ══════════
@router.get("/agents/config/skills")
async def get_skills(entity: str):
    from backend.services.skill_service import list_skills, list_templates
    try:
        return {"success": True, "data": {"skills": list_skills(entity),
                                          "templates": list_templates()}}
    except ValueError as e:
        raise HTTPException(400, str(e))


class SkillFileBody(BaseModel):
    entity: str
    name: str
    content: str
    message: Optional[str] = ""


@router.get("/agents/config/skills/file")
async def get_skill_file(entity: str, name: str):
    from backend.services.skill_service import read_skill_md
    try:
        return {"success": True, "data": read_skill_md(entity, name)}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@router.put("/agents/config/skills/file")
def put_skill_file(body: SkillFileBody):
    """sync def：git 快照 subprocess + _save_lock 串行段。"""
    from backend.services.skill_service import save_skill_md
    try:
        return {"success": True, "data": save_skill_md(body.entity, body.name, body.content, body.message or "")}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


class SkillCreateBody(BaseModel):
    entity: str
    name: str
    description: str
    skeleton: str = "empty"


@router.post("/agents/config/skills/create")
def create_skill(body: SkillCreateBody):
    """sync def：落盘 + git 快照 subprocess。"""
    from backend.services.skill_service import create_skill
    try:
        return {"success": True, "data": create_skill(body.entity, body.name, body.description, body.skeleton)}
    except ValueError as e:
        raise HTTPException(400, str(e))


class SkillActionBody(BaseModel):
    entity: str
    name: str


@router.post("/agents/config/skills/disable")
def disable_skill(body: SkillActionBody):
    """sync def：rename + git 快照 subprocess。"""
    from backend.services.skill_service import disable_skill
    try:
        disable_skill(body.entity, body.name)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except FileExistsError as e:
        raise HTTPException(409, str(e))


@router.post("/agents/config/skills/enable")
def enable_skill(body: SkillActionBody):
    """sync def：rename + git 快照 subprocess。"""
    from backend.services.skill_service import enable_skill
    try:
        enable_skill(body.entity, body.name)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except FileExistsError as e:
        raise HTTPException(409, str(e))


@router.delete("/agents/config/skills")
def delete_skill(entity: str, name: str):
    """sync def：rmtree + git 快照 subprocess。"""
    from backend.services.skill_service import delete_skill
    try:
        delete_skill(entity, name)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


class TemplateInstallBody(BaseModel):
    template: str
    entity: str


@router.post("/agents/config/skills/install")
def install_template(body: TemplateInstallBody):
    """sync def：copytree + git 快照 subprocess。"""
    from backend.services.skill_service import install_template
    try:
        return {"success": True, "data": install_template(body.template, body.entity)}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except FileExistsError as e:
        raise HTTPException(409, str(e))


# ══════════ V2: MCP 接入 ══════════
@router.get("/agents/config/mcp")
async def get_mcp():
    from backend.services.mcp_config_service import list_servers, list_presets
    return {"success": True, "data": {"servers": list_servers(masked=True), "presets": list_presets()}}


class McpServerBody(BaseModel):
    name: str
    config: dict


@router.put("/agents/config/mcp")
async def put_mcp(body: McpServerBody):
    from backend.services.mcp_config_service import upsert_server, validate_server
    errs = validate_server(body.config)
    if errs:
        raise HTTPException(400, detail={"message": "MCP 配置校验失败", "errors": errs})
    upsert_server(body.name, body.config)
    return {"success": True, "restart_needed": True}


@router.delete("/agents/config/mcp")
async def delete_mcp(name: str):
    from backend.services.mcp_config_service import delete_server
    delete_server(name)
    return {"success": True, "restart_needed": True}


class McpTestBody(BaseModel):
    config: dict


@router.post("/agents/config/mcp/test")
def mcp_test(body: McpTestBody):
    """sync def：一次性 stdio MCP 客户端 subprocess（connect_timeout 最坏 120s）。"""
    from backend.services.mcp_config_service import test_connect
    return test_connect(body.config)


class McpPresetBody(BaseModel):
    name: str


@router.post("/agents/config/mcp/preset")
async def install_mcp_preset(body: McpPresetBody):
    from backend.services.mcp_config_service import install_preset
    try:
        return {"success": True, "data": install_preset(body.name), "restart_needed": True}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


# ── MCP 市场（npm 事实上是 MCP server 分发中心）──
class MarketSearchBody(BaseModel):
    query: str


@router.post("/agents/config/mcp/market/search")
def mcp_market_search(body: MarketSearchBody):
    """sync def：httpx 外呼 npm mirror。"""
    from backend.services.mcp_config_service import market_search
    return {"success": True, "data": market_search(body.query)}


class MarketInstallBody(BaseModel):
    package: str


@router.post("/agents/config/mcp/market/install")
def mcp_market_install(body: MarketInstallBody):
    from backend.services.mcp_config_service import market_install
    try:
        return {"success": True, "data": market_install(body.package), "restart_needed": True}
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── 技能外部市场（hermes Skills Hub：skills.sh 2万+ / GitHub 官方源）──
class HubSearchBody(BaseModel):
    query: str


@router.post("/agents/config/skills/hub/search")
def skill_hub_search(body: HubSearchBody):
    """sync def：外呼 skills.sh / GitHub。"""
    from backend.services.skill_hub_service import search
    return {"success": True, "data": search(body.query)}


class HubInstallBody(BaseModel):
    identifier: str
    entity: str


@router.post("/agents/config/skills/hub/install")
def skill_hub_install(body: HubInstallBody):
    from backend.services.skill_hub_service import install
    try:
        return {"success": True, "data": install(body.identifier, body.entity)}
    except (FileNotFoundError, FileExistsError) as e:
        raise HTTPException(409 if isinstance(e, FileExistsError) else 404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


# ══════════ V2: LLM 供应商 ══════════
@router.get("/agents/config/providers")
async def get_providers():
    from backend.services.llm_providers import list_providers, seed_defaults, eligible_default_providers, get_default_provider_name
    seed_defaults()
    return {"success": True, "data": {"providers": list_providers(masked=True),
                                      "eligible": eligible_default_providers(),
                                      "current_default": get_default_provider_name()}}


class ProviderBody(BaseModel):
    name: str
    base_url: str
    api_key: Optional[str] = None   # None/空=不修改已有 key
    model: str
    enabled: bool = True


@router.put("/agents/config/providers")
async def put_provider(body: ProviderBody):
    from backend.services.llm_providers import upsert_provider, get_provider_row
    key = body.api_key
    if not key:
        existing = get_provider_row(body.name)
        key = existing["api_key"] if existing else ""
    upsert_provider(body.name, body.base_url, key, body.model, body.enabled)
    return {"success": True}


@router.delete("/agents/config/providers")
async def delete_provider(name: str):
    from backend.services.llm_providers import delete_provider
    delete_provider(name)
    return {"success": True}


class ProviderTestBody(BaseModel):
    name: str


@router.post("/agents/config/providers/test")
def provider_test(body: ProviderTestBody):
    """sync def：阻塞 HTTP 真请求（timeout 10s）。先判存在再 mark_tested
    （mark_tested 对不存在的 name 抛 KeyError，404 兜在前面）。"""
    import time
    import httpx
    from backend.services.llm_providers import get_provider_row, mark_tested
    row = get_provider_row(body.name)
    if row is None:
        raise HTTPException(404, f"供应商不存在: {body.name}")
    t0 = time.time()
    try:
        r = httpx.post(f"{row['base_url'].rstrip('/')}/chat/completions",
                       headers={"Authorization": f"Bearer {row['api_key']}"},
                       json={"model": row["model"], "messages": [{"role": "user", "content": "hi"}],
                             "max_tokens": 1},
                       timeout=10.0)
        ok = r.status_code == 200
        mark_tested(body.name, ok)
        return {"ok": ok, "latency_ms": int((time.time() - t0) * 1000),
                "error": None if ok else f"HTTP {r.status_code}: {r.text[:150]}"}
    except Exception as e:
        mark_tested(body.name, False)
        return {"ok": False, "latency_ms": int((time.time() - t0) * 1000), "error": str(e)[:150]}


class DefaultProviderBody(BaseModel):
    name: str


@router.post("/agents/config/providers/default")
async def set_default(body: DefaultProviderBody):
    from backend.services.llm_providers import set_default_provider
    try:
        set_default_provider(body.name)
        return {"success": True, "restart_needed": True}
    except ValueError as e:
        raise HTTPException(400, str(e))
