"""
文档问答系统的Gradio界面 - LangChain 0.3最佳实践
"""

import os
import json
import tempfile
import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

import gradio as gr
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage, AIMessage
from app.services.document_qa_service import DocumentQAService
from app.services.session_service import SessionService
from app.core.config import settings
from app.core.logging import logger
from app.schemas.document_qa import QuestionRequest


# 加载环境变量
load_dotenv()

# 初始化服务
document_qa_service = DocumentQAService()
session_service = SessionService()

# 当前会话ID
current_session_id = None
# 会话列表
sessions = {}

def init_session() -> str:
    """初始化新会话"""
    global current_session_id
    current_session_id = session_service.create_chat_history()
    session_name = f"会话 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
    sessions[current_session_id] = session_name
    return current_session_id

def handle_document_upload(file_obj, collection_name):
    """处理文档上传"""
    if not file_obj:
        return "请选择要上传的文件"
    
    try:
        # 保存上传的文件到临时目录
        file_extension = os.path.splitext(file_obj.name)[1]
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
        temp_file.write(file_obj.read())
        temp_file.close()
        
        # 处理文档
        logger.info(f"正在处理上传的文档: {file_obj.name}")
        result = document_qa_service.process_document(
            temp_file.name, collection_name=collection_name
        )
        
        if result["status"] == "error":
            return f"处理文档失败: {result['message']}"
            
        return f"文档'{file_obj.name}'处理成功，包含{result['document_count']}个文档块"
    except Exception as e:
        logger.error(f"处理上传文档时错误: {str(e)}")
        return f"处理文档时错误: {str(e)}"
    finally:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

def handle_question(
    question: str, 
    history: List[List[str]],
    model: str,
    temperature: float,
    use_web_search: bool,
    search_depth: str,
    include_domains: str,
    exclude_domains: str,
    max_results: int
) -> Tuple[List[List[str]], List[List[str]], str]:
    """处理用户问题"""
    global current_session_id
    
    # 确保会话已初始化
    if not current_session_id:
        current_session_id = init_session()
    
    # 如果问题为空，返回原历史
    if not question or question.strip() == "":
        return history, history, ""
    
    # 准备搜索设置
    search_settings = {
        "search_depth": search_depth,
        "max_results": max_results
    }
    
    # 处理包含/排除域名
    if include_domains and include_domains.strip():
        search_settings["include_domains"] = [d.strip() for d in include_domains.split(",") if d.strip()]
    
    if exclude_domains and exclude_domains.strip():
        search_settings["exclude_domains"] = [d.strip() for d in exclude_domains.split(",") if d.strip()]
    
    # 创建请求
    request = QuestionRequest(
        question=question,
        history_id=current_session_id,
        model=model,
        temperature=temperature,
        use_web_search=use_web_search,
        search_settings=search_settings
    )
    
    try:
        # 处理问题
        result = document_qa_service.process_question(request)
        
        # 更新历史ID(以防被重新创建)
        current_session_id = result["history_id"]
        
        # 格式化结果中的来源信息
        sources_text = ""
        
        # 处理本地文档来源
        if result.get("sources") and len(result["sources"]) > 0:
            sources_text += "📚 **本地文档来源:**\n"
            for i, source in enumerate(result["sources"], 1):
                sources_text += f"{i}. {source}\n"
        
        # 处理Web搜索来源
        if result.get("web_sources") and len(result["web_sources"]) > 0:
            if sources_text:
                sources_text += "\n"
            sources_text += "🌐 **网络搜索来源:**\n"
            for i, source in enumerate(result["web_sources"], 1):
                title = source.get("title", "未知标题")
                url = source.get("url", "#")
                sources_text += f"{i}. [{title}]({url})\n"
        
        # 如果没有来源，添加说明
        if not sources_text:
            if use_web_search:
                sources_text = "未找到相关信息来源"
            else:
                sources_text = "没有使用检索增强"
        
        # 更新对话历史
        new_history = history + [[question, result["answer"]]]
        
        return new_history, new_history, sources_text
    except Exception as e:
        logger.error(f"处理问题时出错: {str(e)}")
        error_message = f"处理问题时出错: {str(e)}"
        new_history = history + [[question, error_message]]
        return new_history, new_history, "处理出错，未找到来源"

def handle_new_chat():
    """创建新的聊天会话"""
    global current_session_id
    
    # 创建新会话
    init_session()
    
    # 返回空历史
    return [], [], f"已创建新会话: {sessions[current_session_id]}"

def get_system_status():
    """获取系统状态"""
    status = document_qa_service.get_system_status()
    
    # 格式化状态信息
    if status["status"] == "ready":
        status_text = "✅ 系统已就绪"
    else:
        status_text = "❌ 系统未就绪"
    
    status_text += "\n\n"
    
    if status["vector_store_ready"]:
        status_text += "📚 向量存储: 已就绪\n"
    else:
        status_text += "📚 向量存储: 未就绪 (请上传文档)\n"
    
    if status["web_search_enabled"]:
        status_text += "🌐 网络搜索: 已启用\n"
    else:
        status_text += "🌐 网络搜索: 未启用 (请在环境变量中设置TAVILY_API_KEY)\n"
    
    return status_text

