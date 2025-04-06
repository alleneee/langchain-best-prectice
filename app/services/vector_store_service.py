"""
向量存储服务
"""

from app.utils.vector_store import VectorStoreManager
from app.core.logging import logger

class VectorStoreService:
    """向量存储服务"""
    
    def __init__(self):
        """初始化向量存储服务"""
        self.vector_store_manager = VectorStoreManager()
    
    def is_vector_store_ready(self) -> bool:
        """
        检查向量存储是否就绪
        
        返回:
            布尔值，表示向量存储是否就绪
        """
        try:
            if not hasattr(self.vector_store_manager, 'vector_store') or not self.vector_store_manager.vector_store:
                # 尝试加载向量存储
                self.vector_store_manager.load_milvus_index()
            
            return self.vector_store_manager.vector_store is not None
        except Exception as e:
            logger.error(f"检查向量存储状态时出错: {str(e)}")
            return False 