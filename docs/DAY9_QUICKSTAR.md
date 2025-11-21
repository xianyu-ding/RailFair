# RailFair Day 9 - 快速开始指南 🎫

## 📁 文件清单

```
Day 9 交付文件:
├── price_fetcher.py              (26KB, 800+行) - 核心票价系统
├── test_price_fetcher.py         (15KB, 450+行) - 测试套件  
└── DAY9_DELIVERY_SUMMARY.md      (14KB)          - 交付总结
```

---

## ⚡ 5分钟快速上手

### 1. 基本使用

```python
from datetime import datetime
from price_fetcher import initialize_fares_system

# 初始化系统（使用模拟数据）
cache, comparator = initialize_fares_system(
    db_path="railfair_fares.db",
    use_simulated_data=True
)

# 查询票价
result = comparator.compare_fares(
    origin="EUS",           # 伦敦 Euston
    destination="MAN",      # 曼彻斯特
    departure_date=datetime.now()
)

# 查看结果
print(f"Advance票:  {comparator.format_price(result.advance_price)}")
print(f"Off-Peak票: {comparator.format_price(result.off_peak_price)}")
print(f"Anytime票:  {comparator.format_price(result.anytime_price)}")
print(f"最便宜: {result.cheapest_type.value} - {comparator.format_price(result.cheapest_price)}")
print(f"可节省: {comparator.format_price(result.savings_amount)} ({result.savings_percentage:.1f}%)")
```

### 2. 使用真实NRDP数据（需要账户）

```python
from price_fetcher import initialize_fares_system

# 使用NRDP真实数据
cache, comparator = initialize_fares_system(
    db_path="railfair_fares.db",
    nrdp_email="your_email@example.com",
    nrdp_password="your_password",
    use_simulated_data=False
)

# 其他使用方式相同
result = comparator.compare_fares("EUS", "MAN", datetime.now())
```

---

## 🧪 运行测试

```bash
# 运行所有测试
pytest test_price_fetcher.py -v

# 带覆盖率报告
pytest test_price_fetcher.py --cov=price_fetcher --cov-report=term-missing

# 运行特定测试类
pytest test_price_fetcher.py::TestFareComparator -v
```

---

## 📊 核心数据结构

### 票种类型（TicketType）

| 票种 | 说明 | 价格范围 | 限制 |
|------|------|----------|------|
| ADVANCE | 提前票 | 最便宜 | 特定车次，不可退改 |
| OFF_PEAK | 非高峰票 | 中等 | 非高峰时段有效 |
| ANYTIME | 随时票 | 最贵 | 任何时段，最灵活 |
| SUPER_OFF_PEAK | 超级非高峰 | 很便宜 | 最闲时段 |
| SEASON | 季票 | 包月/年 | 通勤用户 |

### FareInfo（票价信息）

```python
@dataclass
class FareInfo:
    origin: str              # 起点CRS/NLC代码（如"EUS"或"1444"）
    destination: str         # 终点CRS/NLC代码（如"MAN"或"2968"）
    ticket_type: TicketType  # 票种
    ticket_class: TicketClass  # 标准座/头等座
    adult_fare: float        # 成人票价（便士）
    child_fare: float        # 儿童票价（便士）
    valid_from: datetime     # 有效起始日期
    valid_until: datetime    # 有效结束日期
    route_code: str          # 路线代码
    restriction_code: str    # 限制代码
    toc_code: str            # TOC代码（Train Operating Company，设置票价的铁路公司）
    toc_name: str            # TOC名称（如"Virgin Trains"）
    last_updated: datetime   # 最后更新时间
    data_source: str         # 数据来源（NRDP_REAL或NRDP_SIMULATED）
```

### FareComparison（对比结果）

```python
@dataclass
class FareComparison:
    origin: str
    destination: str
    departure_date: datetime
    
    # 价格（便士）
    advance_price: float        # Advance票价
    off_peak_price: float       # Off-Peak票价
    anytime_price: float        # Anytime票价
    
    # 推荐
    cheapest_type: TicketType   # 最便宜票种
    cheapest_price: float       # 最低价格
    savings_amount: float       # 节省金额
    savings_percentage: float   # 节省百分比
    
    # 缓存信息
    cached: bool               # 是否来自缓存
    cache_age_hours: float     # 缓存年龄（小时）
```

---

## 🎯 常见使用场景

### 场景1: 查询单条路线价格

```python
from datetime import datetime
from price_fetcher import initialize_fares_system

# 初始化
cache, comparator = initialize_fares_system("railfair.db", use_simulated_data=True)

# 查询
result = comparator.compare_fares(
    origin="EUS",
    destination="MAN",
    departure_date=datetime(2024, 12, 25, 9, 0)  # 圣诞节早上9点
)

# 显示结果
print(f"🚄 {result.origin} → {result.destination}")
print(f"💰 最便宜: {comparator.format_price(result.cheapest_price)}")
print(f"💸 最多可节省: {comparator.format_price(result.savings_amount)}")
```

