"""
文档问答API端点
"""

from fastapi import APIRouter, UploadFile, File, Form, Request, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
import json
import asyncio
from typing import List, Optional, Dict, Any, AsyncGenerator
import os
import uuid
from pathlib import Path

from app.core.config import settings
from app.core.logging import logger
from app.services.document_qa_service import DocumentQAService
from app.services.session_service import SessionService
from app.schemas.document_qa import (
    QuestionRequest, QuestionResponse, DocumentUploadRequest, 
    DocumentUploadResponse, SessionListResponse
)

# 创建API路由器
router = APIRouter(tags=["document-qa"])

# 创建服务实例
document_qa_service = DocumentQAService()
session_service = SessionService()

@router.post("/document-qa/question", response_model=QuestionResponse)
async def answer_question(request: QuestionRequest):
    """
    提交问题并获取回答
    """
    logger.info(f"接收到问题请求: {request.question[:50]}...")
    
    result = document_qa_service.process_question(request)
    
    return QuestionResponse(
        answer=result["answer"],
        sources=result.get("sources", []),
        web_sources=result.get("web_sources", []),
        history=result.get("history", []),
        history_id=result["history_id"]
    )

@router.post("/document-qa/question/stream")
async def answer_question_stream(request: Request):
    """
    提交问题并获取流式回答
    """
    # 解析请求体
    request_data = await request.json()
    logger.info(f"接收到流式问题请求: {request_data.get('question', '')[:50]}...")
    
    # 创建QuestionRequest对象
    question_request = QuestionRequest(
        question=request_data.get("question", ""),
        history_id=request_data.get("history_id"),
        model=request_data.get("model", "gpt-4o"),
        temperature=request_data.get("temperature", 0.7),
        use_web_search=request_data.get("use_web_search", False)
    )
    
    # 生成流式响应
    async def generate() -> AsyncGenerator[str, None]:
        """生成SSE流式响应"""
        try:
            # 获取流式回答
            async for chunk, metadata in document_qa_service.process_question_stream(question_request):
                # 构建事件数据
                data: Dict[str, Any] = {
                    "text": chunk,
                    "done": False,
                }
                
                # 如果有元数据，则添加到响应中
                if metadata and metadata.get("end_of_response", False):
                    data["done"] = True
                    data["sources"] = metadata.get("sources", [])
                    data["web_sources"] = metadata.get("web_sources", [])
                    data["history_id"] = metadata.get("history_id", "")
                
                # 发送事件
                yield f"data: {json.dumps(data)}\n\n"
        except Exception as e:
            logger.exception(f"流式处理出错: {str(e)}")
            error_data = {
                "text": f"处理您的问题时出错: {str(e)}",
                "done": True
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )

@router.post("/document-qa/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    document_name: Optional[str] = Form(None),
    description: Optional[str] = Form(None)
):
    """
    上传文档
    """
    logger.info(f"接收到文档上传请求: {file.filename}")
    
    # 保存上传文件到临时目录
    temp_file_path = os.path.join(settings.UPLOAD_DIR, f"temp_{uuid.uuid4()}{os.path.splitext(file.filename)[1]}")
    content = await file.read()
    with open(temp_file_path, "wb") as temp_file:
        temp_file.write(content)
    
    # 封装请求对象
    request = DocumentUploadRequest(
        file_path=temp_file_path,
        filename=file.filename,
        document_name=document_name or file.filename,
        description=description or "用户上传的文档"
    )
    
    # 在后台处理文档
    background_tasks.add_task(
        document_qa_service.process_document,
        request
    )
    
    return DocumentUploadResponse(
        message="文档上传成功，正在处理中...",
        filename=file.filename,
        document_name=request.document_name
    )

@router.get("/document-qa/sessions", response_model=SessionListResponse)
async def list_sessions():
    """
    获取会话列表
    """
    sessions = session_service.list_sessions()
    return SessionListResponse(sessions=sessions) 