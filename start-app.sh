#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 加载环境变量
source .env 2>/dev/null || echo -e "${BLUE}[提示]${NC} 没有找到.env文件，请确保您已正确配置环境变量"

# 显示欢迎信息
echo -e "${GREEN}===== RAG文档问答系统启动脚本 =====${NC}"
echo -e "此脚本将启动后端API和Remix前端界面"
echo -e "----------------------------------------"

# 检查Python是否已安装
if ! command -v python &> /dev/null; then
    echo -e "${RED}[错误]${NC} Python未安装。请安装Python 3.8或更高版本。"
    exit 1
fi

# 检查Node.js是否已安装
if ! command -v node &> /dev/null; then
    echo -e "${RED}[错误]${NC} Node.js未安装。请安装Node.js 18或更高版本。"
    exit 1
fi

# 检查虚拟环境并安装依赖
if [ ! -d ".venv" ]; then
    echo -e "${BLUE}[信息]${NC} 创建Python虚拟环境..."
    python -m venv .venv
fi

# 检查前端依赖
if [ ! -d "web/node_modules" ]; then
    echo -e "${BLUE}[信息]${NC} 安装前端依赖..."
    cd web && npm install
    cd ..
fi

# 激活虚拟环境并安装依赖
echo -e "${BLUE}[信息]${NC} 安装后端依赖..."
source .venv/bin/activate || source .venv/Scripts/activate
pip install -r requirements.txt

# 启动应用
echo -e "${GREEN}[成功]${NC} 依赖安装完成。启动应用中..."

# 处理Ctrl+C
trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null' INT

# 启动后端
uvicorn app.main:app --reload &
BACKEND_PID=$!

# 启动前端
cd web && npm run dev &
FRONTEND_PID=$!

# 等待任一进程结束
wait $BACKEND_PID $FRONTEND_PID
echo -e "${YELLOW}[警告]${NC} 应用已停止。"

# 清理进程
kill $BACKEND_PID 2>/dev/null
kill $FRONTEND_PID 2>/dev/null

# 退出虚拟环境
deactivate

echo -e "${GREEN}===== 服务已启动 =====${NC}"
echo -e "后端API服务: http://localhost:8000"
echo -e "前端界面: http://localhost:3000"
echo -e "按Ctrl+C停止所有服务"

# 保持脚本运行
wait 