### 场景2: 对比多条路线

```python
routes = [
    ("EUS", "MAN", "伦敦→曼彻斯特"),
    ("PAD", "BRI", "伦敦→布里斯托"),
    ("KGX", "EDN", "伦敦→爱丁堡"),
]

for origin, dest, name in routes:
    result = comparator.compare_fares(origin, dest, datetime.now())
    print(f"{name}: {comparator.format_price(result.cheapest_price)}")
```

### 场景3: 查询特定票种

```python
from price_fetcher import TicketType, TicketClass

# 只查询Advance票
fare = cache.get_fare(
    origin="EUS",
    destination="MAN",
    ticket_type=TicketType.ADVANCE,
    ticket_class=TicketClass.STANDARD
)

if fare:
    print(f"Advance票价: £{fare.adult_fare/100:.2f}")
else:
    print("未找到票价数据")
```

### 场景4: 批量查询（复用连接）

```python
from price_fetcher import FareCache, FareComparator

cache = FareCache("railfair.db")
comparator = FareComparator(cache)

# 批量查询（自动使用缓存）
routes = [("EUS", "MAN"), ("PAD", "BRI"), ("KGX", "EDN")]

for origin, dest in routes:
    result = comparator.compare_fares(origin, dest, datetime.now())
    print(f"{origin}→{dest}: {comparator.format_price(result.cheapest_price)}")

# 查看缓存统计
stats = cache.get_cache_stats()
print(f"缓存命中: {stats['total_hits']} 次")
print(f"命中率: {stats['hit_rate']:.1%}")
```

---

## 🔧 高级配置

### 1. 自定义缓存路径

```python
import os

# 使用自定义路径
custom_db = "/path/to/my/fares.db"
cache, comparator = initialize_fares_system(custom_db)

# 检查数据库大小
db_size = os.path.getsize(custom_db) / 1024  # KB
print(f"数据库大小: {db_size:.1f} KB")
```

### 2. 直接使用API客户端

```python
from price_fetcher import NRDPClient, FaresParser

# 创建客户端
client = NRDPClient(
    email="your_email@example.com",
    password="your_password"
)

# 获取token
token = client.authenticate()
print(f"Token: {token[:20]}...")

# 下载数据
zip_data = client.download_fares_data(save_path="fares.zip")
print(f"下载完成: {len(zip_data)} bytes")

# 解析数据
parser = FaresParser(zip_data)
fares = parser.parse_simplified_fares(limit=100)
print(f"解析到 {len(fares)} 条票价数据")
```

### 3. 手动管理缓存

```python
from price_fetcher import FareCache, FareInfo, TicketType, TicketClass
from datetime import datetime, timedelta

cache = FareCache("railfair.db")

# 添加自定义票价
custom_fare = FareInfo(
    origin="XXX",
    destination="YYY",
    ticket_type=TicketType.ADVANCE,
    ticket_class=TicketClass.STANDARD,
    adult_fare=5000,  # £50.00
    child_fare=2500,
    valid_from=datetime.now(),
    valid_until=datetime.now() + timedelta(days=30),
    route_code=None,
    restriction_code="CUSTOM",
    last_updated=datetime.now(),
    data_source="MANUAL"
)

# 缓存
cache.cache_fares([custom_fare])

# 查询
fare = cache.get_fare("XXX", "YYY", TicketType.ADVANCE)
print(f"票价: £{fare.adult_fare/100:.2f}")
```

---

## 📈 性能优化建议

### 1. 预热缓存

```python
# 在服务启动时预热缓存
def warm_up_cache(cache, common_routes):
    """预热常用路线缓存"""
    for origin, dest in common_routes:
        for ticket_type in [TicketType.ADVANCE, TicketType.OFF_PEAK, TicketType.ANYTIME]:
            cache.get_fare(origin, dest, ticket_type)

common_routes = [
    ("EUS", "MAN"),
    ("PAD", "BRI"),
    ("KGX", "EDN"),
]

warm_up_cache(cache, common_routes)
```

### 2. 批量查询

```python
# ✅ 好：复用连接
cache = FareCache("railfair.db")
comparator = FareComparator(cache)

for route in routes:
    result = comparator.compare_fares(*route, datetime.now())

# ❌ 差：每次创建新连接
for route in routes:
    cache, comparator = initialize_fares_system("railfair.db")
    result = comparator.compare_fares(*route, datetime.now())
```

### 3. 监控缓存效率

