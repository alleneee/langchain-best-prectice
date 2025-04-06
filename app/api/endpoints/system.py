"""
系统相关API端点
"""

from fastapi import APIRouter, Depends, HTTPException
from uuid import uuid4

from app.core.config import settings
from app.services.session_service import SessionService
from app.services.vector_store_service import VectorStoreService

# 创建API路由器
router = APIRouter(tags=["system"])

# 创建服务实例
session_service = SessionService()
vector_store_service = VectorStoreService()

@router.get("/status")
async def get_system_status():
    """
    获取系统状态
    """
    vector_store_ready = vector_store_service.is_vector_store_ready()
    
    return {
        "status": "ok",
        "vector_store_ready": vector_store_ready,
        "web_search_enabled": settings.ENABLE_WEB_SEARCH
    }

@router.post("/session")
async def create_session():
    """
    创建新的会话
    """
    session_id = session_service.create_chat_history()
    
    return {
        "session_id": session_id
    } 