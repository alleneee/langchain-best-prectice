"""
旅游导游API端点
"""

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import json
import asyncio
from typing import AsyncGenerator, Dict, Any
from app.core.logging import logger
from app.services.tour_guide_service import TourGuideService
from app.schemas.document_qa import QuestionRequest, QuestionResponse

# 创建API路由器
router = APIRouter(tags=["tour-guide"])

# 创建服务实例
tour_guide_service = TourGuideService()

@router.post("/tour-guide", response_model=QuestionResponse)
async def tour_guide_question(request: QuestionRequest):
    """
    提交旅游相关问题并获取回答
    """
    logger.info(f"接收到导游问题请求: {request.question[:50]}...")
    
    result = tour_guide_service.process_question(request)
    
    return QuestionResponse(
        answer=result["answer"],
        sources=result.get("sources", []),
        web_sources=result.get("web_sources", []),
        history=result.get("history", []),
        history_id=result["history_id"]
    )

@router.post("/tour-guide/stream")
async def tour_guide_question_stream(request: Request):
    """
    提交旅游相关问题并获取流式回答
    """
    # 解析请求体
    request_data = await request.json()
    logger.info(f"接收到导游流式问题请求: {request_data.get('question', '')[:50]}...")
    
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
            async for chunk, metadata in tour_guide_service.process_question_stream(question_request):
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