# ⚡ 快速配置指南

## 🎯 5 分钟快速配置前后端连接

### 步骤 1: 获取你的 Cloudflare 后端地址

1. 登录 Cloudflare Dashboard
2. 进入你的 Workers/Pages 项目
3. 复制你的后端地址，例如：
   - `https://railfair-api.your-domain.com`
   - `https://railfair-backend.workers.dev`

### 步骤 2: 配置前端（选择一种方式）

#### 方式 A：使用 Netlify 代理（推荐，避免 CORS 问题）

1. 编辑 `frontend/railfair/netlify.toml`
2. 将第 8 行的地址替换为你的后端地址：

```toml
[[redirects]]
  from = "/api/*"
  to = "https://你的后端地址.workers.dev/api/:splat"  # ⬅️ 替换这里
  status = 200
  force = true
```

3. 保持 `frontend/railfair/config.js` 中的 `configuredBase` 为空：

```javascript
const configuredBase = '';  // 保持为空
```

4. 提交并推送到 Git，Netlify 会自动重新部署

#### 方式 B：直接跨域调用

1. 编辑 `frontend/railfair/config.js`
2. 将第 16 行的地址替换为你的后端地址：

```javascript
const configuredBase = 'https://你的后端地址.workers.dev';  // ⬅️ 替换这里
```

3. 提交并推送到 Git，Netlify 会自动重新部署

### 步骤 3: 配置后端数据库

在 Cloudflare Workers/Pages 的 **Settings** > **Variables and Secrets** 中添加：

```bash
DATABASE_URL=你的数据库连接字符串
RAILFAIR_DB_PATH=data/railfair.db  # 如果使用 SQLite
```

**数据库连接字符串示例：**

- **PostgreSQL**: `postgresql://user:password@host:5432/railfair`
- **MySQL**: `mysql://user:password@host:3306/railfair`
- **SQLite**: `sqlite:///data/railfair.db`

### 步骤 4: 测试连接

1. **测试后端**：
   ```bash
   curl https://你的后端地址.workers.dev/health
   ```
   应该返回 `{"status": "healthy"}`

2. **测试前端**：
   - 打开你的 Netlify 网站
   - 打开浏览器开发者工具（F12）
   - 进入 Network 标签
   - 执行一次搜索
   - 检查 `/api/predict` 请求是否成功（状态码 200）

### ✅ 完成！

如果一切正常，你的网站现在应该可以：
- ✅ 连接到后端 API
- ✅ 访问数据库
- ✅ 显示预测结果

---

## 🐛 如果遇到问题

### 问题 1: CORS 错误

**解决**：使用方式 A（Netlify 代理）而不是方式 B

### 问题 2: 404 错误

**检查**：
- 后端地址是否正确
- 后端是否已部署并运行
- `netlify.toml` 中的地址是否正确

### 问题 3: 数据库连接失败

**检查**：
- `DATABASE_URL` 环境变量是否正确
- 数据库服务是否可访问
- 数据库凭据是否正确

### 问题 4: 预测返回空数据

**解决**：
- 确保数据库中有数据
- 运行数据收集脚本填充数据库

---

## 📚 详细文档

查看 `DEPLOYMENT_GUIDE.md` 获取更详细的配置说明。

