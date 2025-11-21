# app.py 使用指南

`app.py` 是 RailFair 的完整 FastAPI 后端应用，集成了真实的预测引擎和票价系统。

## 📋 前置要求

1. **Python 环境**
   - Python 3.9+
   - 已安装所有依赖（见项目根目录 `requirements.txt`）

2. **数据库文件**
   - 默认路径：`data/railfair.db`
   - 可通过环境变量 `RAILFAIR_DB_PATH` 自定义路径
   - 如果数据库不存在，应用会自动创建

3. **NRDP API 凭据（必需）**
   - 必须在 `.env` 文件中配置：
     ```bash
     NRDP_EMAIL=your_email@example.com
     NRDP_PASSWORD=your_password
     ```
   - 系统仅使用真实NRDP数据，不支持模拟数据
   - 如果没有凭据，系统会抛出错误

4. **依赖模块**
   - `predictor.py` - 预测引擎（必须在项目根目录）
   - `price_fetcher.py` - 票价系统（必须在项目根目录）

## 🚀 启动方式

### 方式1：直接运行（推荐）

```bash
# 从项目根目录运行
python api/app.py
```

### 方式2：作为模块运行

```bash
# 从项目根目录运行
python -m api.app
```

### 方式3：使用 uvicorn 命令

```bash
# 从项目根目录运行
uvicorn api.app:app --host 0.0.0.0 --port 8000

# 开发模式（自动重载）
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
```

### 方式4：自定义端口

```bash
# 使用环境变量
export PORT=8080
uvicorn api.app:app --host 0.0.0.0 --port $PORT

# 或直接指定
uvicorn api.app:app --host 0.0.0.0 --port 8080
```

## ⚙️ 环境变量配置

### NRDP API 凭据（必需）

在项目根目录创建 `.env` 文件：

```bash
# NRDP API 凭据（必需）
NRDP_EMAIL=your_email@example.com
NRDP_PASSWORD=your_password

# 数据库路径（可选）
RAILFAIR_DB_PATH=data/railfair.db
```

**重要**：
- ✅ 系统仅使用真实NRDP数据
- ❌ 不支持模拟数据
- ✅ 如果没有凭据，系统会抛出错误并无法启动

### 数据库路径

```bash
# 使用默认路径 (data/railfair.db)
python api/app.py

# 自定义数据库路径
export RAILFAIR_DB_PATH=/path/to/your/database.db
python api/app.py
```

### 票价数据更新

系统会自动：
- ✅ 每天检查一次数据是否需要更新
- ✅ 如果数据超过1天，自动从NRDP API下载新数据
- ✅ 如果数据未超过1天，使用现有缓存

## 🌐 访问API

启动成功后，你会看到类似输出：

```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 访问地址

- **API根路径**: http://localhost:8000/
- **健康检查**: http://localhost:8000/health
- **Swagger文档**: http://localhost:8000/docs
- **ReDoc文档**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## 📡 API端点使用

### 1. 健康检查

```bash
curl http://localhost:8000/health
```

响应示例：
```json
{
  "status": "healthy",
  "timestamp": "2024-12-20T10:30:00",
  "version": "1.1.0",
  "database": true
}
```

### 2. 延误预测（核心功能）

```bash
curl -X POST "http://localhost:8000/api/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "EUS",
    "destination": "MAN",
    "departure_date": "2024-12-25",
    "departure_time": "09:30",
    "include_fares": true,
    "toc": null
  }'
