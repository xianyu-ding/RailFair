# 🚀 GitHub + Netlify 自动部署指南

本指南将帮助你：
1. ✅ 将项目推送到 GitHub
2. ✅ 配置 Netlify 自动部署
3. ✅ 实现 push 到 GitHub 后 Netlify 自动更新

---

## 📋 步骤 1: 准备 Git 仓库

### 1.1 检查当前状态

项目已经初始化了 Git 仓库。现在需要添加文件并提交。

### 1.2 添加所有文件到 Git

```bash
# 在项目根目录执行
git add .
```

### 1.3 创建首次提交

```bash
git commit -m "Initial commit: RailFair project with frontend and backend"
```

---

## 📤 步骤 2: 创建 GitHub 仓库并推送

### 2.1 在 GitHub 上创建新仓库

1. 登录 [GitHub](https://github.com)
2. 点击右上角的 **+** > **New repository**
3. 填写仓库信息：
   - **Repository name**: `uk-rail-delay-predictor` (或你喜欢的名字)
   - **Description**: UK Rail Delay Predictor with Frontend and Backend
   - **Visibility**: 选择 Public 或 Private
   - ⚠️ **不要**勾选 "Initialize this repository with a README"（因为我们已经有了）
4. 点击 **Create repository**

### 2.2 连接本地仓库到 GitHub

GitHub 会显示一个页面，告诉你如何推送现有仓库。执行以下命令：

```bash
# 在项目根目录执行（替换 YOUR_USERNAME 和 YOUR_REPO_NAME）
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main
```

**示例**：
```bash
git remote add origin https://github.com/yourusername/uk-rail-delay-predictor.git
git branch -M main
git push -u origin main
```

### 2.3 验证推送成功

刷新 GitHub 页面，你应该能看到所有文件已经上传。

---

## 🌐 步骤 3: 配置 Netlify 自动部署

### 3.1 在 Netlify 中连接 GitHub

1. 登录 [Netlify](https://app.netlify.com)
2. 点击 **Add new site** > **Import an existing project**
3. 选择 **GitHub** 作为 Git 提供商
4. 授权 Netlify 访问你的 GitHub 账户（如果还没授权）
5. 选择你的仓库 `uk-rail-delay-predictor`

### 3.2 配置构建设置

在 Netlify 的部署设置页面，配置以下内容：

#### 基本设置

- **Base directory**: `frontend/railfair`
- **Build command**: 留空（静态网站，不需要构建）
- **Publish directory**: `.` (当前目录，即 `frontend/railfair`)

#### 环境变量（如果需要）

如果你的前端需要任何环境变量，可以在 **Environment variables** 部分添加。

### 3.3 配置 Netlify 代理

确保 `netlify.toml` 文件已经配置了后端代理：

```toml
[[redirects]]
  from = "/api/*"
  to = "https://你的Cloudflare后端地址.workers.dev/api/:splat"
  status = 200
  force = true
```

⚠️ **重要**：记得将 `你的Cloudflare后端地址` 替换为实际的后端地址！

### 3.4 部署

点击 **Deploy site**，Netlify 会：
1. 从 GitHub 拉取代码
2. 部署前端到 Netlify CDN
3. 配置代理规则

---

## ✅ 步骤 4: 测试自动部署

### 4.1 测试自动部署

1. 在本地修改一个文件（比如 `frontend/railfair/index.html` 中的标题）
2. 提交并推送：

```bash
git add .
git commit -m "Test auto-deployment"
git push
```

3. 在 Netlify Dashboard 中，你应该能看到：
   - 新的部署自动开始
   - 部署完成后，网站自动更新

### 4.2 验证网站更新

访问你的 Netlify 网站，确认更改已经生效。

---

## 🔄 后续工作流程

以后每次更新网站，只需要：

```bash
# 1. 修改文件
# 2. 提交更改
git add .
git commit -m "描述你的更改"
# 3. 推送到 GitHub
git push
```

Netlify 会自动检测到推送，并自动重新部署！🎉

---

## 📝 重要提示

### ⚠️ 不要提交敏感信息

确保以下文件不会被提交到 GitHub（已在 `.gitignore` 中）：
- `.env` - 包含 API 密钥和密码
- `*.db` - 数据库文件
- `data/raw/*` - 原始数据文件

### 🔐 环境变量管理

**前端（Netlify）**：
- 如果前端需要环境变量，在 Netlify Dashboard > Site settings > Environment variables 中添加
- 这些变量在构建时可用

**后端（Cloudflare）**：
- 在 Cloudflare Workers/Pages 的 Settings > Variables and Secrets 中配置
- 包括 `DATABASE_URL` 等敏感信息

### 🔗 更新后端地址

如果后端地址改变了，需要：

1. 更新 `frontend/railfair/netlify.toml` 中的后端地址
2. 提交并推送：

```bash
git add frontend/railfair/netlify.toml
git commit -m "Update backend API URL"
git push
```

3. Netlify 会自动重新部署

---

## 🐛 常见问题

### Q1: Netlify 部署失败

**检查**：
- Base directory 是否正确设置为 `frontend/railfair`
- Build command 是否留空（静态网站不需要构建）
- 查看 Netlify 部署日志获取详细错误信息

### Q2: 网站更新后看不到变化

**可能原因**：
- 浏览器缓存，尝试硬刷新（Ctrl+Shift+R 或 Cmd+Shift+R）
- Netlify 部署还在进行中，等待完成
- 检查 Netlify 部署日志确认是否成功

### Q3: API 代理不工作

**检查**：
- `netlify.toml` 中的后端地址是否正确
- 后端是否正常运行（访问 `/health` 端点）
- Netlify 部署日志中是否有重定向错误

### Q4: 如何回滚到之前的版本

在 Netlify Dashboard：
1. 进入 **Deploys** 标签
2. 找到之前的成功部署
3. 点击 **...** > **Publish deploy**

---

## 📚 相关文档

- [Netlify 文档](https://docs.netlify.com/)
- [GitHub 文档](https://docs.github.com/)
- [Netlify 重定向文档](https://docs.netlify.com/routing/redirects/)

---

## 🎉 完成！

现在你的工作流程是：
1. 本地修改代码
2. `git push` 到 GitHub
3. Netlify 自动部署 ✨

享受自动化的便利吧！🚀

