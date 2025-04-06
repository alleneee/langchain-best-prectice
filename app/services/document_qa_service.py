"""
文档问答服务 - LangChain 0.3最佳实践
"""

import os
from typing import List, Dict, Any, Optional, Tuple, Union, AsyncGenerator
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableBranch, RunnableLambda
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_community.tools.tavily_search import TavilySearchResults

from app.core.config import settings
from app.core.logging import logger
from app.utils.web_search import WebSearchManager
from app.utils.document_loader import DocumentProcessor
from app.services.session_service import SessionService
from app.schemas.document_qa import Message, ChatHistory, QuestionRequest


class DocumentQAService:
    """文档问答服务，提供问答功能 (RAG功能已移除)"""
    
    def __init__(self):
        """初始化文档问答服务"""
        self.document_processor = DocumentProcessor(
            chunk_size=settings.CHUNK_SIZE, 
            chunk_overlap=settings.CHUNK_OVERLAP
        )
        self.session_service = SessionService()
        self.web_search_manager = WebSearchManager()
        
        logger.info("文档问答服务初始化完成 (RAG功能已禁用)")
    
    def process_question(self, request: QuestionRequest) -> Dict[str, Any]:
        """
        处理用户问题 (不使用RAG)
        
        参数:
            request: 问题请求对象
            
        返回:
            处理结果，包含答案和更新后的聊天历史
        """
        try:
            question = request.question
            history_id = request.history_id
            model = request.model or settings.DEFAULT_MODEL  # 默认使用配置中的模型(gpt-4o)
            temperature = request.temperature or settings.DEFAULT_TEMPERATURE
            
            # 如果使用GPT-4o模型，默认启用web search
            use_web_search = True if model == "gpt-4o" else request.use_web_search
            search_settings = request.search_settings or {}
            
            logger.info(f"处理问题 (无RAG): {question[:50]}...")
            
            # 获取或创建会话历史
            if history_id:
                history = self.session_service.get_chat_history(history_id)
                if not history:
                    history_id = self.session_service.create_chat_history()
                    history = []
            else:
                history_id = self.session_service.create_chat_history()
                history = []
            
            # 添加新的用户消息
            history.append(HumanMessage(content=question))
            
            # 处理问题
            sources = []
            web_sources = None
            
            # 如果只启用了网络搜索，使用网络搜索
            if use_web_search and settings.ENABLE_WEB_SEARCH:
                logger.info("使用网络搜索处理问题")
                answer, web_sources = self._process_with_web_search(
                    question, history, model, temperature, search_settings
                )
            # 否则只使用LLM
            else:
                logger.info("仅使用LLM处理问题")
                answer = self._process_with_llm(
                    question, history, model, temperature
                )
            
            # 添加AI回复到历史
            history.append(AIMessage(content=answer))
            
            # 保存更新后的历史
            self.session_service.save_chat_history(history_id, history)
            
            return {
                "answer": answer,
                "sources": sources,
                "web_sources": web_sources,
                "history_id": history_id,
                "history": [msg.dict() for msg in history]
            }
        except Exception as e:
            logger.error(f"处理问题时出错: {str(e)}", exc_info=True)
            return {"error": f"处理问题时出错: {str(e)}"}
    
    def _process_with_web_search(
        self,
        question: str,
        chat_history: List[Any],
        model: str = "gpt-4o",
        temperature: float = 0.7,
        search_settings: Dict[str, Any] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """使用Web搜索来回答问题"""
        try:
            # 格式化聊天历史 (辅助函数)
            def format_chat_history(history):
                """将聊天历史格式化为字符串"""
                formatted_history = []
                for msg in history[:-1]: # Exclude the current question
                    if isinstance(msg, HumanMessage):
                        formatted_history.append(f"Human: {msg.content}")
                    elif isinstance(msg, AIMessage):
                        formatted_history.append(f"Assistant: {msg.content}")
                return "\n".join(formatted_history)

            formatted_history_str = format_chat_history(chat_history)

            # 执行Web搜索
            web_search_results = self.perform_web_search(question, search_settings)
            web_context = web_search_results.get("context", "")
            web_sources = web_search_results.get("sources", [])
            
            # 准备语言模型
            llm = ChatOpenAI(model=model, temperature=temperature)
            
            # 构建提示
            prompt = ChatPromptTemplate.from_messages([
                ("system", "你是一个智能助手。请根据以下信息和聊天历史回答用户的问题。如果信息不相关，请根据你的知识回答。请在回答结尾处列出来源链接 (如果有)。\n\n"
                           "相关信息:\n{context}\n\n聊天历史:\n{chat_history}"),
                ("human", "{question}")
            ])
            
            # 构建链
            chain = RunnablePassthrough.assign(
                chat_history=RunnableLambda(lambda x: formatted_history_str),
                context=RunnableLambda(lambda x: web_context)
            ) | prompt | llm | StrOutputParser()
            
            # 调用链
            answer = chain.invoke({"question": question})
            
            return answer, web_sources
        except Exception as e:
            logger.error(f"使用Web搜索处理问题时出错: {str(e)}", exc_info=True)
            return f"处理问题时遇到错误: {e}", []
    
    def _process_with_llm(
        self,
        question: str,
        chat_history: List[Any],
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7
    ) -> str:
        """直接使用LLM回答问题"""
        try:
            # 格式化聊天历史
            def format_chat_history(history):
                """将聊天历史格式化为字符串"""
                formatted_history = []
                for msg in history[:-1]: # Exclude the current question
                    if isinstance(msg, HumanMessage):
                        formatted_history.append(f"Human: {msg.content}")
                    elif isinstance(msg, AIMessage):
                        formatted_history.append(f"Assistant: {msg.content}")
                return "\n".join(formatted_history)

            formatted_history_str = format_chat_history(chat_history)
            
            # 准备语言模型
            llm = ChatOpenAI(model=model, temperature=temperature)
            
            # 构建提示
            prompt = ChatPromptTemplate.from_messages([
                ("system", "你是一个智能助手。请根据聊天历史回答用户的问题。\n\n聊天历史:\n{chat_history}"),
                ("human", "{question}")
            ])
            
            # 构建链
            chain = RunnablePassthrough.assign(
                chat_history=RunnableLambda(lambda x: formatted_history_str)
            ) | prompt | llm | StrOutputParser()
            
            # 调用链
            answer = chain.invoke({"question": question})
            
            return answer
        except Exception as e:
            logger.error(f"使用LLM处理问题时出错: {str(e)}", exc_info=True)
            return f"处理问题时遇到错误: {e}"

    def perform_web_search(self, query: str, search_settings: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行Web搜索并返回结果和来源"""
        search_settings = search_settings or {}
        num_results = search_settings.get("num_results", 3) # Default to 3 results
        
        if settings.ENABLE_WEB_SEARCH and settings.TAVILY_API_KEY:
            try:
                logger.info(f"执行Tavily Web搜索: {query[:50]}... (max_results={num_results})")
                search_tool = TavilySearchResults(max_results=num_results)
                results = search_tool.invoke(query)
                
                context = "\n".join([res["content"] for res in results])
                sources = [{"title": res.get("title", "未知标题"), "url": res.get("url", "未知链接")} for res in results]
                
                logger.info(f"Tavily搜索完成，找到{len(sources)}个来源")
                return {"context": context, "sources": sources}
            except Exception as e:
                logger.error(f"Tavily Web搜索失败: {str(e)}", exc_info=True)
                return {"context": "Web搜索失败。", "sources": []}
        else:
            logger.warning("Web搜索未启用或未配置API密钥")
            return {"context": "Web搜索未启用。", "sources": []}

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态信息 (移除了向量存储状态)"""
        web_search_enabled = settings.ENABLE_WEB_SEARCH and bool(settings.TAVILY_API_KEY)
        
        return {
            "web_search_enabled": web_search_enabled,
            "llm_model": settings.DEFAULT_MODEL,
            "langchain_project": settings.LANGCHAIN_PROJECT,
            "upload_dir": str(settings.UPLOAD_DIR),
            "chunk_size": settings.CHUNK_SIZE,
            "chunk_overlap": settings.CHUNK_OVERLAP
        }

    async def process_question_stream(self, request: QuestionRequest) -> AsyncGenerator[Tuple[str, Optional[Dict[str, Any]]], None]:
        """
        处理用户问题并流式返回答案 (不使用RAG)
        
        返回:
            一个异步生成器，产生 (chunk, metadata) 元组
            chunk: 答案的文本块
            metadata: 在最后一个块中包含来源信息 (如果适用)
        """
        try:
            question = request.question
            history_id = request.history_id
            model = request.model or settings.DEFAULT_MODEL
            temperature = request.temperature or settings.DEFAULT_TEMPERATURE
            use_web_search = True if model == "gpt-4o" else request.use_web_search
            search_settings = request.search_settings or {}

            # 使用自定义分块参数创建处理器或使用默认处理器
            document_processor = self.document_processor
            if chunk_size or chunk_overlap:
                document_processor = DocumentProcessor(
                    chunk_size=chunk_size or settings.CHUNK_SIZE,
                    chunk_overlap=chunk_overlap or settings.CHUNK_OVERLAP
                )
            
            # 加载和分割文档
            documents = document_processor.load_and_split(file_path)
            
            if not documents:
                logger.warning(f"文档处理失败或为空: {file_path}")
                return {"status": "error", "message": "文档处理失败或为空"}
            
            # 创建或更新向量索引
            self.vector_store_manager.create_milvus_index(
                documents, collection_name=collection_name
            )
            
            return {
                "status": "success", 
                "message": "文档处理成功", 
                "document_count": len(documents)
            }
        except Exception as e:
            logger.error(f"处理文档时出错: {str(e)}")
            return {"status": "error", "message": f"处理文档时出错: {str(e)}"}
    
    def process_directory(
        self, 
        directory_path: str, 
        collection_name: str = "document_collection", 
        recursive: bool = True
    ) -> Dict[str, Any]:
        """
        处理目录中的所有文档并创建向量索引
        
        参数:
            directory_path: 目录路径
            collection_name: 集合名称
            recursive: 是否递归处理子目录
            
        返回:
            处理结果
        """
        try:
            logger.info(f"处理目录: {directory_path}")
            
            # 加载并分割目录中的所有文档
            documents = self.document_processor.load_directory(directory_path)
            
            if not documents:
                logger.warning(f"目录处理失败或为空: {directory_path}")
                return {"status": "error", "message": "目录处理失败或没有找到支持的文档"}
            
            # 统计处理的文件数量
            # 通过元数据中的source字段统计不重复的文件数
            processed_files = set()
            for doc in documents:
                if 'source' in doc.metadata:
                    processed_files.add(doc.metadata['source'])
            
            file_count = len(processed_files)
            
            # 创建或更新向量索引
            self.vector_store_manager.create_milvus_index(
                documents, collection_name=collection_name
            )
            
            return {
                "status": "success", 
                "message": f"目录处理成功，处理了{file_count}个文件", 
                "document_count": len(documents),
                "file_count": file_count
            }
        except Exception as e:
            logger.error(f"处理目录时出错: {str(e)}")
            return {"status": "error", "message": f"处理目录时出错: {str(e)}"}
    
    def process_web_page(
        self,
        url: str,
        collection_name: str = "document_collection"
    ) -> Dict[str, Any]:
        """
        处理网页内容并创建向量索引
        
        参数:
            url: 网页URL
            collection_name: 集合名称
            
        返回:
            处理结果
        """
        try:
            logger.info(f"处理网页: {url}")
            
            # 加载并分割网页内容
            documents = self.document_processor.load_web_page(url)
            
            if not documents:
                logger.warning(f"网页处理失败或为空: {url}")
                return {"status": "error", "message": "网页处理失败或为空"}
            
            # 创建或更新向量索引
            self.vector_store_manager.create_milvus_index(
                documents, collection_name=collection_name
            )
            
            return {
                "status": "success", 
                "message": "网页处理成功", 
                "document_count": len(documents)
            }
        except Exception as e:
            logger.error(f"处理网页时出错: {str(e)}")
            return {"status": "error", "message": f"处理网页时出错: {str(e)}"}
    
    def process_question(self, request: QuestionRequest) -> Dict[str, Any]:
        """
        处理用户问题
        
        参数:
            request: 问题请求对象
            
        返回:
            处理结果，包含答案、来源和更新后的聊天历史
        """
        try:
            question = request.question
            history_id = request.history_id
            model = request.model or settings.DEFAULT_MODEL  # 默认使用配置中的模型(gpt-4o)
            temperature = request.temperature or settings.DEFAULT_TEMPERATURE
            
            # 如果使用GPT-4o模型，默认启用web search
            use_web_search = True if model == "gpt-4o" else request.use_web_search
            search_settings = request.search_settings or {}
            
            logger.info(f"处理问题: {question[:50]}...")
            
            # 获取或创建会话历史
            if history_id:
                history = self.session_service.get_chat_history(history_id)
                if not history:
                    history_id = self.session_service.create_chat_history()
                    history = []
            else:
                history_id = self.session_service.create_chat_history()
                history = []
            
            # 添加新的用户消息
            history.append(HumanMessage(content=question))
            
            # 处理问题
            sources = []
            web_sources = None
            
            # 如果同时启用了向量检索和网络搜索，使用混合检索
            if use_web_search and settings.ENABLE_WEB_SEARCH and self.vector_store_manager.vector_store:
                answer, sources, web_sources = self._process_with_hybrid_retrieval(
                    question, history, model, temperature, search_settings
                )
            # 如果只启用了网络搜索，使用网络搜索
            elif use_web_search and settings.ENABLE_WEB_SEARCH:
                answer, web_sources = self._process_with_web_search(
                    question, history, model, temperature, search_settings
                )
            # 如果向量存储已就绪，使用RAG
            elif self.vector_store_manager.vector_store:
                answer, sources = self._process_with_rag(
                    question, history, model, temperature
                )
            # 否则只使用LLM
            else:
                answer = self._process_with_llm(
                    question, history, model, temperature
                )
            
            # 添加AI回复到历史
            history.append(AIMessage(content=answer))
            
            # 保存更新后的历史
            self.session_service.save_chat_history(history_id, history)
            
            # 格式化历史以便于前端显示
            formatted_history = [
                {"role": "user" if isinstance(msg, HumanMessage) else "assistant", 
                 "content": msg.content}
                for msg in history
            ]
            
            result = {
                "answer": answer,
                "sources": sources,
                "history": formatted_history,
                "history_id": history_id
            }
            
            # 如果有网络搜索结果，添加到响应中
            if web_sources:
                result["web_sources"] = web_sources
                
            return result
        except Exception as e:
            logger.error(f"处理问题时出错: {str(e)}")
            return {
                "answer": f"处理您的问题时出错: {str(e)}",
                "sources": [],
                "history": [],
                "history_id": history_id or self.session_service.create_chat_history()
            }
    
    def _process_with_rag(
        self, 
        question: str, 
        chat_history: List[Any], 
        model: str = "gpt-3.5-turbo", 
        temperature: float = 0.7
    ) -> Tuple[str, List[str]]:
        """
        使用RAG处理问题
        
        参数:
            question: 用户问题
            chat_history: 聊天历史
            model: 使用的模型
            temperature: 模型温度参数
            
        返回:
            (回答, 来源列表)
        """
        # 检索相关文档
        retrieved_docs = self.vector_store_manager.similarity_search(question, k=4)
        
        # 提取文档内容
        source_docs = []
        doc_contents = []
        for doc in retrieved_docs:
            content = doc.page_content
            source = doc.metadata.get("source", "未知来源")
            doc_contents.append(content)
            if source not in source_docs:
                source_docs.append(source)
        
        # 设置上下文
        context = "\n\n".join(doc_contents)
        
        # 创建LLM
        llm = ChatOpenAI(model=model, temperature=temperature)
        
        # RAG提示模板
        TEMPLATE = """你是一个专业的助手，请回答用户的问题。
        
我已经为你提供了一些相关文档内容作为参考，你可以在回答问题时使用这些文档中的信息作为补充，但不必局限于这些内容。
如果文档中没有足够的信息，请使用你自己的知识提供全面准确的回答。
如果文档内容与问题相关，请优先参考这些内容，但你可以自由补充额外的信息使回答更加完整。
如果文档内容与问题无关，请直接使用你自己的知识回答问题。

相关文档内容:
{context}

聊天历史:
{chat_history}

问题: {question}

回答:"""
        
        # 创建提示
        prompt = PromptTemplate.from_template(TEMPLATE)
        
        # 格式化历史
        def format_chat_history(history):
            formatted = []
            for msg in history:
                role = "用户" if isinstance(msg, HumanMessage) else "助手"
                formatted.append(f"{role}: {msg.content}")
            return "\n".join(formatted)
        
        # 创建链
        chain = (
            {"context": RunnablePassthrough(), 
             "question": lambda _: question,
             "chat_history": lambda _: format_chat_history(chat_history[:-1])}
            | prompt
            | llm
            | StrOutputParser()
        )
        
        # 执行链
        answer = chain.invoke(context)
        
        return answer, source_docs
    
    def _process_with_web_search(
        self,
        question: str,
        chat_history: List[Any],
        model: str = "gpt-4o",
        temperature: float = 0.7,
        search_settings: Dict[str, Any] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        使用Web搜索处理问题
        
        参数:
            question: 用户问题
            chat_history: 聊天历史
            model: 使用的模型
            temperature: 模型温度参数
            search_settings: 搜索设置
            
        返回:
            (回答, 网络来源)
        """
        # 如果使用GPT-4o且启用了OpenAI Web Search
        if model == "gpt-4o" and settings.ENABLE_OPENAI_WEB_SEARCH:
            try:
                # 创建带有网络搜索工具的LLM
                llm = ChatOpenAI(model=model, temperature=temperature)
                web_search_tool = {"type": "web_search_preview"}
                llm_with_tools = llm.bind_tools([web_search_tool])
                
                # 格式化历史
                def format_chat_history(history):
                    formatted = []
                    for msg in history[:-1]:  # 不包含最新的问题
                        if isinstance(msg, HumanMessage):
                            formatted.append({"role": "user", "content": msg.content})
                        elif isinstance(msg, AIMessage):
                            formatted.append({"role": "assistant", "content": msg.content})
                        elif isinstance(msg, SystemMessage):
                            formatted.append({"role": "system", "content": msg.content})
                    return formatted
                
                formatted_history = format_chat_history(chat_history)
                
                logger.info(f"使用GPT-4o内置Web Search处理问题: {question[:50]}...")
                
                # 创建系统消息
                system_message = """你是一个专业的助手，能够利用网络搜索工具获取最新信息，并结合自身知识回答问题。

对于需要最新信息、具体数据或事实的问题，请优先使用网络搜索工具查找相关信息。
对于不需要最新信息或搜索结果不足的情况，请结合你自己的知识提供全面准确的回答。
你可以自由搭配使用搜索结果和自身知识，以提供最有帮助的回答。
请引用你使用的信息来源，特别是对于最新事件、统计数据或特定事实的情况。
如果搜索没有找到相关信息，或者你的知识更适合回答问题，请直接使用你的知识。"""
                
                messages = [SystemMessage(content=system_message)]
                messages.extend(formatted_history)
                messages.append(HumanMessage(content=question))
                
                # 调用LLM
                response = llm_with_tools.invoke(messages)
                
                # 从响应中提取来源信息
                answer = response.content
                web_sources = []
                
                # 提取tool_calls中的引用信息
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    for tool_call in response.tool_calls:
                        if tool_call.get('type') == 'web_search_preview':
                            for block in tool_call.get('search_results', []):
                                source = {
                                    "url": block.get('link', ''),
                                    "title": block.get('title', ''),
                                    "content": block.get('snippet', '')
                                }
                                web_sources.append(source)
                
                return answer, web_sources
                
            except Exception as e:
                logger.error(f"使用GPT-4o Web Search时出错: {str(e)}")
                # 发生错误时回退到Tavily搜索
        
        # 设置搜索参数
        search_settings = search_settings or {}
        search_depth = search_settings.get("search_depth", "basic")
        max_results = search_settings.get("max_results", 5)
        include_domains = search_settings.get("include_domains")
        exclude_domains = search_settings.get("exclude_domains")
        
        # 执行Web搜索
        docs = self.web_search_manager.web_search(
            question,
            search_depth=search_depth,
            max_results=max_results,
            include_domains=include_domains,
            exclude_domains=exclude_domains
        )
        
        # 如果没有搜索结果，直接使用LLM
        if not docs:
            answer = self._process_with_llm(question, chat_history, model, temperature)
            return answer, []
        
        # 提取文档内容和源信息
        web_sources = []
        doc_contents = []
        
        for doc in docs:
            content = doc.page_content
            source = {
                "url": doc.metadata.get("source", ""),
                "title": doc.metadata.get("title", "未知标题"),
                "content_preview": content[:200] + "..." if len(content) > 200 else content
            }
            doc_contents.append(content)
            web_sources.append(source)
        
        # 设置上下文
        context = "\n\n".join(doc_contents)
        
        # 创建LLM
        llm = ChatOpenAI(model=model, temperature=temperature)
        
        # Web搜索提示模板
        TEMPLATE = """你是一个专业的助手，请回答用户的问题。

我已经为你提供了一些网络搜索结果作为参考，你可以在回答问题时使用这些信息作为补充，但不必局限于这些内容。
如果搜索结果中没有足够的信息，请使用你自己的知识提供全面准确的回答。
如果搜索结果与问题相关，请优先参考这些内容，但你可以自由补充额外的信息使回答更加完整。
如果搜索结果与问题无关，请直接使用你自己的知识回答问题。
在适当的情况下，可以引用信息来源，特别是对于最新信息或特定数据。

网络搜索结果:
{context}

聊天历史:
{chat_history}

问题: {question}

回答:"""
        
        # 创建提示
        prompt = PromptTemplate.from_template(TEMPLATE)
        
        # 格式化历史
        def format_chat_history(history):
            formatted = []
            for msg in history:
                role = "用户" if isinstance(msg, HumanMessage) else "助手"
                formatted.append(f"{role}: {msg.content}")
            return "\n".join(formatted)
        
        # 创建链
        chain = (
            {"context": RunnablePassthrough(), 
             "question": lambda _: question,
             "chat_history": lambda _: format_chat_history(chat_history[:-1])}
            | prompt
            | llm
            | StrOutputParser()
        )
        
        # 执行链
        answer = chain.invoke(context)
        
        return answer, web_sources
    
    def _process_with_hybrid_retrieval(
        self,
        question: str,
        chat_history: List[Any],
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        search_settings: Dict[str, Any] = None
    ) -> Tuple[str, List[str], List[Dict[str, Any]]]:
        """
        使用混合检索(本地文档+网络搜索)处理问题
        
        参数:
            question: 用户问题
            chat_history: 聊天历史
            model: 使用的模型
            temperature: 模型温度参数
            search_settings: 搜索设置
            
        返回:
            (回答, 本地来源, 网络来源)
        """
        # 执行本地检索
        local_docs = self.vector_store_manager.similarity_search(question, k=3)
        
        # 提取本地文档内容和来源
        local_sources = []
        local_contents = []
        
        for doc in local_docs:
            content = doc.page_content
            source = doc.metadata.get("source", "未知来源")
            local_contents.append(content)
            if source not in local_sources:
                local_sources.append(source)
        
        # 执行Web搜索
        search_settings = search_settings or {}
        search_depth = search_settings.get("search_depth", "basic")
        max_results = search_settings.get("max_results", 3)  # 减少网络结果数量，因为我们有本地结果
        include_domains = search_settings.get("include_domains")
        exclude_domains = search_settings.get("exclude_domains")
        
        web_docs = self.web_search_manager.web_search(
            question,
            search_depth=search_depth,
            max_results=max_results,
            include_domains=include_domains,
            exclude_domains=exclude_domains
        )
        
        # 提取Web搜索内容和来源
        web_sources = []
        web_contents = []
        
        for doc in web_docs:
            content = doc.page_content
            source = {
                "url": doc.metadata.get("source", ""),
                "title": doc.metadata.get("title", "未知标题"),
                "content_preview": content[:200] + "..." if len(content) > 200 else content
            }
            web_contents.append(content)
            web_sources.append(source)
        
        # 合并内容，先放本地文档，再放网络搜索结果
        all_contents = local_contents + web_contents
        context = "\n\n".join(all_contents)
        
        # 创建LLM
        llm = ChatOpenAI(model=model, temperature=temperature)
        
        # 混合检索提示模板
        TEMPLATE = """你是一个专业的助手，请回答用户的问题。

我已经为你提供了一些相关信息作为参考，包括本地文档内容(前面部分)和网络搜索结果(后面部分)，你可以在回答问题时使用这些信息作为补充，但不必局限于这些内容。
如果提供的信息没有足够的细节，请使用你自己的知识提供全面准确的回答。
如果提供的信息与问题相关，请优先参考这些内容，但你可以自由补充额外的信息使回答更加完整。
如果提供的信息与问题无关，请直接使用你自己的知识回答问题。
在回答中，可以适当标明信息来源(本地文档或网络搜索)。

相关信息内容:
{context}

聊天历史:
{chat_history}

问题: {question}

回答:"""
        
        # 创建提示
        prompt = PromptTemplate.from_template(TEMPLATE)
        
        # 格式化历史
        def format_chat_history(history):
            formatted = []
            for msg in history:
                role = "用户" if isinstance(msg, HumanMessage) else "助手"
                formatted.append(f"{role}: {msg.content}")
            return "\n".join(formatted)
        
        # 创建链
        chain = (
            {"context": RunnablePassthrough(), 
             "question": lambda _: question,
             "chat_history": lambda _: format_chat_history(chat_history[:-1])}
            | prompt
            | llm
            | StrOutputParser()
        )
        
        # 执行链
        answer = chain.invoke(context)
        
        return answer, local_sources, web_sources
    
    def _process_with_llm(
        self,
        question: str,
        chat_history: List[Any],
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7
    ) -> str:
        """
        仅使用LLM处理问题，没有额外的上下文
        
        参数:
            question: 用户问题
            chat_history: 聊天历史
            model: 使用的模型
            temperature: 模型温度参数
            
        返回:
            回答
        """
        # 创建LLM
        llm = ChatOpenAI(model=model, temperature=temperature)
        
        # 创建消息列表
        messages = [
            SystemMessage(content="""你是一个专业的助手，请回答用户的问题。

利用你的知识库尽可能提供有帮助、准确和全面的回答。
你可以分析问题的不同方面，并提供相关的见解和信息。
如果用户的问题不明确，你可以要求澄清或提供基于你理解的最佳回答。
如果你对某个问题不确定，请坦诚地表明，不要编造信息。""")
        ]
        
        # 添加聊天历史
        if chat_history and len(chat_history) > 1:
            # 添加前面的历史记录，但不包括当前的用户问题
            messages.extend(chat_history[:-1])
        
        # 添加当前问题
        messages.append(HumanMessage(content=question))
        
        # 获取回答
        response = llm.invoke(messages)
        
        return response.content
    
    def perform_web_search(self, query: str, search_settings: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        执行独立的Web搜索，不生成回答
        
        参数:
            query: 搜索查询
            search_settings: 搜索设置
            
        返回:
            搜索结果
        """
        try:
            # 设置搜索参数
            search_settings = search_settings or {}
            search_depth = search_settings.get("search_depth", "basic")
            max_results = search_settings.get("max_results", 5)
            include_domains = search_settings.get("include_domains")
            exclude_domains = search_settings.get("exclude_domains")
            
            # 执行搜索
            results = self.web_search_manager.search_with_metadata(
                query, 
                search_depth=search_depth,
                max_results=max_results,
                include_domains=include_domains,
                exclude_domains=exclude_domains
            )
            
            return {
                "results": results,
                "count": len(results),
                "query": query,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"执行Web搜索失败: {str(e)}")
            return {
                "results": [],
                "count": 0,
                "query": query,
                "status": "error",
                "error": str(e)
            }
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        获取系统状态
        
        返回:
            系统状态信息
        """
        status = {
            "status": "ready" if self.vector_store_manager.vector_store else "not_ready",
            "vector_store_ready": self.vector_store_manager.vector_store is not None,
            "document_count": None,  # 暂不实现文档计数
            "web_search_enabled": settings.ENABLE_WEB_SEARCH and settings.TAVILY_API_KEY is not None
        }
        
        return status

    async def process_question_stream(self, request: QuestionRequest) -> AsyncGenerator[Tuple[str, Optional[Dict[str, Any]]], None]:
        """
        流式处理问题
        
        参数:
            request: 问题请求对象
            
        返回:
            生成器，产生(文本块, 元数据)元组
        """
        try:
            question = request.question
            history_id = request.history_id
            temperature = request.temperature or settings.DEFAULT_TEMPERATURE
            
            logger.info(f"流式处理问题: {question[:50]}...")
            
            # 获取或创建会话历史
            if history_id:
                history = self.session_service.get_chat_history(history_id)
                if not history:
                    history_id = self.session_service.create_chat_history()
                    history = []
            else:
                history_id = self.session_service.create_chat_history()
                history = []
            
            # 添加用户问题到历史
            history.append(HumanMessage(content=question))
            
            # 检索相关上下文
            context = ""
            sources = []
            web_sources = []
            
            # 从向量存储中检索
            if self.vector_store_manager.vector_store:
                logger.debug("从向量存储中检索相关文档")
                retrieved_docs = self.vector_store_manager.search(question, top_k=5)
                
                for doc in retrieved_docs:
                    context += f"{doc.page_content}\n\n"
                    if hasattr(doc, 'metadata') and 'source' in doc.metadata:
                        source = doc.metadata['source']
                        if source not in sources:
                            sources.append(source)
            
            # 网络搜索
            if request.use_web_search and settings.ENABLE_WEB_SEARCH:
                logger.debug("执行网络搜索")
                web_results = self.search_service.search(question)
                
                for result in web_results:
                    if len(context) < 8000:  # 限制上下文长度
                        context += f"URL: {result['url']}\n标题: {result['title']}\n内容: {result['content']}\n\n"
                    
                    web_sources.append({
                        "url": result['url'],
                        "title": result['title'],
                        "content": result['content'][:200]  # 截取摘要
                    })
            
            # 构建系统提示
            if context:
                system_prompt = f"""你是一个问答助手。请根据以下参考信息回答用户的问题。

参考信息：
{context}

如果参考信息中没有相关内容，请使用你自己的知识回答，并说明这是基于你自己的知识。
回答要简洁、准确、有帮助，并基于提供的参考信息。"""
            else:
                system_prompt = """你是一个问答助手。请回答用户的问题。
回答要简洁、准确、有帮助。如果你不确定答案，请诚实地说明。"""
            
            # 创建流式模型
            streaming_llm = ChatOpenAI(
                model=request.model,
                temperature=temperature,
                streaming=True
            )
            
            # 准备消息列表
            messages = [SystemMessage(content=system_prompt)]
            messages.extend(history)
            
            # 用于收集完整回答
            full_response = ""
            
            # 执行流式生成
            async for chunk in streaming_llm.astream(messages):
                # LangChain的chunk对象是一个消息对象，需要从content属性获取内容
                if hasattr(chunk, 'content'):
                    text_chunk = chunk.content
                    if text_chunk:  # 确保不是空字符串
                        full_response += text_chunk
                        yield text_chunk, None
            
            # 更新会话历史
            history.append(AIMessage(content=full_response))
            self.session_service.save_chat_history(history_id, history)
            
            # 准备元数据
            metadata = {
                "end_of_response": True,
                "sources": sources,
                "web_sources": web_sources,
                "history_id": history_id
            }
            
            # 发送空块和元数据，表示流结束
            yield "", metadata
            
        except Exception as e:
            logger.exception(f"流式处理出错: {str(e)}")
            # 返回错误信息
            error_message = f"处理您的问题时出错: {str(e)}"
            metadata = {
                "end_of_response": True,
                "error": str(e)
            }
            yield error_message, metadata 