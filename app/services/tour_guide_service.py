"""
导游Agent服务 - 基于LangGraph实现的导游服务
"""

import os
from typing import Dict, Any, List, Optional, Tuple, AsyncGenerator

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import Tool

# 条件导入MCPToolClient
try:
    from langchain_mcp_adapters import MCPToolClient
    AMAP_MCP_AVAILABLE = True
except ImportError:
    AMAP_MCP_AVAILABLE = False
    from app.core.logging import logger
    logger.warning("langchain_mcp_adapters模块未安装，高德地图MCP功能将不可用")

from app.core.config import settings
from app.core.logging import logger
from app.services.session_service import SessionService
from app.schemas.document_qa import QuestionRequest


# 定义导游Agent的状态类型
class TourGuideState(dict):
    """导游Agent的状态"""
    messages: List[Any]  # 消息历史
    context: Optional[Dict[str, Any]] = None  # 可选上下文信息


class TourGuideService:
    """导游Agent服务，提供旅游指南和建议"""
    
    def __init__(self):
        """初始化导游Agent服务"""
        self.session_service = SessionService()
        
        # 初始化存储
        self.memory = MemorySaver()
        
        # 初始化工具
        self.tools = self._init_tools()
        
        # 初始化模型
        self.model = ChatOpenAI(model=settings.DEFAULT_MODEL)
        
        # 初始化Agent
        self.agent = self._init_agent()
        
        logger.info("导游Agent服务初始化完成")
    
    def _init_tools(self) -> List[Any]:
        """初始化Agent工具"""
        tools = []
        
        # 添加高德地图MCP工具
        self._add_amap_mcp_tools(tools)
        
        # 添加其他旅游相关工具
        # 创建一个简单的时区转换工具
        from langchain.tools import tool
        
        @tool
        def convert_timezone(date_time: str, source_timezone: str, target_timezone: str) -> str:
            """
            将指定日期时间从源时区转换为目标时区。
            
            参数:
                date_time: 格式为 'YYYY-MM-DD HH:MM:SS' 的日期时间
                source_timezone: 源时区，如 'UTC', 'Asia/Shanghai', 'America/New_York'
                target_timezone: 目标时区，如 'UTC', 'Asia/Shanghai', 'America/New_York'
            
            返回:
                目标时区的日期时间，格式为 'YYYY-MM-DD HH:MM:SS'
            """
            from datetime import datetime
            import pytz
            
            try:
                # 解析日期时间
                dt = datetime.strptime(date_time, '%Y-%m-%d %H:%M:%S')
                
                # 设置源时区
                source_tz = pytz.timezone(source_timezone)
                dt_with_tz = source_tz.localize(dt)
                
                # 转换到目标时区
                target_tz = pytz.timezone(target_timezone)
                converted_dt = dt_with_tz.astimezone(target_tz)
                
                return converted_dt.strftime('%Y-%m-%d %H:%M:%S')
            
            except Exception as e:
                return f"时区转换错误: {str(e)}"
        
        tools.append(convert_timezone)
        
        return tools
    
    def _add_amap_mcp_tools(self, tools: List[Any]) -> None:
        """添加高德地图MCP工具"""
        # 如果没有MCP适配器可用，则跳过
        if not AMAP_MCP_AVAILABLE:
            logger.warning("高德地图MCP功能未启用，需要安装langchain-mcp-adapters包")
            return
            
        try:
            # 高德地图API密钥 
            amap_key = settings.AMAP_API_KEY or os.environ.get("AMAP_API_KEY", "40f2aa8a68ed8aeefffc4f3dda204baf")
            
            if not amap_key:
                logger.warning("未配置高德地图API密钥，跳过MCP工具加载")
                return
                
            # 初始化MCP客户端，连接高德地图MCP服务
            logger.info(f"正在连接高德地图MCP服务...")
            mcp_client = MCPToolClient(
                url=f"https://mcp.amap.com/sse?key={amap_key}"
            )
            
            # 获取MCP工具
            logger.info("正在加载高德地图MCP工具...")
            mcp_tools = mcp_client.get_tools()
            
            # 转换为LangChain工具
            for tool in mcp_tools:
                langchain_tool = Tool(
                    name=tool.name,
                    description=tool.description,
                    func=tool.func
                )
                tools.append(langchain_tool)
            
            logger.info(f"成功加载高德地图MCP工具: {len(mcp_tools)}个")
        except Exception as e:
            logger.error(f"加载高德地图MCP工具失败: {str(e)}")
            logger.exception("详细错误信息:")
    
    def _init_agent(self) -> StateGraph:
        """初始化导游Agent"""
        # 设置系统提示
        system_message = """你是一位专业的旅游导游助手，可以提供全球各地的旅游建议和信息。
        
你擅长：
1. 推荐旅游目的地、景点和行程安排
2. 提供目的地的文化、历史背景知识
3. 分享当地美食、住宿和交通建议
4. 解答旅行常见问题和注意事项
5. 根据用户偏好（如预算、时间、兴趣）定制旅行建议
"""

        # 如果高德地图MCP可用，添加相关功能描述
        if AMAP_MCP_AVAILABLE:
            system_message += """
你将主要使用高德地图工具，而不是其他搜索工具。当用户提问时，优先使用高德地图工具获取信息。你可以：
- 搜索景点、酒店、餐厅等兴趣点
- 规划从A点到B点的最佳路线
- 获取公交路线和时间信息
- 查询城市天气信息
- 提供周边兴趣点推荐

每次回答中，清晰标明信息来源是"高德地图数据"，以便用户区分内容是来自高德MCP工具还是你自己的知识库。
"""

        system_message += """
请使用可用的工具获取最新信息。如果高德地图工具无法提供足够信息，再使用你自己的知识。
当你推荐景点或活动时，尽可能提供具体的细节信息和实用建议。
回答要友好、专业，就像一位热情的当地向导。"""
        
        # 创建ReAct Agent
        if self.tools:
            # 设置带有系统提示的模型
            llm_with_system = self.model.with_config(
                configurable={
                    "system": system_message
                }
            )
            
            # 使用工具创建Agent
            agent = create_react_agent(
                llm_with_system,
                self.tools
            )
            
            # 创建工作流
            workflow = StateGraph(TourGuideState)
            
            # 定义节点
            workflow.add_node("agent", agent)
            
            # 定义边
            workflow.add_edge("agent", END)
            
            # 设置入口
            workflow.set_entry_point("agent")
            
            # 编译工作流
            return workflow.compile()
        else:
            # 如果没有工具，直接使用聊天模型
            logger.warning("导游Agent没有工具可用，将使用简单对话模式")
            return None
    
    def process_question(self, request: QuestionRequest) -> Dict[str, Any]:
        """
        处理旅游相关问题
        
        参数:
            request: 问题请求对象
            
        返回:
            回答和相关信息
        """
        try:
            question = request.question
            history_id = request.history_id
            temperature = request.temperature or settings.DEFAULT_TEMPERATURE
            
            logger.info(f"处理导游问题: {question[:50]}...")
            
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
            
            # 用于跟踪工具使用情况
            used_tools = set()
            
            # 如果有可用的Agent
            if self.agent and self.tools:
                # 准备输入状态
                state = TourGuideState(
                    messages=history,
                    context={"thread_id": history_id}
                )
                
                # 执行Agent
                result = self.agent.invoke(state)
                
                # 提取回答
                messages = result["messages"]
                answer = messages[-1].content if messages else "抱歉，无法处理您的请求。"
                
                # 提取可能的来源
                sources = []
                web_sources = []
                amap_used = False
                
                # 从工具执行中提取来源信息
                for message in messages:
                    if hasattr(message, 'tool_calls') and message.tool_calls:
                        for tool_call in message.tool_calls:
                            # 记录使用的工具名称
                            tool_name = tool_call.get('name', '')
                            used_tools.add(tool_name)
                            
                            # 检测是否使用了高德MCP工具
                            if 'amap' in tool_name.lower() or 'map' in tool_name.lower():
                                amap_used = True
                            
                            # 处理检索工具的结果
                            if tool_call.get('name') == 'destination_search':
                                for doc in tool_call.get('documents', []):
                                    if 'source' in doc.get('metadata', {}):
                                        source = doc['metadata']['source']
                                        if source not in sources:
                                            sources.append(source)
                
                # 添加工具使用信息
                if amap_used:
                    if not answer.endswith(("。", ".", "!", "?", "！", "？")):
                        answer += "。"
                    answer += "\n\n[信息来源：高德地图数据]"
                
                if used_tools:
                    logger.info(f"使用了以下工具: {', '.join(used_tools)}")
            else:
                # 如果没有Agent，使用简单对话模式
                model = ChatOpenAI(model=settings.DEFAULT_MODEL, temperature=temperature)
                
                # 创建系统消息
                system_message = SystemMessage(content="""你是一位专业的旅游导游助手，可以提供全球各地的旅游建议和信息。
                请根据你的知识提供有趣、准确、有帮助的旅行建议。""")
                
                # 准备消息
                messages = [system_message]
                if len(history) > 1:
                    messages.extend(history[:-1])  # 添加历史对话，但不包括最新问题
                
                messages.append(HumanMessage(content=question))
                
                # 调用模型
                response = model.invoke(messages)
                answer = response.content
                sources = []
                web_sources = []
            
            # 添加回答到历史
            history.append(AIMessage(content=answer))
            
            # 保存更新的历史
            self.session_service.save_chat_history(history_id, history)
            
            # 格式化历史用于前端显示
            formatted_history = [
                {"role": "user" if isinstance(msg, HumanMessage) else "assistant", 
                 "content": msg.content}
                for msg in history
            ]
            
            # 构建结果
            result = {
                "answer": answer,
                "sources": sources,
                "history": formatted_history,
                "history_id": history_id,
                "tools_used": list(used_tools)  # 添加使用的工具列表
            }
            
            # 如果有网络搜索结果，添加到响应
            if web_sources:
                result["web_sources"] = web_sources
                
            return result
            
        except Exception as e:
            logger.error(f"导游Agent处理问题时出错: {str(e)}")
            return {
                "answer": f"处理您的旅游问题时出错: {str(e)}",
                "sources": [],
                "history": [],
                "history_id": history_id or self.session_service.create_chat_history()
            } 

    async def process_question_stream(self, request: QuestionRequest) -> AsyncGenerator[Tuple[str, Optional[Dict[str, Any]]], None]:
        """
        流式处理旅游相关问题
        
        参数:
            request: 问题请求对象
            
        返回:
            生成器，产生(文本块, 元数据)元组
        """
        try:
            question = request.question
            history_id = request.history_id
            temperature = request.temperature or settings.DEFAULT_TEMPERATURE
            
            logger.info(f"流式处理导游问题: {question[:50]}...")
            
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
            
            # 创建流式模型
            streaming_llm = ChatOpenAI(
                model=request.model,
                temperature=temperature,
                streaming=True
            )
            
            # 准备系统提示
            system_prompt = """你是一位专业的旅游导游助手，可以提供全球各地的旅游建议和信息。
            
            你擅长：
            1. 推荐旅游目的地、景点和行程安排
            2. 提供目的地的文化、历史背景知识
            3. 分享当地美食、住宿和交通建议
            4. 解答旅行常见问题和注意事项
            5. 根据用户偏好（如预算、时间、兴趣）定制旅行建议
            
            请使用你的知识提供准确、有用的旅游信息。回答要友好、专业，就像一位热情的当地向导。"""
            
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
                "sources": [],  # 这里可以添加实际的来源
                "web_sources": [],  # 这里可以添加网络来源
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