#!/bin/bash

# 定义颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查虚拟环境是否激活
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${BLUE}[状态]${NC} 激活Python虚拟环境..."
    source .venv/bin/activate
fi

# 启动后端API
echo -e "${GREEN}=== 启动后端API ===${NC}"
echo -e "${BLUE}[状态]${NC} 启动API服务器..."
cd app && python -c "from api import app; import uvicorn; uvicorn.run(app, host='0.0.0.0', port=8000)" &
API_PID=$!
cd ..

# 等待API服务器启动
echo -e "${BLUE}[状态]${NC} 等待API服务器启动..."
sleep 2

# 启动前端
echo -e "${GREEN}=== 启动前端应用 ===${NC}"
echo -e "${BLUE}[状态]${NC} 启动Remix开发服务器..."
cd web && npm run dev &
FRONTEND_PID=$!

# 清理函数
function cleanup {
    echo -e "\n${BLUE}[状态]${NC} 关闭服务..."
    kill $API_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

# 设置捕获CTRL+C信号
trap cleanup SIGINT

echo -e "${GREEN}=== 服务已启动 ===${NC}"
echo -e "后端API: http://localhost:8000"
echo -e "前端应用: http://localhost:3000"
echo -e "按 Ctrl+C 停止所有服务"

# 保持脚本运行
wait 