```

**请求参数说明：**
- `origin` (必需): 出发站CRS代码（3个大写字母，如 "EUS"）
- `destination` (必需): 到达站CRS代码（3个大写字母，如 "MAN"）
- `departure_date` (必需): 出发日期（格式：YYYY-MM-DD）
- `departure_time` (必需): 出发时间（格式：HH:MM，24小时制）
- `include_fares` (可选): 是否包含票价比较（默认：false）
- `toc` (可选): 火车运营公司代码（如 "VT"）

**响应示例：**
```json
{
  "request_id": "req_abc123def456",
  "prediction": {
    "delay_minutes": 12.5,
    "confidence": 0.78,
    "on_time_probability": 0.65,
    "category": "MINOR",
    "confidence_level": "HIGH",
    "sample_size": 156,
    "is_degraded": false,
    "degradation_reason": null
  },
  "fares": {
    "advance_price": 25.50,
    "off_peak_price": 45.00,
    "anytime_price": 89.00,
    "cheapest_type": "advance",
    "savings_amount": 63.50,
    "savings_percentage": 71.35,
    "data_source": "NRDP_REAL"
  },
  // 注意：如果没有真实票价数据，fares字段为null
  // 前端应显示"❌ 不可用（暂无真实票价数据）"
  "recommendations": [
    {
      "type": "money",
      "title": "Save £63.50",
      "description": "Book advance tickets to save 71.4% compared to anytime fares",
      "score": 8.5
    }
  ],
  "explanation": "Based on 156 historical services...",
  "metadata": {
    "processing_time_ms": 45.2,
    "timestamp": "2024-12-20T10:30:00",
    "api_version": "1.1.0",
    "route": "EUS-MAN",
    "prediction_engine": "statistical_v1",
    "fare_engine": "nrdp_real_v1"
  }
}
```

### 3. 提交反馈

```bash
curl -X POST "http://localhost:8000/api/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "req_abc123def456",
    "actual_delay_minutes": 15,
    "was_cancelled": false,
    "rating": 4,
    "comment": "预测相当准确"
  }'
```

### 4. 获取统计信息

```bash
curl http://localhost:8000/api/stats
```

## 🧪 使用 Python 客户端

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. 健康检查
response = requests.get(f"{BASE_URL}/health")
print(response.json())

# 2. 预测延误
prediction_request = {
    "origin": "EUS",
    "destination": "MAN",
    "departure_date": "2024-12-25",
    "departure_time": "09:30",
    "include_fares": True
}

response = requests.post(f"{BASE_URL}/api/predict", json=prediction_request)
result = response.json()

print(f"预测延误: {result['prediction']['delay_minutes']} 分钟")
print(f"置信度: {result['prediction']['confidence']:.1%}")
print(f"最便宜票价: £{result['fares']['cheapest_price']:.2f}")

# 3. 提交反馈
feedback = {
    "request_id": result["request_id"],
    "actual_delay_minutes": 15,
    "was_cancelled": False,
    "rating": 4
}
response = requests.post(f"{BASE_URL}/api/feedback", json=feedback)
print(response.json())
```

## 🎯 使用演示脚本

项目提供了完整的演示脚本：

```bash
# 在另一个终端启动服务器
python api/app.py

# 然后运行演示
python api/demo.py
```

演示脚本会自动测试所有功能。

## ⚠️ 速率限制

API 实施了速率限制：
- **每分钟**: 100 次请求
- **每天**: 1000 次请求

超过限制会返回 `429 Too Many Requests` 错误。

## 🔍 调试和日志

### 查看日志

应用会输出详细的日志信息：
- 请求日志：每个请求的方法、路径、状态码、处理时间
- 错误日志：详细的错误堆栈信息

### 开发模式

修改 `app.py` 第 561 行，启用自动重载：

```python
reload=True  # 开发时启用，代码修改后自动重启
```

或使用 uvicorn 的 `--reload` 参数：

```bash
uvicorn api.app:app --reload
```

## 🐛 常见问题

### 1. 模块导入错误

**错误**: `ModuleNotFoundError: No module named 'predictor'`

**解决**: 确保从项目根目录运行，而不是从 `api` 目录：

```bash
# ✅ 正确
cd /path/to/uk-rail-delay-predictor
python api/app.py

# ❌ 错误
cd /path/to/uk-rail-delay-predictor/api
python app.py
```

### 2. 数据库文件不存在

**错误**: 数据库文件未找到

**解决**: 
- 应用会自动创建数据库文件
- 或设置环境变量指定数据库路径：
  ```bash
  export RAILFAIR_DB_PATH=/path/to/database.db
  ```

### 3. 端口被占用

**错误**: `Address already in use`

**解决**: 
- 使用其他端口：
  ```bash
  uvicorn api.app:app --port 8001
  ```
- 或关闭占用端口的进程

### 4. CORS 错误（前端调用时）

如果从浏览器调用API遇到CORS错误，检查 `app.py` 中的 CORS 配置（第 56-62 行），确保允许你的前端域名。

## 📚 更多信息

- **API文档**: 启动后访问 http://localhost:8000/docs
- **完整测试**: 运行 `pytest api/test_main.py -v`
- **项目README**: 查看项目根目录的 `README.md`

