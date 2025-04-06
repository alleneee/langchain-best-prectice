"""
文档加载和处理模块 - LangChain 0.3最佳实践
"""

import os
from typing import List, Optional, Dict, Any, Union
from pathlib import Path
import json
import tempfile

from langchain_core.documents import Document
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    MarkdownTextSplitter,
    Language,
)
from langchain_text_splitters.python import PythonCodeTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredFileLoader,
    CSVLoader,
    UnstructuredExcelLoader,
    UnstructuredMarkdownLoader,
    UnstructuredPowerPointLoader,
    UnstructuredHTMLLoader,
    JSONLoader,
    DirectoryLoader
)

# EPUB格式当前不支持
EPUB_SUPPORT = False

try:
    from langchain_community.document_loaders import PlaywrightURLLoader
    WEB_SUPPORT = True
except ImportError:
    WEB_SUPPORT = False

from app.core.config import settings
from app.core.logging import logger


class DocumentProcessor:
    """文档处理器，支持多种文档格式的加载和处理"""
    
    def __init__(self, 
                chunk_size: int = None, 
                chunk_overlap: int = None,
                add_metadata: bool = True):
        """
        初始化文档处理器
        
        参数:
            chunk_size: 文档分块大小，默认使用配置中的设置
            chunk_overlap: 分块重叠大小，默认使用配置中的设置
            add_metadata: 是否添加扩展元数据
        """
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.add_metadata = add_metadata
        logger.info(f"初始化文档处理器: 块大小={self.chunk_size}, 重叠={self.chunk_overlap}")
        
        # 默认文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
        )
        
        # 特定格式的分割器
        self.markdown_splitter = MarkdownTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        
        self.code_splitter = PythonCodeTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
    
    def load_and_split(self, file_path: Union[str, Path]) -> List[Document]:
        """
        加载并分割文档
        
        参数:
            file_path: 文档路径
            
        返回:
            分割后的文档列表
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)
            
        if not file_path.exists():
            logger.error(f"文件不存在: {file_path}")
            return []
        
        # 根据文件扩展名选择合适的加载器和分割器
        file_extension = file_path.suffix.lower()
        try:
            loader, splitter = self._get_loader_and_splitter(file_path, file_extension)
            
            if not loader:
                logger.error(f"不支持的文件类型: {file_extension}")
                return []
            
            # 加载文档
            documents = loader.load()
            logger.info(f"成功加载文档，原始文档数: {len(documents)}")
            
            # 分割文档
            chunks = splitter.split_documents(documents)
            logger.info(f"文档分割完成，生成的文档块数: {len(chunks)}")
            
            # 添加元数据
            self._add_metadata(chunks, file_path)
            
            return chunks
            
        except Exception as e:
            logger.error(f"加载文档时出错: {e}")
            return []
    
    def _get_loader_and_splitter(self, file_path: Path, file_extension: str):
        """获取匹配的加载器和分割器"""
        
        loader = None
        splitter = self.text_splitter
        
        if file_extension == '.pdf':
            logger.info(f"使用PDF加载器处理: {file_path}")
            loader = PyPDFLoader(str(file_path))
            
        elif file_extension == '.txt':
            logger.info(f"使用文本加载器处理: {file_path}")
            loader = TextLoader(str(file_path))
            
        elif file_extension in ['.docx', '.doc']:
            logger.info(f"使用非结构化加载器处理Word文档: {file_path}")
            loader = UnstructuredFileLoader(str(file_path), mode="elements")
            
        elif file_extension == '.md':
            logger.info(f"使用Markdown加载器处理: {file_path}")
            try:
                loader = UnstructuredMarkdownLoader(str(file_path))
                splitter = self.markdown_splitter
            except ImportError as e:
                logger.warning(f"Markdown加载器初始化失败 ({e})，尝试使用文本加载器作为备选")
                loader = TextLoader(str(file_path))
                splitter = self.text_splitter
            
        elif file_extension == '.csv':
            logger.info(f"使用CSV加载器处理: {file_path}")
            loader = CSVLoader(str(file_path))
            
        elif file_extension in ['.xlsx', '.xls']:
            logger.info(f"使用Excel加载器处理: {file_path}")
            loader = UnstructuredExcelLoader(str(file_path))
            
        elif file_extension in ['.pptx', '.ppt']:
            logger.info(f"使用PowerPoint加载器处理: {file_path}")
            loader = UnstructuredPowerPointLoader(str(file_path))
            
        elif file_extension == '.json':
            logger.info(f"使用JSON加载器处理: {file_path}")
            try:
                loader = JSONLoader(
                    str(file_path),
                    jq_schema='.[]',
                    content_key='content'
                )
            except Exception as e:
                logger.warning(f"JSON加载器初始化失败，尝试使用通用加载器: {e}")
                loader = UnstructuredFileLoader(str(file_path))
            
        elif file_extension == '.html':
            logger.info(f"使用HTML加载器处理: {file_path}")
            loader = UnstructuredHTMLLoader(str(file_path))
            
        elif file_extension == '.epub' and EPUB_SUPPORT:
            logger.info(f"使用EPUB加载器处理: {file_path}")
            # EPUB当前不支持，使用通用加载器
            loader = UnstructuredFileLoader(str(file_path))
            
        elif file_extension in ['.py', '.js', '.java', '.c', '.cpp', '.cs', '.go', '.rb']:
            logger.info(f"使用代码加载器处理: {file_path}")
            loader = TextLoader(str(file_path))
            splitter = self.code_splitter
            
        else:
            # 如果没有匹配的加载器，尝试使用通用加载器
            logger.warning(f"未知文件类型 {file_extension}，尝试使用通用加载器")
            try:
                loader = UnstructuredFileLoader(str(file_path), mode="elements")
            except Exception as e:
                logger.error(f"通用加载器失败: {e}")
                # 回退到简单的文本加载器
                try:
                    loader = TextLoader(str(file_path))
                except:
                    loader = None
        
        return loader, splitter
    
    def _add_metadata(self, chunks: List[Document], file_path: Path):
        """为文档块添加元数据"""
        file_name = file_path.name
        file_type = file_path.suffix.lower()[1:]  # 去掉开头的'.'
        file_size = file_path.stat().st_size
        
        for i, chunk in enumerate(chunks):
            # 保留原有元数据
            metadata = chunk.metadata or {}
            
            # 添加基本元数据
            if 'source' not in metadata:
                metadata['source'] = str(file_name)
                
            # 添加扩展元数据
            if self.add_metadata:
                metadata.update({
                    'file_type': file_type,
                    'file_size': file_size,
                    'chunk_index': i,
                    'total_chunks': len(chunks)
                })
            
            # 更新文档元数据
            chunk.metadata = metadata
    
    def load_directory(self, directory_path: Union[str, Path]) -> List[Document]:
        """
        加载目录中的所有支持文档
        
        参数:
            directory_path: 目录路径
            
        返回:
            分割后的文档列表
        """
        if isinstance(directory_path, str):
            directory_path = Path(directory_path)
            
        if not directory_path.exists() or not directory_path.is_dir():
            logger.error(f"目录不存在或不是目录: {directory_path}")
            return []
        
        # 支持的文件扩展名
        supported_extensions = [
            '.pdf', '.txt', '.docx', '.doc', '.csv', 
            '.xlsx', '.xls', '.md', '.pptx', '.ppt', 
            '.json', '.html'
        ]
        
        if EPUB_SUPPORT:
            supported_extensions.append('.epub')
        
        # 尝试使用DirectoryLoader
        try:
            # 注意：DirectoryLoader在某些环境下可能有问题，使用try-except保障
            loader = DirectoryLoader(
                str(directory_path),
                glob="**/*.*",
                show_progress=True,
                use_multithreading=True,
                loader_cls=UnstructuredFileLoader
            )
            documents = loader.load()
            logger.info(f"使用DirectoryLoader加载目录，文档数: {len(documents)}")
            
            # 分割文档
            chunks = self.text_splitter.split_documents(documents)
            logger.info(f"目录文档分割完成，生成的文档块数: {len(chunks)}")
            
            return chunks
        except Exception as e:
            logger.warning(f"使用DirectoryLoader加载目录失败，回退到逐文件处理: {e}")
        
        # 回退方案: 逐文件处理
        all_documents = []
        for file_path in directory_path.glob("**/*.*"):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                logger.info(f"处理目录中的文件: {file_path}")
                try:
                    chunks = self.load_and_split(file_path)
                    all_documents.extend(chunks)
                except Exception as e:
                    logger.error(f"处理文件 {file_path} 时出错: {e}")
        
        logger.info(f"目录处理完成，总共加载了 {len(all_documents)} 个文档块")
        return all_documents
        
    def load_web_page(self, url: str) -> List[Document]:
        """
        加载网页内容
        
        参数:
            url: 网页URL
            
        返回:
            分割后的文档列表
        """
        if not WEB_SUPPORT:
            logger.error("未安装Playwright，无法加载网页")
            # 创建一个简单的文档作为替代
            doc = Document(
                page_content=f"无法加载网页 {url}，因为未安装Playwright",
                metadata={"source": url, "title": "加载失败"}
            )
            return [doc]
        
        try:
            loader = PlaywrightURLLoader([url])
            documents = loader.load()
            logger.info(f"成功加载网页: {url}")
            
            # 分割文档
            chunks = self.text_splitter.split_documents(documents)
            logger.info(f"网页分割完成，生成的文档块数: {len(chunks)}")
            
            # 添加元数据
            for chunk in chunks:
                if 'source' not in chunk.metadata:
                    chunk.metadata['source'] = url
            
            return chunks
        except Exception as e:
            logger.error(f"加载网页时出错: {e}")
            # 创建一个简单的文档作为替代
            doc = Document(
                page_content=f"加载网页 {url} 时出错: {str(e)}",
                metadata={"source": url, "title": "加载错误", "error": str(e)}
            )
            return [doc] 