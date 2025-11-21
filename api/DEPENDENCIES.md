# app.py 依赖文件说明

## 📋 概述

`api/app.py` 是 RailFair 的主应用文件，它依赖以下 Python 模块和文件。

## 🔗 必需的项目模块（项目根目录）

### 1. `predictor.py` ⭐ **必需**

**位置**: 项目根目录 (`/predictor.py`)

**用途**: 延误预测引擎

**导入内容**:
```python
from predictor import (
    predict_delay,           # 核心预测函数
    get_prediction_explanation,  # 生成解释文本
    ConfidenceLevel,         # 置信度枚举
    PredictionResult         # 预测结果数据类
)
```

**功能**:
- 基于历史统计数据预测延误
- 提供置信度评估
- 生成人性化的预测解释

**如果缺失**: 应用无法启动，会抛出 `ModuleNotFoundError`

---

### 2. `price_fetcher.py` ⭐ **必需**

**位置**: 项目根目录 (`/price_fetcher.py`)

**用途**: 票价对比系统

**导入内容**:
```python
from price_fetcher import (
    initialize_fares_system,  # 初始化票价系统
    FareComparator,           # 票价对比引擎
    FareComparison,           # 票价对比结果
    TicketType                # 票种枚举
)
```

**功能**:
- 从 NRDP API 下载真实票价数据
- 解析并缓存票价数据
- 提供票价对比功能
- 每天自动更新数据

**如果缺失**: 应用无法启动，会抛出 `ModuleNotFoundError`

---

## 📦 第三方库依赖

这些库需要通过 `pip install -r requirements.txt` 安装：

### FastAPI 相关
- `fastapi` - Web框架
- `uvicorn[standard]` - ASGI服务器
- `pydantic` - 数据验证
- `pydantic-settings` - 配置管理

### 其他
- `python-dotenv` - 环境变量加载（可选，但推荐）

**完整依赖列表**: 见项目根目录的 `requirements.txt`

---

## 📁 文件结构要求

```
uk-rail-delay-predictor/
├── api/
│   └── app.py              ← 主应用文件
├── predictor.py            ← ⭐ 必需
├── price_fetcher.py        ← ⭐ 必需
├── .env                    ← ⭐ 必需（包含NRDP凭据）
├── data/
│   └── railfair.db         ← 数据库（会自动创建）
└── requirements.txt          ← Python依赖
```

---

## 🔍 导入机制

`app.py` 通过以下方式导入根目录模块：

```python
# 第24-25行：添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 第38-49行：导入项目模块
from predictor import ...
from price_fetcher import ...
```

**重要**: 必须从项目根目录运行 `app.py`，否则无法找到这些模块。

---

## ✅ 验证依赖

### 检查模块是否存在

```bash
# 从项目根目录运行
python -c "from predictor import predict_delay; print('✅ predictor.py 可用')"
python -c "from price_fetcher import initialize_fares_system; print('✅ price_fetcher.py 可用')"
```

### 检查第三方库

```bash
pip list | grep -E "fastapi|uvicorn|pydantic"
```

### 检查环境变量

```bash
# 检查 .env 文件
cat .env | grep NRDP
```

---

## 🚨 常见错误

### 1. ModuleNotFoundError: No module named 'predictor'

**原因**: 从错误的目录运行，或文件不存在

**解决**:
```bash
# ✅ 正确：从项目根目录运行
cd /path/to/uk-rail-delay-predictor
python api/app.py

# ❌ 错误：从api目录运行
cd /path/to/uk-rail-delay-predictor/api
python app.py
```

### 2. ModuleNotFoundError: No module named 'price_fetcher'

**原因**: 同上

**解决**: 确保从项目根目录运行

### 3. ValueError: 未提供NRDP凭据

**原因**: `.env` 文件中缺少 `NRDP_EMAIL` 或 `NRDP_PASSWORD`

**解决**: 在项目根目录创建 `.env` 文件并添加凭据

---

## 📊 依赖关系图

```
app.py
├── predictor.py
│   └── 依赖: data/railfair.db (数据库)
│
├── price_fetcher.py
│   ├── 依赖: data/railfair.db (数据库)
│   ├── 依赖: .env (NRDP凭据)
│   └── 依赖: data/fares_data.zip (缓存文件，可选)
│
└── 第三方库
    ├── fastapi
    ├── uvicorn
    ├── pydantic
    └── python-dotenv (可选)
```

---

## 🎯 快速检查清单

在运行 `app.py` 之前，确保：

- [ ] `predictor.py` 存在于项目根目录
- [ ] `price_fetcher.py` 存在于项目根目录
- [ ] `.env` 文件存在并包含 `NRDP_EMAIL` 和 `NRDP_PASSWORD`
- [ ] 已安装所有依赖：`pip install -r requirements.txt`
- [ ] 从项目根目录运行：`python api/app.py`
- [ ] 数据库文件路径正确（默认：`data/railfair.db`）

---

## 📚 相关文档

- **完整使用指南**: `api/USAGE.md`
- **数据来源说明**: `api/DATA_SOURCES.md`
- **NRDP配置**: `api/NRDP_SETUP.md`
- **故障排除**: `api/TROUBLESHOOTING.md`

