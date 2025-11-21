# API 环境变量配置说明

## 📋 predictor.py 不需要 API 认证

**重要**：`predictor.py` 本身**不需要**API用户名密码！

`predictor.py` 只从本地数据库（`data/railfair.db`）读取统计数据，不调用任何外部API。因此：

- ✅ **不需要** HSP API 用户名密码来运行 `api/app.py`
- ✅ **不需要** HSP API 用户名密码来使用预测功能
- ✅ 只要数据库中有数据，预测就能工作

## 🔑 API 认证用于数据收集

API用户名密码是用于**数据收集脚本**的，不是用于预测的：

### 需要API认证的脚本：
- `fetch_hsp.py` - 从HSP API收集历史数据
- `fetch_hsp_batch.py` - 批量收集数据
- `hsp_client.py` - HSP API客户端
- `analyze_future_timetable.py` - 分析未来时刻表

### 不需要API认证的脚本：
- ✅ `api/app.py` - FastAPI服务器
- ✅ `api/demo.py` - 演示脚本
- ✅ `predictor.py` - 预测引擎（只读数据库）

## 📝 .env 文件配置检查

你的 `.env` 文件配置示例：

```bash
HSP_USERNAME=your_email@example.com
HSP_PASSWORD=your_password_here
```

### 可选：添加 HSP_EMAIL

有些脚本也支持 `HSP_EMAIL` 作为备选。如果你想添加（可选）：

```bash
# 在 .env 文件中添加（可选）
HSP_EMAIL=vanessading00@gmail.com
```

但这不是必需的，因为代码会优先使用 `HSP_USERNAME`。

## ✅ 验证配置

### 检查环境变量是否加载

```bash
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('HSP_USERNAME:', os.getenv('HSP_USERNAME')); print('HSP_PASSWORD:', 'SET' if os.getenv('HSP_PASSWORD') else 'NOT SET')"
```

### 测试API连接（如果需要收集数据）

```bash
python scripts/test_api_connection.py
```

## 🚨 常见问题

### Q: 运行 `api/app.py` 时提示需要API认证？

**A**: 这不应该发生。`predictor.py` 不调用API。如果出现错误，可能是：
1. 数据库文件不存在或路径错误
2. 数据库表结构不匹配
3. 其他代码错误

### Q: 预测功能不工作，是因为API认证问题吗？

**A**: 不是。预测功能不工作通常是因为：
1. 数据库中没有该路线的统计数据
2. 数据库表结构不匹配
3. 数据库文件路径错误

### Q: 什么时候需要API认证？

**A**: 只有在运行数据收集脚本时才需要：
- 首次收集数据：`python fetch_hsp.py`
- 批量收集数据：`python fetch_hsp_batch.py`
- 测试API连接：`python scripts/test_api_connection.py`

## 📚 总结

- ✅ `api/app.py` 和 `predictor.py` **不需要**API认证
- ✅ 你的 `.env` 配置是正确的
- ✅ 预测功能只依赖本地数据库
- ⚠️ API认证只用于数据收集脚本

如果预测功能有问题，检查数据库而不是API认证！

