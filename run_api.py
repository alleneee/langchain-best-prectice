"""
直接启动API服务器
"""
import sys
import os

# 确保app模块可以被导入
sys.path.insert(0, os.path.abspath("."))

try:
    import uvicorn
    
    # 直接从api.py导入app对象
    from app.api import app
    
    if __name__ == "__main__":
        print("正在启动文档问答系统API服务器...")
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保已安装所有依赖: pip install -r requirements.txt")
except Exception as e:
    print(f"启动服务器时发生错误: {e}") 