# 🚀 RailFair 快速启动指南

本指南将帮助你快速启动前后端，让网页能够查询真实的API数据。

## 📋 前置要求

1. **Python 3.9+** 已安装
2. **数据库文件** `data/railfair.db` 存在
3. **依赖包** 已安装（见下方）

## 🔧 步骤 1: 安装依赖

```bash
# 从项目根目录运行
pip3 install -r requirements.txt
```

**注意**: Redis 是可选的。如果没有 Redis，系统会自动使用内存缓存。

## 🚀 步骤 2: 启动后端 API

### 方式 A: 使用启动脚本（推荐）

```bash
# 给脚本执行权限（首次运行）
chmod +x start_api.sh

# 启动API
./start_api.sh
```

### 方式 B: 直接运行

```bash
# 从项目根目录运行
python3 -m api.app
```

### 方式 C: 使用 uvicorn

```bash
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
```

**验证后端运行**:
- 打开浏览器访问: http://localhost:8000/docs
- 应该看到 Swagger API 文档
- 访问: http://localhost:8000/health
- 应该返回健康状态

## 🌐 步骤 3: 启动前端（可选，用于本地测试）

### 方式 A: 使用启动脚本

```bash
# 给脚本执行权限（首次运行）
chmod +x start_frontend.sh

# 启动前端
./start_frontend.sh
```

### 方式 B: 使用 Python HTTP 服务器

```bash
cd frontend/railfair
python3 -m http.server 3000
```

### 方式 C: 使用其他服务器

你也可以使用任何静态文件服务器，例如：
- **VS Code Live Server** 扩展
- **Netlify Dev** (如果已配置)
- **其他 HTTP 服务器**

**访问前端**: http://localhost:3000

## ✅ 步骤 4: 测试查询

1. **打开前端页面**: http://localhost:3000
2. **输入查询信息**:
   - 起点站: 例如 `EUS` (London Euston)
   - 终点站: 例如 `MAN` (Manchester Piccadilly)
   - 日期和时间: 选择未来日期和时间
3. **点击搜索按钮**
4. **查看结果**: 应该显示延误预测和票价信息

## 🔍 故障排除

### 问题 1: 后端无法启动

**检查**:
- 数据库文件是否存在: `ls data/railfair.db`
- 依赖是否安装: `pip3 list | grep fastapi`
- 端口 8000 是否被占用: `lsof -i :8000`

**解决**:
```bash
# 检查数据库
ls -lh data/railfair.db

# 重新安装依赖
pip3 install -r requirements.txt

# 使用其他端口
PORT=8080 python3 -m api.app
```

### 问题 2: 前端无法连接后端

**检查**:
- 后端是否运行: 访问 http://localhost:8000/health
- 前端配置是否正确: 检查 `frontend/railfair/config.js`
- 浏览器控制台是否有错误

**解决**:
```javascript
// 确保 frontend/railfair/config.js 中配置了:
const configuredBase = 'http://localhost:8000';
```

### 问题 3: 查询返回错误

**检查**:
- 数据库是否有数据: `sqlite3 data/railfair.db "SELECT COUNT(*) FROM route_statistics;"`
- API 日志是否有错误信息
- 浏览器网络请求是否成功

**解决**:
```bash
# 检查数据库数据
sqlite3 data/railfair.db "SELECT origin, destination, total_services FROM route_statistics LIMIT 5;"

# 查看API日志
# 在运行API的终端中查看输出
```

### 问题 4: Redis 连接错误

**这是正常的！** Redis 是可选的。如果没有 Redis，系统会：
- 自动使用内存缓存
- 在日志中显示警告（可以忽略）
- 功能完全正常，只是缓存不会持久化

## 📝 环境变量配置（可选）

如果需要自定义配置，创建 `.env` 文件：

```bash
# 数据库路径
RAILFAIR_DB_PATH=data/railfair.db

# Redis 配置（可选）
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# 日志级别
LOG_LEVEL=INFO
```

## 🎯 快速测试命令

```bash
# 测试后端健康检查
curl http://localhost:8000/health

# 测试预测API
curl -X POST http://localhost:8000/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "EUS",
    "destination": "MAN",
    "departure_date": "2025-12-25",
    "departure_time": "09:30",
    "include_fares": true
  }'
```

## 📚 更多信息

- **API 文档**: http://localhost:8000/docs (Swagger UI)
- **API 使用指南**: `api/USAGE.md`
- **部署指南**: `DEPLOYMENT_GUIDE.md`

## 🆘 需要帮助？

如果遇到问题：
1. 检查后端日志输出
2. 检查浏览器控制台错误
3. 查看 `api/TROUBLESHOOTING.md`
4. 验证数据库文件和数据

---

**祝你使用愉快！** 🚂✨

