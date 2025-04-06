"""
网络搜索工具模块 - 基于Tavily实现Web搜索功能
"""

import os
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from app.core.config import settings
from app.core.logging import logger

# 尝试导入Tavily，如果不可用则提供备用实现
TAVILY_AVAILABLE = False
try:
    from langchain_tavily import TavilySearchAPIRetriever
    TAVILY_AVAILABLE = True
    logger.info("Tavily搜索模块已加载")
except ImportError:
    logger.warning("Tavily模块未安装，将使用模拟搜索实现")
    # 创建一个模拟的Document类，用于兼容接口
    class MockDocument:
        def __init__(self, content, metadata=None):
            self.page_content = content
            self.metadata = metadata or {}


class WebSearchManager:
    """Web搜索管理类，使用Tavily实现网络搜索"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化Web搜索管理器
        
        参数:
            api_key: Tavily API密钥，默认从环境变量或配置获取
        """
        self.api_key = api_key or settings.TAVILY_API_KEY or os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            logger.warning("未设置Tavily API密钥，Web搜索功能将不可用")
        else:
            logger.info("初始化Web搜索管理器")
            # 确保设置了环境变量，因为TavilySearch会使用它
            os.environ["TAVILY_API_KEY"] = self.api_key
    
    def web_search(self, 
                  query: str, 
                  search_depth: str = "basic", 
                  max_results: int = 5,
                  include_domains: Optional[List[str]] = None,
                  exclude_domains: Optional[List[str]] = None,
                  ) -> List[Document]:
        """
        执行Web搜索并返回结果
        
        参数:
            query: 搜索查询
            search_depth: 搜索深度，可选 "basic" 或 "advanced"
            max_results: 最大结果数量
            include_domains: 限制搜索的域名列表
            exclude_domains: 排除搜索的域名列表
            
        返回:
            文档对象列表
        """
        if not TAVILY_AVAILABLE:
            logger.warning("Tavily模块未安装，无法执行实际Web搜索")
            # 返回模拟结果
            return [
                Document(
                    page_content="这是一个模拟的搜索结果，因为Tavily模块未安装。请使用pip install langchain_tavily安装该模块。",
                    metadata={"source": "模拟搜索", "title": "模拟搜索结果"}
                )
            ]
        
        if not self.api_key:
            logger.error("未设置Tavily API密钥，无法执行Web搜索")
            return []
        
        try:
            # 创建检索器参数
            retriever_kwargs = {
                "k": max_results,
                "search_depth": search_depth,
            }
            
            # 添加可选参数
            if include_domains:
                retriever_kwargs["include_domains"] = include_domains
            
            if exclude_domains:
                retriever_kwargs["exclude_domains"] = exclude_domains
            
            # 创建Tavily检索器并执行搜索
            logger.info(f"执行Web搜索，查询: {query}")
            retriever = TavilySearchAPIRetriever(**retriever_kwargs)
            docs = retriever.get_relevant_documents(query)
            
            logger.info(f"搜索成功，获取到 {len(docs)} 条结果")
            return docs
        except Exception as e:
            logger.error(f"Web搜索失败: {str(e)}")
            return []
    
    def search_with_metadata(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        执行Web搜索并返回带有完整元数据的结果
        
        参数:
            query: 搜索查询
            **kwargs: 传递给web_search方法的其它参数
            
        返回:
            完整结果列表，包含URL、标题、内容和元数据
        """
        docs = self.web_search(query, **kwargs)
        results = []
        
        for doc in docs:
            result = {
                "content": doc.page_content,
                "url": doc.metadata.get("source", ""),
                "title": doc.metadata.get("title", ""),
                "metadata": doc.metadata
            }
            results.append(result)
        
        return results


# 使用示例
if __name__ == "__main__":
    # 设置API密钥
    import dotenv
    dotenv.load_dotenv()
    
    # 创建管理器
    search_manager = WebSearchManager()
    
    # 执行搜索
    results = search_manager.web_search("What is LangChain?")
    
    # 打印结果
    print(f"找到 {len(results)} 个结果:")
    for i, doc in enumerate(results):
        print(f"结果 {i+1}:")
        print(f"内容: {doc.page_content[:150]}...")
        print(f"来源: {doc.metadata.get('source', '未知')}")
        print("-" * 50) 