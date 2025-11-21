# API 文件夹索引

本文件夹包含所有 RailFair FastAPI 后端相关的文件。

## 📁 文件结构

### 核心应用文件

- **`app.py`** ⭐ - 主应用文件（集成版本，推荐使用）
  - 集成了真实的预测引擎和票价系统
  - 版本：1.1.0
  - 用于生产环境

- **`main.py`** - 基础应用文件（Day 10-11版本）
  - 完整的API框架，使用模拟数据
  - 版本：1.0.0
  - 用于开发和参考

- **`__init__.py`** - Python包初始化文件

### 测试和演示

- **`test_main.py`** - 完整的测试套件
  - 31个测试用例
  - 覆盖所有端点和错误情况
  - 运行：`pytest api/test_main.py -v`

- **`demo.py`** - API功能演示脚本
  - 演示所有API端点
  - 测试输入验证、速率限制等
  - 运行：`python api/demo.py`

### 文档

- **`README.md`** - API文件夹说明
  - 文件结构介绍
  - 基本使用方法

- **`USAGE.md`** - 详细使用指南
  - 完整的启动说明
  - API端点使用示例
  - Python客户端示例
  - 环境变量配置

- **`QUICKSTART.md`** - 快速启动指南
  - 端口占用问题解决
  - 快速启动命令

- **`TROUBLESHOOTING.md`** - 故障排除指南
  - 常见问题解决
  - 连接问题诊断

- **`DEPENDENCIES.md`** - 依赖文件说明
  - app.py 需要的所有Python模块
  - 文件位置和导入说明
  - 常见错误解决

- **`INDEX.md`** - 本文件（文件索引）

## 🚀 快速开始

### 启动服务器

```bash
# 从项目根目录运行
python api/app.py
```

### 访问API文档

启动后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- 健康检查: http://localhost:8000/health

### 运行测试

```bash
pytest api/test_main.py -v
```

### 运行演示

```bash
python api/demo.py
```

## 📚 相关文件位置

以下文件不在本文件夹，但与API相关：

- **`predictor.py`** (项目根目录) - 预测引擎模块
- **`price_fetcher.py`** (项目根目录) - 票价系统模块
- **`scripts/test_api_connection.py`** - National Rail API连接测试（不是FastAPI相关）

## 🔗 相关文档

项目文档中与API相关的部分：
- `docs/DAY10_11_COMPLETE_REPORT.md` - Day 10-11交付报告
- `docs/DAY10_11_DELIVERY_CHECKLIST.md` - Day 10-11交付清单

