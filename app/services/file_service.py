"""
文件服务 - 处理文件上传和管理
"""

import os
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path
from fastapi import UploadFile

from app.core.config import settings
from app.core.logging import logger

class FileService:
    """文件服务，处理文件上传和管理"""
    
    def __init__(self):
        """初始化文件服务"""
        self.upload_dir = settings.UPLOAD_DIR
        
        # 确保上传目录存在
        os.makedirs(self.upload_dir, exist_ok=True)
    
    async def save_upload_file(self, file: UploadFile) -> Dict[str, Any]:
        """
        保存上传的文件
        
        参数:
            file: 上传的文件
            
        返回:
            包含文件信息的字典
        """
        try:
            # 生成唯一文件名
            file_ext = os.path.splitext(file.filename)[1] if file.filename else ""
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = os.path.join(self.upload_dir, unique_filename)
            
            # 保存文件
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            
            # 返回文件信息
            return {
                "filename": file.filename,
                "content_type": file.content_type,
                "file_path": file_path,
                "file_size": len(content)
            }
        except Exception as e:
            logger.error(f"保存文件失败: {str(e)}")
            raise
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        获取文件信息
        
        参数:
            file_path: 文件路径
            
        返回:
            包含文件信息的字典
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            file_stat = os.stat(file_path)
            file_name = os.path.basename(file_path)
            
            return {
                "filename": file_name,
                "file_path": file_path,
                "file_size": file_stat.st_size,
                "created_at": file_stat.st_ctime,
                "modified_at": file_stat.st_mtime
            }
        except Exception as e:
            logger.error(f"获取文件信息失败: {str(e)}")
            raise
    
    def delete_file(self, file_path: str) -> bool:
        """
        删除文件
        
        参数:
            file_path: 文件路径
            
        返回:
            是否成功删除
        """
        try:
            if not os.path.exists(file_path):
                return False
                
            os.remove(file_path)
            return True
        except Exception as e:
            logger.error(f"删除文件失败: {str(e)}")
            return False
    
    def list_uploaded_files(self) -> List[Dict[str, Any]]:
        """
        列出所有上传的文件
        
        返回:
            文件信息列表
        """
        try:
            files = []
            for filename in os.listdir(self.upload_dir):
                file_path = os.path.join(self.upload_dir, filename)
                if os.path.isfile(file_path):
                    files.append(self.get_file_info(file_path))
            return files
        except Exception as e:
            logger.error(f"列出文件失败: {str(e)}")
            return [] 