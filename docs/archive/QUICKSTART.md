# 🚀 Quick Start Guide

## Day 1 完成后的后续步骤

### 1️⃣ 配置 API 凭证

编辑 `.env` 文件:
```bash
cd ~/uk-rail-delay-predictor
nano .env
```

填入你的 National Rail Data Portal 凭证:
```bash
# 必填: HSP API
HSP_USERNAME=your_actual_username
HSP_PASSWORD=your_actual_password

# 必填: Darwin Push Port
DARWIN_USERNAME=your_actual_username
DARWIN_PASSWORD=your_actual_password

# 可选: Knowledgebase API
KB_USERNAME=your_actual_username
KB_PASSWORD=your_actual_password
```

### 2️⃣ 测试 API 连接

```bash
cd ~/uk-rail-delay-predictor
./venv/bin/python scripts/test_api_connection.py
```

期望输出:
```
============================================================
  UK Rail Delay Predictor - API Connection Tests
============================================================

============================================================
  Configuration Test
============================================================
✅ HSP_API: Configured
✅ Darwin: Configured
...

✅ HSP API connection successful!
📊 Retrieved X service records
```

### 3️⃣ 手动测试 HSP API

在 Python 中测试:
```python
from src.data_collection import HSPClient
from datetime import datetime, timedelta

# 创建客户端
client = HSPClient()

# 测试连接
if client.test_connection():
    print("✅ API 连接成功!")
    
    # 获取昨天的数据
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # 查询 Paddington → Oxford 路线
    data = client.get_service_metrics(
        from_loc="PADTON",
        to_loc="OXFD",
        from_date=yesterday,
        to_date=yesterday,
        from_time="0800",
        to_time="1800"
    )
    
    print(f"获取到 {len(data.get('Services', []))} 条记录")
```

### 4️⃣ 常用命令

```bash
# 激活虚拟环境
cd ~/uk-rail-delay-predictor
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 验证环境
python scripts/validate_setup.py

# 测试 API
python scripts/test_api_connection.py

# 安装额外的包
pip install package_name

# 查看日志
tail -f logs/rail_predictor_*.log
```

### 5️⃣ 项目结构快速参考

```
📁 数据存储
  data/raw/hsp/         → HSP API 原始数据
  data/raw/darwin/      → Darwin 实时数据
  data/processed/       → 清洗后的数据
  
📁 源代码
  src/data_collection/  → API 客户端
  src/utils/           → 工具函数
  
📁 输出
  models/saved_models/ → 训练好的模型
  logs/                → 日志文件
```

### 6️⃣ 常见问题

**Q: API 连接失败?**
```bash
# 检查凭证
cat .env | grep USERNAME

# 检查网络连接
curl -I https://hsp-prod.rockshore.net

# 查看详细日志
cat logs/rail_predictor_*.log | grep ERROR
```

**Q: 缺少依赖包?**
```bash
pip install -r requirements.txt
```

**Q: 数据存储在哪里?**
```bash
# HSP 数据
ls -lh data/raw/hsp/

# 查看最新文件
ls -lt data/raw/hsp/ | head
```

### 7️⃣ 下一步: Day 2

准备开始 Day 2 时:
1. ✅ 确认所有 API 连接成功
2. ✅ 熟悉项目结构
3. ✅ 查看样本数据格式
4. 🚀 开始实现 Darwin Push Port 客户端

---

## 🔗 有用的链接

- [HSP API 文档](https://wiki.openraildata.com/index.php/HSP)
- [Darwin Push Port 文档](https://wiki.openraildata.com/index.php/Darwin:Push_Port)
- [Knowledgebase 文档](https://wiki.openraildata.com/index.php/KnowledgeBase)
- [National Rail 数据门户](https://www.nationalrail.co.uk/developers/)

## 📞 获取帮助

遇到问题时:
1. 检查日志文件: `logs/rail_predictor_*.log`
2. 查看错误日志: `logs/errors_*.log`
3. 运行验证脚本: `python scripts/validate_setup.py`
4. 检查 API 状态: National Rail 状态页面

---
*Happy Coding! 🚂*