```python
def print_cache_efficiency(cache):
    """打印缓存效率报告"""
    stats = cache.get_cache_stats()
    
    print("缓存效率报告:")
    print(f"  总记录: {stats['total_records']}")
    print(f"  总查询: {stats['total_hits']}")
    print(f"  命中率: {stats['hit_rate']:.1%}")
    
    print(f"\n热门路线:")
    for origin, dest, hits in stats['top_routes'][:5]:
        print(f"  {origin}→{dest}: {hits} 次")

# 使用
print_cache_efficiency(cache)
```

---

## 🚨 常见问题

### Q1: 价格单位是什么？

**A:** 所有价格存储为**便士**（pence）。

```python
# 存储: 2500便士
fare.adult_fare = 2500

# 显示: £25.00
comparator.format_price(2500)  # "£25.00"

# 转换
pounds = pence / 100
pence = pounds * 100
```

### Q2: 如何更新票价数据？

**A:** 系统会自动检查数据是否需要更新（默认7天），也可以手动更新：

```python
# 方法1: 重新初始化（会自动检查是否需要更新）
cache, comparator = initialize_fares_system(
    "railfair.db",
    nrdp_email="your@email.com",
    nrdp_password="password",
    use_simulated_data=False
)
# 系统会：
# - 检查ZIP文件是否存在且新鲜（<7天）
# - 检查数据库是否有数据
# - 如果需要，自动下载并解析最新数据

# 方法2: 手动下载并缓存
client = NRDPClient(email, password)
zip_data, last_modified = client.download_fares_data(save_path="fares_data.zip")
parser = FaresParser(zip_data)
fares = parser.parse_all_fares()  # 解析完整数据（包括.FFL, .NFO, .NDF文件）
cache.cache_fares(fares)

# 方法3: 强制更新（删除ZIP文件或数据库）
import os
if os.path.exists("fares_data.zip"):
    os.remove("fares_data.zip")
# 下次初始化时会自动重新下载
```

**数据更新频率**：
- Fares数据每周更新一次（NRDP官方）
- 系统建议每天检查一次更新
- 缓存数据会保留，直到检测到新版本

### Q3: NRDP认证失败怎么办？

**A:** 系统会自动降级到模拟数据：

```python
try:
    cache, comparator = initialize_fares_system(
        "railfair.db",
        nrdp_email="wrong@email.com",
        nrdp_password="wrong_password",
        use_simulated_data=False
    )
except Exception as e:
    print(f"NRDP失败: {e}")
    # 自动使用模拟数据
    cache, comparator = initialize_fares_system(
        "railfair.db",
        use_simulated_data=True
    )
```

### Q4: 如何清空缓存？

**A:** 删除数据库文件：

```python
import os

db_path = "railfair_fares.db"

# 删除数据库
if os.path.exists(db_path):
    os.remove(db_path)

# 重新初始化
cache, comparator = initialize_fares_system(db_path)
```

### Q5: 支持哪些车站代码？

**A:** 系统自动支持CRS代码（3个字母）和NLC代码（4位数字），会自动转换：

```python
# 常用车站CRS代码
stations = {
    "EUS": "London Euston",        # NLC: 1444
    "PAD": "London Paddington",    # NLC: 3087
    "KGX": "London Kings Cross",   # NLC: 0526
    "VIC": "London Victoria",      # NLC: 0045
    "MAN": "Manchester Piccadilly", # NLC: 2968
    "BHM": "Birmingham New Street", # NLC: 1072
    "BRI": "Bristol Temple Meads",  # NLC: 3231
    "EDN": "Edinburgh Waverley",    # NLC: 2373
    "BTN": "Brighton",              # NLC: 5269
}

# 查询示例（系统会自动转换CRS到NLC）
result = comparator.compare_fares("EUS", "MAN", datetime.now())

# 也可以直接使用NLC代码
result = comparator.compare_fares("1444", "2968", datetime.now())
```

**注意**：系统会自动从Locations文件（.LOC）加载CRS到NLC的映射，支持3,400+个车站的自动转换。

---

## 💡 最佳实践

### 1. 始终检查结果

```python
result = comparator.compare_fares("EUS", "MAN", datetime.now())

if result.cached:
    print(f"✅ 来自缓存 (年龄: {result.cache_age_hours:.1f}小时)")
else:
    print("⚠️  未找到缓存数据")

# 检查数据来源
advance_fare = cache.get_fare("EUS", "MAN", TicketType.ADVANCE)
if advance_fare:
    print(f"数据来源: {advance_fare.data_source}")
    if advance_fare.toc_name:
        print(f"票价制定者: {advance_fare.toc_name}")
    
# 注意：异常价格（> £1000）会被自动过滤，显示为"不可用"
if result.advance_price and result.advance_price > 0:
    print(f"Advance: {comparator.format_price(result.advance_price)}")
else:
    print("Advance: 不可用")
```

### 2. 使用上下文管理器

