# RailFair Day 8 - 快速开始指南 🚀

## 📁 文件清单

```
Day 8 交付文件:
├── predictor.py              (25KB, 728行) - 核心预测引擎 + 测试代码
└── DAY8_DELIVERY_SUMMARY.md  (13KB)        - 交付总结
```

---

## ⚡ 快速使用

### 1. 基本预测

```python
from datetime import datetime
from predictor import predict_delay

# 预测早高峰 Banbury 到 Manchester
result = predict_delay(
    db_path="data/railfair.db",
    origin="BAN",
    destination="MAN", 
    departure_datetime=datetime(2024, 12, 20, 9, 0)
)

print(f"准点率: {result.on_time_probability:.1%}")
print(f"预期延误: {result.expected_delay_minutes:.1f}分钟")
print(f"置信度: {result.confidence.value}")
```

### 2. 使用预测器类

```python
from predictor import DelayPredictor, PredictionInput
from datetime import datetime

with DelayPredictor("data/railfair.db") as predictor:
    # 创建输入
    input_params = PredictionInput(
        origin_crs="BAN",
        destination_crs="MAN",
        departure_datetime=datetime(2024, 12, 20, 9, 0),
        toc=None
    )
    
    # 执行预测
    result = predictor.predict(input_params)
    
    # 获取用户友好解释
    explanation = predictor.get_prediction_explanation(result)
    print(explanation)
```

---

## 🧪 运行测试

```bash
# 运行测试（使用真实数据库）
python3 predictor.py
```

测试包括：
- ✅ 基础预测测试
- ✅ 不同时段预测对比
- ✅ 工作日 vs 周末对比
- ✅ 降级策略测试
- ✅ 性能测试（<100ms验证）
- ✅ 预测解释测试

---

## 📊 核心数据结构

### PredictionInput（输入）

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| origin_crs | str | ✅ | 起点CRS代码（如"EUS"） |
| destination_crs | str | ✅ | 终点CRS代码（如"MAN"） |
| departure_datetime | datetime | ✅ | 计划出发时间 |
| toc | str | ❌ | TOC运营商代码（如"VT"） |

### PredictionResult（输出）

| 字段 | 类型 | 说明 |
|------|------|------|
| on_time_probability | float | 准点概率(0-1) |
| delay_5_probability | float | 5分钟内延误概率 |
| expected_delay_minutes | float | 预期延误分钟数 |
| confidence | ConfidenceLevel | 置信度(HIGH/MEDIUM/LOW/VERY_LOW) |
| sample_size | int | 历史样本数量 |
| is_degraded | bool | 是否使用降级策略 |
| reliability_score | float | 可靠性评分(0-100) |

---

## 🎯 使用场景

### 场景1: 查询具体班次

```python
# 用户输入: "2024年12月20日9:00从Banbury到Manchester"
result = predict_delay("data/railfair.db", "BAN", "MAN", 
                       datetime(2024, 12, 20, 9, 0))

if result.on_time_probability > 0.8:
    print("✅ 这趟车很可能准点")
elif result.is_degraded:
    print("⚠️  数据有限，预测仅供参考")
else:
    print(f"⏱️  预计延误 {result.expected_delay_minutes:.0f} 分钟")
```

### 场景2: 比较不同时段

```python
times = [6, 9, 14, 18, 21]  # 不同小时
for hour in times:
    dt = datetime(2024, 12, 20, hour, 0)
    result = predict_delay("data/railfair.db", "BAN", "MAN", dt)
    print(f"{hour:02d}:00 - 准点率 {result.on_time_probability:.1%}")
```

### 场景3: 批量预测

```python
from predictor import DelayPredictor, PredictionInput
from datetime import datetime, timedelta

# 未来7天，每天9:00的预测
with DelayPredictor("data/railfair.db") as predictor:
    for day in range(7):
        dt = datetime.now() + timedelta(days=day)
        dt = dt.replace(hour=9, minute=0)
        
        result = predictor.predict(PredictionInput(
            origin_crs="BAN",
            destination_crs="MAN", 
            departure_datetime=dt,
            toc=None
        ))
        
        print(f"Day {day+1}: {result.on_time_probability:.1%}")
```

---

## 🔧 调整时间因子

如需自定义时间调整因子：

```python
predictor = DelayPredictor("data/railfair.db")

# 修改时段调整
from predictor import TimeSlot, DayType
predictor.time_adjustments[TimeSlot.MORNING_PEAK] = 1.25  # 从1.15改为1.25

# 修改日期调整
predictor.day_type_adjustments[DayType.WEEKEND] = 0.85   # 从0.90改为0.85
```

---

## 📈 性能指标

| 指标 | 数值 | 说明 |
|------|------|------|
| 响应时间 | 5.10ms | 单次预测平均时间（真实数据库） |
| QPS | 196/s | 每秒查询数 |
| 测试场景 | 6个 | 真实数据测试场景 |
| 数据库 | 真实 | 使用 data/railfair.db (210条路线) |

---

## 🚨 常见问题

### Q1: 数据库路径错误
```python
# ❌ 错误
predictor = DelayPredictor("wrong_path.db")

# ✅ 正确
import os
db_path = os.path.join(os.getcwd(), "data", "railfair.db")
if os.path.exists(db_path):
    predictor = DelayPredictor(db_path)
else:
    print(f"❌ 数据库文件不存在: {db_path}")
```

### Q2: 时区问题
```python
# ✅ 使用本地时间（UK时区）
from datetime import datetime
dt = datetime(2024, 12, 24, 8, 30)  # 本地时间

# ⚠️  注意：系统假设所有时间为UK时间
```

### Q3: 降级预测
```python
result = predict_delay("data/railfair.db", "XXX", "YYY", datetime.now())

if result.is_degraded:
    print(f"⚠️  {result.degradation_reason}")
    # 决定是否使用降级结果
```

### Q4: 数据库不存在
```python
# 确保已运行 calculate_stats.py 生成统计数据
# 数据库文件应该在 data/railfair.db
```

---

## 🔗 依赖关系

### Day 8 依赖：
- ✅ Day 6-7: 统计预计算系统（route_statistics表）

### Day 8 支持：
- Day 9: 价格对比功能
- Day 10-11: FastAPI后端
- Day 12: 推荐算法

---

## 📝 下一步

1. **Day 9**: 价格获取与缓存
2. **Day 10**: FastAPI后端开发
3. **Day 12**: 结合预测+价格的推荐算法

---

## 💡 最佳实践

### 1. 使用上下文管理器
```python
# ✅ 推荐：自动关闭连接
with DelayPredictor("data/railfair.db") as predictor:
    result = predictor.predict(input_params)

# ❌ 避免：手动管理连接
predictor = DelayPredictor("data/railfair.db")
result = predictor.predict(input_params)
predictor.close()  # 容易忘记
```

### 2. 检查降级状态
```python
result = predict_delay(...)

if result.is_degraded:
    # 向用户显示警告
    show_warning(result.degradation_reason)
    
if result.confidence == ConfidenceLevel.VERY_LOW:
    # 建议用户查看替代方案
    suggest_alternatives()
```

### 3. 批量操作优化
```python
# ✅ 复用连接
with DelayPredictor("data/railfair.db") as predictor:
    for route in routes:
        result = predictor.predict(route)

# ❌ 每次创建新连接（效率较低）
for route in routes:
    result = predict_delay("data/railfair.db", ...)  # 每次新建连接
```

### 4. 使用真实数据测试
```bash
# 运行内置测试（使用真实数据库）
python3 predictor.py
```

---

*更新于: 2024-11-16*  
*版本: Day 8*  
*作者: Vanessa @ RailFair*
