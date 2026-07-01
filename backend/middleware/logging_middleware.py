"""
API 调用日志中间件
自动记录所有 API 请求
"""
import time
import json
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Callable
from backend.utils.loggers import log_api_call


class LoggingMiddleware(BaseHTTPMiddleware):
    """API 调用日志中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # 读取请求体（对于 POST/PUT）
        request_params = {}
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    request_params = json.loads(body.decode())
            except Exception:
                request_params = {"raw": "unable to parse"}

        # 处理请求
        response = await call_next(request)

        # 计算耗时
        latency_ms = (time.time() - start_time) * 1000

        # 记录日志
        try:
            log_api_call(
                method=request.method,
                path=request.url.path,
                user_id=request.headers.get("user-id", "anonymous"),
                request_params=request_params,
                response_status=response.status_code,
                latency_ms=latency_ms,
                error_message=None if response.status_code < 400 else "request failed"
            )
        except Exception as e:
            # 日志记录失败不影响主流程
            print(f"Logging failed: {e}")

        return response
