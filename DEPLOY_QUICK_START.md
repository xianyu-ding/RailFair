# ⚡ 快速部署指南 - 5分钟上线

## 🎯 前提条件

1. ✅ 后端已部署（Cloudflare Workers 或其他）
2. ✅ 知道后端地址（例如：`https://railfair-api.workers.dev`）
3. ✅ 有 GitHub 账户
4. ✅ 有 Netlify 账户（免费注册：https://app.netlify.com）

---

## 📝 步骤 1: 更新后端地址（1分钟）

### 如果使用 Netlify 代理（推荐）

编辑 `frontend/railfair/netlify.toml`，更新第9行：

```toml
to = "https://你的后端地址.workers.dev/api/:splat"  # ⬅️ 替换这里
```

**示例**：
```toml
to = "https://railfair-api.your-subdomain.workers.dev/api/:splat"
```

### 如果直接调用后端

编辑 `frontend/railfair/config.js`，更新第23行：

```javascript
const configuredBase = 'https://你的后端地址.workers.dev';
```

---

## 📤 步骤 2: 推送到 GitHub（2分钟）

```bash
# 1. 检查更改
git status

# 2. 添加文件
git add frontend/railfair/

# 3. 提交
git commit -m "Deploy frontend to production"

# 4. 推送（如果还没设置远程仓库，先设置）
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

**或者使用部署脚本**：
```bash
./deploy_frontend.sh
```

---

## 🌐 步骤 3: 在 Netlify 中部署（2分钟）

### 3.1 连接 GitHub

1. 登录 [Netlify](https://app.netlify.com)
2. 点击 **Add new site** > **Import an existing project**
3. 选择 **GitHub**
4. 授权 Netlify 访问 GitHub（如果还没授权）
5. 选择你的仓库

### 3.2 配置构建设置

在部署设置页面：

- **Base directory**: `frontend/railfair`
- **Build command**: 留空
- **Publish directory**: `.`

### 3.3 部署

点击 **Deploy site**

---

## ✅ 步骤 4: 验证（1分钟）

1. **等待部署完成**（通常1-2分钟）
2. **访问你的网站**（Netlify 会提供一个地址，例如：`https://your-site.netlify.app`）
3. **测试功能**:
   - 查询一个路线
   - 检查票价显示（应该是 `-` 而不是 "Unavailable"）
   - 点击"查看中间站台"按钮

---

## 🔄 后续更新

以后每次更新，只需：

```bash
git add .
git commit -m "更新描述"
git push
```

Netlify 会自动检测并重新部署！✨

---

## 🐛 如果遇到问题

### 问题 1: 部署失败

**检查**:
- Base directory 是否正确：`frontend/railfair`
- Build command 是否留空
- 查看 Netlify 部署日志

### 问题 2: API 不工作

**检查**:
- `netlify.toml` 中的后端地址是否正确
- 后端是否正常运行
- 浏览器控制台是否有错误

### 问题 3: 网站地址在哪里？

在 Netlify Dashboard：
- 进入你的站点
- 在 **Site overview** 可以看到网站地址
- 格式：`https://your-site-name.netlify.app`

---

## 📞 需要帮助？

查看详细文档：
- `DEPLOY_FRONTEND.md` - 完整部署指南
- `GITHUB_DEPLOYMENT.md` - GitHub 集成指南
- `DEPLOYMENT_GUIDE.md` - 详细配置说明

---

**现在就开始部署吧！** 🚀