def create_demo():
    """创建Gradio演示界面"""
    # 创建初始会话
    init_session()
    
    with gr.Blocks(title="文档问答系统", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 📚 文档问答系统 🤖")
        
        with gr.Row():
            with gr.Column(scale=3):
                with gr.Accordion("系统状态", open=True):
                    status_output = gr.Markdown(get_system_status())
                    status_refresh = gr.Button("刷新状态")
                
                with gr.Accordion("文档上传", open=True):
                    file_upload = gr.File(label="选择文档文件")
                    collection_name = gr.Textbox(
                        label="集合名称", 
                        value="document_collection",
                        info="用于组织向量索引的集合名称"
                    )
                    upload_button = gr.Button("上传并处理")
                    upload_output = gr.Textbox(label="上传结果")
                
                with gr.Accordion("搜索设置", open=False):
                    use_web_search = gr.Checkbox(
                        label="启用网络搜索", 
                        value=settings.ENABLE_WEB_SEARCH,
                        info="是否使用Tavily API进行网络搜索"
                    )
                    with gr.Column(visible=settings.ENABLE_WEB_SEARCH):
                        search_depth = gr.Radio(
                            label="搜索深度",
                            choices=["basic", "advanced"],
                            value="basic",
                            info="basic: 快速搜索; advanced: 深度搜索(更慢但更全面)"
                        )
                        max_results = gr.Slider(
                            label="最大结果数",
                            minimum=1,
                            maximum=10,
                            value=5,
                            step=1,
                            info="返回的最大搜索结果数量"
                        )
                        include_domains = gr.Textbox(
                            label="包含的域名",
                            placeholder="例如: wikipedia.org, github.com",
                            info="只搜索这些域名(用逗号分隔)"
                        )
                        exclude_domains = gr.Textbox(
                            label="排除的域名",
                            placeholder="例如: pinterest.com, instagram.com",
                            info="排除这些域名(用逗号分隔)"
                        )
            
            with gr.Column(scale=7):
                chatbot = gr.Chatbot(
                    label="对话",
                    height=500,
                    show_copy_button=True,
                    show_share_button=False,
                    avatar_images=("👤", "🤖")
                )
                with gr.Row():
                    with gr.Column(scale=8):
                        question_input = gr.Textbox(
                            label="输入问题",
                            placeholder="请输入您的问题...",
                            lines=3
                        )
                    with gr.Column(scale=1, min_width=100):
                        submit_button = gr.Button("提交")
                        clear_button = gr.Button("清空")
                        new_chat_button = gr.Button("新会话")
                
                with gr.Accordion("来源参考", open=True):
                    sources_output = gr.Markdown(label="信息来源")
                
                with gr.Accordion("模型设置", open=False):
                    with gr.Row():
                        model_selector = gr.Dropdown(
                            label="选择模型",
                            choices=["gpt-3.5-turbo", "gpt-4-turbo", "gpt-4o"],
                            value=settings.DEFAULT_MODEL,
                            info="用于回答问题的大语言模型"
                        )
                        temperature_slider = gr.Slider(
                            label="温度",
                            minimum=0.0,
                            maximum=1.0,
                            value=settings.DEFAULT_TEMPERATURE,
                            step=0.1,
                            info="控制回答的随机性(值越高，回答越多样)"
                        )
        
        # 设置事件处理函数
        question_input.submit(
            handle_question,
            inputs=[question_input, chatbot, model_selector, temperature_slider, 
                    use_web_search, search_depth, include_domains, exclude_domains, max_results],
            outputs=[chatbot, chatbot, sources_output],
            queue=True
        )
        
        submit_button.click(
            handle_question,
            inputs=[question_input, chatbot, model_selector, temperature_slider, 
                    use_web_search, search_depth, include_domains, exclude_domains, max_results],
            outputs=[chatbot, chatbot, sources_output],
            queue=True
        )
        
        clear_button.click(
            lambda: ([], [], ""),
            outputs=[chatbot, chatbot, sources_output],
            queue=False
        )
        
        new_chat_button.click(
            handle_new_chat,
            outputs=[chatbot, chatbot, sources_output],
            queue=False
        )
        
        upload_button.click(
            handle_document_upload,
            inputs=[file_upload, collection_name],
            outputs=[upload_output],
            queue=True
        )
        
        status_refresh.click(
            lambda: get_system_status(),
            outputs=[status_output],
            queue=False
        )
        
        # 状态变更可见性
        use_web_search.change(
            lambda x: gr.update(visible=x),
            inputs=[use_web_search],
            outputs=[gr.Column.update(visible=True)]
        )
    
    return demo

# 启动应用
if __name__ == "__main__":
    demo = create_demo()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,
        debug=False,
        auth=None,
        favicon_path=None
    ) 