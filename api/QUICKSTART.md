# API 快速启动指南

## 端口被占用问题

如果遇到 `address already in use` 错误，有两种解决方案：

### 方案1：关闭占用端口的进程（推荐）

```bash
# 查找占用8000端口的进程
lsof -ti:8000

# 关闭进程（替换PID为实际进程号）
kill <PID>

# 或者强制关闭
kill -9 <PID>
```

### 方案2：使用其他端口

```bash
# 使用8001端口
uvicorn api.app:app --host 0.0.0.0 --port 8001

# 或修改 app.py 中的端口号
# 将第559行的 port=8000 改为 port=8001
```

## 快速启动

```bash
# 从项目根目录运行
python api/app.py
```

启动成功后访问：
- http://localhost:8000/docs (Swagger文档)
- http://localhost:8000/health (健康检查)

