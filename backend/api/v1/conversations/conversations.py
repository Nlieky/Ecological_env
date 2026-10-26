"""对话历史API"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from sqlalchemy import text

from backend.services.conversation_service import ConversationService
from backend.database.session import SessionLocal
from backend.models.api import (
    StandardResponse,
    ConversationListResponse,
    ConversationCreateRequest
)

router = APIRouter(tags=["对话历史"])

conversation_service = ConversationService()


@router.get("/conversations", response_model=StandardResponse)
async def list_conversations(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态过滤"),
    search: Optional[str] = Query(None, max_length=200, description="标题或会话ID搜索")
):
    """获取对话历史列表

    返回分页的对话历史列表，支持按状态过滤。
    """
    try:
        result = conversation_service.list_conversations(
            page=page,
            page_size=page_size,
            status=status,
            search=search
        )
        return StandardResponse(
            success=True,
            data=result,
            metadata={
                "total_count": result["total_count"],
                "page": page,
                "page_size": page_size
            }
        )
    except Exception as e:
        return StandardResponse(
            success=False,
            error={
                "code": "CONVERSATION_LIST_ERROR",
                "message": str(e)
            }
        )


@router.post("/conversations", response_model=StandardResponse)
async def create_conversation(request: ConversationCreateRequest):
    """创建新对话

    创建一个新的对话记录，用于存储对话历史。
    """
    try:
        result = conversation_service.create_conversation(request)
        return StandardResponse(
            success=True,
            data=result,
            metadata={"timestamp": result.get("started_at")}
        )
    except Exception as e:
        return StandardResponse(
            success=False,
            error={
                "code": "CONVERSATION_CREATE_ERROR",
                "message": str(e)
            }
        )


@router.get("/conversations/{conversation_id}", response_model=StandardResponse)
async def get_conversation(conversation_id: str):
    """获取对话详情

    获取指定对话的详细信息，包括所有消息历史。
    """
    try:
        result = conversation_service.get_conversation(conversation_id)

        if not result:
            return StandardResponse(
                success=False,
                error={
                    "code": "CONVERSATION_NOT_FOUND",
                    "message": f"对话 {conversation_id} 不存在"
                }
            )

        return StandardResponse(
            success=True,
            data=result
        )
    except Exception as e:
        return StandardResponse(
            success=False,
            error={
                "code": "CONVERSATION_GET_ERROR",
                "message": str(e)
            }
        )


@router.delete("/conversations/{conversation_id}", response_model=StandardResponse)
async def delete_conversation(conversation_id: str):
    """删除指定对话（含其所有消息）"""
    try:
        db = SessionLocal()
        deleted_msgs = db.execute(
            text("DELETE FROM conversation_messages WHERE conversation_id = :id"),
            {"id": conversation_id}
        )
        deleted_conv = db.execute(
            text("DELETE FROM conversations WHERE id = :id"),
            {"id": conversation_id}
        )
        db.commit()
        db.close()
        return StandardResponse(success=True, data={"deleted": True, "conversation_id": conversation_id})
    except Exception as e:
        return StandardResponse(success=False, error={"code": "CONVERSATION_DELETE_ERROR", "message": str(e)})


@router.delete("/conversations", response_model=StandardResponse)
async def clear_all_conversations():
    """清除所有对话历史"""
    try:
        db = SessionLocal()
        db.execute(text("DELETE FROM conversation_messages"))
        db.execute(text("DELETE FROM conversations"))
        db.commit()
        db.close()
        return StandardResponse(success=True, data={"cleared": True})
    except Exception as e:
        return StandardResponse(success=False, error={"code": "CONVERSATION_CLEAR_ERROR", "message": str(e)})
