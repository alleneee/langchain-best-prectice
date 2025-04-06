"""
向量存储工具模块 - LangChain 0.3最佳实践
"""

from typing import List, Optional, Dict, Any
import os
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore
from langchain_community.vectorstores.milvus import Milvus
from langchain_openai import OpenAIEmbeddings
from langchain_core.embeddings import Embeddings


class VectorStoreManager:
    """向量存储管理类，仅支持Milvus"""
    
    def __init__(self, 
                embedding_model: Optional[Embeddings] = None,
                milvus_connection_args: Optional[Dict[str, Any]] = None):
        """
        初始化向量存储管理器
        
        参数:
            embedding_model: 嵌入模型，默认使用OpenAIEmbeddings
            milvus_connection_args: Milvus连接参数
        """
        self.embedding_model = embedding_model or OpenAIEmbeddings()
        self.milvus_connection_args = milvus_connection_args or {
            "host": os.environ.get("MILVUS_HOST", "localhost"), 
            "port": os.environ.get("MILVUS_PORT", "19530")
        }
        self.vector_store = None
    
    def create_milvus_index(self, documents: List[Document],
                           collection_name: str = "document_collection") -> VectorStore:
        """
        创建Milvus向量索引
        
        参数:
            documents: 文档列表
            collection_name: 集合名称
            
        返回:
            Milvus向量存储实例
        """
        if not documents:
            print("警告: 没有文档提供给Milvus索引")
            return None
        
        try:
            vector_store = Milvus.from_documents(
                documents=documents,
                embedding=self.embedding_model,
                collection_name=collection_name,
                connection_args=self.milvus_connection_args
            )
            
            self.vector_store = vector_store
            print(f"Milvus索引已创建: {collection_name}")
            return vector_store
        except Exception as e:
            print(f"创建Milvus索引失败: {e}")
            return None
    
    def load_milvus_index(self, 
                         collection_name: str = "document_collection") -> Optional[VectorStore]:
        """
        加载已存在的Milvus索引
        
        参数:
            collection_name: 集合名称
            
        返回:
            Milvus向量存储实例
        """
        try:
            vector_store = Milvus(
                embedding_function=self.embedding_model,
                collection_name=collection_name,
                connection_args=self.milvus_connection_args
            )
            self.vector_store = vector_store
            print(f"成功加载Milvus索引: {collection_name}")
            return vector_store
        except Exception as e:
            print(f"加载Milvus索引失败: {e}")
            return None
    
    def similarity_search(self, query: str, k: int = 4, 
                         filter: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        执行相似性搜索
        
        参数:
            query: 查询文本
            k: 返回的结果数量
            filter: 过滤条件
            
        返回:
            相关文档列表
        """
        if not self.vector_store:
            print("错误: 未初始化向量存储，请先创建或加载索引")
            return []
        
        try:
            if filter:
                results = self.vector_store.similarity_search(
                    query, k=k, filter=filter
                )
            else:
                results = self.vector_store.similarity_search(query, k=k)
            return results
        except Exception as e:
            print(f"相似性搜索失败: {e}")
            return []

    def similarity_search_with_score(self, query: str, 
                                   k: int = 4) -> List[tuple[Document, float]]:
        """
        执行相似性搜索并返回分数
        
        参数:
            query: 查询文本
            k: 返回的结果数量
            
        返回:
            包含(文档, 分数)元组的列表
        """
        if not self.vector_store:
            print("错误: 未初始化向量存储，请先创建或加载索引")
            return []
        
        try:
            results = self.vector_store.similarity_search_with_score(query, k=k)
            return results
        except Exception as e:
            print(f"带分数的相似性搜索失败: {e}")
            return []


# 使用示例
if __name__ == "__main__":
    from document_loader import DocumentProcessor
    
    # 示例：创建和使用向量存储
    processor = DocumentProcessor()
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data"
    
    # 创建向量存储目录
    vector_store_dir = base_dir / "vector_store"
    vector_store_dir.mkdir(exist_ok=True)
    
    # 加载和处理文档
    docs = processor.process_documents(str(data_dir))
    
    if docs:
        # 创建向量存储
        vector_manager = VectorStoreManager(
            milvus_connection_args={
                "host": os.environ.get("MILVUS_HOST", "localhost"), 
                "port": os.environ.get("MILVUS_PORT", "19530")
            }
        )
        vector_store = vector_manager.create_milvus_index(docs)
        
        # 执行查询
        if vector_store:
            results = vector_manager.similarity_search("查询示例")
            print(f"找到 {len(results)} 个相关文档")
            for i, doc in enumerate(results):
                print(f"结果 {i+1}:")
                print(f"内容: {doc.page_content[:100]}...")
                print(f"元数据: {doc.metadata}")
                print("-" * 40)
