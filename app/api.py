"""
文档问答系统API - LangChain 0.3最佳实践
"""

from typing import List, Optional, Dict, Any
import os
from pathlib import Path
import json
import tempfile
import uuid
import time
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Query, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.core.logging import logger
from app.core.config import settings
from app.services.document_qa_service import DocumentQAService
from app.services.captcha_service import CaptchaService
from app.services.tour_guide_service import TourGuideService
from app.schemas.document_qa import (
    QuestionRequest, QuestionResponse, 
    DocumentUploadRequest, DocumentUploadResponse,
    CaptchaResponse, SystemStatusResponse,
    WebSearchRequest, WebSearchResponse,
    SessionRequest, SessionResponse, SessionListResponse
)


app = FastAPI(
    title="文档问答系统API",
    description="基于LangChain和向量数据库的文档问答系统",
    version="0.3.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化服务
document_qa_service = DocumentQAService()
captcha_service = CaptchaService()
tour_guide_service = TourGuideService()

# 添加静态文件支持
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# 定义API路由前缀
api_prefix = settings.API_PREFIX

# 定义API端点
@app.get("/")
async def root():
    """API根端点，返回简单的欢迎信息"""
    return {"message": "欢迎使用文档问答系统API"}


@app.get(f"{api_prefix}/status", response_model=SystemStatusResponse)
async def get_status():
    """获取系统状态"""
    status = document_qa_service.get_system_status()
    return status


@app.post(f"{api_prefix}/question", response_model=QuestionResponse)
async def question(request: QuestionRequest):
    """
    处理用户问题
    
    接收用户问题，并返回基于文档的回答或使用GPT-4o内置web search功能获取的回答
    """
    if not request.question:
        raise HTTPException(status_code=400, detail="问题不能为空")
    
    logger.info(f"接收到问题: {request.question[:50]}...")
    
    # 如果请求中没有指定模型，默认使用GPT-4o
    if not request.model:
        request.model = settings.DEFAULT_MODEL
    
    # 对于GPT-4o模型，自动启用web search功能
    if request.model == "gpt-4o" and settings.ENABLE_OPENAI_WEB_SEARCH:
        request.use_web_search = True
    
    result = document_qa_service.process_question(request)
    return result


@app.post(f"{api_prefix}/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    collection_name: Optional[str] = Form("document_collection"),
    overwrite: bool = Form(False),
    chunk_size: Optional[int] = Form(None),
    chunk_overlap: Optional[int] = Form(None)
):
    """
    上传文档并处理
    
    接收用户上传的文档，处理并创建向量索引
    """
    if not file:
        raise HTTPException(status_code=400, detail="未提供文件")
    
    # 检查文件类型
    filename = file.filename or ""
    file_extension = filename.split(".")[-1].lower()
    
    # 支持的文件类型
    supported_extensions = [
        "pdf", "txt", "md", "docx", "doc", 
        "csv", "xlsx", "xls", "pptx", "ppt", 
        "json", "html"
    ]
    
    if file_extension not in supported_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的文件类型。支持的类型：{', '.join([ext.upper() for ext in supported_extensions])}"
        )
    
    # 保存上传的文件到临时目录
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}")
    try:
        content = await file.read()
        temp_file.write(content)
        temp_file.close()
        
        # 处理文档，使用自定义分块参数
        logger.info(f"正在处理上传的文档: {filename}")
        result = document_qa_service.process_document(
            temp_file.name, 
            collection_name=collection_name,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        return DocumentUploadResponse(
            status="success",
            message=f"文档'{filename}'处理成功",
            filename=filename,
            document_count=result["document_count"]
        )
    except Exception as e:
        logger.error(f"处理上传文档时错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理文档时错误: {str(e)}")
    finally:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)


@app.post(f"{api_prefix}/upload-batch", response_model=DocumentUploadResponse)
async def upload_batch(
    files: List[UploadFile] = File(...),
    collection_name: Optional[str] = Form("document_collection"),
    overwrite: bool = Form(False)
):
    """
    批量上传文档并处理
    
    接收多个文档，处理并创建向量索引
    """
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="未提供文件")
    
    # 支持的文件类型
    supported_extensions = [
        "pdf", "txt", "md", "docx", "doc", 
        "csv", "xlsx", "xls", "pptx", "ppt", 
        "json", "html"
    ]
    
    # 检查所有文件类型
    for file in files:
        filename = file.filename or ""
        file_extension = filename.split(".")[-1].lower()
        if file_extension not in supported_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"文件 '{filename}' 类型不支持。支持的类型：{', '.join([ext.upper() for ext in supported_extensions])}"
            )
    
    total_documents = 0
    processed_files = []
    errors = []
    
    # 处理每个文件
    for file in files:
        filename = file.filename or ""
        file_extension = filename.split(".")[-1].lower()
        
        # 保存上传的文件到临时目录
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}")
        try:
            content = await file.read()
            temp_file.write(content)
            temp_file.close()
            
            # 处理文档
            logger.info(f"正在处理上传的文档: {filename}")
            result = document_qa_service.process_document(
                temp_file.name, collection_name=collection_name
            )
            
            if result["status"] == "success":
                total_documents += result.get("document_count", 0)
                processed_files.append(filename)
            else:
                errors.append(f"处理文件 '{filename}' 失败: {result.get('message')}")
                
        except Exception as e:
            logger.error(f"处理上传文档 '{filename}' 时错误: {str(e)}")
            errors.append(f"处理文件 '{filename}' 失败: {str(e)}")
        finally:
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
    
    # 判断处理结果
    if not processed_files and errors:
        raise HTTPException(status_code=500, detail="; ".join(errors))
    
    return DocumentUploadResponse(
        status="success",
        message=f"成功处理 {len(processed_files)}/{len(files)} 个文件" + 
                (f", 错误: {'; '.join(errors)}" if errors else ""),
        filename=", ".join(processed_files),
        document_count=total_documents
    )


