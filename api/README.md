# RailFair API

FastAPI后端服务，提供英国火车延误预测和票价比较功能。

## 文件结构

- **`app.py`** - 主应用文件（集成版本，Day 12）
  - 集成了真实的预测引擎和票价系统
  - **仅使用真实NRDP数据** - 完全移除模拟数据
  - **每天自动更新票价数据**
  - 版本：1.1.0
  - **推荐用于生产环境**

- **`main.py`** - 基础应用文件（Day 10-11版本）
  - 完整的API框架，但使用模拟数据
  - 版本：1.0.0
  - 仅用于历史参考，不推荐使用

- **`demo.py`** - API功能演示脚本
  - 演示所有API端点
  - 测试输入验证、速率限制等

- **`test_main.py`** - 完整的测试套件
  - 31个测试用例
  - 覆盖所有端点和错误情况

## 运行方式

### 启动主应用（推荐）

```bash
# 方式1：直接运行
python api/app.py

# 方式2：作为模块运行
python -m api.app

# 方式3：使用uvicorn
uvicorn api.app:app --host 0.0.0.0 --port 8000
```

### 运行基础版本

```bash
python api/main.py
# 或
python -m api.main
```

### 运行演示

```bash
# 确保API服务器正在运行（在另一个终端）
python api/demo.py
# 或
python -m api.demo
```

### 运行测试

```bash
# 从项目根目录运行
pytest api/test_main.py -v

# 或使用相对导入
cd api
pytest test_main.py -v
```

## API端点

- `GET /` - API信息
- `GET /health` - 健康检查
- `GET /docs` - Swagger UI文档
- `GET /redoc` - ReDoc文档
- `POST /api/predict` - 延误预测
- `POST /api/feedback` - 提交反馈
- `GET /api/stats` - 使用统计

## 访问文档

启动服务器后，访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

