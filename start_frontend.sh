#!/bin/bash
# RailFair 前端启动脚本（本地开发）
# 使用 Python 简单 HTTP 服务器

set -e

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🌐 启动 RailFair 前端服务器...${NC}"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 错误: 未找到 python3${NC}"
    exit 1
fi

# 进入前端目录
cd frontend/railfair

# 检查文件
if [ ! -f "index.html" ]; then
    echo -e "${RED}❌ 错误: 找不到 index.html${NC}"
    exit 1
fi

# 启动服务器
PORT=${PORT:-3000}
echo -e "${GREEN}✅ 前端服务器启动在 http://localhost:${PORT}${NC}"
echo -e "${YELLOW}⚠️  确保后端API运行在 http://localhost:8000${NC}"
echo ""
echo -e "${YELLOW}按 Ctrl+C 停止服务器${NC}"
echo ""

# 启动Python HTTP服务器
python3 -m http.server ${PORT}

