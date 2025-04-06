"""
文档问答相关的数据模式
"""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field


class Message(BaseModel):
    """聊天消息模型"""
    role: str = Field(..., description="消息角色：user或assistant")
    content: str = Field(..., description="消息内容")


class ChatHistory(BaseModel):
    """聊天历史模型"""
    messages: List[Message] = Field(default_factory=list, description="消息列表")
    history_id: Optional[str] = Field(None, description="历史ID")


class QuestionRequest(BaseModel):
    """问题请求模型"""
    question: str = Field(..., description="用户问题")
    history_id: Optional[str] = Field(None, description="历史ID，用于关联会话")
    model: Optional[str] = Field(None, description="使用的模型名称")
    temperature: Optional[float] = Field(None, description="模型温度参数")
    use_web_search: Optional[bool] = Field(False, description="是否使用网络搜索")
    search_settings: Optional[Dict[str, Any]] = Field(None, description="网络搜索设置")


class QuestionResponse(BaseModel):
    """问题响应模型"""
    answer: str = Field(..., description="问题回答")
    sources: List[str] = Field(default_factory=list, description="信息来源")
    history: List[Dict[str, str]] = Field(default_factory=list, description="聊天历史")
    history_id: str = Field(..., description="历史ID")
    web_sources: Optional[List[Dict[str, Any]]] = Field(None, description="网络搜索来源")


class DocumentUploadRequest(BaseModel):
    """文档上传请求模型"""
    collection_name: Optional[str] = Field(None, description="文档集合名称")
    captcha_id: Optional[str] = Field(None, description="验证码ID")
    captcha_text: Optional[str] = Field(None, description="验证码文本")


class DocumentUploadResponse(BaseModel):
    """文档上传响应模型"""
    status: str = Field(..., description="状态：success或error")
    message: str = Field(..., description="响应消息")
    document_count: Optional[int] = Field(None, description="处理的文档数量")


class CaptchaResponse(BaseModel):
    """验证码响应模型"""
    captcha_id: str = Field(..., description="验证码ID")
    captcha_image: str = Field(..., description="验证码图像（base64编码）")


class SystemStatusResponse(BaseModel):
    """系统状态响应模型"""
    status: str = Field(..., description="系统状态")
    vector_store_ready: bool = Field(..., description="向量存储是否就绪")
    document_count: Optional[int] = Field(None, description="文档数量")
    web_search_enabled: bool = Field(False, description="网络搜索是否启用")


class WebSearchRequest(BaseModel):
    """网络搜索请求模型"""
    query: str = Field(..., description="搜索查询")
    search_depth: Optional[str] = Field("basic", description="搜索深度：basic或advanced")
    max_results: Optional[int] = Field(5, description="最大结果数量")
    include_domains: Optional[List[str]] = Field(None, description="包含的域名列表")
    exclude_domains: Optional[List[str]] = Field(None, description="排除的域名列表")


class WebSearchResponse(BaseModel):
    """网络搜索响应模型"""
    results: List[Dict[str, Any]] = Field(default_factory=list, description="搜索结果")
    count: int = Field(..., description="结果数量")
    query: str = Field(..., description="查询内容")
    status: str = Field("success", description="状态")


class SessionRequest(BaseModel):
    """会话请求模型"""
    session_id: Optional[str] = Field(None, description="会话ID，为None时创建新会话")


class SessionResponse(BaseModel):
    """会话响应模型"""
    session_id: str = Field(..., description="会话ID")
    message: str = Field(..., description="状态消息")
    created_at: str = Field(..., description="创建时间")


class SessionListResponse(BaseModel):
    """会话列表响应模型"""
    sessions: List[Dict[str, Any]] = Field(..., description="会话列表") 