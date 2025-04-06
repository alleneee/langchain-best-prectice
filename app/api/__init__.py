"""
API路由初始化
"""

from fastapi import APIRouter
from app.api.endpoints import document_qa, tour_guide, system

api_router = APIRouter()

# 包含所有API端点
api_router.include_router(document_qa.router)
api_router.include_router(tour_guide.router)
api_router.include_router(system.router)
