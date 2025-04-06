"""
Agent Service - Implements LangGraph agent for document QA system
"""

import os
from typing import Dict, Any, List, Optional

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from app.core.config import settings
from app.core.logging import logger
from app.utils.vector_store import VectorStoreManager
from app.services.session_service import SessionService
from app.schemas.document_qa import QuestionRequest


class AgentService:
    """Agent service using LangGraph for enhanced document question answering"""
    
    def __init__(self):
        """Initialize the agent service"""
        self.session_service = SessionService()
        self.vector_store_manager = VectorStoreManager()
        self.memory = MemorySaver()
        
        # Initialize tools
        self.tools = self._init_tools()
        
        # Initialize model
        self.model = ChatAnthropic(model=settings.DEFAULT_MODEL)
        
        # Initialize the agent
        self.agent = self._init_agent()
        
        logger.info("Agent service initialized successfully")
    
    def _init_tools(self) -> List[Any]:
        """Initialize the tools for the agent"""
        tools = []
        
        # Add Tavily search tool if enabled
        if settings.ENABLE_WEB_SEARCH and settings.TAVILY_API_KEY:
            search_tool = TavilySearchResults(max_results=3)
            tools.append(search_tool)
        
        # Add vector store retriever tool if available
        if self.vector_store_manager.vector_store:
            retriever = self.vector_store_manager.vector_store.as_retriever(
                search_kwargs={"k": 3}
            )
            
            from langchain.tools.retriever import create_retriever_tool
            retriever_tool = create_retriever_tool(
                retriever,
                "document_search",
                "Search for information in the uploaded documents. For any questions about documents you've uploaded, you must use this tool."
            )
            tools.append(retriever_tool)
        
        return tools
    
    def _init_agent(self) -> Any:
        """Initialize the LangGraph agent"""
        # Customize system prompt
        system_message = """You are a helpful assistant that can answer questions based on the available tools. 
        If the question is about documents that have been uploaded, use the document_search tool.
        If the question requires real-time information or general knowledge, use the tavily_search_results_json tool.
        Always be helpful, accurate, and provide sources when available."""
        
        # Create the agent
        agent = create_react_agent(
            self.model,
            self.tools,
            prompt=system_message,
            checkpointer=self.memory
        )
        
        return agent
    
    def process_question(self, request: QuestionRequest) -> Dict[str, Any]:
        """
        Process a user's question using the agent
        
        Args:
            request: The question request object
        
        Returns:
            Dictionary containing the answer and other metadata
        """
        try:
            question = request.question
            history_id = request.history_id
            temperature = request.temperature or settings.DEFAULT_TEMPERATURE
            
            logger.info(f"Processing question with agent: {question[:50]}...")
            
            # Get or create a thread ID (session)
            thread_id = history_id or self.session_service.create_chat_history()
            
            # Prepare the input
            messages = [HumanMessage(content=question)]
            
            # Configure agent
            config = {
                "configurable": {"thread_id": thread_id},
                "recursion_limit": 10,  # Limit the number of steps
            }
            
            # Process the question
            response = self.agent.invoke(
                {"messages": messages},
                config
            )
            
            # Extract answer
            answer = response["messages"][-1].content
            
            # Format the response for the API
            formatted_response = {
                "answer": answer,
                "sources": [],  # Sources would need to be extracted from the tool usage
                "history_id": thread_id,
                "history": [{"role": "user", "content": question}, 
                           {"role": "assistant", "content": answer}]
            }
            
            return formatted_response
        
        except Exception as e:
            logger.error(f"Error processing question with agent: {str(e)}")
            return {
                "answer": f"Error processing your question: {str(e)}",
                "sources": [],
                "history": [],
                "history_id": history_id or self.session_service.create_chat_history()
            } 