# 🚀 RailFair 部署配置指南

本指南将帮助你配置前端（Netlify）和后端（Cloudflare）之间的连接，使网站能够正常使用 API 并访问数据库。

## 📋 目录

1. [后端配置（Cloudflare）](#后端配置cloudflare)
2. [前端配置（Netlify）](#前端配置netlify)
3. [数据库配置](#数据库配置)
4. [CORS 配置](#cors-配置)
5. [测试连接](#测试连接)
6. [常见问题](#常见问题)

---

## 🔧 后端配置（Cloudflare）

### 1. 环境变量配置

在 Cloudflare 部署后端时，需要设置以下环境变量：

#### 必需的环境变量

```bash
# 数据库连接（根据你的数据库类型选择）
# SQLite（本地文件，不推荐生产环境）
DATABASE_URL=sqlite:///data/railfair.db

# PostgreSQL（推荐生产环境）
DATABASE_URL=postgresql://username:password@host:port/database_name

# MySQL
DATABASE_URL=mysql://username:password@host:port/database_name

# 数据库路径（如果使用 SQLite）
RAILFAIR_DB_PATH=data/railfair.db
```

#### 可选的环境变量

```bash
# 数据库连接池配置
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# Redis 缓存（可选，如果使用 Redis）
REDIS_URL=redis://localhost:6379/0

# 日志级别
LOG_LEVEL=INFO
```

### 2. 在 Cloudflare Workers/Pages 中设置环境变量

1. 登录 Cloudflare Dashboard
2. 进入你的 Workers/Pages 项目
3. 进入 **Settings** > **Variables and Secrets**
4. 添加上述环境变量

### 3. 数据库部署选项

#### 选项 A：使用 Cloudflare D1（推荐）

Cloudflare D1 是 Cloudflare 提供的 SQLite 数据库服务：

```bash
# 1. 创建 D1 数据库
wrangler d1 create railfair-db

# 2. 在 wrangler.toml 中配置
[[d1_databases]]
binding = "DB"
database_name = "railfair-db"
database_id = "your-database-id"

# 3. 在代码中使用
# DATABASE_URL 会自动从 D1 binding 获取
```

#### 选项 B：使用外部 PostgreSQL/MySQL

如果你使用外部数据库（如 Supabase、Railway、PlanetScale）：

```bash
# PostgreSQL 示例
DATABASE_URL=postgresql://user:password@host:5432/railfair

# MySQL 示例  
DATABASE_URL=mysql://user:password@host:3306/railfair
```

#### 选项 C：使用 Cloudflare R2 + SQLite 文件

如果使用 SQLite 文件，可以存储在 Cloudflare R2 中：

```bash
# 需要自定义代码来从 R2 读取 SQLite 文件
# 参考 Cloudflare R2 文档
```

---

## 🌐 前端配置（Netlify）

### 方式 1：使用 Netlify 代理（推荐）

这种方式可以避免 CORS 问题，因为浏览器认为 API 调用来自同一个域名。

1. **编辑 `frontend/railfair/netlify.toml`**：

```toml
[[redirects]]
  from = "/api/*"
  to = "https://your-cloudflare-backend.workers.dev/api/:splat"
  status = 200
  force = true
```

将 `https://your-cloudflare-backend.workers.dev` 替换为你的实际 Cloudflare 后端地址。

2. **保持 `frontend/railfair/config.js` 中的 `configuredBase` 为空**：

```javascript
const configuredBase = '';  // 留空，使用 Netlify 代理
```

3. **重新部署到 Netlify**

### 方式 2：直接跨域调用

如果你不想使用代理，可以直接配置后端地址：

1. **编辑 `frontend/railfair/config.js`**：

```javascript
const configuredBase = 'https://your-cloudflare-backend.workers.dev';
```

2. **确保后端 CORS 配置正确**（见下方 CORS 配置部分）

3. **重新部署到 Netlify**

---

## 🗄️ 数据库配置

### 检查数据库连接

后端代码会自动从环境变量 `DATABASE_URL` 读取数据库连接信息。

#### 验证数据库连接

在 Cloudflare Workers 中，你可以添加一个健康检查端点来验证数据库连接：

```python
@app.get("/health")
async def health_check():
    """健康检查，包括数据库连接"""
    try:
        # 测试数据库连接
        db_pool.health_check()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}
```

### 数据库迁移

如果你的数据库需要初始化表结构，确保在部署时运行迁移脚本：

```bash
# 在本地运行迁移
python init_database.py

# 如果使用 D1，使用 wrangler 执行 SQL
wrangler d1 execute railfair-db --file=create_tables.sql
```

---

## 🔐 CORS 配置

后端已经配置了 CORS，允许所有来源：

```python
# api/app.py 中已配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 生产环境建议

为了安全，建议在生产环境中限制允许的来源：

```python
# 只允许你的 Netlify 域名
allowed_origins = [
    "https://your-site.netlify.app",
    "https://your-custom-domain.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
```

---

## ✅ 测试连接

### 1. 测试后端健康检查

```bash
# 替换为你的后端地址
curl https://your-cloudflare-backend.workers.dev/health
```

应该返回：

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00",
  "services": {
    "api": "operational",
    "database": "operational"
  }
}
```

### 2. 测试 API 端点

```bash
# 测试预测端点
curl -X POST https://your-cloudflare-backend.workers.dev/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "KGX",
    "destination": "MAN",
    "departure_date": "2024-01-15",
    "departure_time": "10:00:00",
    "include_fares": true
  }'
```

### 3. 测试前端连接

1. 打开浏览器开发者工具（F12）
2. 进入 **Network** 标签
3. 在你的网站上执行一次搜索
4. 检查 `/api/predict` 请求：
   - ✅ 状态码应该是 `200`
   - ✅ 响应应该包含预测数据
   - ❌ 如果看到 CORS 错误，检查后端 CORS 配置

### 4. 检查控制台错误

在浏览器控制台中检查是否有错误：

- **CORS 错误**：后端 CORS 配置问题
- **404 错误**：API 地址配置错误
- **500 错误**：后端服务器错误，检查 Cloudflare Workers 日志

---

## 🐛 常见问题

### Q1: 前端无法连接到后端 API

**可能原因：**
1. API 地址配置错误
2. CORS 配置问题
3. 后端未正确部署

**解决方法：**
1. 检查 `config.js` 或 `netlify.toml` 中的后端地址是否正确
2. 在浏览器开发者工具中查看 Network 标签，检查请求的 URL
3. 直接访问后端健康检查端点，确认后端正常运行

### Q2: CORS 错误

**错误信息：**
```
Access to fetch at 'https://...' from origin 'https://...' has been blocked by CORS policy
```

**解决方法：**
1. 确保后端 CORS 配置允许你的前端域名
2. 或者使用 Netlify 代理（方式 1），避免跨域问题

### Q3: 数据库连接失败

**错误信息：**
```
Database connection failed
```

**解决方法：**
1. 检查 `DATABASE_URL` 环境变量是否正确设置
2. 验证数据库服务是否可访问（如果使用外部数据库）
3. 检查数据库凭据是否正确
4. 查看 Cloudflare Workers 日志获取详细错误信息

### Q4: 预测返回空数据

**可能原因：**
1. 数据库中缺少该路线的数据
2. 数据库表结构不匹配

**解决方法：**
1. 检查数据库中是否有该路线的统计数据
2. 运行数据收集脚本填充数据库
3. 验证数据库表结构是否正确

### Q5: Netlify 代理不工作

**可能原因：**
1. `netlify.toml` 配置错误
2. 后端地址不正确

**解决方法：**
1. 检查 `netlify.toml` 中的 `to` 地址是否正确
2. 确保后端地址包含 `/api` 路径
3. 重新部署 Netlify 站点

---

## 📝 快速检查清单

部署前请确认：

- [ ] 后端已部署到 Cloudflare 并正常运行
- [ ] 后端环境变量已正确设置（特别是 `DATABASE_URL`）
- [ ] 数据库已初始化并包含数据
- [ ] 前端 `config.js` 或 `netlify.toml` 已配置后端地址
- [ ] 后端健康检查端点返回 `200 OK`
- [ ] 浏览器控制台没有 CORS 错误
- [ ] API 请求返回正确的数据

---

## 🔗 相关文档

- [FastAPI CORS 文档](https://fastapi.tiangolo.com/tutorial/cors/)
- [Cloudflare Workers 文档](https://developers.cloudflare.com/workers/)
- [Cloudflare D1 文档](https://developers.cloudflare.com/d1/)
- [Netlify 重定向文档](https://docs.netlify.com/routing/redirects/)

---

## 💡 需要帮助？

如果遇到问题，请检查：

1. Cloudflare Workers 日志
2. Netlify 部署日志
3. 浏览器开发者工具（Network 和 Console 标签）
4. 后端健康检查端点响应

祝你部署顺利！🚀

