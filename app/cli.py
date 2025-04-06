"""
文档问答系统的命令行界面
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Optional, Dict, Any
import uuid

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

from app.core.config import settings
from app.services.document_qa_service import DocumentQAService
from app.schemas.document_qa import QuestionRequest


def clear_screen():
    """清除屏幕"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """打印应用程序标题"""
    print("\n" + "=" * 60)
    print(f"  {settings.PROJECT_NAME} v{settings.PROJECT_VERSION}")
    print("=" * 60)


def print_help():
    """打印帮助信息"""
    print("\n命令:")
    print("  /help         - 显示帮助")
    print("  /load [路径]   - 加载文档")
    print("  /status       - 检查系统状态")
    print("  /new          - 新建会话")
    print("  /clear        - 清空当前会话")
    print("  /model [模型]  - 切换模型 (gpt-3.5-turbo, gpt-4, etc.)")
    print("  /temp [值]    - 设置温度 (0.0-1.0)")
    print("  /exit         - 退出程序")
    print("=" * 60)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="RAG文档问答系统命令行界面")
    parser.add_argument("--doc", "-d", type=str, help="要加载的文档路径")
    parser.add_argument("--model", "-m", type=str, default="gpt-3.5-turbo", help="使用的模型")
    parser.add_argument("--temp", "-t", type=float, default=0.7, help="模型温度参数")
    return parser.parse_args()


def main():
    """主函数"""
    # 加载环境变量
    load_dotenv()
    
    # 解析命令行参数
    args = parse_args()
    
    # 创建会话和服务
    document_qa_service = DocumentQAService()
    session_id = str(uuid.uuid4())
    model = args.model
    temperature = args.temp
    
    # 打印应用标题
    clear_screen()
    print_header()
    print("\n欢迎使用文档问答系统命令行界面!")
    print("输入 /help 查看可用命令")
    
    # 如果提供了文档，尝试加载
    if args.doc:
        doc_path = args.doc
        print(f"\n正在加载文档: {doc_path}")
        success = document_qa_service.process_document(doc_path)
        if success:
            print("文档加载成功! 您现在可以开始提问。")
        else:
            print("文档加载失败。请检查文件路径和格式是否正确。")
    
    # 检查系统状态
    status = document_qa_service.get_system_status()
    print(f"\n系统状态: {status['status']} - {status['message']}")
    print(f"当前模型: {model}")
    print(f"温度参数: {temperature}")
    print(f"会话ID: {session_id}")
    
    # 主循环
    print("\n请输入您的问题 (或输入命令):")
    while True:
        user_input = input("\n> ").strip()
        
        # 检查是否是命令
        if user_input.startswith("/"):
            command = user_input.split(" ")[0].lower()
            args = user_input[len(command):].strip()
            
            if command == "/exit":
                print("谢谢使用！再见！")
                sys.exit(0)
            elif command == "/help":
                print_help()
            elif command == "/status":
                status = document_qa_service.get_system_status()
                print(f"系统状态: {status['status']} - {status['message']}")
                print(f"当前模型: {model}")
                print(f"温度参数: {temperature}")
                print(f"会话ID: {session_id}")
            elif command == "/load":
                if not args:
                    print("错误: 请指定文档路径，例如 /load ./data/mydoc.pdf")
                    continue
                    
                doc_path = args
                print(f"正在加载文档: {doc_path}")
                success = document_qa_service.process_document(doc_path)
                if success:
                    print("文档加载成功! 您现在可以开始提问。")
                else:
                    print("文档加载失败。请检查文件路径和格式是否正确。")
            elif command == "/new":
                session_id = str(uuid.uuid4())
                print(f"已创建新会话 (ID: {session_id})")
            elif command == "/clear":
                print("已清空会话历史")
            elif command == "/model":
                if not args:
                    print(f"当前模型: {model}")
                    print("使用 /model [模型名称] 设置新模型")
                else:
                    model = args
                    print(f"模型已设置为: {model}")
            elif command == "/temp":
                if not args:
                    print(f"当前温度: {temperature}")
                    print("使用 /temp [值] 设置新温度 (0.0-1.0)")
                else:
                    try:
                        new_temp = float(args)
                        if 0 <= new_temp <= 1:
                            temperature = new_temp
                            print(f"温度已设置为: {temperature}")
                        else:
                            print("温度必须在0.0到1.0之间")
                    except ValueError:
                        print("无效的温度值")
            else:
                print(f"未知命令: {command}")
                print("输入 /help 查看可用命令")
        else:
            # 处理问题
            if not user_input:
                continue
                
            # 检查系统是否就绪
            if not document_qa_service.is_ready:
                print("系统未就绪。请先加载文档 (/load [路径])。")
                continue
            
            # 创建请求
            request = QuestionRequest(
                question=user_input,
                model=model,
                temperature=temperature,
                history_id=session_id
            )
            
            print("\n正在思考...\n")
            
            # 处理问题
            try:
                result = document_qa_service.process_question(request)
                answer = result["answer"]
                sources = result["sources"]
                
                # 打印回答
                print(f"{answer}\n")
                
                # 打印来源
                if sources:
                    print("来源文档:")
                    for i, source in enumerate(sources, 1):
                        print(f"  {i}. {source}")
                    print()
            except Exception as e:
                print(f"处理问题时出错: {e}")
    
    
if __name__ == "__main__":
    main() 