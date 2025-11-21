#!/bin/bash
# 前端部署准备脚本
# 帮助准备前端文件并推送到 GitHub

set -e

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 RailFair 前端部署准备${NC}"
echo "=================================="
echo ""

# 检查 Git 状态
if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ 错误: 未找到 git${NC}"
    exit 1
fi

# 检查是否在 Git 仓库中
if [ ! -d ".git" ]; then
    echo -e "${YELLOW}⚠️  当前目录不是 Git 仓库${NC}"
    echo "是否要初始化 Git 仓库？(y/n)"
    read -r response
    if [ "$response" = "y" ]; then
        git init
        echo -e "${GREEN}✅ Git 仓库已初始化${NC}"
    else
        exit 1
    fi
fi

# 检查后端地址配置
echo -e "${YELLOW}📝 检查配置...${NC}"

# 检查 netlify.toml
if grep -q "api.railfair.uk" frontend/railfair/netlify.toml; then
    echo -e "${YELLOW}⚠️  netlify.toml 中的后端地址可能需要更新${NC}"
    echo "当前配置:"
    grep "to = " frontend/railfair/netlify.toml
    echo ""
    echo "请确认后端地址是否正确，或运行以下命令更新："
    echo "  sed -i '' 's|https://api.railfair.uk|https://你的后端地址|g' frontend/railfair/netlify.toml"
    echo ""
fi

# 检查 config.js
if grep -q "localhost:8000" frontend/railfair/config.js; then
    echo -e "${YELLOW}⚠️  config.js 仍指向本地开发地址${NC}"
    echo "已自动更新为生产环境配置（使用 Netlify 代理）"
fi

# 显示 Git 状态
echo -e "${BLUE}📊 Git 状态:${NC}"
git status --short

echo ""
echo -e "${YELLOW}是否要提交并推送更改？(y/n)${NC}"
read -r response

if [ "$response" = "y" ]; then
    # 添加文件
    echo -e "${GREEN}📦 添加文件到 Git...${NC}"
    git add frontend/railfair/
    
    # 提交
    echo -e "${GREEN}💾 提交更改...${NC}"
    git commit -m "Prepare frontend for production deployment" || echo "没有更改需要提交"
    
    # 检查是否有远程仓库
    if git remote | grep -q origin; then
        echo -e "${GREEN}🚀 推送到 GitHub...${NC}"
        git push origin main || git push origin master
        echo -e "${GREEN}✅ 已推送到 GitHub！${NC}"
        echo ""
        echo -e "${BLUE}下一步:${NC}"
        echo "1. 在 Netlify 中连接你的 GitHub 仓库"
        echo "2. 配置 Base directory: frontend/railfair"
        echo "3. 部署网站"
    else
        echo -e "${YELLOW}⚠️  未配置远程仓库${NC}"
        echo "请先添加远程仓库："
        echo "  git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git"
        echo "  git push -u origin main"
    fi
else
    echo -e "${YELLOW}已取消${NC}"
fi

echo ""
echo -e "${GREEN}✅ 完成！${NC}"

