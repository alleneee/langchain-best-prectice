"""
会话管理服务，用于存储和管理聊天历史
"""

import os
import json
import time
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.core.config import settings
from app.core.logging import logger
from app.schemas.document_qa import Message, ChatHistory


class SessionService:
    """会话管理服务，管理用户会话和聊天历史"""
    
    def __init__(self, sessions_dir: Optional[Path] = None):
        """
        初始化会话服务
        
        参数:
            sessions_dir: 会话存储目录 (使用settings.DATA_DIR)
        """
        self.sessions_dir = sessions_dir or settings.DATA_DIR / "sessions"
        self.sessions: Dict[str, Dict[str, Any]] = {}  # {session_id: {history, last_access, created_at}}
        
        # 确保会话目录存在
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载现有会话
        self._load_existing_sessions()
        logger.info(f"会话服务初始化，会话目录: {self.sessions_dir}, 已加载 {len(self.sessions)} 个会话")
    
    def _load_existing_sessions(self) -> None:
        """加载已存在的会话文件"""
        try:
            for file_path in self.sessions_dir.glob("*.json"):
                session_id = file_path.stem
                try:
                    with file_path.open('r', encoding='utf-8') as f:
                        session_data = json.load(f)
                        
                    messages = []
                    for msg_data in session_data.get('messages', []):
                        if isinstance(msg_data, dict) and 'role' in msg_data and 'content' in msg_data:
                            messages.append(Message(role=msg_data['role'], content=msg_data['content']))
                        elif isinstance(msg_data, Message):
                            messages.append(msg_data)
                        
                    langchain_messages = []
                    for msg_data in session_data.get('langchain_messages', []):
                         if isinstance(msg_data, dict) and 'type' in msg_data and 'content' in msg_data:
                             if msg_data['type'] == 'human': langchain_messages.append(HumanMessage(content=msg_data['content']))
                             elif msg_data['type'] == 'ai': langchain_messages.append(AIMessage(content=msg_data['content']))
                             elif msg_data['type'] == 'system': langchain_messages.append(SystemMessage(content=msg_data['content']))
                    
                    final_messages_for_lc = langchain_messages if langchain_messages else self.convert_to_langchain_messages(messages)
                    
                    self.sessions[session_id] = {
                        'langchain_history': final_messages_for_lc,
                        'last_access': time.time(),
                        'created_at': session_data.get('created_at', datetime.now().isoformat())
                    }
                    logger.debug(f"加载会话: {session_id}, 消息数: {len(final_messages_for_lc)}")
                except Exception as e:
                    logger.error(f"加载会话 {session_id} ({file_path}) 失败: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"加载会话目录 {self.sessions_dir} 失败: {e}", exc_info=True)
    
    def create_session(self) -> str:
        """
        创建新的会话
        
        返回:
            新会话的ID
        """
        return self.create_chat_history()
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话数据
        
        参数:
            session_id: 会话ID
            
        返回:
            会话数据字典，如果不存在则返回None
        """
        if session_id in self.sessions:
            self.sessions[session_id]['last_access'] = time.time()
            return {
                 'history': self.convert_from_langchain_messages(self.sessions[session_id]['langchain_history']),
                 'last_access': self.sessions[session_id]['last_access'],
                 'created_at': self.sessions[session_id]['created_at']
            }
        return None
    
    def get_history(self, session_id: str) -> Optional[ChatHistory]:
        """
        获取会话历史
        
        参数:
            session_id: 会话ID
            
        返回:
            聊天历史对象，如果会话不存在则返回None
        """
        lc_history = self.get_chat_history(session_id)
        if lc_history is not None:
            return ChatHistory(messages=self.convert_from_langchain_messages(lc_history))
        return None
    
    def update_history(self, session_id: str, history: ChatHistory) -> bool:
        """
        更新会话历史
        
        参数:
            session_id: 会话ID
            history: 新的聊天历史
            
        返回:
            更新是否成功
        """
        lc_messages = self.convert_to_langchain_messages(history.messages)
        return self.save_chat_history(session_id, lc_messages)
    
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
        
        lc_message = self.convert_to_langchain_messages([message])[0]
        self.sessions[session_id]['langchain_history'].append(lc_message)
        self.sessions[session_id]['last_access'] = time.time()
        
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
        file_path = self.sessions_dir / f"{session_id}.json"
        try:
            if file_path.exists():
                file_path.unlink()
            logger.info(f"删除会话: {session_id}")
            return True
        except Exception as e:
            logger.error(f"删除会话文件 {file_path} 失败: {e}", exc_info=True)
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
        
        self.sessions[session_id]['langchain_history'] = []
        self.sessions[session_id]['last_access'] = time.time()
        
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
                'message_count': len(data.get('langchain_history', [])),
                'last_access': datetime.fromtimestamp(data['last_access']).isoformat(),
                'created_at': data['created_at']
            })
        result.sort(key=lambda x: x['last_access'], reverse=True)
        return result
    
    def get_session_count(self) -> int:
        """获取当前活动会话的数量"""
        return len(self.sessions)
    
    def _save_session(self, session_id: str) -> None:
        """
        保存单个会话到文件 (使用LangChain消息格式)
        
        参数:
            session_id: 会话ID
        """
        if session_id not in self.sessions:
            logger.warning(f"尝试保存不存在的会话 {session_id}，跳过")
            return
        
        session_data = self.sessions[session_id]
        file_path = self.sessions_dir / f"{session_id}.json"
        
        serializable_messages = []
        for msg in session_data.get('langchain_history', []):
            if isinstance(msg, HumanMessage): type_str = 'human'
            elif isinstance(msg, AIMessage): type_str = 'ai'
            elif isinstance(msg, SystemMessage): type_str = 'system'
            else: type_str = 'unknown'
            serializable_messages.append({'type': type_str, 'content': msg.content})
            
        save_data = {
            'langchain_messages': serializable_messages,
            'created_at': session_data.get('created_at', datetime.now().isoformat())
        }
        
        try:
            temp_file_path = file_path.with_suffix('.tmp')
            with temp_file_path.open('w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            os.replace(temp_file_path, file_path)
            
            logger.debug(f"保存会话到文件: {file_path}")
        except Exception as e:
            logger.error(f"保存会话 {session_id} 到 {file_path} 失败: {e}", exc_info=True)
            if temp_file_path.exists():
                try: temp_file_path.unlink()
                except OSError: pass
    
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
            if msg.role == 'user' or msg.role == 'human':
                lc_messages.append(HumanMessage(content=msg.content))
            elif msg.role == 'assistant' or msg.role == 'ai':
                lc_messages.append(AIMessage(content=msg.content))
            elif msg.role == 'system':
                lc_messages.append(SystemMessage(content=msg.content))
            else:
                logger.warning(f"未知消息角色 '{msg.role}'，跳过转换")
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
            else:
                try:
                    role = 'unknown'
                    if hasattr(msg, 'type'):
                        if msg.type == 'human': role = 'user'
                        elif msg.type == 'ai': role = 'assistant'
                        elif msg.type == 'system': role = 'system'
                    content = getattr(msg, 'content', str(msg))
                    messages.append(Message(role=role, content=content))
                except Exception as e:
                    logger.warning(f"无法转换未知类型的LangChain消息: {type(msg)}, 错误: {e}")
        return messages
    
    def create_chat_history(self) -> str:
        """
        创建新的聊天历史并返回其ID (用于LangChain)
        
        返回:
            新聊天历史的ID
        """
        history_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()
        self.sessions[history_id] = {
            'langchain_history': [],
            'last_access': time.time(),
            'created_at': created_at
        }
        self._save_session(history_id)
        logger.info(f"创建新的聊天历史 (LangChain): {history_id}")
        return history_id
    
    def get_chat_history(self, history_id: str) -> Optional[List[Any]]:
        """
        获取指定ID的LangChain聊天历史
        
        参数:
            history_id: 聊天历史ID (即 session_id)
            
        返回:
            LangChain消息列表 (HumanMessage, AIMessage等)，如果不存在则返回None
        """
        if history_id in self.sessions:
            self.sessions[history_id]['last_access'] = time.time()
            return list(self.sessions[history_id].get('langchain_history', []))
        
        file_path = self.sessions_dir / f"{history_id}.json"
        if file_path.exists():
             logger.warning(f"会话 {history_id} 不在内存中，但文件存在。尝试加载...")
             self._load_existing_sessions()
             if history_id in self.sessions:
                  return list(self.sessions[history_id].get('langchain_history', []))
             else:
                  logger.error(f"尝试加载 {history_id} 后仍然失败。")
                  return None
        else:
            logger.warning(f"找不到会话历史: {history_id}")
            return None
    
    def save_chat_history(self, history_id: str, lc_messages: List[Any]) -> bool:
        """
        保存或更新指定ID的LangChain聊天历史
        
        参数:
            history_id: 聊天历史ID (即 session_id)
            lc_messages: LangChain消息列表
            
        返回:
            保存是否成功
        """
        if history_id not in self.sessions:
            logger.warning(f"尝试保存到不存在的会话 {history_id}，将创建新会话。")
            created_at = datetime.now().isoformat()
            self.sessions[history_id] = {
                'langchain_history': [],
                'last_access': time.time(),
                'created_at': created_at
            }
        
        self.sessions[history_id]['langchain_history'] = lc_messages
        self.sessions[history_id]['last_access'] = time.time()
        self._save_session(history_id)
        logger.debug(f"保存聊天历史 (LangChain): {history_id}, 消息数: {len(lc_messages)}")
        return True 