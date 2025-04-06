"""
文档问答系统后端API启动脚本

本脚本直接启动后端API服务。
支持正确的路由格式，包括：
- /api/question - 处理问题
- /api/upload - 上传文档
- /api/status - 获取系统状态
- /api/session - 会话管理
"""
import sys
import os
import uvicorn
import importlib.util

def main():
    print("正在启动文档问答系统API服务器...")
    
    # 切换到app目录确保相对导入正常工作
    os.chdir("app")
    
    try:
        # 动态导入api.py模块
        api_spec = importlib.util.spec_from_file_location("api", "api.py")
        api_module = importlib.util.module_from_spec(api_spec)
        api_spec.loader.exec_module(api_module)
        
        # 获取app实例
        app = api_module.app
        
        # 启动服务器
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            workers=1
        )
    except Exception as e:
        print(f"启动服务器时错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 