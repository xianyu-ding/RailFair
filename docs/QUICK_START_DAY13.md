# Day 13 快速启动指南

## ✅ Redis 已安装并运行

Redis 服务已经成功启动，现在可以运行优化版应用了。

---

## 🚀 快速启动步骤

### 1. 确保依赖已安装

```bash
# 激活虚拟环境
source railenv/bin/activate

# 安装/更新依赖
pip install -r requirements.txt
```

### 2. 验证 Redis 连接

```bash
# 测试 Redis 连接
redis-cli ping
# 应该返回: PONG

# 或使用 Python 测试
python -c "import redis; r = redis.Redis(); r.ping(); print('✅ Redis 连接成功')"
```

### 3. 启动应用

```bash
# 方式 1: 直接运行
python api/app.py

# 方式 2: 使用 uvicorn
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 验证应用运行

打开浏览器访问：
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health
- 系统统计: http://localhost:8000/api/statistics

---

## 📊 运行负载测试

```bash
# 启动应用后，在另一个终端运行：
locust -f api/load_test.py --host=http://localhost:8000

# 然后在浏览器打开 http://localhost:8089 查看测试界面
```

---

## 🔧 Redis 管理命令

```bash
# 查看 Redis 状态
brew services list | grep redis

# 停止 Redis
brew services stop redis

# 启动 Redis
brew services start redis

# 重启 Redis
brew services restart redis

# 查看 Redis 日志
tail -f /opt/homebrew/var/log/redis.log
```

---

## 🎯 预期结果

应用启动时应该看到：

```
==================================================
RailFair API v2.0 - Optimized Edition
Redis Cache: ✅ Connected
Database Pool: ✅ Healthy
Fare Engine: ✅ Ready
==================================================
```

如果看到 `Redis Cache: ❌ Not available`，检查：
1. Redis 是否运行: `redis-cli ping`
2. 端口是否正确: 默认 6379
3. 防火墙设置

---

## 📝 环境变量（可选）

如果需要自定义配置，可以设置：

```bash
export REDIS_HOST=localhost
export REDIS_PORT=6379
export DB_POOL_SIZE=20
export RAILFAIR_DB_PATH=data/railfair.db
```

---

## 🐛 故障排除

### 问题: 应用无法连接 Redis

**检查步骤**:
```bash
# 1. 检查 Redis 是否运行
redis-cli ping

# 2. 检查端口
lsof -i :6379

# 3. 查看应用日志
# 应用会自动降级到数据库模式，仍然可以运行
```

### 问题: 模块导入错误

**解决**:
```bash
# 确保在项目根目录
cd /Volumes/HP\ P900/RailFair/uk-rail-delay-predictor

# 确保虚拟环境激活
source railenv/bin/activate

# 重新安装依赖
pip install -r requirements.txt
```

---

## ✅ 验证清单

- [ ] Redis 已安装并运行 (`redis-cli ping` 返回 PONG)
- [ ] 依赖已安装 (`pip list | grep redis`)
- [ ] 数据库文件存在 (`ls data/railfair.db`)
- [ ] 应用可以启动 (`python api/app.py`)
- [ ] 健康检查通过 (`curl http://localhost:8000/health`)

---

## 🌐 前端 API 地址配置

部署前端时需要让页面能够访问实际的 API 域名。`frontend/script.js` 会按以下优先级自动选择 `API_BASE`：

1. 全局变量：在 `script.js` 之前注入
   ```html
   <script>
     window.__RAILFAIR_API_BASE__ = 'https://api.railfair.uk';
   </script>
   ```
2. `html` 标签属性：
   ```html
   <html lang="en" data-api-base="https://api.railfair.uk">
   ```
3. 如果都未设置，则默认使用当前页面 `window.location.origin`。

最终请求地址为 `API_BASE + '/api'`，因此一旦后端部署在独立域名，只需以上任意方式设置即可，无需修改前端源代码。

---

*最后更新: 2024-11-19*

