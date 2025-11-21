# API 故障排除指南

## "This site can't be reached" 问题

### ✅ 服务器状态检查

服务器正在运行！可以通过以下方式验证：

```bash
# 检查进程
ps aux | grep "python api/app.py"

# 检查端口
lsof -i:8000

# 测试连接
curl http://localhost:8000/health
```

### 🔍 常见原因和解决方案

#### 1. 使用了错误的URL

**错误**：
- `http://0.0.0.0:8000` ❌
- `http://your-ip:8000` ❌

**正确**：
- `http://localhost:8000` ✅
- `http://127.0.0.1:8000` ✅

#### 2. 浏览器缓存问题

**解决方案**：
- 清除浏览器缓存
- 使用隐私模式/无痕模式
- 尝试不同的浏览器

#### 3. 防火墙阻止

**检查**：
```bash
# macOS 检查防火墙
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate
```

**解决方案**：
- 临时关闭防火墙测试
- 或添加Python到防火墙允许列表

#### 4. 服务器只监听localhost

当前服务器配置为只监听 `127.0.0.1`（本地），无法从其他设备访问。

**如果需要从其他设备访问**，需要修改 `api/app.py`：

```python
# 将 host="0.0.0.0" 改为 host="0.0.0.0"（已经是这样）
# 但确保防火墙允许连接
```

### 🧪 测试步骤

1. **测试本地连接**：
```bash
curl http://localhost:8000/health
```

应该返回：
```json
{"status":"healthy","timestamp":"...","version":"1.1.0","database":true}
```

2. **在浏览器中测试**：
   - 打开浏览器
   - 访问：`http://localhost:8000/docs`
   - 或访问：`http://127.0.0.1:8000/docs`

3. **检查服务器日志**：
   查看运行 `python api/app.py` 的终端，应该看到请求日志。

### 📝 正确的访问地址

- **API根路径**: http://localhost:8000/
- **健康检查**: http://localhost:8000/health
- **Swagger文档**: http://localhost:8000/docs
- **ReDoc文档**: http://localhost:8000/redoc
- **API预测**: http://localhost:8000/api/predict

### 🔧 如果仍然无法访问

1. **重启服务器**：
```bash
# 停止当前服务器（Ctrl+C）
# 然后重新启动
python api/app.py
```

2. **检查是否有错误**：
   查看终端输出，是否有错误信息

3. **尝试不同端口**：
```bash
PORT=8001 python api/app.py
# 然后访问 http://localhost:8001/docs
```

4. **检查Python环境**：
```bash
python --version
which python
```

