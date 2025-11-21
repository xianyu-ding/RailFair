# 🚀 前端部署到生产环境指南

## 📋 部署前准备

### 1. 确认后端地址

首先，你需要知道你的后端API地址。有两种情况：

#### 情况 A: 后端已部署到 Cloudflare Workers

你的后端地址可能是：
- `https://railfair-api.your-subdomain.workers.dev`
- `https://api.railfair.uk` (如果使用自定义域名)

#### 情况 B: 后端还在本地运行

如果后端还在本地，你需要先部署后端，或者暂时使用本地地址测试。

### 2. 更新配置文件

#### 方式 1: 使用 Netlify 代理（推荐）

这种方式可以避免 CORS 问题，因为浏览器认为 API 调用来自同一个域名。

**步骤**:

1. **更新 `frontend/railfair/netlify.toml`**:
   ```toml
   [[redirects]]
     from = "/api/*"
     to = "https://你的后端地址.workers.dev/api/:splat"  # ⬅️ 替换这里
     status = 200
     force = true
   ```

2. **保持 `frontend/railfair/config.js` 为空**:
   ```javascript
   const configuredBase = '';  // 留空，使用 Netlify 代理
   ```

#### 方式 2: 直接跨域调用

如果你不想使用代理，可以直接配置后端地址：

1. **更新 `frontend/railfair/config.js`**:
   ```javascript
   const configuredBase = 'https://你的后端地址.workers.dev';
   ```

2. **确保后端 CORS 配置正确**（后端已配置为允许所有来源）

---

## 🌐 部署到 Netlify

### 方法 1: 通过 GitHub 自动部署（推荐）

#### 步骤 1: 确保代码已推送到 GitHub

```bash
# 检查 Git 状态
git status

# 如果有未提交的更改
git add .
git commit -m "Prepare for production deployment"
git push
```

#### 步骤 2: 在 Netlify 中连接 GitHub

1. 登录 [Netlify](https://app.netlify.com)
2. 点击 **Add new site** > **Import an existing project**
3. 选择 **GitHub** 作为 Git 提供商
4. 授权 Netlify 访问你的 GitHub 账户（如果还没授权）
5. 选择你的仓库

#### 步骤 3: 配置构建设置

在 Netlify 的部署设置页面，配置以下内容：

- **Base directory**: `frontend/railfair`
- **Build command**: 留空（静态网站，不需要构建）
- **Publish directory**: `.` (当前目录，即 `frontend/railfair`)

#### 步骤 4: 配置环境变量（如果需要）

如果你的前端需要任何环境变量，可以在 **Environment variables** 部分添加。

#### 步骤 5: 部署

点击 **Deploy site**，Netlify 会：
1. 从 GitHub 拉取代码
2. 部署前端到 Netlify CDN
3. 配置代理规则（如果使用 `netlify.toml`）

### 方法 2: 手动拖放部署（快速测试）

1. 访问 [Netlify Drop](https://app.netlify.com/drop)
2. 将 `frontend/railfair` 文件夹拖放到页面
3. Netlify 会自动部署

**注意**: 这种方式不会自动更新，每次更新需要重新拖放。

---

## ✅ 部署后验证

### 1. 检查部署状态

在 Netlify Dashboard 中：
- 查看 **Deploys** 标签，确认部署成功
- 查看部署日志，确认没有错误

### 2. 测试网站

访问你的 Netlify 网站地址（例如：`https://your-site.netlify.app`）

### 3. 测试 API 连接

1. **打开浏览器开发者工具** (F12)
2. **查看 Network 标签页**
3. **在网站上执行一次查询**
4. **检查 API 请求**:
   - 请求是否成功（状态码 200）
   - 响应数据是否正确

### 4. 测试功能

- ✅ 票价显示是否正确（显示 `-` 而不是 "Unavailable"）
- ✅ 中间站台按钮是否可以点击
- ✅ 查询功能是否正常

---

## 🔧 更新后端地址

如果后端地址改变了，需要：

1. **更新配置文件**:
   - 如果使用 Netlify 代理：更新 `frontend/railfair/netlify.toml`
   - 如果直接调用：更新 `frontend/railfair/config.js`

2. **提交并推送**:
   ```bash
   git add frontend/railfair/netlify.toml  # 或 config.js
   git commit -m "Update backend API URL"
   git push
   ```

3. **Netlify 会自动重新部署**

---

## 🐛 常见问题

### Q1: 部署后网站无法访问 API

**检查**:
- `netlify.toml` 中的后端地址是否正确
- 后端是否正常运行（访问 `/health` 端点）
- Netlify 部署日志中是否有重定向错误
- 浏览器控制台是否有 CORS 错误

### Q2: 网站更新后看不到变化

**可能原因**:
- 浏览器缓存，尝试硬刷新（Ctrl+Shift+R 或 Cmd+Shift+R）
- Netlify 部署还在进行中，等待完成
- 检查 Netlify 部署日志确认是否成功

### Q3: API 代理返回 404

**检查**:
- 后端地址是否正确
- 后端路由是否正确（应该是 `/api/predict` 而不是 `/predict`）
- Netlify 代理配置是否正确

### Q4: 如何查看 Netlify 网站地址

在 Netlify Dashboard：
- 进入你的站点
- 在 **Site overview** 页面可以看到网站地址
- 格式通常是：`https://your-site-name.netlify.app`

---

## 📝 部署检查清单

部署前：
- [ ] 后端已部署并正常运行
- [ ] 知道后端地址
- [ ] 更新了 `netlify.toml` 或 `config.js`
- [ ] 代码已提交到 Git

部署后：
- [ ] Netlify 部署成功
- [ ] 网站可以正常访问
- [ ] API 请求成功
- [ ] 查询功能正常
- [ ] 票价显示正确（显示 `-`）
- [ ] 中间站台功能正常

---

## 🎉 完成！

部署成功后，你的网站就可以在互联网上访问了！

**后续更新**:
- 只需 `git push` 到 GitHub
- Netlify 会自动检测并重新部署

