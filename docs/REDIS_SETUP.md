# Redis 安装和配置指南

## 🎯 方案选择

根据你的系统情况，可以选择以下方案之一：

---

## 方案 1: 使用 Homebrew 安装 Redis (推荐)

### macOS 安装步骤

```bash
# 1. 安装 Redis
brew install redis

# 2. 启动 Redis 服务
brew services start redis

# 3. 验证 Redis 是否运行
redis-cli ping
# 应该返回: PONG
```

### 停止 Redis
```bash
brew services stop redis
```

### 手动启动（不注册为服务）
```bash
redis-server /opt/homebrew/etc/redis.conf
```

---

## 方案 2: 使用 Python 虚拟环境中的 Redis (临时方案)

如果不想安装系统级 Redis，可以使用 Python 的 `fakeredis` 进行测试：

```bash
# 安装 fakeredis (仅用于开发测试)
pip install fakeredis

# 然后修改 api/redis_cache.py，在开发模式下使用 fakeredis
```

**注意**: fakeredis 只适合开发测试，不适合生产环境。

---

## 方案 3: 不使用 Redis (降级模式)

`api/redis_cache.py` 已经实现了熔断器模式，如果 Redis 不可用，会自动降级到直接查询数据库。

### 验证降级模式

1. **不启动 Redis**，直接运行应用：
```bash
python api/app.py
```

2. 应用启动时会显示：
```
⚠️ Failed to connect to Redis: ...
🔴 Circuit breaker OPEN
```

3. 应用仍然可以运行，只是没有缓存功能，所有查询直接访问数据库。

---

## 方案 4: 使用 Docker (如果以后安装 Docker)

### 安装 Docker Desktop for Mac
1. 下载: https://www.docker.com/products/docker-desktop
2. 安装后启动 Docker Desktop
3. 运行: `docker run -d --name redis -p 6379:6379 redis:alpine`

---

## ✅ 推荐方案

**对于 macOS 用户，推荐使用方案 1 (Homebrew)**：

```bash
# 一键安装和启动
brew install redis && brew services start redis

# 验证
redis-cli ping
```

---

## 🔧 配置检查

安装 Redis 后，检查配置：

```bash
# 检查 Redis 是否在运行
redis-cli ping

# 查看 Redis 信息
redis-cli info

# 测试连接
redis-cli
> SET test "hello"
> GET test
> exit
```

---

## 📝 环境变量配置

应用使用以下环境变量（都有默认值）：

```bash
# 如果 Redis 在默认位置，不需要设置
# 如果需要自定义，可以设置：
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_DB=0
export REDIS_POOL_SIZE=20
```

---

## 🚨 故障排除

### 问题 1: Redis 连接失败
**症状**: 应用启动时显示 "Failed to connect to Redis"

**解决**:
```bash
# 检查 Redis 是否运行
redis-cli ping

# 如果没有运行，启动它
brew services start redis
```

### 问题 2: 端口被占用
**症状**: `Address already in use`

**解决**:
```bash
# 查找占用 6379 端口的进程
lsof -i :6379

# 停止该进程或使用其他端口
export REDIS_PORT=6380
```

### 问题 3: 权限问题
**症状**: `Permission denied`

**解决**:
```bash
# 确保 Redis 数据目录有正确权限
sudo chown -R $(whoami) /opt/homebrew/var/db/redis
```

---

## 🎯 快速开始

**最简单的启动方式**：

```bash
# 1. 安装 Redis
brew install redis

# 2. 启动 Redis (后台服务)
brew services start redis

# 3. 验证
redis-cli ping

# 4. 启动应用
python api/app.py
```

---

## 📊 性能对比

| 模式 | 响应时间 | 说明 |
|------|---------|------|
| 有 Redis 缓存 | <10ms (缓存命中) | 最佳性能 |
| 无 Redis (降级) | ~40-50ms | 直接查询数据库 |
| 无 Redis + 连接池 | ~5-8ms | 使用连接池优化 |

**结论**: 即使没有 Redis，应用仍然可以正常工作，只是性能会稍慢一些。

---

*最后更新: 2024-11-19*

