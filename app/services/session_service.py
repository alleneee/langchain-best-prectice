"""
会话管理服务，用于存储和管理聊天历史
"""

import os
import json
import time
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.core.config import settings
from app.core.logging import logger
from app.schemas.document_qa import Message, ChatHistory


class SessionService:
    """会话管理服务，管理用户会话和聊天历史"""
    
    def __init__(self, sessions_dir: str = None):
        """
        初始化会话服务
        
        参数:
            sessions_dir: 会话存储目录
        """
        self.sessions_dir = sessions_dir or settings.SESSIONS_DIR
        self.sessions: Dict[str, Dict[str, Any]] = {}  # {session_id: {history, last_access}}
        
        # 确保会话目录存在
        os.makedirs(self.sessions_dir, exist_ok=True)
        
        # 加载现有会话
        self._load_existing_sessions()
        logger.info(f"会话服务初始化，已加载 {len(self.sessions)} 个会话")
    
    def _load_existing_sessions(self) -> None:
        """加载已存在的会话文件"""
        try:
            for filename in os.listdir(self.sessions_dir):
                if filename.endswith('.json'):
                    session_id = filename.replace('.json', '')
                    file_path = os.path.join(self.sessions_dir, filename)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            session_data = json.load(f)
                            
                        messages = []
                        for msg in session_data.get('messages', []):
                            if 'role' in msg and 'content' in msg:
                                messages.append(Message(role=msg['role'], content=msg['content']))
                        
                        self.sessions[session_id] = {
                            'history': ChatHistory(messages=messages),
                            'last_access': time.time(),
                            'created_at': session_data.get('created_at', 
                                                          datetime.now().isoformat())
                        }
                        logger.debug(f"加载会话: {session_id}, 消息数: {len(messages)}")
                    except Exception as e:
                        logger.error(f"加载会话 {session_id} 失败: {e}")
        except Exception as e:
            logger.error(f"加载会话目录失败: {e}")
    
    def create_session(self) -> str:
        """
        创建新的会话
        
        返回:
            新会话的ID
        """
        session_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()
        
        self.sessions[session_id] = {
            'history': ChatHistory(messages=[]),
            'last_access': time.time(),
            'created_at': created_at
        }
        
        # 保存到文件
        self._save_session(session_id)
        logger.info(f"创建新会话: {session_id}")
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话数据
        
        参数:
            session_id: 会话ID
            
        返回:
            会话数据字典，如果不存在则返回None
        """
        if session_id in self.sessions:
            # 更新最后访问时间
            self.sessions[session_id]['last_access'] = time.time()
            return self.sessions[session_id]
        return None
    
    def get_history(self, session_id: str) -> Optional[ChatHistory]:
        """
        获取会话历史
        
        参数:
            session_id: 会话ID
            
        返回:
            聊天历史对象，如果会话不存在则返回None
        """
        session = self.get_session(session_id)
        return session['history'] if session else None
    
    def update_history(self, session_id: str, history: ChatHistory) -> bool:
        """
        更新会话历史
        
        参数:
            session_id: 会话ID
            history: 新的聊天历史
            
        返回:
            更新是否成功
        """
        if session_id not in self.sessions:
            logger.warning(f"尝试更新不存在的会话: {session_id}")
            return False
        
        self.sessions[session_id]['history'] = history
        self.sessions[session_id]['last_access'] = time.time()
        
        # 保存到文件
        self._save_session(session_id)
        logger.debug(f"更新会话历史: {session_id}, 消息数: {len(history.messages)}")
        
        return True
    
    def add_message(self, session_id: str, message: Message) -> bool:
        """
        添加消息到会话
        
        参数:
            session_id: 会话ID
            message: 消息对象
            
        返回:
            添加是否成功
        """
        if session_id not in self.sessions:
            logger.warning(f"尝试添加消息到不存在的会话: {session_id}")
            return False
        
        self.sessions[session_id]['history'].messages.append(message)
        self.sessions[session_id]['last_access'] = time.time()
        
        # 保存到文件
        self._save_session(session_id)
        logger.debug(f"添加消息到会话: {session_id}, 角色: {message.role}")
        
        return True
    
    def delete_session(self, session_id: str) -> bool:
        """
        删除会话
        
        参数:
            session_id: 会话ID
            
        返回:
            删除是否成功
        """
        if session_id not in self.sessions:
            logger.warning(f"尝试删除不存在的会话: {session_id}")
            return False
        
        # 从内存中删除
        del self.sessions[session_id]
        
        # 删除文件
        file_path = os.path.join(self.sessions_dir, f"{session_id}.json")
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            logger.info(f"删除会话: {session_id}")
            return True
        except Exception as e:
            logger.error(f"删除会话文件失败: {e}")
            return False
    
    def clear_history(self, session_id: str) -> bool:
        """
        清空会话历史
        
        参数:
            session_id: 会话ID
            
        返回:
            清空是否成功
        """
        if session_id not in self.sessions:
            logger.warning(f"尝试清空不存在的会话: {session_id}")
            return False
        
        self.sessions[session_id]['history'] = ChatHistory(messages=[])
        self.sessions[session_id]['last_access'] = time.time()
        
        # 保存到文件
        self._save_session(session_id)
        logger.info(f"清空会话历史: {session_id}")
        
        return True
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        列出所有会话
        
        返回:
            会话信息列表
        """
        result = []
        for session_id, data in self.sessions.items():
            result.append({
                'session_id': session_id,
                'message_count': len(data['history'].messages),
                'last_access': datetime.fromtimestamp(data['last_access']).isoformat(),
                'created_at': data['created_at']
            })
        return result
    
    def _save_session(self, session_id: str) -> None:
        """
        保存会话到文件
        
        参数:
            session_id: 会话ID
        """
        if session_id not in self.sessions:
            return
        
        session_data = self.sessions[session_id]
        file_path = os.path.join(self.sessions_dir, f"{session_id}.json")
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'session_id': session_id,
                    'messages': [msg.model_dump() for msg in session_data['history'].messages],
                    'created_at': session_data.get('created_at', datetime.now().isoformat())
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存会话文件失败: {e}")
    
    def convert_to_langchain_messages(self, messages: List[Message]) -> List[Any]:
        """
        将内部消息格式转换为LangChain消息格式
        
        参数:
            messages: 内部消息列表
            
        返回:
            LangChain消息对象列表
        """
        lc_messages = []
        for msg in messages:
            if msg.role == 'user':
                lc_messages.append(HumanMessage(content=msg.content))
            elif msg.role == 'assistant':
                lc_messages.append(AIMessage(content=msg.content))
            elif msg.role == 'system':
                lc_messages.append(SystemMessage(content=msg.content))
        return lc_messages
    
    def convert_from_langchain_messages(self, lc_messages: List[Any]) -> List[Message]:
        """
        将LangChain消息格式转换为内部消息格式
        
        参数:
            lc_messages: LangChain消息列表
            
        返回:
            内部消息对象列表
        """
        messages = []
        for msg in lc_messages:
            if isinstance(msg, HumanMessage):
                messages.append(Message(role='user', content=msg.content))
            elif isinstance(msg, AIMessage):
                messages.append(Message(role='assistant', content=msg.content))
            elif isinstance(msg, SystemMessage):
                messages.append(Message(role='system', content=msg.content))
        return messages
    
    def create_chat_history(self) -> str:
        """
        创建新的聊天历史
        
        返回:
            新聊天历史的ID
        """
        return self.create_session()
        
    def get_chat_history(self, history_id: str) -> List[Any]:
        """
        获取聊天历史
        
        参数:
            history_id: 历史ID
            
        返回:
            LangChain消息对象列表，如果历史不存在则返回None
        """
        session = self.get_session(history_id)
        if not session:
            return None
        
        # 转换为LangChain消息格式
        return self.convert_to_langchain_messages(session['history'].messages)
    
    def save_chat_history(self, history_id: str, lc_messages: List[Any]) -> bool:
        """
        保存聊天历史
        
        参数:
            history_id: 历史ID
            lc_messages: LangChain消息列表
            
        返回:
            保存是否成功
        """
        if history_id not in self.sessions:
            # 创建新会话
            self.sessions[history_id] = {
                'history': ChatHistory(messages=[], history_id=history_id),
                'last_access': time.time(),
                'created_at': datetime.now().isoformat()
            }
        
        # 转换为内部消息格式
        messages = self.convert_from_langchain_messages(lc_messages)
        history = ChatHistory(messages=messages, history_id=history_id)
        
        # 更新会话
        self.sessions[history_id]['history'] = history
        self.sessions[history_id]['last_access'] = time.time()
        
        # 保存到文件
        self._save_session(history_id)
        logger.debug(f"保存聊天历史: {history_id}, 消息数: {len(messages)}")
        
        return True 