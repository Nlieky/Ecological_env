"""Transport proxy to the existing Hermes main-agent service."""
import httpx
import hashlib
import logging
from fastapi import HTTPException
from backend.core.config import settings
from shared.assistant.protocol import SCHEMAS, validate_actions, parse_model_answer
from shared.assistant.protocol import ProtocolError, SAFE_ERROR_DETAILS

logger = logging.getLogger(__name__)


async def respond(req):
    try:
        async with httpx.AsyncClient(timeout=65, trust_env=False) as client:
            response = await client.post(settings.AGENT_SERVICE_URL.rstrip('/') + '/system-assistant/respond', json=req.model_dump())
        if response.status_code != 200:
            status = response.status_code if response.status_code in {409, 502, 503, 504} else 503
            detail = {409: '系统助手繁忙，请稍后重试。', 502: '系统助手返回无效，未执行任何操作。',
                      503: '主智能体服务暂不可用，未执行任何操作。', 504: '系统助手响应超时，未执行任何操作。'}[status]
            if status == 502:
                try:
                    candidate = response.json().get('detail')
                    if isinstance(candidate, str) and candidate in SAFE_ERROR_DETAILS.values():
                        detail = candidate
                except (ValueError, TypeError, AttributeError):
                    pass
            raise HTTPException(status, detail)
        from shared.assistant.master_turn import validate_response
        return validate_response(response.json(), req.session_id, req.context.model_dump() if req.context else {})
    except HTTPException:
        raise
    except (httpx.TimeoutException, TimeoutError):
        raise HTTPException(504, "系统助手响应超时，未执行任何操作。") from None
    except httpx.HTTPError:
        raise HTTPException(503, "主智能体服务暂不可用，未执行任何操作。") from None
    except ProtocolError as exc:
        logger.warning('system_interaction_proxy_protocol task=%s capability=%s path=%s code=%s', hashlib.sha256(req.session_id.encode()).hexdigest(), exc.capability, exc.path, exc.code)
        raise HTTPException(502, SAFE_ERROR_DETAILS.get(exc.code, SAFE_ERROR_DETAILS['invalid_response'])) from None
    except (ValueError, TypeError, KeyError):
        raise HTTPException(502, "系统助手返回无效，未执行任何操作。") from None
