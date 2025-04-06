"""
系统信息API端点
"""

from fastapi import APIRouter
from typing import Dict, Any

from app.core.config import settings
from app.core.logging import logger
from app.services.document_qa_service import DocumentQAService
from app.services.session_service import SessionService

router = APIRouter()

document_qa_service = DocumentQAService()
session_service = SessionService()

@router.get("/status", summary="获取系统状态", response_model=Dict[str, Any])
def get_status() -> Dict[str, Any]:
    """
    获取应用程序的当前状态和配置信息。
    
    包括:
    - LLM 模型配置
    - Web 搜索启用状态
    - LangChain 项目信息
    - 上传目录
    - 文档分块设置
    - 当前会话数量
    """
    logger.info("请求系统状态")
    try:
        web_search_enabled = settings.ENABLE_WEB_SEARCH and bool(settings.TAVILY_API_KEY)
        session_count = session_service.get_session_count()
        
        status_info = {
            "status": "ok",
            "llm_model": settings.DEFAULT_MODEL,
            "web_search_enabled": web_search_enabled,
            "langchain_project": settings.LANGCHAIN_PROJECT,
            "upload_dir": str(settings.UPLOAD_DIR),
            "chunk_size": settings.CHUNK_SIZE,
            "chunk_overlap": settings.CHUNK_OVERLAP,
            "active_sessions": session_count
        }
        return status_info
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}", exc_info=True)
        return {"status": "error", "message": f"获取系统状态失败: {str(e)}"}

@router.post("/session")
async def create_session():
    """
    创建新的会话
    """
    session_id = session_service.create_chat_history()
    
    return {
        "session_id": session_id
    } 