@app.post(f"{api_prefix}/upload-url", response_model=DocumentUploadResponse)
async def upload_from_url(
    url: str = Body(..., embed=True),
    collection_name: Optional[str] = Body("document_collection"),
    overwrite: bool = Body(False)
):
    """
    从URL加载网页内容
    
    接收URL，加载网页内容并处理
    """
    if not url:
        raise HTTPException(status_code=400, detail="未提供URL")
    
    try:
        # 处理网页内容
        logger.info(f"正在处理URL: {url}")
        result = document_qa_service.process_web_page(
            url, collection_name=collection_name
        )
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        return DocumentUploadResponse(
            status="success",
            message=f"URL '{url}' 处理成功",
            filename=url,
            document_count=result["document_count"]
        )
    except Exception as e:
        logger.error(f"处理URL时错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理URL时错误: {str(e)}")


@app.post(f"{api_prefix}/upload-directory", response_model=DocumentUploadResponse)
async def upload_directory(
    directory_path: str = Body(..., embed=True),
    collection_name: Optional[str] = Body("document_collection"),
    recursive: bool = Body(True)
):
    """
    处理本地目录中的所有文档
    
    接收目录路径，处理目录中的所有支持文档
    """
    if not directory_path:
        raise HTTPException(status_code=400, detail="未提供目录路径")
    
    if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
        raise HTTPException(status_code=400, detail=f"目录不存在或不是有效目录: {directory_path}")
    
    try:
        # 处理目录中的文档
        logger.info(f"正在处理目录: {directory_path}")
        result = document_qa_service.process_directory(
            directory_path, collection_name=collection_name, recursive=recursive
        )
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        return DocumentUploadResponse(
            status="success",
            message=f"目录 '{directory_path}' 处理成功，共处理 {result.get('file_count', 0)} 个文件",
            filename=directory_path,
            document_count=result["document_count"]
        )
    except Exception as e:
        logger.error(f"处理目录时错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理目录时错误: {str(e)}")


@app.get(f"{api_prefix}/captcha", response_model=CaptchaResponse)
async def get_captcha():
    """
    获取验证码
    
    生成验证码图片和ID
    """
    captcha_id, captcha_data = captcha_service.generate_captcha()
    return CaptchaResponse(
        captcha_id=captcha_id,
        captcha_image=captcha_data
    )


@app.post(f"{api_prefix}/web-search", response_model=WebSearchResponse)
async def web_search(request: WebSearchRequest):
    """
    执行网络搜索
    
    进行网络搜索并返回结果
    """
    if not request.query:
        raise HTTPException(status_code=400, detail="搜索查询不能为空")
    
    if not settings.ENABLE_WEB_SEARCH:
        raise HTTPException(status_code=403, detail="网络搜索功能未启用")
        
    if not settings.TAVILY_API_KEY:
        raise HTTPException(status_code=503, detail="未配置Tavily API密钥")
    
    logger.info(f"执行网络搜索: {request.query[:50]}...")
    
    # 设置搜索参数
    search_settings = {
        "search_depth": request.search_depth,
        "max_results": request.max_results,
        "include_domains": request.include_domains,
        "exclude_domains": request.exclude_domains
    }
    
    result = document_qa_service.perform_web_search(request.query, search_settings)
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("error", "搜索失败"))
    
    return WebSearchResponse(
        query=result["query"],
        results=result["results"],
        count=result["count"],
        status="success"
    )


@app.post(f"{api_prefix}/session", response_model=SessionResponse)
async def create_or_get_session(request: SessionRequest = Body({})):
    """
    创建或获取会话
    
    创建新会话或获取现有会话信息
    """
    session_id = request.session_id if request and hasattr(request, 'session_id') else None
    
    if session_id:
        # 获取现有会话
        session = document_qa_service.session_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return SessionResponse(
            session_id=session_id,
            message="获取会话成功",
            created_at=session.get("created_at", datetime.now().isoformat())
        )
    else:
        # 创建新会话
        new_session_id = document_qa_service.session_service.create_session()
        session = document_qa_service.session_service.get_session(new_session_id)
        
        return SessionResponse(
            session_id=new_session_id,
            message="创建会话成功",
            created_at=session.get("created_at", datetime.now().isoformat())
        )


@app.get(f"{api_prefix}/sessions", response_model=SessionListResponse)
async def list_sessions():
    """
    列出所有会话
    
    返回所有可用会话的列表
    """
    sessions = document_qa_service.session_service.list_sessions()
    return SessionListResponse(sessions=sessions)


@app.delete(f"{api_prefix}/session/{{session_id}}")
async def delete_session(session_id: str):
    """
    删除会话
    
    删除指定的会话及其历史记录
    """
    success = document_qa_service.session_service.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    return {"message": "会话删除成功", "session_id": session_id}


@app.post(f"{api_prefix}/tour-guide", response_model=QuestionResponse)
async def tour_guide_question(request: QuestionRequest):
    """
    处理旅游导游相关问题
    
    使用专门的导游Agent处理旅行、景点、行程等相关问题
    """
    if not request.question:
        raise HTTPException(status_code=400, detail="问题不能为空")
    
    logger.info(f"接收到导游问题: {request.question[:50]}...")
    
    # 如果请求中没有指定模型，默认使用GPT-4o
    if not request.model:
        request.model = settings.DEFAULT_MODEL
    
    # 对于GPT-4o模型，自动启用web search功能
    if request.model == "gpt-4o" and settings.ENABLE_OPENAI_WEB_SEARCH:
        request.use_web_search = True
    
    result = tour_guide_service.process_question(request)
    return result
