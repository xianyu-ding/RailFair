# 速率限制说明

## 📋 速率限制配置

API实施了速率限制以防止滥用：
- **每分钟**: 100 次请求
- **每天**: 1000 次请求

## ⚠️ 遇到速率限制时

### 方法1：自动重置（推荐）

`demo.py` 现在会自动检测并重置速率限制：

```bash
python api/demo.py
```

如果检测到速率限制已触发，会自动重置。

### 方法2：手动重置

使用重置端点：

```bash
# 使用 curl
curl -X POST http://localhost:8000/api/reset-rate-limit

# 或使用 Python
python -c "import requests; r = requests.post('http://localhost:8000/api/reset-rate-limit'); print(r.json())"
```

### 方法3：等待

速率限制是基于时间窗口的：
- **每分钟限制**: 等待1分钟后自动重置
- **每天限制**: 等待24小时后自动重置

### 方法4：重启服务器

重启API服务器会清除所有速率限制数据：

```bash
# 停止服务器 (Ctrl+C)
# 然后重新启动
python api/app.py
```

## 🔍 检查速率限制状态

查看当前统计：

```bash
curl http://localhost:8000/api/stats
```

响应示例：
```json
{
  "total_requests": 102,
  "unique_clients": 2,
  "total_feedback": 0,
  "average_rating": 0,
  "api_version": "1.1.0",
  "timestamp": "2025-11-19T22:18:58.647744"
}
```

如果 `total_requests` 接近或超过限制，说明速率限制可能已触发。

## 🛠️ 开发/测试环境

在开发或测试时，如果频繁触发速率限制，可以：

1. **临时提高限制**（修改 `api/app.py`）：
```python
# 在 app.py 第161行
rate_limiter = RateLimiter(
    minute_limit=1000,  # 提高到1000
    day_limit=10000     # 提高到10000
)
```

2. **禁用速率限制**（仅用于开发）：
```python
# 在预测端点中注释掉速率限制检查
# if not rate_limiter.is_allowed(client_id):
#     raise HTTPException(...)
```

3. **使用重置端点**：
```bash
# 在测试前重置
curl -X POST http://localhost:8000/api/reset-rate-limit
```

## 📝 速率限制工作原理

1. **客户端识别**: 基于IP地址和User-Agent生成唯一指纹
2. **时间窗口**: 使用滑动时间窗口计算请求数
3. **自动清理**: 超过24小时的请求记录会自动清理
4. **内存存储**: 速率限制数据存储在内存中，重启服务器会清除

## ⚡ 快速解决方案

如果演示脚本遇到速率限制：

```bash
# 1. 重置速率限制
curl -X POST http://localhost:8000/api/reset-rate-limit

# 2. 重新运行演示
python api/demo.py
```

或者直接重启服务器：

```bash
# 停止当前服务器 (Ctrl+C)
# 重新启动
python api/app.py
```

## 🔗 相关端点

- `GET /api/stats` - 查看使用统计
- `POST /api/reset-rate-limit` - 重置速率限制（开发用）