```python
# ✅ 推荐：自动清理
from price_fetcher import FareCache

def query_fares(db_path, routes):
    cache = FareCache(db_path)
    comparator = FareComparator(cache)
    
    results = []
    for origin, dest in routes:
        result = comparator.compare_fares(origin, dest, datetime.now())
        results.append(result)
    
    return results
```

### 3. 记录缓存统计

```python
import logging

def log_cache_stats(cache):
    stats = cache.get_cache_stats()
    
    logging.info(f"缓存统计: {stats['total_records']}条记录")
    logging.info(f"命中率: {stats['hit_rate']:.1%}")
    
    for ticket_type, count in stats['by_ticket_type'].items():
        logging.info(f"  {ticket_type}: {count}条")
```

---

## 🔗 相关文档

### Day 9 文档
- [price_fetcher.py](computer:///mnt/user-data/outputs/price_fetcher.py) - 核心模块
- [test_price_fetcher.py](computer:///mnt/user-data/outputs/test_price_fetcher.py) - 测试套件
- [DAY9_DELIVERY_SUMMARY.md](computer:///mnt/user-data/outputs/DAY9_DELIVERY_SUMMARY.md) - 详细文档

### 相关模块
- Day 8: predictor.py - 延误预测引擎
- Day 10-11: FastAPI后端（待开发）

---

## 🎯 完整示例

### 示例1: 完整查询流程

```python
from datetime import datetime
from price_fetcher import initialize_fares_system

def main():
    # 1. 初始化系统
    print("初始化票价系统...")
    cache, comparator = initialize_fares_system(
        "railfair.db",
        use_simulated_data=True
    )
    
    # 2. 查询票价
    print("\n查询: 伦敦 → 曼彻斯特")
    result = comparator.compare_fares(
        origin="EUS",
        destination="MAN",
        departure_date=datetime(2024, 12, 25, 9, 0)
    )
    
    # 3. 显示结果
    print(f"\n票种对比:")
    print(f"  Advance:  {comparator.format_price(result.advance_price)}")
    print(f"  Off-Peak: {comparator.format_price(result.off_peak_price)}")
    print(f"  Anytime:  {comparator.format_price(result.anytime_price)}")
    
    print(f"\n💰 推荐: {result.cheapest_type.value.title()}")
    print(f"   价格: {comparator.format_price(result.cheapest_price)}")
    print(f"   节省: {comparator.format_price(result.savings_amount)}")
    print(f"   节省率: {result.savings_percentage:.1f}%")
    
    # 4. 缓存统计
    stats = cache.get_cache_stats()
    print(f"\n📊 缓存统计:")
    print(f"   总记录: {stats['total_records']}")
    print(f"   总查询: {stats['total_hits']}")
    print(f"   命中率: {stats['hit_rate']:.1%}")

if __name__ == "__main__":
    main()
```

### 示例2: 与预测引擎结合

```python
from datetime import datetime
from predictor import DelayPredictor, PredictionInput
from price_fetcher import initialize_fares_system

def combined_recommendation(db_path, origin, dest, departure_time):
    """结合延误预测和票价的综合推荐"""
    
    # 1. 延误预测
    predictor = DelayPredictor(db_path)
    prediction = predictor.predict(PredictionInput(
        origin_crs=origin,
        destination_crs=dest,
        departure_datetime=departure_time
    ))
    
    # 2. 票价查询
    cache, comparator = initialize_fares_system(
        f"{db_path}_fares.db",
        use_simulated_data=True
    )
    fares = comparator.compare_fares(origin, dest, departure_time)
    
    # 3. 综合推荐
    print(f"🚄 {origin} → {dest}")
    print(f"\n📊 延误预测:")
    print(f"   准点率: {prediction.on_time_probability:.1%}")
    print(f"   预期延误: {prediction.expected_delay_minutes:.1f}分钟")
    
    print(f"\n💰 票价对比:")
    print(f"   最便宜: {comparator.format_price(fares.cheapest_price)}")
    print(f"   可节省: {comparator.format_price(fares.savings_amount)}")
    
    # 4. 决策建议
    if prediction.on_time_probability > 0.8 and fares.cheapest_type.value == "advance":
        print(f"\n✅ 推荐: Advance票")
        print(f"   理由: 准点率高 + 价格最优")
    elif prediction.on_time_probability < 0.5:
        print(f"\n⚠️  推荐: Off-Peak/Anytime票")
        print(f"   理由: 延误风险高，建议选灵活票种")
    else:
        print(f"\n👍 推荐: {fares.cheapest_type.value.title()}票")
        print(f"   理由: 性价比最优")

# 使用示例
combined_recommendation(
    "railfair.db",
    "EUS", "MAN",
    datetime(2024, 12, 25, 9, 0)
)
```

---

*更新于: 2024-11-16*  
*版本: Day 9*  
*作者: Vanessa @ RailFair*