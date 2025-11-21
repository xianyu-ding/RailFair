# 🚀 前端部署到生产环境 - 完整指南

## 📋 快速开始

### 方式 1: 使用部署脚本（最简单）

```bash
./deploy_frontend.sh
```

脚本会：
- 检查配置
- 提示更新后端地址
- 提交并推送到 GitHub

### 方式 2: 手动部署

按照 `DEPLOY_QUICK_START.md` 中的步骤操作。

---

## 🔧 配置后端地址

### 当前配置

根据 `wrangler.toml`，后端地址应该是：
- `https://api.railfair.uk` (如果已配置自定义域名)

或者：
- `https://railfair-api.your-subdomain.workers.dev` (如果使用 workers.dev 子域名)

### 更新配置

#### 如果后端在 `api.railfair.uk`

**无需修改**，`netlify.toml` 已配置正确。

#### 如果后端在 workers.dev

编辑 `frontend/railfair/netlify.toml`：

```toml
to = "https://railfair-api.your-subdomain.workers.dev/api/:splat"
```

---

## 📤 部署步骤

### 1. 确保代码已提交

```bash
git status
git add frontend/railfair/
git commit -m "Deploy frontend to production"
```

### 2. 推送到 GitHub

```bash
git push
```

### 3. 在 Netlify 中部署

#### 首次部署

1. 访问 [Netlify](https://app.netlify.com)
2. **Add new site** > **Import an existing project**
3. 选择 **GitHub**
4. 选择你的仓库
5. 配置：
   - **Base directory**: `frontend/railfair`
   - **Build command**: 留空
   - **Publish directory**: `.`
6. 点击 **Deploy site**

#### 后续更新

只需 `git push`，Netlify 会自动重新部署！

---

## ✅ 部署后检查

1. **网站可以访问**
   - 访问 Netlify 提供的地址
   - 应该能看到 RailFair 首页

2. **API 连接正常**
   - 执行一次查询
   - 检查浏览器控制台（F12）是否有错误
   - 检查 Network 标签页，API 请求应该成功

3. **功能正常**
   - 票价显示 `-`（不是 "Unavailable"）
   - 中间站台按钮可以点击
   - 查询返回正确结果

---

## 🔗 相关文档

- `DEPLOY_QUICK_START.md` - 5分钟快速部署
- `DEPLOY_FRONTEND.md` - 完整部署指南
- `GITHUB_DEPLOYMENT.md` - GitHub 集成说明

---

## 🎉 完成！

部署成功后，你的网站就可以在互联网上访问了！

每次更新只需 `git push`，Netlify 会自动部署。✨

