"""对话服务层

负责对话历史的管理和持久化。
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from backend.database.session import SessionLocal
from backend.models.conversation import Conversation, ConversationMessage, ConversationStatus, MessageRole
from backend.models.api import ConversationCreateRequest


class ConversationService:
    """对话服务类"""
    
    def __init__(self):
        self.db = SessionLocal
    
    def get_db_session(self) -> Session:
        """获取数据库会话"""
        return self.db()
    
    def create_conversation(self, request: ConversationCreateRequest) -> Dict[str, Any]:
        """创建新对话
        
        Args:
            request: 创建对话请求
            
        Returns:
            包含对话ID的字典
        """
        db = self.get_db_session()
        try:
            conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
            
            conversation = Conversation(
                id=conversation_id,
                user_id=request.user_id,
                title=request.title or "新对话",
                status=ConversationStatus.ACTIVE,
                started_at=datetime.now()
            )
            
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
            
            return {
                "id": conversation.id,
                "user_id": conversation.user_id,
                "title": conversation.title,
                "status": conversation.status.value,
                "started_at": conversation.started_at.isoformat() if conversation.started_at else None
            }
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """获取对话详情（含消息历史）

        Args:
            conversation_id: 对话ID

        Returns:
            对话详情字典（含 messages 列表），不存在返回None
        """
        db = self.get_db_session()
        try:
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()

            if not conversation:
                return None

            # 拉取该对话下的全部消息，按时间正序排列
            messages = (
                db.query(ConversationMessage)
                .filter(ConversationMessage.conversation_id == conversation_id)
                .order_by(ConversationMessage.timestamp.asc())
                .all()
            )

            return {
                "id": conversation.id,
                "user_id": conversation.user_id,
                "title": conversation.title,
                "status": conversation.status.value,
                "started_at": conversation.started_at.isoformat() if conversation.started_at else None,
                "ended_at": conversation.ended_at.isoformat() if conversation.ended_at else None,
                "message_count": conversation.message_count,
                "messages": [
                    {
                        "role": msg.role.value if hasattr(msg.role, "value") else str(msg.role),
                        "content": msg.content,
                        "tool_call_info": msg.tool_call_info,
                        "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                    }
                    for msg in messages
                ],
            }
        finally:
            db.close()
    
    def list_conversations(self, page: int = 1, page_size: int = 20, 
                          status: Optional[str] = None) -> Dict[str, Any]:
        """列出对话
        
        Args:
            page: 页码
            page_size: 每页数量
            status: 状态过滤
            
        Returns:
            对话列表结果
        """
        db = self.get_db_session()
        try:
            query = db.query(Conversation)
            
            if status:
                query = query.filter(Conversation.status == status)
            
            total_count = query.count()
            # 按开始时间倒序（最新对话在前），保证分页结果确定性
            conversations = query.order_by(
                Conversation.started_at.desc()
            ).offset((page - 1) * page_size).limit(page_size).all()
            
            return {
                "conversations": [
                    {
                        "id": conv.id,
                        "title": conv.title,
                        "started_at": conv.started_at.isoformat() if conv.started_at else None,
                        "message_count": conv.message_count,
                        "status": conv.status.value
                    }
                    for conv in conversations
                ],
                "total_count": total_count,
                "page": page,
                "page_size": page_size
            }
        finally:
            db.close()
    
    def add_message(self, conversation_id: str, role: str,
                   content: str, tool_call_info: Optional[Dict] = None) -> Dict[str, Any]:
        """添加消息到对话

        Args:
            conversation_id: 对话ID
            role: 消息角色
            content: 消息内容
            tool_call_info: 工具调用信息

        Returns:
            消息ID

        Raises:
            ValueError: 如果对话不存在
        """
        db = self.get_db_session()
        try:
            # 首先检查对话是否存在
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()

            if not conversation:
                raise ValueError(f"对话不存在: {conversation_id}")

            message_id = f"msg_{uuid.uuid4().hex[:12]}"

            message = ConversationMessage(
                id=message_id,
                conversation_id=conversation_id,
                role=role,
                content=content,
                tool_call_info=tool_call_info,
                timestamp=datetime.now()
            )

            # 更新对话的消息计数
            conversation.message_count += 1

            db.add(message)
            db.commit()

            return {"id": message_id, "timestamp": message.timestamp.isoformat()}
        except ValueError:
            # 直接重新抛出 ValueError，不需要 rollback（没有修改）
            raise
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    def get_or_create_conversation(
        self,
        conversation_id: str,
        title: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Conversation:
        """按主键获取对话，不存在则创建。

        供 /api/query 复用：用 session_id 作为 conversation_id，
        同一 session 的多轮问答会追加到同一条对话记录。

        Args:
            conversation_id: 对话ID（通常为 session_id）
            title: 标题（首次创建时生效，默认 "新对话"）
            user_id: 用户ID

        Returns:
            Conversation ORM 实例
        """
        db = self.get_db_session()
        try:
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()

            if conversation is None:
                conversation = Conversation(
                    id=conversation_id,
                    user_id=user_id,
                    title=title or "新对话",
                    status=ConversationStatus.ACTIVE,
                    started_at=datetime.now(),
                )
                db.add(conversation)
                db.commit()
                db.refresh(conversation)

            return conversation
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def record_exchange(
        self,
        conversation_id: str,
        user_query: str,
        assistant_response: str,
        title: Optional[str] = None,
        tool_call_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """原子地记录一轮问答（user + assistant 两条消息）。

        供 /api/query 在拿到 Agent 响应后调用，把真实问答写入
        conversations / conversation_messages 表，使前端聊天历史能看到
        真实内容。用 session_id 作为 conversation_id：同一 session 的多轮
        问答追加到同一条对话；标题取自首条提问。

        Args:
            conversation_id: 对话ID（通常为 session_id）
            user_query: 用户提问
            assistant_response: Agent 返回的回答
            title: 对话标题（仅首次创建时生效，默认截取首条提问前 40 字）
            tool_call_info: 附加在 assistant 消息上的元数据（如来源、耗时）

        Returns:
            {"conversation_id": ..., "user_message_id": ..., "assistant_message_id": ...}
        """
        if title is None:
            title = user_query[:40] + ("..." if len(user_query) > 40 else "")

        db = self.get_db_session()
        try:
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()

            if conversation is None:
                conversation = Conversation(
                    id=conversation_id,
                    title=title,
                    status=ConversationStatus.ACTIVE,
                    started_at=datetime.now(),
                )
                db.add(conversation)
                db.flush()  # 拿到主键，后续消息可引用同一事务内的 conversation

            now = datetime.now()
            user_message = ConversationMessage(
                id=f"msg_{uuid.uuid4().hex[:12]}",
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content=user_query,
                timestamp=now,
            )
            assistant_message = ConversationMessage(
                id=f"msg_{uuid.uuid4().hex[:12]}",
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=assistant_response,
                tool_call_info=tool_call_info,
                timestamp=now,
            )
            db.add(user_message)
            db.add(assistant_message)

            conversation.message_count = (conversation.message_count or 0) + 2
            db.commit()

            return {
                "conversation_id": conversation.id,
                "user_message_id": user_message.id,
                "assistant_message_id": assistant_message.id,
            }
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
