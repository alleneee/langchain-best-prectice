"""
应用程序配置模块
"""

import os
from pathlib import Path
from typing import Optional, Literal
from pydantic_settings import BaseSettings, Field

# 项目根目录
# Determine project root based on the location of this file
# This assumes config.py is in app/core/
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()

# Data directory for local storage (e.g., sessions, potentially uploads if not /tmp)
# Check if running on Vercel (using env var set in api/index.py or Vercel's built-in envs)
IS_VERCEL = os.environ.get('VERCEL') == '1' or os.environ.get('VERCEL_ENV')

# Use /tmp for data storage on Vercel, otherwise use local data directory
if IS_VERCEL:
    # Vercel provides a writable /tmp directory
    DATA_DIR = Path("/tmp")
    UPLOAD_DIR_BASE = Path("/tmp/uploads")
    # Optionally use Vercel Blob for persistent storage if needed
    # VERCEL_BLOB_STORE_ID = os.environ.get('BLOB_READ_WRITE_TOKEN', '').split('_')[1] if os.environ.get('BLOB_READ_WRITE_TOKEN') else None
else:
    # Local development paths
    DATA_DIR = PROJECT_ROOT / "data"
    UPLOAD_DIR_BASE = DATA_DIR / "uploads"

# Static files directory (usually served separately in production)
STATIC_DIR = PROJECT_ROOT / "static"

# Ensure data directories exist (especially for local dev)
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR_BASE.mkdir(parents=True, exist_ok=True)

class Settings(BaseSettings):
    """应用程序设置类"""
    # Project metadata
    PROJECT_NAME: str = "LangChain Best Practice API"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "API for LangChain Best Practice application"

    # API settings
    API_V1_STR: str = "/api/v1"

    # OpenAI API Key
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")

    # LangChain settings
    LANGCHAIN_TRACING_V2: bool = Field(True, env="LANGCHAIN_TRACING_V2")
    LANGCHAIN_ENDPOINT: Optional[str] = Field(None, env="LANGCHAIN_ENDPOINT")
    LANGCHAIN_API_KEY: Optional[str] = Field(None, env="LANGCHAIN_API_KEY")
    LANGCHAIN_PROJECT: Optional[str] = Field("LangChain Best Practice", env="LANGCHAIN_PROJECT")

    # Tavily Search API Key (Optional)
    TAVILY_API_KEY: Optional[str] = Field(None, env="TAVILY_API_KEY")
    ENABLE_WEB_SEARCH: bool = Field(False, env="ENABLE_WEB_SEARCH")

    # Amap API Key (Optional)
    AMAP_API_KEY: Optional[str] = Field(None, env="AMAP_API_KEY")

    # Google API Key and CSE ID (Optional)
    GOOGLE_API_KEY: Optional[str] = Field(None, env="GOOGLE_API_KEY")
    GOOGLE_CSE_ID: Optional[str] = Field(None, env="GOOGLE_CSE_ID")

    # Upload directory (use the base path determined above)
    UPLOAD_DIR: Path = UPLOAD_DIR_BASE

    # Cache settings (Redis or in-memory)
    CACHE_TYPE: Literal["redis", "memory"] = "memory" # Default to memory for Vercel unless Redis is configured
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None

    # Session and data storage paths
    DATA_DIR: Path = DATA_DIR # Use the base path determined above
    STATIC_DIR: Path = STATIC_DIR

    # Document processing settings
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = 'utf-8'
        extra = 'ignore' # Ignore extra fields from .env

settings = Settings()

# Ensure upload directory exists (runtime check)
# Note: This might not be necessary if using /tmp on Vercel as it should exist
# However, it's good practice for local dev
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True) 