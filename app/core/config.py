"""
应用程序配置模块
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
UPLOAD_DIR = ROOT_DIR / "uploads"
VECTOR_STORE_DIR = ROOT_DIR / "vector_stores"
STATIC_DIR = ROOT_DIR / "static"
SESSIONS_DIR = ROOT_DIR / "sessions"

# 确保必要的目录存在
for dir_path in [DATA_DIR, UPLOAD_DIR, VECTOR_STORE_DIR, STATIC_DIR, SESSIONS_DIR]:
    dir_path.mkdir(exist_ok=True, parents=True)

class Settings(BaseSettings):
    """应用程序设置类"""
    # 应用程序设置
    APP_NAME: str = "RAG文档问答系统API"
    APP_DESCRIPTION: str = "基于LangChain和OpenAI的RAG文档问答系统API"
    APP_VERSION: str = "0.1.0"
    API_PREFIX: str = "/api"
    
    # OpenAI相关设置
    OPENAI_API_KEY: Optional[str] = None
    DEFAULT_MODEL: str = "gpt-4o"
    DEFAULT_TEMPERATURE: float = 0.0
    ENABLE_OPENAI_WEB_SEARCH: bool = False
    
    # Tavily网络搜索设置
    TAVILY_API_KEY: Optional[str] = None
    ENABLE_WEB_SEARCH: bool = False
    
    # 高德地图API设置
    AMAP_API_KEY: Optional[str] = None
    
    # Milvus相关设置
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: str = "19530"
    
    # 文档处理设置
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    
    # 会话和数据存储设置
    DATA_DIR: Path = DATA_DIR
    UPLOAD_DIR: Path = UPLOAD_DIR
    VECTOR_STORE_DIR: Path = VECTOR_STORE_DIR
    STATIC_DIR: Path = STATIC_DIR
    SESSIONS_DIR: Path = SESSIONS_DIR
    
    # FastAPI设置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # 日志设置
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

# 全局设置实例
settings = Settings() 