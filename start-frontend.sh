#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== 启动Remix前端应用 ===${NC}"
echo -e "${BLUE}[状态]${NC} 检查前端依赖..."

# 检查Remix前端目录是否存在
if [ ! -d "web" ]; then
    echo -e "${RED}[错误]${NC} 找不到web目录"
    exit 1
fi

cd web

# 检查依赖是否已安装
if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}[状态]${NC} 安装前端依赖..."
    npm install
fi

# 启动开发服务器
echo -e "${BLUE}[状态]${NC} 启动Remix开发服务器..."
npm run dev

echo -e "${GREEN}[成功]${NC} 前端服务已启动，可访问 http://localhost:3000" 