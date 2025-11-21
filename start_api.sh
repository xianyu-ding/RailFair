#!/bin/bash
# RailFair API 启动脚本
# 用于启动本地开发服务器

set -e

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 启动 RailFair API 服务器...${NC}"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 错误: 未找到 python3${NC}"
    exit 1
fi

# 检查数据库文件
DB_PATH="data/railfair.db"
if [ ! -f "$DB_PATH" ]; then
    echo -e "${YELLOW}⚠️  警告: 数据库文件不存在 ($DB_PATH)${NC}"
    echo -e "${YELLOW}   系统将尝试创建数据库，但可能需要先运行数据收集脚本${NC}"
fi

# 检查依赖
echo -e "${GREEN}📦 检查依赖...${NC}"
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  警告: 缺少依赖，正在安装...${NC}"
    pip3 install -r requirements.txt
fi

# 设置环境变量（如果需要）
export RAILFAIR_DB_PATH="${RAILFAIR_DB_PATH:-data/railfair.db}"

# 启动服务器
echo -e "${GREEN}✅ 启动服务器在 http://localhost:8000${NC}"
echo -e "${GREEN}📚 API 文档: http://localhost:8000/docs${NC}"
echo -e "${GREEN}🔍 健康检查: http://localhost:8000/health${NC}"
echo ""
echo -e "${YELLOW}按 Ctrl+C 停止服务器${NC}"
echo ""

# 运行API
python3 -m api.app

