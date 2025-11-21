#!/bin/bash

# RailFair GitHub 设置脚本
# 这个脚本会帮助你设置 Git 并推送到 GitHub

set -e

echo "🚀 RailFair GitHub 设置脚本"
echo "================================"
echo ""

# 检查是否在正确的目录
if [ ! -f "api/app.py" ]; then
    echo "❌ 错误: 请在项目根目录运行此脚本"
    exit 1
fi

# 检查 Git 是否已初始化
if [ ! -d ".git" ]; then
    echo "📦 初始化 Git 仓库..."
    git init
fi

# 检查是否有未提交的更改
if [ -n "$(git status --porcelain)" ]; then
    echo "📝 发现未提交的更改，正在添加..."
    git add .
    
    echo ""
    read -p "请输入提交信息 (默认: Initial commit): " commit_message
    commit_message=${commit_message:-"Initial commit: RailFair project"}
    
    git commit -m "$commit_message"
    echo "✅ 已提交更改"
else
    echo "✅ 没有未提交的更改"
fi

# 检查是否已设置远程仓库
if git remote | grep -q "origin"; then
    echo "✅ 已设置远程仓库: $(git remote get-url origin)"
    echo ""
    read -p "是否要推送到 GitHub? (y/n): " push_confirm
    if [ "$push_confirm" = "y" ] || [ "$push_confirm" = "Y" ]; then
        echo "📤 推送到 GitHub..."
        git push -u origin main || git push -u origin master
        echo "✅ 推送完成！"
    fi
else
    echo ""
    echo "📋 下一步："
    echo "1. 在 GitHub 上创建新仓库"
    echo "2. 复制仓库 URL（例如: https://github.com/username/repo.git）"
    echo "3. 运行以下命令："
    echo ""
    echo "   git remote add origin <你的仓库URL>"
    echo "   git branch -M main"
    echo "   git push -u origin main"
    echo ""
    read -p "如果你已经创建了仓库，请输入仓库 URL (或按 Enter 跳过): " repo_url
    
    if [ -n "$repo_url" ]; then
        git remote add origin "$repo_url"
        git branch -M main 2>/dev/null || git branch -M master
        echo "📤 推送到 GitHub..."
        git push -u origin main || git push -u origin master
        echo "✅ 推送完成！"
    fi
fi

echo ""
echo "🎉 设置完成！"
echo ""
echo "📚 下一步："
echo "1. 在 Netlify 中连接你的 GitHub 仓库"
echo "2. 配置 Base directory 为: frontend/railfair"
echo "3. 配置 Build command 留空"
echo "4. 配置 Publish directory 为: ."
echo ""
echo "详细说明请查看: GITHUB_DEPLOYMENT.md"

