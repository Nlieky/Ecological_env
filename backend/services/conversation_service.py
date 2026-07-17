"""对话服务层

负责对话历史的管理和持久化。
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from backend.database.session import SessionLocal
from backend.models.conversation import Conversation, ConversationMessage, ConversationStatus
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
        """获取对话详情
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            对话详情字典，不存在返回None
        """
        db = self.get_db_session()
        try:
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            
            if not conversation:
                return None
            
            return {
                "id": conversation.id,
                "user_id": conversation.user_id,
                "title": conversation.title,
                "status": conversation.status.value,
                "started_at": conversation.started_at.isoformat() if conversation.started_at else None,
                "ended_at": conversation.ended_at.isoformat() if conversation.ended_at else None,
                "message_count": conversation.message_count
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
