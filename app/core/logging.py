"""
日志配置模块
"""

import logging
import sys
from typing import Optional

from app.core.config import settings

def setup_logger(name: Optional[str] = None) -> logging.Logger:
    """
    配置和获取日志记录器
    
    参数:
        name: 日志记录器名称，默认为None
        
    返回:
        logging.Logger: 日志记录器实例
    """
    logger_name = name or "app"
    logger = logging.getLogger(logger_name)
    
    # 避免重复配置
    if logger.handlers:
        return logger
    
    # 设置日志级别
    log_level = getattr(logging, settings.LOG_LEVEL.upper())
    logger.setLevel(log_level)
    
    # 创建控制台处理器
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    
    # 设置日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    # 添加处理器到日志记录器
    logger.addHandler(handler)
    
    return logger

# 应用程序默认日志记录器
logger = setup_logger("app") 