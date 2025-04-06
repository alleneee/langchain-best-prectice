"""
文档加载工具模块 - LangChain 0.3最佳实践
"""

from typing import List, Optional
import os
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredFileLoader,
    DirectoryLoader,
)
from langchain_core.documents import Document


class DocumentProcessor:
    """文档处理类，支持多种格式文档的加载与处理"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        初始化文档处理器
        
        参数:
            chunk_size: 分块大小
            chunk_overlap: 分块重叠大小
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
    
    def load_single_document(self, file_path: str) -> List[Document]:
        """
        加载单个文档文件
        
        参数:
            file_path: 文件路径
            
        返回:
            Document对象列表
        """
        # 获取文件扩展名并转为小写
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext == ".pdf":
                loader = PyPDFLoader(file_path)
            elif ext == ".txt":
                loader = TextLoader(file_path, encoding="utf-8")
            else:
                # 对于其他类型的文件，尝试使用通用加载器
                loader = UnstructuredFileLoader(file_path)
            
            documents = loader.load()
            print(f"成功加载文档: {file_path}, 共{len(documents)}页/段")
            return documents
        except Exception as e:
            print(f"加载文档失败: {file_path}, 错误: {e}")
            return []
    
    def load_documents_from_directory(self, directory_path: str, 
                                     glob_pattern: Optional[str] = None) -> List[Document]:
        """
        从目录加载多个文档
        
        参数:
            directory_path: 目录路径
            glob_pattern: 文件匹配模式，如 "*.pdf", "*.txt"
            
        返回:
            Document对象列表
        """
        if not os.path.exists(directory_path):
            print(f"目录不存在: {directory_path}")
            return []
        
        if glob_pattern is None:
            # 默认加载多种常见文档类型
            loader = DirectoryLoader(
                directory_path,
                glob="**/*.*",
                recursive=True,
                use_multithreading=True,
                show_progress=True,
                loader_kwargs={"autodetect_encoding": True},
            )
        else:
            loader = DirectoryLoader(
                directory_path,
                glob=glob_pattern,
                recursive=True,
                use_multithreading=True,
                show_progress=True,
            )
        
        try:
            documents = loader.load()
            print(f"成功从目录加载文档: {directory_path}, 共{len(documents)}个文件")
            return documents
        except Exception as e:
            print(f"从目录加载文档失败: {directory_path}, 错误: {e}")
            return []
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        将文档分块
        
        参数:
            documents: 文档列表
            
        返回:
            分块后的文档列表
        """
        if not documents:
            return []
        
        try:
            split_docs = self.text_splitter.split_documents(documents)
            print(f"文档分块完成: 共{len(split_docs)}个块")
            return split_docs
        except Exception as e:
            print(f"文档分块失败: {e}")
            return documents  # 返回原始文档
    
    def process_documents(self, file_path_or_dir: str, 
                         glob_pattern: Optional[str] = None) -> List[Document]:
        """
        处理文档的主要方法，自动判断是单个文件还是目录
        
        参数:
            file_path_or_dir: 文件路径或目录路径
            glob_pattern: 目录模式匹配
            
        返回:
            处理后的文档块列表
        """
        if os.path.isfile(file_path_or_dir):
            documents = self.load_single_document(file_path_or_dir)
        elif os.path.isdir(file_path_or_dir):
            documents = self.load_documents_from_directory(file_path_or_dir, glob_pattern)
        else:
            print(f"指定的路径既不是文件也不是目录: {file_path_or_dir}")
            return []
        
        # 分块处理
        return self.split_documents(documents)


# 使用示例
if __name__ == "__main__":
    processor = DocumentProcessor(chunk_size=1000, chunk_overlap=200)
    data_dir = Path(__file__).parent.parent / "data"
    docs = processor.process_documents(str(data_dir))
    print(f"处理完成，共得到 {len(docs)} 个文档块")
