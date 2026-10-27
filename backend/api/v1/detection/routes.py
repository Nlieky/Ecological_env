"""轻量检测 API——前端直调 run_detector 脚本(不经 LLM)。

用途:LLM 动作指令返回的检测窗口与大屏当前观看窗口不一致时,前端用本端点
按正确窗口重测,保证标注落在用户眼前数据上。
"""
import json
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from backend.core.config import settings

router = APIRouter(tags=["轻量检测"])

_SCRIPT = Path(__file__).resolve().parents[4] / "skills" / "action-command-core" / "scripts" / "run_detector.py"


class DetectRequest(BaseModel):
    algorithm: str = "constant"          # constant / changepoint / iforest
    indicator: str = "pH"                # pH/COD/TN/NH3-N/TP/SS
    start: str = "now"
    end: str = "now"
    side: str = "effluent"
    plant: str = ""                      # 厂(监测点);空=全库
    source: str | None = Field(default=None, max_length=200)


@router.post("/detection/run")
async def run_detection(req: DetectRequest):
    """跑一次异常检测算子,返回脚本 JSON(actionData.annotations 给前端标注)。"""
    if req.algorithm not in ("constant", "changepoint", "iforest"):
        raise HTTPException(400, "algorithm 必须是 constant/changepoint/iforest")
    if req.source is not None and req.source != settings.INFLUXDB_BUCKET:
        raise HTTPException(400, "检测数据来源与当前业务数据源不一致，未运行检测")
    try:
        r = await run_in_threadpool(subprocess.run,
            [sys.executable, str(_SCRIPT),
             "--algorithm", req.algorithm, "--indicator", req.indicator,
             "--start", req.start, "--end", req.end, "--side", req.side,
             *(["--plant", req.plant] if req.plant else [])],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=90, cwd=str(_SCRIPT.parents[4]),
        )
        out = r.stdout.strip()
        data = json.loads(out) if out else {}
        if not isinstance(data, dict) or data.get("status") != "completed":
            return {"success": False, "error": (data or {}).get("error") or r.stderr[-300:]}
        data['execution_context'] = {key: getattr(req, key) for key in ('algorithm', 'indicator', 'plant', 'start', 'end', 'side')}
        data['execution_context']['source'] = settings.INFLUXDB_BUCKET
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(500, f"检测执行失败: {e}")
